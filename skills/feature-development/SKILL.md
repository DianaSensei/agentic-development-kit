---
name: feature-development
description: End-to-end workflow for building a new feature — requirements analysis, solution proposal, implement/test/fix loop until quality bar is met, then reporting and knowledge capture. Fully technology-agnostic — invokes whichever technical skills the task needs. Works for any project or stack.
argument-hint: "[feature request description]"
---

# Feature Development Workflow

Runs as a single agent, sequentially. This skill holds no technology-specific knowledge itself —
implementation details (language, framework, database, messaging, etc.) come from whichever technical
skill matches the task.

Input: `$ARGUMENTS`

## Step 0 — Discover Context

Read `CLAUDE.md`, memory/MCP if connected, and the existing code/logic relevant to this request. If
`workflow-router` already read these in this same session immediately before handing off, reuse that —
don't re-read from scratch.

This skill also has its own `references/` for requirement-gathering *method* (not technology
knowledge) — load each when its matching step is reached: `ears-syntax.md`, `interview-questions.md`,
`acceptance-criteria.md`, `specification-template.md`, `diagram-guide.md`, `definition-of-done.md`,
`report-and-logs.md`.

**Optional pre-discovery**: if the feature touches 3+ distinct system layers (auth, DB, UI...), the
codebase is unfamiliar or undocumented, or concrete technical facts are needed before requirements can
be asked intelligently — launch parallel Task subagents invoking the relevant technical skills to
gather that context *before* Step 1's interview, so the interview focuses on decisions instead of
exploration. Skip this for a well-scoped, single-domain feature or a codebase already well understood.
See `references/interview-questions.md` → "Multi-Agent Pre-Discovery" for the full pattern.

## Step 1 — Requirements Analysis (dual role: PM + Dev, technology-agnostic)

Restate the request in your own words (re-verify understanding), and list assumptions plus ambiguous
points. Stop and ask the user if anything doesn't add up — never guess at intent.

Interview using two perspectives in parallel (see `references/interview-questions.md` for the full
question sets per category):
- **PM lens**: user value, the problem being solved, scope (in/out, MVP vs. full), success criteria,
  priority.
- **Dev lens**: technical feasibility, systems/APIs/DBs touched, security requirements (auth, sensitive
  data), performance, edge cases, external dependencies.

Use `AskUserQuestion` for any question with a finite, enumerable set of likely answers (priority,
format, MVP vs. full scope, etc.); use open-ended questions only when the answer space can't be
enumerated in advance (e.g. "describe the user journey in your own words"). Don't ask a free-text
question when a structured choice would work just as well.

## Step 2 — Solution Proposal (technology-agnostic; references technical skills only by name)

1. Read the existing architecture/conventions — propose something consistent with them; don't invent
   an unfamiliar pattern without a clear reason.
2. Write the Functional Requirements in EARS format (see `references/ears-syntax.md`) — each
   requirement is one unambiguous sentence: `While <precondition>, when <trigger>, the system shall
   <response>` (or the matching Ubiquitous/Event/State/Optional variant).
3. If more than one direction is reasonable, present them as separate, distinct proposals. Every
   proposal must include the diagrams that actually apply to it (see `references/diagram-guide.md` for
   which diagram types are mandatory vs. conditional vs. skip, with templates) — Flow and Sequence
   diagrams are always required; Architecture/Component diagrams are required only if the proposal
   changes system boundaries or adds/removes a service/module; an ERD is required only if the proposal
   changes the data model/schema. Don't draw a diagram type that doesn't apply to the change's scope.
   Beyond diagrams, every proposal also includes:
   - Relevant Non-Functional Requirements (performance, security, scalability) where there's a concrete
     constraint — never invent a number when it isn't known; write "needs confirmation" instead of
     guessing.
   - Trade-offs versus the other proposal(s).
   - Acceptance Criteria in Given/When/Then form, meeting the INVEST bar (see
     `references/acceptance-criteria.md`), plus Edge Cases and a Definition of Done for this proposal.
   - An Error Handling table (error condition → response/status → message) for any new logic, where
     applicable.
   - The task list to complete — for each task, note which technical skill it's expected to draw on
     when implemented; no need to spell out technology detail here.
4. Write the full contents of this step (every proposal — FR/EARS, diagrams, NFRs, trade-offs,
   AC/Edge Cases/DoD, error handling, task list) to `docs/plans/<feature-slug>.md`, following the
   section layout in `references/specification-template.md`. This file is the durable record for later
   reference — it does not replace presenting the full proposal directly to the user in conversation.
5. A recommended proposal with rationale is fine to offer; never pick one on the user's behalf.

**CHECKPOINT (required)**: present the full proposal (already written to `docs/plans/<feature-slug>.md`)
and wait for the user to confirm the requirements/solution. Do not proceed to Step 3 without an
explicit confirmation.

Immediately after the user decides at the CHECKPOINT: update `docs/plans/<feature-slug>.md` — move the
chosen proposal to the top, clearly marked (e.g. `## ✅ Chosen: <name>`); move rejected proposals below
it, each wrapped in `<details><summary>Rejected: <name></summary> ... </details>` so they render
collapsed by default on renderers that support it (GitHub, VS Code preview, etc.).

## Step 3 — Implement + Test (loop until the quality bar is met)

### 3.1 Implement

