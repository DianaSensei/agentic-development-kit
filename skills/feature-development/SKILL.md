---
name: feature-development
description: End-to-end workflow for building a new feature - requirements analysis, solution proposal, implement/test/fix loop until quality bar is met, then reporting and knowledge capture. Fully technology-agnostic - invokes whichever technical skills the task needs. Works for any project or stack.
argument-hint: "[feature request description]"
hooks:
  PreToolUse:
    - matcher: "Edit|Write|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/skill-gate.sh"
          timeout: 15
          statusMessage: "Checking the owning skill was read..."
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/checkpoint-gate.sh"
          timeout: 15
          statusMessage: "Checking the CHECKPOINT was confirmed..."
  Stop:
    - hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/quality-gate.sh"
          timeout: 30
          statusMessage: "Quality gate..."
metadata:
  domain: workflow
  triggers: add capability, build feature, implement requirement, behavior change, feature request
  role: orchestrator
  scope: end-to-end
  output-format: code-and-report
  related-skills: workflow-router, code-review-skill, test-master, ui-ux-design-skill, technical-proposal-writer
---

# Feature Development Workflow

Runs as a single agent, sequentially. Holds no technology-specific knowledge - implementation detail
(language, framework, database, messaging) comes from whichever technical skill matches the task.

Input: `$ARGUMENTS`

## Step 0 - Discover Context

Read `CLAUDE.md`, memory/MCP if connected, and the existing code relevant to the request. If
`workflow-router` just read these before handing off, reuse that rather than re-reading.

This skill's own `references/` cover requirement-gathering *method* (not technology) - load each when its
step is reached: `ears-syntax.md`, `interview-questions.md`, `acceptance-criteria.md`,
`specification-template.md`, `diagram-guide.md`, `definition-of-done.md`, `report-and-logs.md`.

**Optional pre-discovery**: if the feature touches 3+ system layers (auth, DB, UI...), the codebase is
unfamiliar/undocumented, or technical facts are needed before requirements can be asked intelligently -
launch parallel Task subagents on the relevant technical skills *before* Step 1, so the interview covers
decisions instead of exploration. Skip for a well-scoped, single-domain feature or a familiar codebase.
Full pattern: `references/interview-questions.md` → "Multi-Agent Pre-Discovery".

## Step 1 - Requirements Analysis (`business-analyst`, confirmed with the user here)

Launch the `business-analyst` subagent (Task tool) with the raw request plus whatever Step 0 found. It
runs on `Read, Grep, Glob, Bash` only - **no `Edit`/`Write`, so this step is architecturally unable to
touch code**, not merely told not to. It returns `requirement_clarified`, `feasibility_verdict`,
`draft_acceptance_criteria`, `draft_edge_cases`, `draft_definition_of_done`,
`impact_assessment_preliminary`, `assumptions`, `open_questions` (contract:
`agents/business-analyst.md`).

A subagent can't ask the user anything - `AskUserQuestion` is unavailable to it by design - so that stays
here in the main thread:

- Non-empty `open_questions`, or a `feasibility_verdict` that isn't `feasible`: resolve each with the
  user before proceeding, never guess at intent. Use `AskUserQuestion` wherever the likely answers are
  finite and enumerable (framing per category in `references/interview-questions.md` - PM lens: user
  value, scope, priority; Dev lens: feasibility, security, performance, edge cases); open-ended chat only
  when the answer space genuinely can't be enumerated.
- Fold the answers back into `business-analyst`'s output before Step 2. Re-invoke it only if the answers
  substantially reopen a `not_feasible_as_stated` verdict.

## Step 2 - Solution Proposal (`solution-architect`, refined and checkpointed here)

1. Launch `solution-architect` (Task tool) with Step 1's finalized output. Also read-only (`Read, Grep,
   Glob` - no `Bash`, no `Edit`/`Write`). Returns one or more `proposals`, each with sequence/flow
   diagrams, trade-off analysis, architecture decisions, finalized AC/edge cases/DoD, and a
   `task_breakdown` assigning work to Tier-2 agents where one exists (contract:
   `agents/solution-architect.md`).
2. Bring each proposal up to this workflow's documentation bar - `solution-architect`'s contract doesn't
   require these, so add them where they actually apply:
   - Acceptance criteria restated as EARS functional requirements (`references/ears-syntax.md`), checked
     against INVEST (`references/acceptance-criteria.md`).
   - An Architecture/Component diagram if system boundaries change or a service is added/removed; an ERD
     if the data model changes. `references/diagram-guide.md` has the mandatory/conditional/skip rules -
     don't add a diagram type the change doesn't call for.
   - An Error Handling table (condition → response/status → message) for new logic.
   - Non-functional requirements where a concrete constraint exists. Never invent a number - write "needs
     confirmation" instead.
3. Write every refined proposal to `docs/plans/<feature-slug>.md` per
   `references/specification-template.md`. This is the durable record; it does not replace presenting the
   proposal to the user in conversation.
4. `solution-architect` may mark one `recommended` - fine to relay, but never choose on the user's behalf.

**CHECKPOINT (required)**: present the full proposal, then confirm via `AskUserQuestion` with `header`
set exactly to `"Checkpoint"` (options: one per proposal, plus "Revise" - free text always available via
"Other"). Do not proceed to Step 3 without explicit confirmation. Presenting is not confirming - Step 3 is
gated on this literal call, so moving on after merely presenting will be caught.

Immediately after the user decides: update `docs/plans/<feature-slug>.md` - chosen proposal to the top,
marked (`## ✅ Chosen: <name>`); rejected ones below, each wrapped in
`<details><summary>Rejected: <name></summary> ... </details>` so they render collapsed.

