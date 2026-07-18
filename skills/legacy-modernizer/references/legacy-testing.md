# Legacy Testing Strategies

## Method

Seven techniques for making legacy code safe to change. Each answers a different question about
behavior that's otherwise undocumented.

**Characterization tests.** Write tests that lock in *current* behavior — bugs included — not the
behavior that "should" happen. This is the foundational technique everything else builds on: once
characterization tests are green, any refactor that changes undocumented behavior fails loudly instead
of shipping silently. Fixing an actual bug found this way is a deliberate, separate, explicitly-labeled
step — not something that happens as a side effect of refactoring.

**Golden master testing.** For output too complex to assert field-by-field (a generated report, a
large formatted document), capture the full output as a saved reference artifact once, then compare
future runs against it byte-for-byte or via hash. A mismatch means output changed; a human decides
whether that change was intended (update the golden master) or a regression (fix the code).

**Snapshot testing.** The same idea as golden master, applied specifically to structured data (API
responses, serialized objects). Normalize non-meaningful variation before comparing — sort map/object
keys, strip timestamps — so an unrelated ordering change doesn't produce a false diff that has to be
manually re-approved.

**Parallel run (shadow testing).** Run the legacy and new implementations side by side against the
same real input, compare their results, and log any discrepancy — but keep serving the legacy result
to users throughout. This validates the new implementation against real-world input distributions
without ever putting user-facing correctness at risk on the new, unproven path. Only once the shadow
comparison has run clean for a meaningful period does the new implementation become a candidate to
actually serve traffic (at which point it hands off to the strangler fig pattern's routing/rollout
mechanics).

**Mutation testing.** Deliberately introduce small, automated bugs ("mutants") into the code and check
whether the existing test suite catches each one. A mutant that survives (no test fails) reveals an
untested edge case that a plain coverage percentage would never surface, because coverage only measures
whether a line executed, not whether its outcome was actually asserted on.

**Property-based testing.** Instead of enumerating fixed example inputs, state invariants that must
hold for *any* valid input (a result is never negative, never exceeds the input, a round-trip
serialize/deserialize is lossless) and let a generator produce many randomized inputs to search for a
counterexample. Especially effective on legacy logic where the exact rules are unclear but general
properties of correct behavior are still known.

**Coverage-guided test generation.** Use coverage tooling to find code paths the existing suite never
exercises, then write targeted tests for exactly those paths — a directed way to close gaps, rather
than adding tests blindly in the hope of raising a percentage.

## Boundary

- These techniques exist to make legacy code *safe to change*, not to certify that legacy behavior is
  *correct*. Characterization and golden-master tests intentionally encode existing bugs as "expected"
  — that's by design, so a refactor doesn't silently break behavior someone downstream may be relying
  on, even unintentionally. Deciding a piece of behavior is actually wrong and should change is a
  product/business decision, made explicitly, separate from and prior to any refactor.
- A parallel run's "new" result is never served to users under any circumstance — divergence is
  logged and investigated by a human, never auto-resolved by picking whichever result "looks more
  correct."
- Testing strategy here is a prerequisite for the other three references (strangler fig, refactoring
  patterns, migration strategies) — it does not replace them. Tests make a change safe to *attempt*;
  they don't perform the migration or refactor themselves.
