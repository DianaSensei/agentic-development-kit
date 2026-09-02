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
  triggers: new feature, add capability, build feature, implement requirement, behavior change, feature request
  role: orchestrator
  scope: end-to-end
  output-format: code-and-report
  related-skills: workflow-router, code-review-skill, test-master, ui-ux-design-skill, technical-proposal-writer
---

# Feature Development Workflow

Runs as a single agent, sequentially. This skill holds no technology-specific knowledge itself -
implementation details (language, framework, database, messaging, etc.) come from whichever technical
skill matches the task.

Input: `$ARGUMENTS`

## Step 0 - Discover Context

Read `CLAUDE.md`, memory/MCP if connected, and the existing code/logic relevant to this request. If
`workflow-router` already read these in this same session immediately before handing off, reuse that -
don't re-read from scratch.

This skill also has its own `references/` for requirement-gathering *method* (not technology
knowledge) - load each when its matching step is reached: `ears-syntax.md`, `interview-questions.md`,
`acceptance-criteria.md`, `specification-template.md`, `diagram-guide.md`, `definition-of-done.md`,
`report-and-logs.md`.

**Optional pre-discovery**: if the feature touches 3+ distinct system layers (auth, DB, UI...), the
codebase is unfamiliar or undocumented, or concrete technical facts are needed before requirements can
be asked intelligently - launch parallel Task subagents invoking the relevant technical skills to
gather that context *before* Step 1's interview, so the interview focuses on decisions instead of
exploration. Skip this for a well-scoped, single-domain feature or a codebase already well understood.
See `references/interview-questions.md` → "Multi-Agent Pre-Discovery" for the full pattern.

## Step 1 - Requirements Analysis (delegated to `business-analyst`, confirmed with the user here)

Launch the `business-analyst` subagent (Task tool) with the raw request plus anything Step 0 already
found (avoids redundant re-discovery). `business-analyst` is restricted to `Read, Grep, Glob, Bash` -
no `Edit`/`Write` - so this step is architecturally unable to touch code, not merely instructed not to.
It returns `requirement_clarified`, `feasibility_verdict`, `draft_acceptance_criteria`,
`draft_edge_cases`, `draft_definition_of_done`, `impact_assessment_preliminary`, `assumptions`, and
`open_questions` (see `agents/business-analyst.md` for its full contract).

A subagent cannot ask the user anything directly - `AskUserQuestion` is unavailable to it by design -
so that part stays here, in the main thread:
- If `open_questions` is non-empty, or `feasibility_verdict` isn't `feasible`, resolve each one with the
  user before proceeding - never guess at intent. Use `AskUserQuestion` for anything with a finite,
  enumerable set of likely answers (see `references/interview-questions.md` for question framing per
  category - PM lens: user value, scope, priority; Dev lens: technical feasibility, security,
  performance, edge cases); use open-ended chat only when the answer space can't be enumerated in
  advance. Don't ask a free-text question when a structured choice would work just as well.
- Fold the user's answers into `business-analyst`'s output (resolve `open_questions`, update
  `requirement_clarified`/`feasibility_verdict` if the answers changed them) before Step 2 - no need to
  re-invoke `business-analyst` unless the answers substantially reopen a `not_feasible_as_stated` verdict.

## Step 2 - Solution Proposal (delegated to `solution-architect`, refined and checkpointed here)

1. Launch the `solution-architect` subagent (Task tool) with `business-analyst`'s finalized output from
   Step 1. Like `business-analyst`, it is restricted to read-only tools (`Read, Grep, Glob`, no `Bash`,
   no `Edit`/`Write`) - it designs, it does not touch code. It returns one or more `proposals`, each with
   sequence/flow diagrams, trade-off analysis, architecture decisions, finalized acceptance
   criteria/edge cases/DoD, and a `task_breakdown` assigning work to Tier-2 agents where one exists (see
   `agents/solution-architect.md` for its full contract).