## Step 3 - Implement + Test (loop until the quality bar is met)

### 3.1 Implement

Before writing any code covered by a technical skill (Java/Spring part → `java-spring-skill`, DB part →
`database-skill`), you MUST `Read` that skill's full `SKILL.md` first. A name never substitutes for its
actual content. Multiple skills in one task → read all of them fully before writing any code for it, not
read-one-code-some-read-the-next. Once read, follow it exactly rather than improvising from general
background knowledge.

**A read only counts within the SAME request.** For a NEW user request, re-read the skill from scratch
even if you remember reading it a turn ago - the user may have edited it since.

**Optional Tier-2 dispatch**: where `task_breakdown` assigned a task to a Tier-2 agent that actually
exists (`java-ecosystem-engineer`, `tauri-react-engineer`, `data-storage-architect`, `api-spec-designer`),
it may go through the Task tool instead of being implemented inline - those agents write and run their own
tests for the piece they own. Not required: anything without a matching Tier-2 agent is implemented
directly under the read-the-`SKILL.md` rule above.

### 3.2 Test

Write and run tests per the relevant technical skill. Check results against every Step 2 acceptance
criterion, every listed edge case, the Definition of Done, and the **quality bar**
(`references/definition-of-done.md`): tests pass, no open severe defects, coverage adequate for every
important AC - a token test that skips an AC doesn't count.

### 3.3 Fix loop (when the bar isn't met)

For EACH distinct issue:

1. Diagnose, fix, re-run its tests - **attempt #1**.
2. Still failing → retry, incrementing that issue's counter (#2, #3...).
3. **Maximum 5 attempts per issue.** After the 5th, STOP - don't try again. Raise it to the user: the
   issue, what was tried each attempt, why it's still unresolved, and what decision is needed (different
   approach, accept a limitation, more information).
4. A new, distinct issue gets its own counter and its own 5 attempts. Never pool counts across issues.
5. Once resolved, re-run ALL relevant tests to confirm nothing else broke, then return to 3.2.

Repeat 3.1 → 3.2 → 3.3 until quality bar, AC, and DoD are all met, OR an issue must be raised to the user
- stop the workflow there, never call it done unilaterally.

## Step 4 - Final Report (required)

Template: `references/report-and-logs.md` → "Final Report Template". At minimum: AC/DoD items met vs. not
met; risks/issues encountered throughout, including ones already fixed and any raised to the user; files
changed; fix attempts used per issue, so the user can see the actual difficulty.

No checkpoint here - go straight to Step 5 (logging is low-risk and easy to amend if the user's feedback
changes something).

## Step 5 - Knowledge Capture (immediately after Step 4)

Templates for both files: `references/report-and-logs.md`.

1. Memory/MCP if connected: key decisions and the final outcome.
2. `docs/changelog/<feature-slug>.md` - derived from `docs/plans/<feature-slug>.md` (chosen proposal + its
   diagrams, updated if the design shifted during implementation), plus the rationale for choosing it,
   final AC/DoD status, remaining risk, and files changed. This records what was ACTUALLY built (unlike
   `docs/plans/`, which captures proposals at decision time); it isn't a `docs/decisions/` entry because
   once complete it's a change log, not a standalone decision record.
3. **Experience log (required, cumulative, never overwritten)**: append one entry per Step 3.3 issue -
   fixed or not - to `docs/knowledge/experience-log.md`, using the reference's template. Next time a
   similar issue appears, in this project or another, reading this first avoids retrying a known dead end.

## Boundaries

- Owns the *workflow* only. Every technical detail comes from the matching skill, read in full at the
  point it's applied (3.1) - never improvise conventions this workflow doesn't own.
- Steps 1-2 run as subagents specifically so requirements and design happen with no `Edit`/`Write`
  available at all - a checkpoint enforced by the tool set rather than by asking nicely. That's why this
  file's job through Step 2 is orchestration, not the analysis/design itself. Step 3 runs in the main
  thread, since implementation genuinely needs `Edit`/`Write` and is already gated by
  `skill-gate`/`checkpoint-gate`/`quality-gate`.
- **New capability or intentionally changed behavior only.** Current behavior actually being wrong is
  `bug-fix`'s job even when phrased as "improve X"; a change that must not alter external behavior at all
  is `refactor`'s. `workflow-router` normally classifies this - if invoked directly, check first.
- Decides *what* to test and *when* (3.2). Test design, mocking strategy, and test architecture come from
  the relevant technical skill, or `test-master` for broader strategy.
- Step 2's `docs/plans/<feature-slug>.md` is part of this workflow, not a standalone deliverable. If the
  user wants only a requirements document with no implementation, say so explicitly after the CHECKPOINT
  instead of silently continuing into Step 3.
- No dedicated security or architecture review beyond reaching the DoD - deeper passes go to
  `secure-code-guardian`, `architecture-designer`, or `solution-design-principles` (SOLID,
  coupling/cohesion, Well-Architected, 12-Factor) before the thing is built.
