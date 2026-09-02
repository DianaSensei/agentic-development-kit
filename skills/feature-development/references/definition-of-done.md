# Definition of Done - Quality Bar (Step 3.2)

What "meets the quality bar" concretely means before leaving the Step 3 implement/test loop. This
checklist is what turns "I tested it" into something verifiable, and is deliberately stricter than
"tests pass" alone - a green suite that skips an important AC is not done.

## Checklist

- [ ] Every Acceptance Criterion from Step 2 has at least one test that would fail if that AC were
      violated (not just a test that happens to pass alongside it).
- [ ] Every listed Edge Case has explicit coverage - not implicitly exercised as a side effect of
      another test.
- [ ] All tests pass, including the full existing suite for the touched area (not only newly added
      tests) - Step 3.3's fix loop already enforces re-running everything after each fix; this is the
      exit condition, not just the retry condition.
- [ ] No known severe defect is left open. "Severe" means: violates an AC, causes data loss/corruption,
      or breaks an existing feature. A cosmetic or genuinely out-of-scope issue can be logged as a
      follow-up instead of blocking, but say so explicitly in the Step 4 report - don't silently drop it.
- [ ] Coverage is adequate specifically for the AC/Edge Cases that matter for this feature - not a
      blanket percentage target. A high line-coverage number achieved by testing trivial paths while an
      AC has no dedicated test does not satisfy this bar.
- [ ] The Definition of Done items agreed to in Step 2 for the chosen proposal are all checked off, or
      explicitly called out as not met with a reason.

## What Does Not Count as Done

- "It compiles/builds" - necessary, not sufficient.
- "I manually tried it once and it looked right" - not a substitute for a written test that will catch
  a regression later.
- A test that asserts on implementation details (e.g. a specific internal function was called) instead
  of on the AC's actual observable behavior - this passes even when the AC-level behavior is wrong,
  because it isn't actually checking the AC.
- Partial coverage described as "good enough" without stating which AC/Edge Case is uncovered and why
  that's acceptable - every gap must be a stated decision, not an omission.

## Using This With Step 3.3's Fix Loop

Run this checklist after every pass through 3.1 → 3.2, not only once at the very end - treat any
unchecked item the same as a failing test for the purposes of the fix-attempt counter in 3.3. If an
item can't be checked off after 5 attempts (per the normal fix-loop limit), it gets raised to the user
like any other unresolved issue, not silently waived.
