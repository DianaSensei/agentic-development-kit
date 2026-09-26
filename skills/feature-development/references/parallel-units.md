# Parallel Units

How Step 3.1 builds independent parts of an approved plan at the same time, each by a
`unit-implementer` agent in its own git worktree, and brings them back into the working tree.

Parallel work saves wall-clock time and costs tokens: every agent reads the code and the skills
again in its own context. It pays for units that each take real work. For a change of a few edits,
build it sequentially.

## When units may run in parallel

All of these, or the plan is built sequentially as usual:

1. **The approved plan declares them.** The plan's `## Parallel units` section, written in Step 2
   from `solution-architect`'s `task_breakdown` and shown at the CHECKPOINT, names two or more units.
   The user approved the plan with it, so running them in parallel is not a new decision. A unit
   the plan does not declare is never parallelised on the lead agent's own judgment.
2. **No dependency between them.** No unit is in another's `depends_on`. A task that depends on a
   parallel unit runs after the units have been applied.
3. **Disjoint files.** No path, and no directory prefix, appears in two units' `files`. A shared
   registry, route table, barrel file, lockfile or config that each unit would add a line to is
   the classic hidden overlap. Keep it out of every unit and edit it once, after applying them.
4. **A git repository with a commit to branch from**, and no uncommitted change to any path in any
   unit's `files`: a worktree starts from a commit, so it would not see such a change.

## Before dispatching

- `base_commit`: `git rev-parse HEAD` in the working tree.
- The unit's context that is not at `base_commit`: the plan (just written, usually uncommitted),
  an API contract materialised in 3.1. Pass the relevant excerpt inline as `plan_excerpt` and
  `context_files`. If a unit would need a whole uncommitted module to build on, it depends on
  that work: build that first, sequentially, and leave the unit out of the parallel set.
- Read the owning skills yourself as usual (3.1). The agents read them too: they run in their own
  context, where your reads do not count, and the workflow's skill gate does not check a
  subagent's edits. Naming the skills in the prompt is what makes them read.

## Dispatch

One `unit-implementer` per unit, **all in a single message** so they run at the same time. Each
prompt carries, with these literal labels: `unit` (id, task, `files`, the acceptance criteria and
edge cases it owns), `plan_excerpt`, `base_commit`, `skill_paths` (the technical skills that
own the unit's files, each with the path of the `SKILL.md` you read: the ones you read for it, and
any the project's `skill_map` in `.claude/quality-check.config.json` names for those paths),
`context_files` if any, and
`specialist` with `specialist_path` when `task_breakdown` assigned the unit to a Tier-2 agent
that exists. Write project
paths relative to the repository root: the agent works in its worktree, and an absolute path into
your tree points it at your copy instead. The agent's
frontmatter sets `isolation: worktree`; each result names its worktree's path and branch.

## Bringing the units back

For each unit, in the plan's order:

1. Check its output. `checkpoint.required`, `open_questions`, or `test_run_result` FAIL: resolve
   with the user before applying anything from that unit, as for any Tier-2 agent.
2. Check scope: `git diff --name-only <base_commit> <branch>` lists only paths inside the unit's
   `files`. A path outside is not applied silently: tell the user which, and why the agent said it
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

Then make the edits the units reported in `outside_files_needed` (the shared registry lines),
run the whole test suite with the project's documented command (Step 3.2 as usual: the units' own
tests passed in isolation, which says nothing about them together), and continue. Look for
conventions the units settled differently (an import style, a fixture, a helper each wrote for
itself): each agent chose alone, and the change should read as one piece.

## Reporting

The Step 4 report lists the units that ran in parallel, each unit's test result, any unit built
sequentially after a failed apply and why, and any outside-scope path a unit asked for.

## Settings that help

- `"worktree": {"baseRef": "head"}` in `.claude/settings.json` makes worktrees branch from the
  local HEAD instead of the default branch. The agent resets to `base_commit` either way, so it is
  a convenience, not a requirement.
- The worktrees live under `.claude/worktrees/`, and `git status` lists them while they exist.
  Adding `.claude/worktrees/` to `.gitignore` keeps them out of it.
