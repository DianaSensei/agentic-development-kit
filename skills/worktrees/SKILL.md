---
name: worktrees
description: Organizes the user's parallel work by task - one folder per task under a root the user chose, holding a checkout of every repository the task needs (worktrees on the task's branch for the ones it changes, pinned at a tag or commit for the ones it builds against) and a manifest, task.json, that records each one's role and version and the task's build and test, and rebuilds the workspace elsewhere. Checks a task as a whole and records the commit of every repository each check ran on, gives each task its own ports, compose project and cache, shows every task's state, syncs with bases, and removes finished tasks without losing work. Use when the user wants to work without disturbing their checkout, change several repositories, build against others at a known version, run tasks or agents in parallel, or clean up worktrees. Not for feature-development's unit worktrees under .claude/worktrees/, nor pull requests (code-host).
metadata:
  domain: workflow
  triggers: worktree, git worktree, new task folder, multi-repo change, several repositories, pinned dependency, build against, integration test across repositories, parallel tasks, parallel agents, switch task, clean up worktrees, stale branches, task manifest
  role: specialist
  scope: implementation
  output-format: report
  related-skills: feature-development, code-host, workflow-router, project-setup
---

# Worktrees

Work is organized by **task**, not by repository. A task is one folder holding everything it needs to be
built and tested - the repositories it changes, the ones it builds against, its sample data - each at the
version this task needs, and a manifest that says so:

```
~/worktrees/                          the root - the user's choice, set once
├── billing-feat-abc/                 a task
│   ├── task.json                     the manifest: roles, versions, build, test, env
│   ├── CLAUDE.md                     generated: the task, each folder's role, each repo's CLAUDE.md imported
│   ├── task.env                      generated: the task's own ports, compose project, cache folder
│   ├── checks.jsonl                  every check: result, and the commit of each repository it ran on
│   ├── api/                          edit: a worktree of ~/code/api on billing-feat-abc
│   ├── web/                          edit: a worktree of ~/code/web on billing-feat-abc
│   ├── shared-lib/                   dependency: a worktree of ~/code/shared-lib detached at v2.3.0
│   └── fixtures/                     copied in from ~/data/billing-fixtures
└── fix-login-timeout/
    └── ...
```

A worktree belongs to one repository, so a task across four repositories holds four, and two such tasks
hold eight. Each repository's main checkout stays where it is, on whatever branch it was on; a worktree
shares its history, so there is nothing to clone.

Everything goes through one script, `python3 <this skill's dir>/scripts/wt.py`. It does the git work and
holds the safety rules, so the rules do not depend on remembering them. Standard library only.

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
   each new worktree, with the task's environment.
3. **Where to clone** (only for `restore` on a machine that lacks a repository):
   `wt.py init --sources ~/code`. Ask before setting it; without it, `restore` clones nothing.

## Starting a task

Before the command, settle with the user - or from the request - what the task needs:

- **Which repositories it changes** (edit) and **which it only builds or tests against** (dependency).
  A dependency is still a folder in the task: the task builds against *that* version, not whatever
  happens to be checked out somewhere.
- **The version of each dependency** - a tag or a commit for a stable one, a branch name to take origin's
  copy as it is now. The manifest records the commit either way.
- **What else it needs** that is not in a repository: sample data, local config (`--extra`).
- **How the task is built and tested as a whole** (`--build`, `--test`): one repository's tests passing
  says little when the change spans several.

```bash
wt.py new billing-feat-abc api web --dep shared-lib@v2.3.0 --dep build-tools@v5 \
  --extra ~/data/billing-fixtures:fixtures \
  --build "make -C api build" --test "make -C api integration-test" \
  --note "Invoice totals include tax per line"
```

- **Name the repositories as the user did.** A path is relative to the session's folder (`code/api`),
  or absolute; a bare name is a registered repository (`wt.py repo list`). The script resolves and
  checks each one and says which it cannot find. Don't search the filesystem for them first; if one is
  not found, ask the user where it is.
- **The task name is the folder name**, and by default also the branch name. When the team has a
  branch convention (`feat/...`, a ticket key), pass `--branch`. Take the convention from `CLAUDE.md` or
  the repository's recent branches; if neither shows one, ask.
- **The base** of an edit repository is its `origin/HEAD`, fetched first, so the task starts from what
  the team has now and not from a stale local `main`. `--base` sets one for all; `web@origin/release/2.x`
  sets one for that repository.
