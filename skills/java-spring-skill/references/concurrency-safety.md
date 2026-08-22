# Concurrency-Safe Mutations (shared counters/resources)

Applies whenever multiple concurrent requests read-then-write the same shared, bounded resource: a
counter, balance, inventory count, rate limit, or any numeric field with an invariant that must never be
violated under concurrent access (e.g. "never goes below zero", "never exceeds a limit").

## The failure mode: check-then-act (TOCTOU)

```java
// UNSAFE — race condition between read and write
Resource r = repository.findById(id).orElseThrow();
if (r.getRemaining() >= amount) {
    r.setRemaining(r.getRemaining() - amount);
    repository.save(r);
}
```

Between the read and the write, another concurrent transaction can do the exact same read, see the same
"still available" value, and also proceed — both commit, the invariant is silently violated (overselling,
negative balance, exceeded limit). This is invisible in manual testing and under low load; it only shows up
under concurrency, which is exactly why it must be designed against up front, not discovered in production.

## Pattern 1 — Atomic conditional UPDATE (default choice)

Express the check as the `WHERE` clause of a single UPDATE statement, so the read-decide-write happens
inside the database engine as one atomic step:

```java
@Modifying(clearAutomatically = true, flushAutomatically = true)
@Query("UPDATE Resource r SET r.remaining = r.remaining - :amount WHERE r.id = :id AND r.remaining >= :amount")
int decrementIfAvailable(@Param("id") String id, @Param("amount") int amount);
```

```java
@Transactional
public void consume(String resourceId, int amount) {
    int updated = repository.decrementIfAvailable(resourceId, amount);
    if (updated == 0) {
        throw new ResourceExhaustedException(resourceId);
    }
}
```

Why this is correct with no explicit locking: an `UPDATE` statement always performs a "current read" —
it reads the latest **committed** value and locks the row before evaluating the `WHERE` clause, regardless
of the transaction's isolation level (`READ COMMITTED` or `REPEATABLE READ` — this differs from a plain
`SELECT`, which under `REPEATABLE READ` can return a stale snapshot). There is no window between decision
and write for another transaction to interleave. This is the default choice for the vast majority of
shared-counter problems: single round trip, no explicit lock hint, highest throughput.

This only works when the entire decision fits in a `WHERE` clause. If eligibility depends on business logic
that can't be expressed as a row-level condition, use Pattern 2 instead.

