# Parallel Units

How Step 3.1 builds an approved plan's units in **waves** - every unit whose dependencies are done, at
the same time, each by a `unit-implementer` agent in its own git worktree - brings them back into the
working tree, and answers a unit's question without throwing its work away.

Parallel work saves wall-clock time and costs tokens: every agent reads the code and the skills
again in its own context. It pays for units that each take real work. For a change of a few edits,
build it sequentially.

## When units may run in parallel

All of these, or the plan is built sequentially as usual:

1. **The approved plan declares them.** The plan's `## Parallel units` section, written in Step 2
   from `solution-architect`'s `task_breakdown` and shown at the CHECKPOINT, names two or more units,
   each with its `files` and what it `depends_on`.
   The user approved the plan with it, so running them in parallel is not a new decision. A unit
   the plan does not declare is never parallelised on the lead agent's own judgment.
2. **Dependencies are declared, and form waves.** Each unit's `depends_on` names the units it builds
   on. Wave 1 is every unit with none; wave *n* is every unit whose dependencies are all in earlier
   waves. Units in the same wave never depend on each other. A cycle means the plan is wrong - back
   to the user, never guessed around.
3. **Disjoint files within a wave.** No path, and no directory prefix, appears in two units' `files`
   in the same wave. A shared
   registry, route table, barrel file, lockfile or config that each unit would add a line to is
   the classic hidden overlap. Keep it out of every unit and edit it once, after applying them.
4. **A git repository with a commit to branch from**, and no uncommitted change to any path in any
   unit's `files`: a worktree starts from a commit, so it would not see such a change.

## Waves

A wave with one unit is built by you, in the working tree, as ordinary Step 3.1 work: a worktree and
an agent for a single unit cost more than they save. A wave with two or more units is dispatched as
below. Between waves:

1. Bring the wave's units back (below), make their `outside_files_needed` edits, and run the whole
   test suite. A failure is fixed now - the next wave builds on this one.
2. **Snapshot** the working tree when the next wave dispatches agents (a one-unit wave you build
   yourself needs none):
   `bash <this skill's dir>/scripts/snapshot.sh take <wave number>` prints a commit holding the tree as
   it is, on top of HEAD, on no branch - the user's branch and staging area stay exactly as they were
   - and that sha is the next wave's `base_commit`. A worktree can only start from a commit, and the
   workflow never commits on the user's branch; this is how wave 2 sees wave 1's code.
3. After the last wave, `bash <this skill's dir>/scripts/snapshot.sh drop` removes the snapshots'
   refs.

## Before dispatching

- `base_commit`: for wave 1, `git rev-parse HEAD` in the working tree; for later waves, the snapshot
  taken after the previous wave.
- The unit's context that is not at `base_commit`: the plan (just written, usually uncommitted),
  an API contract materialised in 3.1. Pass the relevant excerpt inline as `plan_excerpt` and
  `context_files`. If a unit would need a whole uncommitted module to build on, it depends on
  that work: build that first, sequentially, and leave the unit out of the parallel set.
- Read the owning skills yourself as usual (3.1). The agents read them too: they run in their own
  context, where your reads do not count, and the workflow's skill gate does not check a
  subagent's edits. Naming the skills in the prompt is what makes them read.

## Dispatch

The kit's dispatch gate denies a `unit-implementer` dispatch until this file has been read in the
session, and until the prompt carries `lane`, `base_commit` and `ticket` (or `candidate`). A denial
names what is missing.

