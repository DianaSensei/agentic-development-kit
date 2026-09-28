---
name: worktrees
description: Organizes the user's parallel work in git worktrees by task - one folder per task under a root the user chose (~/worktrees/billing-feat-abc/{api,web}), holding a worktree of every repository the task touches, all on the task's branch. Starts a task across one or several repositories at once, shows every task's state across all projects (uncommitted, unpushed, pushed, already in its base), keeps each up to date with its base, runs a command in each, and removes finished tasks without losing work. Use when the user wants to start work without disturbing their current checkout, work on a change that spans repositories, switch between tasks, or see or clean up their worktrees and stale branches. Not for the unit worktrees feature-development creates under .claude/worktrees/ (its own, cleaned by its leftovers.sh), and not for opening pull requests (code-host).
metadata:
  domain: workflow
  triggers: worktree, git worktree, new task folder, multi-repo change, several repositories, parallel branches, switch task, clean up worktrees, stale branches
  role: specialist
  scope: implementation
  output-format: report
  related-skills: feature-development, code-host, workflow-router, project-setup
---

# Worktrees

Work is organized by **task**, not by repository. A task that changes an API and the web app that
calls it is one folder, with both repositories inside, on one branch:

```
~/worktrees/                       the root - the user's choice, set once
├── billing-feat-abc/              a task
│   ├── CLAUDE.md                  generated: the task, its branch, each repo's own CLAUDE.md imported
│   ├── api/                       a worktree of ~/code/api on billing-feat-abc
│   └── web/                       a worktree of ~/code/web on billing-feat-abc
└── fix-login-timeout/
    └── api/
```

Each repository's main checkout stays where it is, on whatever branch it was on. A worktree shares its
repository's history, so there is nothing to clone and a commit in one is visible in the others at once.

Everything goes through one script, `python3 <this skill's dir>/scripts/wt.py`. It does the git work
and holds the safety rules, so the rules do not depend on remembering them. Standard library only.

## First use: ask once, then remember

The root and the repositories are the user's, not the project's: they live in
`~/.config/adk/worktrees.json` and apply to every project.

1. **The root.** `wt.py init` shows what is set. If no root is set, ask the user where task folders
   should live (`AskUserQuestion`; suggest `~/worktrees`) and run `wt.py init --root <path>`. Never
   pick one yourself: it is a folder in their home they will open every day.
2. **The repositories.** A repository is registered the first time a task names it by path, under its
   folder name. Register it by hand when the name should differ, or when a fresh checkout needs more
   than the code:
   `wt.py repo add api ~/code/api --copy .env --copy .env.local --setup "npm ci"`.
   `--copy` names untracked files copied from the main checkout into each new worktree. It is how a
   worktree gets its `.env`. Ask the user which files; name them, never read them. `--setup` runs in
   each new worktree.

## Starting a task

```bash
wt.py new billing-feat-abc api web --note "Invoice totals include tax per line"
```

- **Name the repositories as the user did.** A path is relative to the session's folder (`code/api`),
  or absolute; a bare name is a registered repository (`wt.py repo list`). The script resolves and
  checks each one and says which it cannot find. Don't search the filesystem for them first; if one is
  not found, ask the user where it is.
- **The task name is the folder name**, and by default also the branch name. When the team has a
  branch convention (`feat/...`, a ticket key), pass `--branch`. Take the convention from `CLAUDE.md` or
  the repository's recent branches; if neither shows one, ask.
- **The base** is each repository's `origin/HEAD`, fetched first, so the task starts from what the team
  has now and not from a stale local `main`. Pass `--base` to branch from something else.
- **A branch that already exists** is checked out, not recreated. That covers a local branch, or one on
  `origin` (a teammate's, or a review), which is then tracked.
- **All or none.** If any repository fails (its branch is already checked out somewhere, or the base is
  missing), nothing is left behind: no folder, no worktree, no new branch.
- **Another repository later:** `wt.py add billing-feat-abc worker`. The task's `CLAUDE.md` is refreshed
  and anything the user wrote outside its generated block is kept.

Then tell the user where to open it. A session cannot move itself into another folder:
- **Cross-repository work:** start Claude Code in the task folder. Its `CLAUDE.md` imports each
  repository's own and says there is no repository at the top: git runs per folder, as
  `git -C api ...`.
- **One repository with the full workflow:** start Claude Code in that repository's folder. The kit's
  hooks and gates read the project's `.claude/quality-check.config.json`, which lives in each
  repository, not in the task folder.

## Working across repositories

- **Contract first.** When one repository calls another, change and test the provider's side (the API,
  the message, the schema) first. Then change the consumer against it, in the same task.
