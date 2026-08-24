---
name: refactor
description: Code-refactoring workflow — improve structure/performance/maintainability WITHOUT changing external behavior (API responses, side effects, output must stay 100% identical). Use when the request is to clean up/restructure/improve code quality, not to add a new feature or fix wrong behavior. Fully technology-agnostic — invokes whichever technical skills the task needs.
argument-hint: "[code to refactor + reason]"
---

# Refactor Workflow

Runs as a single agent, sequentially. The OVERRIDING principle throughout: **the system's external
behavior (API responses, side effects, data written, logs, events emitted, etc.) MUST stay 100%
identical before and after the refactor**. If at any point a refactor turns out to be impossible without
changing behavior — STOP, tell the user, don't unilaterally treat it as "a refactor with a small fix
bundled in."

## Step 0 — Discover Context

Read `CLAUDE.md`, memory/MCP if connected, and the existing code/logic in the area to be refactored. If
`workflow-router` already read these in this same session immediately before handing off, reuse that —
don't re-read from scratch.

## Step 1 — Pin Down the Pain Point (vague descriptions not accepted)

A refactor request must make concrete WHY it's needed — a generic reason like "the code is ugly" isn't
accepted. Clarify which one of these pain points applies:
- Code duplication (DRY violation) — where, and how many places it repeats.
- Coupling too tight, hard to test in isolation (too many unrelated dependencies need mocking).
- Poor performance due to structure (not due to a missing index/cache — that's the relevant technical
  skill's job; refactor here is about code structure).
- Hard to extend due to a design-principle violation (a God class, a Single Responsibility violation...).
- Naming/structure inconsistent with the project's current convention.

If the user's description is vague ("clean up this code"), ask which specific pain point is being
targeted before continuing — a refactor with no clear target tends to sprawl into unnecessary changes.

To name a pain point precisely rather than by feel — and to state the concrete symptom it produces, which
is what makes Step 6's "how the pain point was resolved" verifiable — read `solution-design-principles`
for the relevant heuristic (DRY vs. the wrong abstraction, coupling/cohesion, SRP/SLAP method
decomposition, the reuse trap of an accreted shared function).

## Step 2 — Check the "Safety Net" BEFORE Refactoring (required, never skipped)

A safe refactor requires test coverage of the CURRENT behavior before touching any code.
1. Check existing tests for the area to be refactored — do they cover the important behavioral branches
   (not just the happy path)?
2. If coverage is MISSING: write **characterization tests** first — tests that lock in the CURRENT
   behavior exactly (whether or not that behavior is optimal, whether or not it has a latent bug — do
   NOT fix a bug at this step, just record "this is how it currently behaves"). If a genuine bug is
   discovered while writing characterization tests, STOP, tell the user: this is no longer a pure
   refactor — it needs to go through `bug-fix` first, then come back to the refactor once fixed.
3. Do NOT start Step 3 without a sufficiently reliable safety net in place.

## Step 3 — Propose a Refactor Approach

1. Read the existing conventions/architecture, propose the fitting refactor pattern (extract
   method/class, introduce interface, replace conditional with polymorphism...). If the refactor's scope
   is large enough to need strangler fig / branch by abstraction (gradually replacing a large
   module/service that can't be safely changed in one small step) — read `legacy-modernizer` in full
   (the technical skill specializing in exactly this: facade/routing, dual-write, dependency mapping,
   in-depth characterization testing) and apply its method within this Step 3/4, instead of reinventing
   the approach — `legacy-modernizer` does NOT run its own CHECKPOINT/report/changelog; this workflow
   remains the sole orchestrator.
2. If more than one direction is reasonable, present multiple proposals with trade-offs (extent of
   change, risk, time), similar to `feature-development` Step 2 — but instead of AC/Edge Cases in the
   sense of new behavior, use a "Behavior Preservation Checklist" (the specific behaviors that MUST stay
   identical, cross-checked against the characterization tests from Step 2).
3. Decide scope: a single-pass refactor (if small) or split into incremental small steps (if large) —
   prefer splitting so each step is easy to verify and easy to roll back if something goes wrong.

**CHECKPOINT (required)**: present the proposal and wait for the user to confirm before executing.

## Step 4 — Execute (small steps, continuously verified)

1. Refactor in the SMALL steps defined in Step 3 — do NOT do one large pass and only test at the very
   end (high risk, hard to pinpoint the source of a failure if one occurs).
2. After EVERY small step: re-run all relevant tests (including the characterization tests) — they MUST
   pass 100% before moving to the next small step.
3. If a step breaks a test: fix it within a reasonable scope, **maximum 3 attempts** for that step
   (fewer than the 5 used by `feature-development`/`bug-fix`, since a refactor is inherently lower-risk —
   repeated failed fixes are themselves a signal the refactor direction is unstable). If still failing
   after 3 attempts: **ROLL BACK that step** (revert to the state before this small step, using git if
   available), report to the user, and don't continue refactoring on top of a broken state.
4. Reference the relevant technical skill (`Read` the full `SKILL.md` at the point of applying it, never
   reused from an earlier request in the session — same principle as `feature-development`) for the
   stack's correct coding conventions.

## Step 5 — Confirm Behavior Is Unchanged (required, the core difference from the other two workflows)

1. Re-run the ENTIRE relevant test suite (not just the refactored area's tests) — confirm nothing else
   in the system broke.
2. Cross-check the "Behavior Preservation Checklist" from Step 3 — confirm every item still holds.
3. Where possible, compare concrete output before/after (e.g. run the same input, compare the response)
   for concrete evidence beyond "tests pass" — tests can miss a case.

## Step 6 — Final Report (required)

- How the original pain point was resolved (cross-checked against Step 1).
- A clear confirmation: did external behavior change at all (must be "No" — if it did, this is a serious
  issue to surface prominently, not bury in the details).
- List of files changed, number of small steps taken, whether any step needed a rollback.
- Remaining risk, if any.
- Whether `code-review-skill` was run (if available) before reporting.

No separate confirmation checkpoint is needed here — proceed straight to Step 7 after reporting
(logging is a low-risk side effect, easy to amend later if the user's feedback changes something).

## Step 7 — Knowledge Capture (immediately after Step 6)

1. Memory/MCP (if connected): record the refactor pattern applied and why.
2. Changelog file: `docs/changelog/<refactor-slug>.md` — the original pain point, the chosen approach
   (+ reasoning), the behavior preservation checklist, the final outcome (cross-checked against Step 5),
   and the list of files changed. This is the record of what was ACTUALLY refactored — it doesn't
   belong in `docs/decisions/` because once complete it's a change log, not a standalone decision record.
3. **Experience log** (cumulative, append-only): `docs/knowledge/experience-log.md` — record which
   refactor pattern was effective/ineffective for this type of pain point, for reference the next time a
   similar pain point comes up.