2. For each proposal, bring it up to this workflow's own documentation bar before writing it down -
   `solution-architect`'s own contract doesn't require these, so add them here only where they actually
   apply:
   - Restate the acceptance criteria as EARS-format functional requirements where not already phrased
     that way (see `references/ears-syntax.md`), and check them against the INVEST bar (see
     `references/acceptance-criteria.md`).
   - Add an Architecture/Component diagram if the proposal changes system boundaries or adds/removes a
     service, and an ERD if it changes the data model (see `references/diagram-guide.md` for the full
     mandatory/conditional/skip rules) - don't add a diagram type the change's scope doesn't call for.
   - An Error Handling table (error condition → response/status → message) for any new logic, where
     applicable.
   - Relevant Non-Functional Requirements (performance, security, scalability) where there's a concrete
     constraint - never invent a number when it isn't known; write "needs confirmation" instead of
     guessing.
3. Write the full contents (every proposal, refined per above) to `docs/plans/<feature-slug>.md`,
   following the section layout in `references/specification-template.md`. This file is the durable
   record for later reference - it does not replace presenting the full proposal directly to the user in
   conversation.
4. `solution-architect` may mark one proposal `recommended` with a reason - fine to offer that to the
   user, but never pick one on the user's behalf regardless of the recommendation.

**CHECKPOINT (required)**: present the full proposal (already written to `docs/plans/<feature-slug>.md`),
then ask for confirmation via `AskUserQuestion` with `header` set exactly to `"Checkpoint"` (options: one
per proposal if more than one, plus "Revise" - free text is always available via "Other"). Do not proceed
to Step 3 without an explicit confirmation. Presenting the proposal is not the same as confirming it -
Step 3 is gated on this literal `AskUserQuestion` call, so simply moving on after presenting will be
caught.

Immediately after the user decides at the CHECKPOINT: update `docs/plans/<feature-slug>.md` - move the
chosen proposal to the top, clearly marked (e.g. `## ✅ Chosen: <name>`); move rejected proposals below
it, each wrapped in `<details><summary>Rejected: <name></summary> ... </details>` so they render
collapsed by default on renderers that support it (GitHub, VS Code preview, etc.).

## Step 3 - Implement + Test (loop until the quality bar is met)

### 3.1 Implement

Before writing any code for a piece of work that falls under a technical skill (e.g. the Java/Spring
part → `java-spring-skill`, the DB part → `database-skill`) - you MUST `Read` the full `SKILL.md` for
that skill at that point, never inferring its content from its name alone. A skill's name never
substitutes for reading its actual content before applying it.

**Don't reuse a previous request's read within the same session**: if this is a NEW user request
(different from one already handled earlier in this conversation), `Read` the relevant skill again from
scratch, even if you "remember" reading it last turn - its content may have changed between turns (the
user may have just edited it). A skill only counts as "already read" within the continuous scope of the
SAME request/task currently being worked, never carried across separate requests.

If one task touches MULTIPLE skills (e.g. both Java/Spring and Database), read all of them fully before
writing any code for that task - don't read one, code some, then read the next.

Once read, follow that skill's conventions/knowledge exactly - don't invent an approach from general
background knowledge when the matching skill already specifies one.

**Optional Tier-2 dispatch**: if `solution-architect`'s `task_breakdown` assigned a task to a Tier-2
agent that actually exists (e.g. `java-ecosystem-engineer`, `tauri-react-engineer`,
`data-storage-architect`, `api-spec-designer`), it may be dispatched via the Task tool instead of
implemented inline here - those agents write and run their own tests for the piece they own. Not
required: a task with no matching Tier-2 agent, or any technical skill without one, is implemented
directly per the `Read`-the-`SKILL.md` rule above, exactly as before.

### 3.2 Test

Write and run tests per the relevant technical skill (unit/integration/functional, as fits the project).
Check results against:

- Every Acceptance Criterion finalized in Step 2.
- Every listed Edge Case.
- The Definition of Done.
- **Quality bar** (see `references/definition-of-done.md` for the full checklist): tests pass, no
  open severe defects, coverage is adequate for every important AC - a token test that skips an AC
  does not count.

### 3.3 If the quality bar isn't met - enter the fix loop

For EACH issue/failure found (a failing test, a problem self-identified during review):