One `unit-implementer` per unit, **all in a single message** so they run at the same time. Its
`subagent_type` is `adk-adlc:unit-implementer` - a plugin's agents carry the plugin's prefix. Each
prompt carries, with these literal labels: `unit` (id, task, `files`, the acceptance criteria and
edge cases it owns), `lane` (the unit's `files` again, as a JSON array on one line - `lane:
["src/shop/orders.py", "scripts/"]` - which the lane guard reads), `ticket` (the unit's ticket from the
plan's `## Tickets`, inline: the plan is usually uncommitted, so it is not in the unit's worktree),
`plan_excerpt`, `base_commit`, `skill_paths` (the technical skills that
own the unit's files, each with the path of the `SKILL.md` you read: the ones you read for it, and
any the project's `skill_map` in `.claude/quality-check.config.json` names for those paths),
`context_files` if any, and
`specialist` with `specialist_path` when `task_breakdown` assigned the unit to a Tier-2 agent
that exists. Pick the model by the ticket's tier (`tickets.md` → "Who builds what"): a **tight**
ticket goes out with the Agent tool's `model` set to `models.build`; a **loose** one with no `model`,
so it runs on your own. Write project
paths relative to the repository root: the agent works in its worktree, and an absolute path into
your tree points it at your copy instead. The agent's
frontmatter sets `isolation: worktree`; each result names its worktree's path and branch.

## A unit with a question: answer, then resume

A unit that meets a decision it does not own, or finds its ticket wrong (`plan_mismatch`), stops,
commits what it has (`WIP <unit>: ...`), and returns `checkpoint.required` with the question or the
mismatch. Its worktree, branch and context are still there -
do not redo the unit:

1. **Answer from what is already decided**, when the plan, the intent, `CLAUDE.md` or an earlier answer
   settles it: quote where.
2. **Otherwise ask the user** (`AskUserQuestion` - only you can; the agent cannot). Units of the same
   wave that do not depend on the question keep going; only this unit and those that depend on it
   wait.
3. **Resume the same agent** with `SendMessage` (a deferred tool - load it with `ToolSearch`), to the
   agent id its result gave: the answer, and where it came from. It continues in its own worktree,
   with everything it already read. Its next result arrives as a notification.
4. No `SendMessage` in this session, or the agent is gone: dispatch a fresh `unit-implementer` with the
   answer and `resume_from: <its branch>` - its WIP commit is the starting point, not a blank one.

A question that changes the plan itself - scope, an acceptance criterion, a unit's `files` - is the
user's CHECKPOINT again, not an answer to relay: stop the dependent units and put the change to them.

## Bringing the units back

For each unit, in the plan's order:

1. Check its output. `open_questions` or `checkpoint.required` → the section above. `test_run_result`
   FAIL → resume the agent with what the failure is, the same way, before applying anything from it.
2. Check scope: `git diff --name-only <base_commit> <branch>` lists only paths inside the unit's
   `files`. The lane guard (`tickets.md` → "Lanes") already denied its edits outside them; this catches
   what it cannot see, such as a file written from Bash. A path outside is not applied silently: tell the user which, and why the agent said it
   needed it.
3. Apply it to the working tree, uncommitted, like every other change this workflow makes:
   ```bash
   git diff --binary <base_commit> <branch> > "$tmp/<unit-id>.patch"
   git apply --check "$tmp/<unit-id>.patch" && git apply "$tmp/<unit-id>.patch"
   ```
   The workflow never commits on the user's branch; the unit's commit stays on its own branch.
4. `git apply --check` fails: the units overlapped after all. Apply nothing from it; build that
   unit sequentially in the working tree, using its branch as a reference, and log it for the
   Step 4 report.
5. Clean up once the patch is applied or abandoned: `git worktree remove --force <path>` and
   `git branch -D <branch>`. `--force` because the unit's test run leaves untracked caches behind;
   the unit's work is in its commit, already applied. They are this workflow's own temporary
   worktree and branch, nothing else; never remove one you did not create.

Then make the edits the units reported in `outside_files_needed` and the plan's `owner: lead` ticket (the
shared registry lines),
run the whole test suite with the project's documented command (Step 3.2 as usual: the units' own
tests passed in isolation, which says nothing about them together), and continue. Look for
conventions the units settled differently (an import style, a fixture, a helper each wrote for
itself): each agent chose alone, and the change should read as one piece.

## Reporting

The Step 4 report lists the waves and the units in each, each unit's test result, every question a
unit raised with who answered it and how, any unit built sequentially after a failed apply and why,
and any outside-scope path a unit asked for.

## Settings that help

- `"worktree": {"baseRef": "head"}` in `.claude/settings.json` makes worktrees branch from the
  local HEAD instead of the default branch. The agent resets to `base_commit` either way, so it is
  a convenience, not a requirement.
- The worktrees live under `.claude/worktrees/`, and `git status` lists them while they exist.
  Adding `.claude/worktrees/` to `.gitignore` keeps them out of it.
