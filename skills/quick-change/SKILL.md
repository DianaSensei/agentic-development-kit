---
name: quick-change
description: The fast path for a small, local code change with one obvious form - a typo or message fix, a rename inside one module, a small bug whose fix is plain, a config value, a test to add - done directly with the machine checks still on (owning skill read, the project's convention checks, tests run, self-review), and no analyst, architect, plan document or Checkpoint. workflow-router sends a change here only when it meets every entry criterion, and a Stop hook sends it back when the diff outgrows them. Not for anything with a decision in it, a public contract, a schema or migration, security, auth, money, a new dependency, or more than a few files - those go to feature-development, bug-fix or refactor.
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
          command: "\"${CLAUDE_PLUGIN_ROOT}/hooks/quick-change-scope.sh\""
          timeout: 15
          statusMessage: "Checking the change still fits the quick path..."
        - type: command
          command: "\"${CLAUDE_PLUGIN_ROOT}/hooks/quality-gate.sh\""
          timeout: 30
          statusMessage: "Quality gate..."
metadata:
  domain: workflow
  triggers: quick fix, small change, typo, rename, tweak, just do it
  role: orchestrator
  scope: implementation
  output-format: code
  related-skills: workflow-router, code-review-skill, feature-development, bug-fix, refactor
---

# Quick Change

The full workflows cost minutes and several agent runs; that pays for a change with a decision in it
and is waste for one without. This path does the change directly and keeps only what is cheap and
proven: the owning skill read before the edit, the project's own checks on every write, the tests run
after the last edit, and a self-review. The checks are enforced by hooks, not by this text.

## Entry criteria (all of them)

`workflow-router` checks these before sending a change here; check them again once you have read the
code, because reading is when a "small" change shows its size.

1. **One obvious form.** Nothing for the user to decide - no limit, policy, name for a new concept,
   tradeoff or behavior choice. A bug fix qualifies only when the right behavior is not in question.
2. **Small and local**: about 3 files and 60 changed lines at most, tests included.
3. **No expensive path**: no schema or migration, public API or message contract, auth or security,
   payments or other money, CI or deployment configuration, dependency added or upgraded, and nothing
   under `.claude/` or in `CLAUDE.md`.
4. **The user asked for this change**, not for an investigation.

Any one fails → this is not a quick change. Hand it back to `workflow-router` with what you read, and
say in one line why.

The user can override either way. "Full process for this one" goes to the full workflow whatever the
size. "Just do it" on a change that fails a criterion: say in one line what makes it risky, then follow
their call - the checks below still run.

## Steps

1. **Read** the code you will change - directly, with `Grep` and `Read`; a subagent costs more than the
   whole change - and the owning technical skill's `SKILL.md` if one owns it (the skill gate holds the
   edit until you have).
2. **Change it**, the smallest change that does the job, in the file's existing style.
3. **Test**: a behavior change gets a test that fails without it; then run the project's tests. The
   quality gate wants a test run after your last edit - and report its result as it is.
4. **Self-review**: `code-review-skill`'s checklist on the diff (the quality gate wants it read after
   your last edit).
5. **Report** in a few lines: what changed and where, the test command and its result, anything you
   noticed but left alone. No plan document, intent, changelog or postmortem - a quick change is
   recorded by its commit.

A user correction during a quick change still goes to the experience log, as in the full workflows
(`feature-development`'s `references/report-and-logs.md`): the learning loop does not depend on the
path.

## When it grows

The Stop hook compares the finished diff against the entry criteria - file count, line count, the
expensive paths. It fires when a quick change quietly became something else. Then stop, hand the
change to `workflow-router` for the full workflow with what you learned, and let the user decide
whether to keep what is written so far.
