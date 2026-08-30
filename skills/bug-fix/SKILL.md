---
name: bug-fix
description: Complete bug-fix workflow — gather symptoms, attempt to reproduce, wait for user confirmation before fixing, implement/fix in a loop until quality is met, then report, capture knowledge, and produce a postmortem. Fully technology-agnostic — invokes whichever technical skills the task needs. Works for any project or stack.
argument-hint: "[bug/symptom description]"
hooks:
  PreToolUse:
    - matcher: "Edit|Write|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/skill-gate.sh"
          timeout: 15
          statusMessage: "Checking the owning skill was read..."
  Stop:
    - hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/quality-gate.sh"
          timeout: 30
          statusMessage: "Quality gate..."
---

# Bug Fix Workflow

Runs as a single agent, sequentially. This skill holds no technology-specific knowledge itself —
implementation details come from whichever technical skill matches the task.

Input: `$ARGUMENTS`

## Step 0 — Discover Context

Read `CLAUDE.md`, memory/MCP if connected, and the existing code/logic relevant to the suspected bug
area. If `workflow-router` already read these in this same session immediately before handing off,
reuse that — don't re-read from scratch.

## Step 1 — Gather Symptoms

Record everything the user knows/observes: expected vs. actual behavior, the conditions it occurs under
(when, what data, what environment), frequency (always or intermittent), and any error messages/logs.
If critical diagnostic information is missing, ask immediately — don't guess ahead of having the minimum
facts needed.

## Step 2 — Attempt to Reproduce

1. Combine the user's symptoms with project context/knowledge (existing code, the processing flow, logs
   if available) to reconstruct a scenario that could plausibly cause the bug.
2. If reproduced: write down the EXACT steps to reproduce it, plus the root cause identified from
   concrete evidence (not a guess).
3. If NOT reproduced: say so plainly — never pretend to understand the cause when it isn't understood.
   Present the plausible hypotheses (each with a confidence level: high/medium/low) and state what
   additional information from the user (more specific logs, more detailed reproduction steps) would
   improve the odds of reproducing it.

## Step 3 — Report for User Review/Approval (required CHECKPOINT)

Present: whether it was reproduced, the root cause (if found, with confidence level), the planned fix
direction (with the technical skill(s) expected to be referenced — kept abstract, no need to spell out
technology detail), related edge cases that must not recur, and the Definition of Done (what counts as
fixed).

**CHECKPOINT**: wait for the user to confirm/approve the fix direction before implementing. Never fix
code without confirmation — even when very confident about the root cause.

## Step 4 — Implement + Retest (loop until quality is met)

### 4.1 Implement the Fix

Fix the actual root cause approved in Step 3 (not the surface symptom). Before writing any code that
falls under a technical skill — you MUST `Read` the full `SKILL.md` for that skill at that point, never
inferring its content from its name alone. A skill's name never substitutes for reading its actual
content before applying it.

If one bug/task touches MULTIPLE skills (e.g. both Java/Spring and Database), read all of them fully
before writing any code for that task — don't read one, code some, then read the next.

### 4.2 Retest

Write a test case that reproduces this exact bug (to guard against recurrence), then re-run ALL
relevant tests (not just the new one) to confirm nothing else broke.

### 4.3 If Not Yet Resolved (bug still present, or a new issue appeared) — Enter the Fix Loop

For EACH issue/failing test case (the original bug not yet gone, or a new issue introduced by the fix):

1. Diagnose, fix, retest — this is **attempt #1** for that issue/test case.
2. Still failing: retry, incrementing the counter (#2, #3...).
3. **Maximum 5 attempts per distinct issue/test case.** If still unresolved after the 5th attempt —
   STOP, raise it to the user: describe the issue, what was tried on each attempt, why it's still
   unresolved, and what decision is needed from the user.
4. A NEW issue/test case gets its own counter — never pool attempt counts across different issues.

Repeat 4.1 → 4.2 → 4.3 until the original bug is fixed, all tests pass, and no new issue was
introduced, OR an issue has to be raised to the user (stop the workflow there).

## Step 5 — Final Report (required)

- Whether the original bug is fixed, whether the DoD is met.
- Risks/issues encountered throughout (including ones already fixed, including any raised to the user).
- List of files changed.
- Number of fix attempts used per issue/test case.

No separate confirmation checkpoint is needed here — proceed straight to Step 6 after reporting
(logging/postmortem is a low-risk side effect, easy to amend later if the user's feedback changes
something).

## Step 6 — Knowledge Capture & Postmortem (immediately after Step 5)

1. Memory/MCP (if connected): record the root cause, the fix, and the final outcome.
2. **Experience log (cumulative, never overwritten)**: append to `docs/knowledge/experience-log.md`
   using the same format as `feature-development` (date, issue description, cause, attempts used,
   outcome, the fix or the approaches that did NOT work).
3. **Postmortem (required, specific to bug-fix)**: create `docs/postmortems/<bug-slug>.md` using the
   template in `references/postmortem-template.md`.

If the bug could NOT be reproduced/fixed (already raised to the user and stopped there), still create
a postmortem with an "Unresolved" section stating the hypotheses tried, why work stopped, and the
recommended next step — so the next person (or future you) doesn't have to start over from scratch.

## Boundaries

- This skill is for **behavior that is currently wrong** — a genuine defect. If the current behavior is
  actually correct and the request is to add/change capability, that's `feature-development`'s job; if
  it's a behavior-preserving structural cleanup, that's `refactor`'s job. `workflow-router` makes this
  classification when routing; if invoked directly, check first that this really is a defect fix.
- This skill owns the *workflow* (symptoms → reproduce → checkpoint → implement/retest loop → report →
  postmortem) — it holds no language/framework-specific knowledge itself. Technical implementation
  detail comes from the matching technical skill, read in full at the point it's applied (Step 4.1).
- Deep test-design questions beyond "write a test that reproduces this bug" (test architecture, mocking
  strategy) are the relevant technical skill's job and, for broader strategy, `test-master`'s.