1. Diagnose the cause, fix it, re-run the relevant tests. This is **attempt #1** for this issue.
2. Still failing: retry, incrementing the counter for that issue (#2, #3...).
3. **Maximum 5 attempts per distinct issue.** If still unresolved after the 5th attempt - STOP, do not
   try again, raise it to the user: describe the issue, what was tried on each attempt, why it's still
   unresolved, and what decision is needed from the user (a different approach, accepting a limitation,
   or more information).
4. A NEW issue (distinct from the one being worked) gets its own counter with its own 5 attempts - never
   pool attempt counts across different issues.
5. Once an issue is resolved, re-run ALL relevant tests (not just that issue's test) to confirm nothing
   else broke, then return to 3.2.

Repeat 3.1 → 3.2 → 3.3 until the quality bar, AC, and DoD are all met, OR an issue has to be raised to
the user (stop the workflow there - never treat it as done unilaterally).

## Step 4 - Final Report (required)

Report format: see `references/report-and-logs.md` → "Final Report Template". Cover at minimum:
- Which AC/DoD items were met vs. not met.
- Risks/issues encountered throughout (including ones already fixed) - including any that were raised
  to the user.
- List of files changed.
- Number of fix attempts used per issue (so the user can see the actual difficulty).

No separate confirmation checkpoint is needed here - proceed straight to Step 5 after reporting (logging
is a low-risk side effect, easy to amend later if the user's feedback on the report changes something).

## Step 5 - Knowledge Capture (immediately after Step 4, no checkpoint needed)

Templates for both files below: see `references/report-and-logs.md`.

1. Memory/MCP (if connected): record key decisions and the final outcome.
2. Changelog file: `docs/changelog/<feature-slug>.md` - derived from `docs/plans/<feature-slug>.md`
   (the chosen proposal + its diagrams, updated if the design changed during implementation), plus: the
   rationale for the chosen proposal, final AC/DoD status (met/not met), remaining risk, and the list of
   files changed. This is the record of what was ACTUALLY built for this feature (unlike `docs/plans/`,
   which only records the proposals at decision time) - it does not belong in `docs/decisions/` because
   once complete it's a change log, not a standalone decision record.
3. **Experience log (required, cumulative, never overwritten)**: append to
   `docs/knowledge/experience-log.md` - for every issue hit in Step 3.3 (whether fixed or not), one
   entry per issue using the template in `references/report-and-logs.md`.

Purpose: the next time a similar issue comes up (same project or a different one), reading this file
first avoids retrying an approach already known not to work.

## Boundaries

- This skill owns the *workflow* (requirements → proposal → implement/test loop → report → knowledge
  capture) - it holds no language/framework/database-specific knowledge itself. Any technical
  implementation detail comes from the matching technical skill, read in full at the point it's applied
  (Step 3.1); never improvise technical conventions this workflow doesn't own.
- Steps 1-2 are deliberately run as `business-analyst`/`solution-architect` subagents rather than done
  directly here, so that requirements analysis and solution design happen with no `Edit`/`Write` tool
  available at all - a checkpoint enforced by the tool set, not just by asking nicely. This is why this
  file's own job through Step 2 is orchestration (launch the subagent, resolve `open_questions` with the
  user, refine the proposal to this workflow's documentation bar) rather than doing the analysis/design
  itself. Step 3 runs directly in the main thread as before, since implementation genuinely needs
  `Edit`/`Write` and is already gated by `skill-gate`/`checkpoint-gate`/`quality-gate`.
- This skill is for **new capability or intentionally changed behavior** only. If the current behavior
  is actually wrong (a defect), that's `bug-fix`'s job, even if the user phrases the request as
  "improve X" - `workflow-router` makes this classification; if invoked directly without going through
  the router, check first whether the request is really a defect fix in disguise. If the request must
  NOT change any external behavior (pure structural/performance cleanup), that's `refactor`'s job.
- This skill decides *what* to test and *when* in the loop (Step 3.2's quality gate) - the actual test
  design, mocking strategy, and test architecture depend on the relevant technical skill and, for
  broader test strategy questions, `test-master`.
- Step 2 produces a requirements/design document (`docs/plans/<feature-slug>.md`) as part of this
  workflow, not as a standalone deliverable - if the user wants only a requirements document with no
  implementation to follow, say so explicitly after Step 2's CHECKPOINT instead of silently continuing
  into Step 3.
- This skill does not perform a dedicated security or architecture review beyond what's needed to reach
  the DoD - for a deeper pass, coordinate with `secure-code-guardian` or `architecture-designer`, or
  `solution-design-principles` to check a design against foundational engineering principles (SOLID,
  coupling/cohesion, Well-Architected, 12-Factor) before it is built.