## Pattern 2 — Pessimistic lock (`SELECT ... FOR UPDATE`)

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT r FROM Resource r WHERE r.id = :id")
Optional<Resource> findByIdForUpdate(@Param("id") String id);
```

Use only when the eligibility decision requires reading and reasoning over data that a single `WHERE`
clause can't express (e.g. cross-row rules, multi-step computation). The lock is held for the entire
transaction, not just the query — so the transaction must do nothing else slow while holding it, and in
particular **must never call an external service or perform other network I/O between acquiring the lock
and committing** (that connection-holding failure mode is covered in `references/data-jpa.md`). Also watch
lock-acquisition order: if a transaction ever needs to lock more than one row, every code path must acquire
those locks in the same fixed order, or concurrent transactions can deadlock waiting on each other in a
cycle.

## Pattern 3 — Optimistic lock (`@Version`) + retry

Appropriate for low-contention resources (the row is rarely written concurrently). Under high contention on
a hot row, this degrades into a retry storm — each collision means a wasted round trip and a re-attempt,
and it gets worse as contention increases, unlike Pattern 1's throughput which is stable under load. If
using this, cap the retry count and back off between attempts; don't retry unboundedly.

## Choosing a pattern

| Situation | Pattern |
|---|---|
| Decision is a simple threshold/comparison on the row itself | Atomic conditional UPDATE (Pattern 1) — default |
| Decision needs cross-row/complex logic that can't fit a `WHERE` clause | Pessimistic lock (Pattern 2) |
| Row is rarely contended, occasional retry is acceptable | Optimistic lock + `@Version` (Pattern 3) |
| Row is extremely hot (viral traffic) even with Pattern 1 | Consider sharding the counter across multiple rows, only after measuring the hotspot is real |

## Idempotency — a separate problem from concurrency

Preventing overselling between *different* concurrent requests does not prevent the *same* logical request
from being applied twice (client retry after a timeout, double-submit). Any mutating operation the client
might retry needs an idempotency key, checked before mutating and recorded with a `UNIQUE` constraint as
the authoritative backstop:

```java
@Transactional
public void consume(String resourceId, int amount, String idempotencyKey) {
    if (operationRepository.existsByIdempotencyKey(idempotencyKey)) {
        return; // already applied — return the prior result, don't mutate again
    }
    if (repository.decrementIfAvailable(resourceId, amount) == 0) {
        throw new ResourceExhaustedException(resourceId);
    }
    operationRepository.save(new Operation(resourceId, amount, idempotencyKey));
}
```

## Migrating from pessimistic lock to an atomic conditional UPDATE

This is a common refactor once a `SELECT ... FOR UPDATE` site turns out to only need a simple threshold
check. It's safe, but only once every one of these holds:

1. **Single writer path.** Every place in the codebase that mutates the field goes through the new
   `@Modifying` query — a `load entity → mutate field → save()` path left over anywhere reintroduces the
   original race, silently.
2. **No stale entity in the same transaction.** A bulk `@Modifying` query writes directly to the database
   and does not update Hibernate's persistence context (L1 cache). If the same transaction already loaded
   that entity earlier (e.g. `findById` for a response DTO) and something later calls `save()` on that
   now-stale in-memory copy, it silently overwrites the DB's updated value. Use
   `@Modifying(clearAutomatically = true, flushAutomatically = true)`, and avoid loading the same entity
   elsewhere in a transaction that also does the atomic update.
3. **The full eligibility decision fits in the `WHERE` clause.** If it doesn't, keep the pessimistic lock
   for that specific case (migration doesn't have to be all-or-nothing).

Verify the migration with a concurrency test rather than by inspection — this is the only way to actually
prove the invariant holds under contention:

```java
@Test
void concurrentConsume_neverExceedsAvailable() throws Exception {
    repository.save(new Resource(id, /* remaining */ 100));
    int attempts = 500;
    var executor = Executors.newFixedThreadPool(50);
    var latch = new CountDownLatch(attempts);
    var successCount = new AtomicInteger();

    for (int i = 0; i < attempts; i++) {
        executor.submit(() -> {
            try {
                service.consume(id, 1, UUID.randomUUID().toString());
                successCount.incrementAndGet();
            } catch (ResourceExhaustedException ignored) {
            } finally {
                latch.countDown();
            }
        });
    }
    latch.await();

    assertThat(successCount.get()).isEqualTo(100); // exactly the starting amount, never more
    assertThat(repository.findById(id).orElseThrow().getRemaining()).isEqualTo(0);
}
```

Run this against both the old and new implementation before cutting over, and re-run it several times —
timing-dependent bugs don't always reproduce on the first run.

## Quick Reference

| Concern | Do this |
|---|---|
| Shared counter, simple threshold check | Atomic conditional `UPDATE ... WHERE` (Pattern 1) |
| Complex cross-row eligibility logic | Pessimistic lock, keep the transaction short, no external calls while holding it |
| Low-contention resource | Optimistic lock (`@Version`) + bounded retry |
| Multiple rows locked/updated in one transaction | Fixed, consistent lock-acquisition order everywhere — prevents deadlock |
| Client may retry the same logical request | Idempotency key + `UNIQUE` constraint, checked before mutating |
| Migrating pessimistic lock → atomic UPDATE | Single writer path, clear the persistence context, verify with a concurrency test |
| Proving the invariant holds | A real concurrent-threads test — never "looks right" from code review alone |