- **A branch that already exists** is checked out, not recreated. That covers a local branch, or one on
  `origin` (a teammate's, or a review), which is then tracked.
- **A dependency is never branched.** Its worktree is detached at the pinned commit, so two tasks that
  need different versions of `shared-lib` each have their own, and neither can move the other's.
- **Extras are copied, never linked.** A task's tests write to their fixtures; a link would let one
  task's run change another's.
- **All or none.** If any repository fails (its branch is already checked out somewhere, a ref is
  missing), nothing is left behind: no folder, no worktree, no new branch.
- **More later:** `wt.py add billing-feat-abc worker --dep notifier@v1`. The task's `CLAUDE.md` is
  refreshed and anything the user wrote outside its generated block is kept.

Then tell the user where to open it. A session cannot move itself into another folder:
- **Cross-repository work:** start Claude Code in the task folder. Its `CLAUDE.md` says which folders
  may be changed, imports each repository's own, and says there is no repository at the top: git runs
  per folder, as `git -C api ...`.
- **One repository with the full workflow:** start Claude Code in that repository's folder. The kit's
  hooks and gates read the project's `.claude/quality-check.config.json`, which lives in each
  repository, not in the task folder.

## The manifest

`task.json` is the task's record and the way to rebuild it. The script writes it; edit it by hand for
what has no command (the build and test commands, `env`, an owner), then `wt.py refresh <task>`.

```json
{
  "task": "billing-feat-abc",
  "branch": "billing-feat-abc",
  "repositories": {
    "api":        {"role": "edit", "url": "git@github.com:acme/api.git", "base": "origin/main", "start": "9f2c..."},
    "shared-lib": {"role": "dependency", "url": "git@github.com:acme/shared-lib.git", "ref": "v2.3.0", "commit": "41ab..."}
  },
  "external_paths": [{"source": "~/data/billing-fixtures", "destination": "fixtures"}],
  "build": ["make -C api build"],
  "test": ["make -C api integration-test"],
  "env": {"MAVEN_OPTS": "-Dmaven.repo.local=${ADK_TASK_CACHE}/m2"},
  "runtime": {"port_offset": 200}
}
```

- **What the task wants** is in `task.json`; **what was actually tested** is in `checks.jsonl` - the
  commit (and any uncommitted changes) of every repository, per check. Keeping the two apart is what
  lets anyone answer "which versions were built together, and did it pass?".
- **No secrets** in the manifest: it is meant to be shared. Secrets stay in the `.env` files `--copy`
  brings in, or the user's secret manager.
- **Another machine, or a teammate:** `wt.py restore path/to/task.json [--as <name>]` rebuilds the
  workspace - each repository found by its registered name, its recorded path, or cloned from its `url`
  into the sources folder; each dependency at its recorded commit (its ref, when that commit is not
  there); the extras copied again.

## Each task's own environment

Separate checkouts are not enough: builds write to shared caches (`~/.m2`, the npm store, the Go module
cache, Docker image tags) and parallel test runs fight over ports, databases and compose projects. Every
command the script starts (`check`, `run`, `--setup`) - and anything sourced from `task.env` - gets:

| Variable | Value |
|---|---|
| `ADK_TASK`, `ADK_TASK_DIR` | the task's name and folder |
| `ADK_TASK_CACHE` | `<task>/.cache` - a cache folder of its own, removed with the task |
| `ADK_PORT_OFFSET` | 100, 200, ... - unique among the root's tasks; add it to each port a test binds |
| `COMPOSE_PROJECT_NAME` | the task name: containers, networks and volumes of their own |
| the manifest's `env` | the user's own, which may use `${ADK_...}` |

Point each tool's cache at `$ADK_TASK_CACHE` in `env` when a repository installs its build output where
another task would pick it up - `MAVEN_OPTS=-Dmaven.repo.local=${ADK_TASK_CACHE}/m2`,
`npm_config_cache`, `GOMODCACHE`, `CARGO_TARGET_DIR`, a Docker tag with `${ADK_TASK}` - and wire the
repositories to each other's checkouts in the task folder rather than through a registry (`go.work`,
npm/pnpm workspaces, Cargo `[patch]`, `pip install -e`, Gradle `includeBuild`). Ask the user which
applies: it is their build, and it belongs in the build or test command or in `env`, not guessed.
Commands of your own run as `. ./task.env && <command>`.

## Working across repositories

- **Contract first.** When one repository calls another, settle the contract (the API, the message, the
  schema), then change and test the provider's side first, and the consumer against it, in the same task.
  When the consumer has to start before the provider is done, it works against a stub of the agreed
  contract, never against a guess.
- **Check the task as a whole:** `wt.py check <task>` runs the manifest's build, then its test, in the
  task folder, stops at the first failure, and appends the result with every repository's commit to
  `checks.jsonl`. `wt.py check <task> -- <command>` checks one command the same way. Run it before
  calling the task done, and again after any `sync` or `pin`.
- **`wt.py run <task> -- <command>`** runs a command in each edit repository (`--all`: dependencies too)
  and names the ones that failed. One argument is run by the shell, so `-- "make lint && make test"`
  works.
- **Commit and push per repository.** Each gets its own pull request (`code-host`). Link them to each
  other and say which merges first: the provider, when the consumer needs it. Nothing merges all
  repositories at once, so each merge must leave the others working: a provider change stays
  backward-compatible until its consumers have moved (add, migrate, then remove).

## One task, several agents

When one session works the whole task, it opens the task folder and owns everything in it. When the
work is split - an agent per repository - it needs a coordinator:

- **The coordinator** is the session in the task folder. It owns the manifest, the contract, the order
  of the work and `wt.py check`. It settles the contract before anyone writes code.
