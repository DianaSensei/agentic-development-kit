# Code Design Heuristics

Principles below the class/interface level — how to shape logic, module boundaries, and dependencies day
to day. Unlike SOLID, several of these are explicitly heuristics, not laws: they trade off against each
other, and knowing when *not* to apply one is as important as applying it.

Jump to the heuristic matching the concern under review:

| Heuristic | Use when reviewing |
| --- | --- |
| [DRY](#dry--dont-repeat-yourself) · [The Reuse Trap](#the-reuse-trap--when-a-shared-function-accretes-into-a-liability) | Duplicated knowledge; or a shared function that has accreted flags/branches per caller |
| [KISS](#kiss--keep-it-simple) · [YAGNI](#yagni--you-arent-gonna-need-it) | Unjustified complexity; speculative generality |
| [Coupling and Cohesion](#coupling-and-cohesion) | Modules that break each other, or do unrelated things |
| [Law of Demeter](#law-of-demeter-principle-of-least-knowledge) | Chains reaching through object internals |
| [Composed Method / SLAP](#composed-method--single-level-of-abstraction-principle-slap) | Method decomposition, call depth, cross-calling/cycles |
| [Command-Query Separation & TOCTOU](#command-query-separation--re-validation-toctou) | A check that runs more than once — duplication vs. race-condition safeguard |
| [Composition Over Inheritance](#composition-over-inheritance) | Deep or forced class hierarchies |
| [Separation of Concerns](#separation-of-concerns) | One unit mixing business logic, I/O, and presentation |
| [Encapsulate Invariants, Not Cost](#encapsulate-invariants-not-cost) | A cheap-looking method that hides expensive work |

## DRY — Don't Repeat Yourself

**Definition**: Every piece of knowledge should have a single, unambiguous, authoritative representation
in the system.

**Symptom of violation**: The same business rule (a tax rate, a validation regex, a pricing formula)
is copy-pasted in multiple places; fixing a bug requires finding and patching every copy.

**Fix**: Extract the rule to one place; everything else calls it.

**Critical caution — duplication vs. the wrong abstraction**: DRY is about *knowledge*, not *code that
looks similar*. Two pieces of code that are textually similar today but represent different business
rules that will evolve independently are not a DRY violation — merging them creates a false coupling
that breaks the moment one rule changes and the other doesn't. When in doubt: "duplication is far
cheaper than the wrong abstraction" (Sandi Metz). Prefer to wait for a third occurrence before
abstracting (rule of three), unless the duplicated logic is a single well-understood invariant (e.g. a
formula, a regex) that is *obviously* one piece of knowledge from the start.

### The Reuse Trap — When a Shared Function Accretes Into a Liability

This is the wrong-abstraction failure mode above, made concrete: a function starts serving one caller
cleanly, then each new caller with a *similar-but-not-identical* need gets accommodated by bolting on a
parameter or a branch, rather than by asking whether it's really the same knowledge. Repeated enough
times, the function ends up serving many masters, is depended on everywhere, and is simultaneously
too risky to change and too tangled to fully understand.

**Symptom checklist** — treat two or more of these together on the same function as a strong signal, not
just one in isolation:
- **Boolean/enum flag parameters that branch internal behavior** — `process(order, true, false)` is
  unreadable at the call site without opening the function's body to learn what `true` means.
- **A parameter list that has grown over time** (2 params at creation, 6-8 now) — each addition is
  usually one more caller's need bolted on rather than designed in.
- **Comments inside the shared function calling out a specific caller** (`// only used by
  ExpressCheckout, be careful here`) — direct evidence the function is carrying concerns that belong to
  one caller, not all of them.
- **High fan-in (many call sites) *combined with* high internal branching** — either alone is fine (a
  simple, heavily-reused utility; or a complex-but-isolated core algorithm with one caller). Both
  together means many callers depend on behavior that's hard to fully verify, so every change risks
  every caller, and every caller must be re-tested for every change to any branch — including branches
  that caller never actually exercises.
- **Different callers exercise disjoint subsets of the function's branches** — a sign it is, in
  substance, several unrelated functions sharing one name.

**Concrete costs this produces** — the three the symptom checklist above exists to prevent:
- *Hard to control*: changing the function means reasoning about every existing caller, not just the one
  motivating the change.
- *Performance*: a function generalized to satisfy its most demanding caller often does extra work
  (eager-loads data, runs validation) that simpler callers pay for without needing.
- *Hard to trace*: debugging a specific caller's flow means landing inside a function whose branches you
  must mentally filter by "which of these apply to my caller" — reading it out of context of who called
  it, which is itself a SLAP violation, since the function is no longer at one coherent level of
  abstraction.

**Fix — "un-DRY" with intent**:
1. Inline the shared function back into each caller (temporarily; duplication is fine as an intermediate
   state).
2. Look at what's *actually* identical across callers now that they're side by side — usually a small,
   branch-free core.
3. Extract only that true common core as a small function; leave each caller's distinct orchestration in
   the caller itself, not folded back into the shared function via a new flag.
4. If structure (not behavior) genuinely needs to be shared across callers with differing behavior, pass
   a Strategy/Parameter Object instead of a boolean flag — the branch then lives visibly at the call
   site, not hidden inside the shared function.

```java
// Before — one function accreting every caller's special case
Order process(Order order, boolean isExpress, boolean skipInventoryCheck, String discountCode) { ... }

// After — small shared core, orchestration stays at each caller
Order processStandard(Order order) { return applyCore(order); }
Order processExpress(Order order) { return applyCore(order).withExpediting(); }
Order processPromo(Order order, String discountCode) { return applyCore(order).withDiscount(discountCode); }
private Order applyCore(Order order) { ... } // the genuinely shared, branch-free logic
```

**When NOT to over-apply**: A function with several parameters that are plain *data* (not control-flow
flags) serving one coherent purpose is not this smell — the flag here is specifically one that changes
*which code path runs*, not one that changes *what data is processed*.

## KISS — Keep It Simple

**Definition**: Prefer the simplest design that correctly solves the actual problem; complexity must be
justified by a real requirement, not by anticipated cleverness.

**Symptom of violation**: A solution uses a design pattern, framework feature, or abstraction layer that
a reader has to research before understanding what 5 lines of straightforward code would have shown
directly.

**Fix**: Ask "what is the simplest thing that could work here, given the actual (not imagined)
requirements?" and default to it. Add complexity only when a concrete, current requirement demands it.

**When it conflicts with DRY/OCP**: KISS sometimes argues *against* an abstraction that DRY or OCP would
suggest. When two occurrences of logic are simple and the abstraction would be more complex than the
duplication it removes, KISS wins — don't abstract for abstraction's sake.

## YAGNI — You Aren't Gonna Need It

**Definition**: Don't build capability for a requirement that doesn't exist yet, no matter how likely it
seems.

**Symptom of violation**: Configuration options, extension points, or abstraction layers exist with
exactly one implementation/value, "in case we need to support X later."

**Fix**: Build for the requirements that exist now. When the second real requirement actually shows up,
refactor — it's usually cheaper than the carrying cost of unused flexibility, and by then you know the
*actual* shape of the variation instead of guessing it.

**Where YAGNI does not apply**: Requirements explicitly stated as near-term (an NFR, a known roadmap
item within the current milestone) are not "hypothetical" — YAGNI targets *speculative* generality, not
documented near-term scope.

## Coupling and Cohesion

**Coupling** — how much one module knows about / depends on another's internals. **Cohesion** — how
closely the responsibilities within one module relate to each other. The goal: **high cohesion, low
coupling** — modules that are internally focused and externally independent.

| | Low Cohesion | High Cohesion |
| --- | --- | --- |
| **High Coupling** | Worst — tangled *and* unfocused | Common but limiting — focused units, still tightly wired together |
| **Low Coupling** | Fragile — independent but each module does unrelated things | Best — focused units, changeable independently |

**Symptom of tight coupling**: Changing module A's internal implementation (not its public contract)
breaks module B's tests.

**Symptom of low cohesion**: A module's methods each operate on a different, non-overlapping subset of
its own fields — a sign it's really several modules wearing one name.

**Fix for coupling**: Depend on the smallest interface that satisfies the need (see DIP, ISP); pass data,
not the object that produced it, when only the data is needed.

**Fix for cohesion**: Group by what changes together and what data is actually shared, not by technical
layer alone (e.g. not just "all validators in one file" if they validate unrelated domains).

## Law of Demeter (Principle of Least Knowledge)

**Definition**: A method should only talk to its immediate collaborators — not reach through one object
to get to another ("don't talk to strangers").

**Symptom of violation**: A chain like `order.getCustomer().getAddress().getCity()` — the caller now
depends on the internal structure of `Customer` and `Address`, not just `Order`.

```
// Violates LoD — caller depends on 3 levels of internal structure
city = order.getCustomer().getAddress().getCity();

// Follows LoD — Order exposes what callers need
city = order.getShippingCity();
```

**Concrete failure mode this prevents**: A refactor of `Address`'s internal structure breaking dozens of
unrelated call sites across the codebase that only wanted the city.

**When NOT to over-apply**: Fluent builders and simple data-transfer chains (`list.stream().map(...)`)
are not Law of Demeter violations — the rule targets chains that traverse *domain object* internals to
reach unrelated behavior, not standard library composition.

## Composed Method / Single Level of Abstraction Principle (SLAP)

**Definition**: A method's body should sit at one consistent level of abstraction — either it
orchestrates (calls other well-named methods) or it does concrete work, never a mix of both in the same
body. A well-composed method reads like a table of contents; the detail lives one level down, in methods
small and honestly named enough to be trusted without opening them.

**Symptom of violation**: A method that both calls out to other methods *and* has raw loops/conditionals
manipulating fields inline — the reader can't tell, without reading closely, which parts are the "real"
logic and which are just orchestration.

```java
// Orchestrator — one level of abstraction, reads as a sequence of named steps
public Order placeOrder(PlaceOrderCommand cmd) {
    validateCommand(cmd);
    var priced   = calculatePricing(cmd.items());
    var reserved = reserveInventory(cmd.items());
    return orderRepository.save(buildOrder(cmd, priced, reserved));
}
```

**Fix**: Extract Method until each method either orchestrates or computes, not both. Depth of the
resulting call tree is a *symptom*, not a target to hit — 2-3 levels is typical for a well-decomposed use
case because that's what naturally falls out of applying SRP recursively (an orchestrator calls steps;
a step complex enough to have sub-steps becomes its own small orchestrator one level down), not because
depth itself was the goal.

**The forcing tests for "did I decompose at the right boundary"**:
- **Name-able**: can each extracted method get a clear, honest name (no `and`, no `processHelper2`)?
- **Testable in isolation**: can it be unit tested without standing up several layers above it?

If either answer is "no," the boundary is probably wrong, not just under-named.

**A sharper failure mode than depth — cross-calling / cycles**: Depth alone produces a *tree*, which is
easy to trace top-down. Two methods or modules calling into *each other* (A calls B, B calls back into
A, directly or through an intermediary) produces a *cycle* — there's no longer a clear place to start
reading, and it's a common precursor to a real circular dependency between classes/modules. This is a
worse smell than raw nesting depth; when spotted, either merge the two into one cohesive unit, extract
the shared concern into a third collaborator that both call downward into (never sideways/backward), or
invert the dependency (an event/callback) so the call graph becomes a DAG again.

**Other symptoms worth naming explicitly when reviewing a deep or tangled call chain**:
- **Feature Envy** — a method reaches repeatedly into another module's data to do that module's job;
  move the method to where the data lives.
- **Message chain** — see Law of Demeter above.
- **Pass-through layer** — a method that only forwards to one other method, adding no real behavior;
  collapse it unless it exists as a deliberate seam (e.g. the port in Ports & Adapters).

**When NOT to over-apply**: Don't extract a method for a single line of trivial, self-explanatory code
just to hit a target depth — that's KISS working against SLAP; extract because the extraction earns a
name that clarifies intent, not to satisfy a rule mechanically.

## Command-Query Separation & Re-Validation (TOCTOU)

**Definition (Command-Query Separation, Bertrand Meyer)**: A method is either a **command** (has a
side effect, returns nothing meaningful) or a **query** (returns data, has no side effect) — never both.
Keeping this distinction sharp is what makes it safe to reason about whether calling something twice is
free or dangerous.

**Why the same check often legitimately appears more than once in a flow**: When a value can change
between an early check and the point where it's actually used to commit something (concurrent requests,
elapsed time), calling the check again isn't duplication — it's the classic **TOCTOU (Time-Of-Check to
Time-Of-Use)** problem, and the second check is load-bearing. The two calls are actually serving
different purposes even if they look the same:
- An early call is a **query**, used for fast advisory feedback ("you're out of quota" shown to the
  user before they even reach payment).
- The call right before the actual mutation must be a **command** that checks-and-acts atomically in one
  operation, not "read the same query again, see it's fine, then separately mutate" — that sequence
  still has the exact same race-condition gap the first check had.

```java
// Query — advisory, safe to call anywhere, any number of times
public ValidationResult checkAvailable(UserId user, List<Item> items) { ... } // read-only

// Command — the actual source of truth, atomic check-and-consume, called exactly once, at commit time
@Transactional
public ReservationResult reserveQuota(UserId user, List<Item> items) {
    // e.g. UPDATE quotas SET used = used + qty WHERE used + qty <= limit, check rows affected —
    // check and mutate in one atomic operation, no gap for another request to land in between
}
```

**Symptom of the unsafe version**: A "recheck" that calls the same read-only query function again and
then separately performs the mutation — this looks like it re-validates, but the gap between the second
read and the mutation is exactly as exploitable as the gap the first check had.

**Fix**: name the two calls for what they actually are. The advisory check stays a pure query, callable
freely. The authoritative check is a command that performs check-and-mutate as a single atomic
operation (a single SQL statement checked by rows-affected, a DB constraint, or an equivalent atomic
primitive) — never "query, see it's fine, then mutate" as two separate steps, even inside one
transaction, since a second concurrent transaction can still interleave between them without proper
isolation/locking.

**Validate once, pass the proof down (for the genuinely-safe, no-concurrency-risk case)**: When nothing
could plausibly have changed the state between two points in the *same* request (no concurrency risk, no
elapsed time of consequence), re-invoking the same check a second time — e.g. a parent's `checkAll()`
walking every child, and a different code path separately re-invoking `checkChild()` on some of them —
is not TOCTOU, it's plain duplication with an unclear owner. Fix by computing the result once and
threading it through (a `ValidationContext` passed down, memoized per request) rather than letting
multiple call sites independently re-derive the same answer:

```java
// Sink for computed results, threaded through one traversal — no call site re-derives independently
ValidationResult checkAll(Node node, ValidationContext ctx) {
    for (var child : node.children) {
        ctx.computeIfAbsent(child, c -> checkChild(c, ctx)); // computed once, read afterward
    }
    return checkSelf(node, ctx);
}
```

**The one question that decides which case you're in**: *"Could the state this check depends on have
changed between the two calls?"* Yes → keep the second check, but make it atomic with the mutation it
guards (TOCTOU-safe command). No → eliminate the duplicate call, compute once, pass the result down.

## Composition Over Inheritance

**Definition**: Prefer assembling behavior from small, composable parts (has-a) over building deep class
hierarchies (is-a), unless the relationship is a genuine, stable "is-a" that satisfies LSP.

**Symptom of violation**: A class hierarchy more than 2-3 levels deep, or a base class with methods that
only some subclasses actually use meaningfully (frequently also an LSP violation).

**Fix**: Extract the varying behavior into an injected strategy/collaborator instead of a subclass.

```
// Inheritance — brittle as behaviors combine
class Duck extends Animal { fly() {...} swim() {...} quack() {...} }
class RubberDuck extends Duck { fly() { throw ... } } // forced override, LSP violation

// Composition — behaviors combine freely
class Duck {
  constructor(flyBehavior, swimBehavior, quackBehavior) { ... }
}
```

## Separation of Concerns

**Definition**: Distinct responsibilities (e.g. business logic, data access, presentation, cross-cutting
concerns like logging/auth) should live in distinct, independently-reasoned-about units.

**Symptom of violation**: A single function mixes input validation, business rule evaluation, database
calls, and response formatting — testing the business rule requires standing up (or mocking) the whole
stack.

**Fix**: Layer by concern (e.g. handler → service → repository) or, for cross-cutting concerns, extract
to middleware/decorators/aspects rather than repeating the concern inline in every business method.

**Relationship to SRP**: Separation of Concerns is SRP applied at the architectural-layer level rather
than the single-class level — same underlying idea, larger unit of analysis.

## Encapsulate Invariants, Not Cost

**Definition**: Encapsulation should hide *business rules/invariants* behind a well-named method — it
should never hide the *cost* of an operation. A method's name and signature must never imply a
performance profile cheaper than what it actually does. This is the resolution to a common false choice
between "pure OOP encapsulation" and "technical transparency": they conflict only when a codebase
encapsulates the wrong thing.

**Two different things people encapsulate, with opposite outcomes**:
- **Encapsulating a rule** (`order.addItem(item)` refusing to add an item to a completed order) —
  genuinely valuable: prevents a whole class of bug (state pushed into an invalid configuration by
  someone unaware the rule existed), and safe to hide because enforcing it is normally cheap
  (in-memory), so there's no cost being hidden, only complexity.
- **Encapsulating cost** (`order.getItems()` silently issuing a full-table fetch behind what reads like
  a cheap getter) — actively harmful: the abstraction now lies about complexity. The people who pay for
  that lie are developers debugging a performance issue or reasoning about a hot path — not the business
  stakeholders the "business-oriented" naming was meant to serve. Business intent already has a home
  (specs, flow docs, ADRs) that doesn't carry this cost — code hiding technical reality behind business
  language buys little the docs don't already give, while charging every future reader the price of not
  knowing.

**Symptom of violation**: A method shaped like a cheap accessor (a bare noun, no verb suggesting work —
`getX()`, `items()`) that actually performs I/O, a network call, or O(n)-or-worse computation with no
signal at the call site that it's expensive.

**Fix**: Match visibility to cost, not to "does this sound like business language."
- Cheap, invariant-protecting logic: fine to hide behind a business-named method — this is where
  encapsulation earns its keep.
- Expensive/technical operations: keep them visible — through naming that doesn't pretend to be a cheap
  getter (a verb like `fetch`/`load`/`query` rather than `get`), or by placing them only in a
  distinctly-named layer (a repository) whose whole purpose signals "this does I/O," rather than
  smuggling the cost behind an innocuous-looking domain method on an entity.

**Where this bites hardest in practice — read paths on an aggregate's collections**: an ORM-managed
collection getter (`order.getItems()`) is the canonical example — it looks like O(1) field access and
can be an expensive full fetch. This is why read/filter access should go through an explicit
repository query returning a projection, not through the aggregate's own collection field — see
`java-spring-skill`'s `references/data-jpa.md` for the concrete JPA pattern. Reads are exactly where
hiding cost does the most damage: they're the most performance-sensitive path and the one reviewers
trust the abstraction on most readily.

**When NOT to over-apply**: This is not an argument against encapsulation in general, or for exposing
implementation detail everywhere "to be safe." A cheap invariant deserves to be hidden — the heuristic
is specifically about matching the *visibility* of an operation to its *actual cost*, not eliminating
encapsulation.

## Applying These Heuristics Together

These are heuristics, not laws — they exist in tension (DRY vs. KISS, YAGNI vs. OCP) by design. When two
heuristics point in different directions on a real piece of code, name the tension explicitly and pick
based on which failure mode is more expensive *for this specific system*, not by mechanically applying
whichever heuristic comes to mind first.