- **Commit and push per repository.** Each gets its own pull request (`code-host`). Link them to each
  other and say which merges first: the provider, when the consumer needs it.
- **Check them together:** `wt.py run billing-feat-abc -- npm test` runs a command in each repository
  and names the ones that failed. One argument is run by the shell, so `-- "make lint && make test"`
  works.

## Seeing everything

`wt.py status` lists every task under the root, each repository's state, and worktrees of registered
repositories that live outside the root. Name tasks to narrow it, pass `--fetch` to compare against the
remote as it is now, and `--json` to read it programmatically.

| State | Meaning | Safe to remove |
|---|---|---|
| `uncommitted` | changes not committed | no |
| `unpushed` | commits no remote has | no |
| `remote-gone` | commits no remote has, and the branch's remote copy was deleted - usually a squash merge | only once the pull request is confirmed merged |
| `pushed` | every commit is on a remote; not in the base yet | yes - the work is on the remote |
| `in-base` | everything on the branch is already in its base (merged, or nothing done yet) | yes |

A repository shown `on <other branch>` was switched by hand inside the task. Say so; don't switch it
back yourself.

## Keeping up

`wt.py sync billing-feat-abc` fetches, then merges each repository's base into it.
- **Skipped:** a repository with uncommitted changes. Commit or stash first.
- **Conflicts:** the merge is undone, the repository is left exactly as it was, and the conflicting
  files are named. Resolve them deliberately with the command it prints; a conflict is never resolved
  for the user silently.
- **`--rebase`** is for a branch that has never been pushed: rebasing a pushed branch would need a force
  push, so the script refuses it.

## Finishing

- `wt.py remove <task>` removes the task's worktrees, then its folder. Files the user added there (notes,
  scratch) are kept. Each branch is deleted only if it is merged; otherwise it is kept.
- It **refuses** when a repository holds work no remote has, uncommitted or unpushed, and names it.
- `--force` goes ahead anyway. Uncommitted changes are saved as a patch under `<root>/.removed/<task>/`
  first, and a branch with unpushed commits is always kept. Ask the user before passing it, and for
  `remote-gone` confirm the pull request was merged (`code-host`) first.
- `wt.py prune` lists the tasks whose every branch is already in its base, and the `remote-gone` ones to
  check. `prune --yes` removes the first kind; show the list and get the user's yes before running it.

## Rules

- **Never `rm -rf` a worktree folder.** Git keeps a record of every worktree, and deleting the folder
  leaves that record and the branch behind. Remove through the script, or `git worktree remove`.
- **Never lose work.** Nothing here discards uncommitted changes or unpushed commits: the script refuses,
  or keeps them as a patch and a branch. Do not work around a refusal with plain git commands.
- **Only the root is managed.** Worktrees elsewhere are listed, never removed. The kit's own unit
  worktrees under `.claude/worktrees/` belong to `feature-development` and are not even listed.
- **One branch, one place.** Git checks a branch out in one worktree at a time. When a task needs a
  branch that is checked out elsewhere, the script says where; switch it there, or use another branch.

## Boundaries

- **Which workflow the change needs** (quick change, feature, bug fix, refactor) is `workflow-router`'s
  call. This skill only gives the change a place to happen.
- **Unit worktrees** that `feature-development` creates for parallel units under `.claude/worktrees/`,
  and their cleanup (`leftovers.sh`), are that workflow's.
- **Pull requests** - opening, linking, checking merge state - are `code-host`'s.
- **The repository's own settings** (`.gitignore`, hooks, CI) are `project-setup`'s. Task folders live
  outside every repository, so no repository needs a `.gitignore` entry for them.