- **Each agent gets one folder** - its repository's worktree in this task - and nothing else. Record it
  as `"owner"` on that repository in `task.json` and `wt.py refresh`: the task's `CLAUDE.md` then lists
  who owns what. Never two agents in one folder, and never an agent in a dependency.
- **The provider's agent goes first**, or the consumer's works against the agreed stub.
- **Each agent reports back:** its branch and commit, the files it changed, the assumptions it made, the
  checks it ran and their results, and anything blocking it. The coordinator then runs `wt.py check`
  over all of them together - an agent's own green tests are its claim, not the task's result.
- An agent that should get the kit's full workflow (gates, lanes, unit worktrees) runs as its own session
  started in its repository's folder, not as a subagent of the task-folder session.

## Seeing everything

`wt.py status` lists every task under the root, each repository's state, the last check and what has
changed since, and worktrees of registered repositories that live outside the root. Name tasks to
narrow it, pass `--fetch` to compare against the remote as it is now, and `--json` to read it
programmatically.

| State | Meaning | Safe to remove |
|---|---|---|
| `new` | nothing done yet - the branch is where the task started it | yes |
| `uncommitted` | changes not committed | no |
| `unpushed` | commits no remote has | no |
| `remote-gone` | commits no remote has, and the branch's remote copy was deleted - usually a squash merge | only once the pull request is confirmed merged |
| `pushed` | every commit is on a remote; not in the base yet | yes - the work is on the remote |
| `in-base` | everything the task did is already in its base (merged) | yes |
| `unknown` | its base no longer exists, so what the branch holds cannot be told | no - check it by hand |

A dependency is `pinned` (at its recorded commit), `moved` (checked out elsewhere by hand) or `modified`
(a tracked file changed - a dependency is not edited; untracked files are taken as build output). A
repository shown `on <other branch>` was switched by hand inside the task. Say so; don't switch it back
yourself.

## Keeping up

- `wt.py sync <task>` fetches, then merges each edit repository's base into it. Dependencies stay where
  they are pinned.
  - **Skipped:** a repository with uncommitted changes. Commit or stash first.
  - **Conflicts:** the merge is undone, the repository is left exactly as it was, and the conflicting
    files are named. Resolve them deliberately with the command it prints; a conflict is never resolved
    for the user silently.
  - **`--rebase`** is for a branch that has never been pushed: rebasing a pushed branch would need a
    force push, so the script refuses it.
- `wt.py pin <task> <repo> <ref>` moves a dependency to another version and records it. Refused while the
  dependency holds changes of its own.
- After either, `wt.py check <task>` again: the last check was of other versions.

## Two tasks on the same repositories

Each task is checked in its own folder, but they meet when both merge.

- **Independent tasks:** merge one; then `sync` the other, so its bases now carry the first, and `check`
  it again before it merges.
- **Both change a shared interface or logic:** check them together before either merges - a third task on
  the first one's branches (`wt.py new ab-check api@origin/task-a web@origin/task-a`), merge the second's
  in (`wt.py run ab-check -- git merge --no-edit origin/task-b`), `check`, then `remove` it. Its
  `checks.jsonl` records exactly which commits of every repository were tested together.

## Finishing

- `wt.py remove <task>` removes the task's worktrees, its cache and copied extras, then its folder. Files
  the user added there (notes, scratch) are kept. Each branch is deleted only if it is merged; otherwise
  it is kept. The manifest and the check history go to `<root>/.removed/<task>/`, so
  `wt.py restore <root>/.removed/<task>/task.json` brings the task back.
- It **refuses** when a repository holds work no remote has - uncommitted, unpushed, or a dependency
  changed - and names it.
- `--force` goes ahead anyway. Uncommitted changes are saved as a patch under `<root>/.removed/<task>/`
  first, a branch with unpushed commits is always kept, and commits made on a dependency are kept as a
  branch `wt-saved/<task>/<repo>`. Ask the user before passing it, and for `remote-gone` confirm the pull
  request was merged (`code-host`) first.
- `wt.py prune` lists the tasks whose every branch is already in its base, the `remote-gone` ones to
  check, and the untouched (`new`) ones it keeps. `prune --yes` removes the first kind; show the list and
  get the user's yes before running it.

## Rules

- **Never `rm -rf` a worktree folder.** Git keeps a record of every worktree, and deleting the folder
  leaves that record and the branch behind. Remove through the script, or `git worktree remove`.
- **Never lose work.** Nothing here discards uncommitted changes or unpushed commits: the script refuses,
  or keeps them as a patch and a branch. Do not work around a refusal with plain git commands.
- **Never edit a dependency.** It is pinned so the task builds against a known version. A change it needs
  makes it an edit repository of the task - ask the user first.
- **Never share a checkout between tasks.** Even a read-only dependency gets a worktree per task: builds
  write into their sources (`node_modules/`, `target/`), and a worktree costs no clone.
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
- **Pooling worktrees for reuse** (tools such as Treehouse do this per repository) is out of scope: a
  task's worktrees are made for it and removed with it. Such a tool can sit under this one; it does not
  group repositories into a task, pin their versions, or check them together.
