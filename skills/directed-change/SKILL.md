---
name: directed-change
description: The path for a code change where the user brings the plan - the steps, the approach, the files to change or the order to do it in - and wants it carried out as given, not redesigned. Follows their steps in their order with the machine checks still on (owning skill read, the project's convention checks, tests run, self-review), and no analyst, architect, alternative proposals, plan document or Checkpoint - their plan is the approval. Stops and asks when a step contradicts the code, needs a decision the plan does not make, or carries a risk it does not mention; never works around the plan. workflow-router sends a change here whenever the request already says how; also "follow my steps", "do exactly this", "làm theo sườn này". Not for a request that names only the outcome - that is workflow-router's classification.
hooks:
  PreToolUse:
    - matcher: "Edit|Write|MultiEdit|NotebookEdit"
      hooks:
        - type: command
          command: "\"${CLAUDE_PLUGIN_ROOT}/hooks/edit-gates.sh\""
          timeout: 15
          statusMessage: "Checking the owning skill was read..."
  Stop:
    - hooks:
        - type: command
          command: "\"${CLAUDE_PLUGIN_ROOT}/hooks/quality-gate.sh\""
          timeout: 30
          statusMessage: "Quality gate..."
metadata:
  domain: workflow
  triggers: follow my plan, my steps, do exactly this, here is the approach, carry out these steps
  role: orchestrator
  scope: implementation
  output-format: code
  related-skills: workflow-router, quick-change, code-review-skill, reflect, feature-development, bug-fix, refactor
---

# Directed Change

The other workflows assume the agent works out what to do and the user approves it. Here the user has
already worked it out: the steps, the approach, sometimes the order and where to stop. Analysis they
did not ask for, alternatives to the approach they chose and a Checkpoint on a decision they already
made are all cost. The job is the one an implementer has with a ticket: carry the plan out exactly, and
say so the moment it proves wrong.

## What counts as the user's plan

The request says *how*, not only *what*: ordered steps, a named approach ("add a column and backfill it
in the nightly job"), the files or functions to change, the order to change them in. A plan can be
short. A request that names only the outcome ("add discounts to checkout") is not one - it goes through
`workflow-router` as usual. A plan may say where to stop ("do 1 and 2, then show me"); that stop is part
of the plan.

## Rules that hold throughout

- **Their steps, their order.** Each step as written: none added, skipped, merged or reordered, even
  when another order looks better - say so in the report instead.
- **No redesign.** No alternative approach, tradeoff table, analyst or architect agent, and no plan,
  intent or changelog file - unless they ask for one.
- **Their scope.** Change only what the plan names. Anything else that needs fixing goes in the
  report's "noticed, not touched".
- **When the plan is wrong, stop; never work around it.** A step that contradicts the code (a function
  that is not there, a field that means something else, a caller the plan did not count), needs a
  decision the plan does not make, or carries a risk it does not mention (data loss, a migration, auth,
  money, a public contract) → stop before that step. Say what the plan expects, what you found and where
  - the `path:line` or the document, with the line quoted (`feature-development`'s
  `references/sources.md`) - and ask one question with your suggested answer. Steps already done stay
  done; resume at the stopped step with their answer.
- **Their profile fills what the plan leaves open.** Where the plan is silent on how the code is
  written, their `## Code style` lines decide (the profile `reflect` keeps, or the same section in
  `~/.claude/CLAUDE.md`). The project's `CLAUDE.md`, `REVIEW.md` and checks still come first.
- **The checks still run**: the owning skill read before the edit (the skill gate holds it), the
  project's convention checks on every write, tests after the last edit and `code-review-skill` before
  "done" (the quality gate holds the turn). They are not a second opinion on the plan; they catch
  mistakes in carrying it out.

## Steps

1. **Read** the code each step touches - directly, with `Grep` and `Read` - and the owning technical
   skill's `SKILL.md`. Check the plan against what you read: every step's target exists and means what
   the plan assumes. A mismatch found here stops the run before any edit. A ticket the request names is
   read and linked as `workflow-router` → "A ticket in the request" says.
2. **Ask only about ambiguity.** A step that reads two ways gets one question, with your reading as the
   default. A clear plan is not restated back.
3. **Carry out each step in order**: the smallest change that does it, in the file's existing style.
   After each step, one line: what was done and where. Pause where the plan says to pause. With three or
   more steps, keep the session's task list (`TodoWrite`, or `TaskCreate`/`TaskUpdate`) one item per step,
   updated as each starts and ends, so the person can follow; a step that blocks is reported at once,
   in the profile's `## Report` order when it has one, not saved for the end.
4. **Test**: a behavior change gets a test that fails without it, unless the plan says otherwise; then
   run the project's tests and report the result as it is.
5. **Self-review**: `code-review-skill`'s checklist on the diff.
6. **Report**, in the profile's `## Report` order when it has one: each step - done, or stopped and
   why; files changed; the test command and its result; "noticed, not touched"; and, only where it
   matters, a step you would have done differently, one line each.

A correction the user makes during the run goes to the experience log, as in the other workflows
(`feature-development`'s `references/report-and-logs.md`); one about how they want a plan carried out
is also a `reflect` signal.

## Boundaries

- No Checkpoint: the user's plan is the approval, and the checkpoint gate does not hold this path. When
  the plan leaves a real decision open, the stop above is that decision's checkpoint - one question, not
  a proposal round.
- Size does not move a change off this path; a plan that touches ten files is still the user's plan.
  What does is the plan running out - what they gave does not say how to do the rest. Say so, and ask
  whether to extend the plan or take the rest through `workflow-router`.
- `quick-change` is for a small change with nothing to decide that the user did not plan;
  `directed-change` is for a change of any size whose decisions the user already made.