Before writing any code for a piece of work that falls under a technical skill (e.g. the Java/Spring
part → `java-spring-skill`, the DB part → `database-skill`) — you MUST `Read` the full `SKILL.md` for
that skill at that point, never inferring its content from its name alone. A skill's name never
substitutes for reading its actual content before applying it.

**Don't reuse a previous request's read within the same session**: if this is a NEW user request
(different from one already handled earlier in this conversation), `Read` the relevant skill again from
scratch, even if you "remember" reading it last turn — its content may have changed between turns (the
user may have just edited it). A skill only counts as "already read" within the continuous scope of the
SAME request/task currently being worked, never carried across separate requests.

If one task touches MULTIPLE skills (e.g. both Java/Spring and Database), read all of them fully before
writing any code for that task — don't read one, code some, then read the next.

Once read, follow that skill's conventions/knowledge exactly — don't invent an approach from general
background knowledge when the matching skill already specifies one.

### 3.2 Test

Write and run tests per the relevant technical skill (unit/integration/functional, as fits the project).
Check results against:

- Every Acceptance Criterion finalized in Step 2.
- Every listed Edge Case.
- The Definition of Done.
- **Quality bar** (see `references/definition-of-done.md` for the full checklist): tests pass, no
  open severe defects, coverage is adequate for every important AC — a token test that skips an AC
  does not count.

### 3.3 If the quality bar isn't met — enter the fix loop

For EACH issue/failure found (a failing test, a problem self-identified during review):

1. Diagnose the cause, fix it, re-run the relevant tests. This is **attempt #1** for this issue.
2. Still failing: retry, incrementing the counter for that issue (#2, #3...).
3. **Maximum 5 attempts per distinct issue.** If still unresolved after the 5th attempt — STOP, do not
   try again, raise it to the user: describe the issue, what was tried on each attempt, why it's still
   unresolved, and what decision is needed from the user (a different approach, accepting a limitation,
   or more information).
4. A NEW issue (distinct from the one being worked) gets its own counter with its own 5 attempts — never
   pool attempt counts across different issues.
5. Once an issue is resolved, re-run ALL relevant tests (not just that issue's test) to confirm nothing
   else broke, then return to 3.2.

Repeat 3.1 → 3.2 → 3.3 until the quality bar, AC, and DoD are all met, OR an issue has to be raised to
the user (stop the workflow there — never treat it as done unilaterally).

## Step 4 — Final Report (required)

Report format: see `references/report-and-logs.md` → "Final Report Template". Cover at minimum:
- Which AC/DoD items were met vs. not met.
- Risks/issues encountered throughout (including ones already fixed) — including any that were raised
  to the user.
- List of files changed.
- Number of fix attempts used per issue (so the user can see the actual difficulty).

No separate confirmation checkpoint is needed here — proceed straight to Step 5 after reporting (logging
is a low-risk side effect, easy to amend later if the user's feedback on the report changes something).

## Step 5 — Knowledge Capture (immediately after Step 4, no checkpoint needed)

Templates for both files below: see `references/report-and-logs.md`.

1. Memory/MCP (if connected): record key decisions and the final outcome.
2. Changelog file: `docs/changelog/<feature-slug>.md` — derived from `docs/plans/<feature-slug>.md`
   (the chosen proposal + its diagrams, updated if the design changed during implementation), plus: the
   rationale for the chosen proposal, final AC/DoD status (met/not met), remaining risk, and the list of
   files changed. This is the record of what was ACTUALLY built for this feature (unlike `docs/plans/`,
   which only records the proposals at decision time) — it does not belong in `docs/decisions/` because
   once complete it's a change log, not a standalone decision record.
3. **Experience log (required, cumulative, never overwritten)**: append to
   `docs/knowledge/experience-log.md` — for every issue hit in Step 3.3 (whether fixed or not), one
   entry per issue using the template in `references/report-and-logs.md`.

Purpose: the next time a similar issue comes up (same project or a different one), reading this file
first avoids retrying an approach already known not to work.

## Boundaries

- This skill owns the *workflow* (requirements → proposal → implement/test loop → report → knowledge
  capture) — it holds no language/framework/database-specific knowledge itself. Any technical
  implementation detail comes from the matching technical skill, read in full at the point it's applied
  (Step 3.1); never improvise technical conventions this workflow doesn't own.
- This skill is for **new capability or intentionally changed behavior** only. If the current behavior
  is actually wrong (a defect), that's `bug-fix`'s job, even if the user phrases the request as
  "improve X" — `workflow-router` makes this classification; if invoked directly without going through
  the router, check first whether the request is really a defect fix in disguise. If the request must
  NOT change any external behavior (pure structural/performance cleanup), that's `refactor`'s job.
- This skill decides *what* to test and *when* in the loop (Step 3.2's quality gate) — the actual test
  design, mocking strategy, and test architecture depend on the relevant technical skill and, for
  broader test strategy questions, `test-master`.
- Step 2 produces a requirements/design document (`docs/plans/<feature-slug>.md`) as part of this
  workflow, not as a standalone deliverable — if the user wants only a requirements document with no
  implementation to follow, say so explicitly after Step 2's CHECKPOINT instead of silently continuing
  into Step 3.
- This skill does not perform a dedicated security or architecture review beyond what's needed to reach
  the DoD — for a deeper pass, coordinate with `secure-code-guardian` or `architecture-designer`, or
  `solution-design-principles` to check a design against foundational engineering principles (SOLID,
  coupling/cohesion, Well-Architected, 12-Factor) before it is built.
