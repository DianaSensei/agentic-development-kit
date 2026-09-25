---
name: project-setup
description: Sets up a project repository for this kit and the AI-native SDLC in one pass - a one-page CLAUDE.md built from the repo's real commands and layout, a REVIEW.md the independent reviewer reads, a CODEOWNERS for the policy files, a committed .claude/settings.json (secret-file deny rules, lockfile protection, the kit enabled for every teammate), a quality-check config whose skill_map matches the stack, the code host's MCP server in .mcp.json, and the independent-review CI job for GitHub Actions or GitLab CI. Detects what exists first, shows the plan, never overwrites - existing files only receive additions. Use when the user asks to set up, bootstrap, onboard, or "install the kit into" a project, or to add the playbook files (CLAUDE.md, REVIEW.md, CODEOWNERS, settings) to a repo. Not for configuring Claude Code's own personal settings (that is update-config) and not for writing application code.
metadata:
  domain: workflow
  triggers: set up project, bootstrap repo, onboard repository, add CLAUDE.md, add REVIEW.md, install kit in project
  role: specialist
  scope: end-to-end
  output-format: document
  related-skills: workflow-router, intent-capture, independent-review, code-review-skill, code-host
---

# Project Setup

Everything this kit relies on in a project, created in one pass so the playbook's files exist instead of
being documented: `CLAUDE.md` (what every session reads first), `REVIEW.md` (what the independent
reviewer holds changes to), `CODEOWNERS` (who approves the files that steer the agent),
`.claude/settings.json` (guardrails and the kit itself, for every teammate), the quality-check config,
the code host's MCP server, and the CI reviewer - on GitHub or GitLab.

Input: `$ARGUMENTS`

## Rules that hold throughout

- **Never overwrite.** An existing file only receives additions, each one listed in the report. A
  conflicting line in an existing file stays as it is; say what conflicts instead of "fixing" it.
- **Only what the repo shows.** A command goes into `CLAUDE.md` because a `Makefile`, `package.json`,
  `pyproject.toml`, `Cargo.toml`, `build.gradle`, CI workflow or README names it - never from what a
  stack usually uses. Where nothing names one, write nothing for it.
- **Never invent people.** `CODEOWNERS` is written only with handles the user gives. No handles → no
  file, listed as a follow-up.
- **Don't read what you protect.** Detect secret files by name only - `Glob` or `ls`. Never `Read`,
  `Grep`, `cat` or `head` a `.env*` file, a key, or anything under `secrets/`: not to check whether it
  really holds secrets (assume it does), not to learn a variable name for `CLAUDE.md`, not to see what
  a run command needs. A value read once is in the transcript for good, and this setup exists to stop
  exactly that. Where `CLAUDE.md` needs to say a command wants environment variables, name the file
  (`needs a .env - see README`), never its contents.

## Step 1 - Detect

A quick inventory, no writes:
- Existing: `CLAUDE.md`, `REVIEW.md`, `CODEOWNERS` (root, `.github/`, `.gitlab/`, `docs/`),
  `.claude/settings.json`, `.claude/quality-check.config.json`, `.mcp.json`,
  `.github/workflows/*independent-review*`, `.gitlab-ci.yml` (and whether it already includes the kit's
  `ci/gitlab/independent-review.yml`).
- Code host: `git remote get-url origin` (or `.git/config`), by `code-host`'s Step 1 rules - GitHub
  or GitLab. No remote, or an unknown host: no CI file and no `.mcp.json` entry; both become
  follow-ups.
- Stack: manifest and build files, languages by file extension, test and lint commands with where each
  was found.
- Layout: source, test, migration, generated (`dist/`, `build/`, `gen/`, `*_pb2.py`, ...) and vendored
  directories.
- Sensitive names, by file name only: `.env*`, `*.pem`, `*.key`, `secrets/`, `credentials*`. Their
  existence is all this step needs.
- Lockfiles: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `uv.lock`,
  `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`.

## Step 2 - Plan, then confirm

Present one table - file, action (create / add to / skip), and what goes in - then confirm with
`AskUserQuestion`, `header` `"Setup"`, options "Apply" / "Change something". Ask for `CODEOWNERS`
handles in the same call (free text via "Other"), e.g. who owns the agent's policy files and who
accepts intents. If the user already said to proceed without questions, skip the confirmation, skip
`CODEOWNERS`, and say both in the report.

## Step 3 - Write

Each file per its reference; read the reference before writing that file.

| File | Reference | Key points |
|---|---|---|
| `CLAUDE.md` | `references/claude-md.md` | One page. Commands, layout, conventions seen in the code, and an empty `## Common mistakes` heading - the learning loop's promotions land there. An existing `CLAUDE.md` gets that heading appended if it has none, plus only what else is missing |
| `REVIEW.md` | `references/review-md.md` | What the independent reviewer must always check, severity overrides, paths it skips |
| `CODEOWNERS` | below | Only with the user's handles |
| `.claude/settings.json` | `references/settings.md` | Deny rules, lockfile protection, the kit enabled; strict JSON, merged key by key into an existing file |
| `.claude/quality-check.config.json` | below | Only if missing |
| `.mcp.json` | below | The code host's MCP server, only if no server there is one already |
| GitHub: `.github/workflows/independent-review.yml` | below | Only if no reviewer workflow exists |
| GitLab: `.gitlab-ci.yml` | below | One `include:` item added; only if the kit's review template is not included yet |

**`CODEOWNERS`** (the existing one's location; else `.github/CODEOWNERS` on GitHub, `CODEOWNERS` at the
root on GitLab): one line per path, owners exactly as the user gave them.

```
CLAUDE.md                 @<policy owners>
REVIEW.md                 @<policy owners>
.claude/                  @<policy owners>
.mcp.json                 @<policy owners>
.github/workflows/        @<policy owners>
docs/intents/             @<intent owners>
```

On GitLab the CI line is `.gitlab-ci.yml @<policy owners>` instead of `.github/workflows/`.

These files steer what the agent does in every session, so a change to them is a policy change: the
playbook has policy owners sign off. `CODEOWNERS` only enforces that once branch protection requires
code-owner review (on GitLab, code-owner approval on a protected branch, a Premium feature) - say so in
the report.

**Writes under `.claude/`, and to `.mcp.json`, need a person.** Claude Code asks before any write to
its own configuration - which tools and servers the agent gets - even when other edits are allowed, and
refuses it outright in a non-interactive session: an agent does not grant itself permissions. That is expected, not an error to work around: never try
another route (a shell redirect, a copy). If the write is refused, put the file's exact final content
in the report under its path, so the user can create it with one paste.

**`.claude/quality-check.config.json`**: copy this plugin's `hooks/quality-check.config.json`, then cut
`skill_map` down to rows whose files exist in this repo (a Python-only project keeps only the SQL and
migration rows, if it has migrations). Keep every `mode` at `warn` - blocking is a decision the team
makes after watching the gates, not a default.

**`.mcp.json`**: add a `codehost` server as `code-host` Step 3 gives it for the project scope - GitHub's
remote server with `"Authorization": "Bearer ${GITHUB_PAT}"`, or GitLab's `https://<host>/api/v4/mcp`
(its users sign in with `/mcp`). Neither holds a secret. Merge into an existing file key by key.

**GitHub - `.github/workflows/independent-review.yml`**: copy this plugin's `ci/independent-review.yml`
as is. It references the kit at `@main`; pinning it to a release tag is a follow-up, not something to
guess.

**GitLab - `.gitlab-ci.yml`**: add this item to the top-level `include:` (a single-entry `include:`
becomes a list holding the old entry and this one; no `include:` → put the block at the top of the
file; no file → the file is just this block). Touch nothing else in the file.

```yaml
include:
  - remote: https://raw.githubusercontent.com/DianaSensei/agentic-development-kit/main/ci/gitlab/independent-review.yml
    inputs:
      kit_ref: main
```

The job runs in the `test` stage. A file whose `stages:` list has no `test` gets
`stage: <one of its stages>` under `inputs:` - GitLab rejects a pipeline whose job names an undefined
stage.

## Step 4 - Verify

- Parse every JSON file you wrote or changed (`jq empty <file>` or `python3 -m json.tool <file>`). No
  shell available → re-read the file and check it by eye for trailing commas and comments, and say it
  was not machine-checked.
- Re-read each existing file you added to and confirm every original line is still there.
- `CLAUDE.md` stays about one page (roughly 60 lines); a longer one stops being read.

## Step 5 - Report

A table of every file with created / added to / skipped and why, then the follow-ups only a person can
do:
- Commit the files - they are the team's shared setup, and untracked they apply to one machine.
- Each teammate trusts the folder once: `allow` rules and the kit's marketplace entry wait for that,
  while `deny` and `ask` rules apply immediately.
- The code host's MCP server: each teammate exports `GITHUB_PAT` (GitHub) or signs in with `/mcp`
  (GitLab), and approves the project's `.mcp.json` server once.
- GitHub: the `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`) repository secret for the CI reviewer;
  branch protection requiring the `independent-review / review` check, and code-owner review if
  `CODEOWNERS` was written.
- GitLab: masked CI/CD variables `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`) and
  `ADK_GITLAB_TOKEN` - a project access token with the Reporter role and the `api` scope, which the
  pipeline posts the review with; "Pipelines must succeed" in the merge request settings.
- `CODEOWNERS` handles, if skipped.

## Boundaries

- Personal or machine-wide Claude Code settings (`~/.claude/settings.json`, keybindings, model) are
  `update-config`'s; this skill writes only files committed to the project.
- Organization-wide policy that users cannot override belongs in managed settings, deployed by an
  administrator - out of reach of a repository file; mention it when the user asks for enforcement a
  project file cannot give.
- Writes configuration and documentation only, never application code. Once set up, work starts at
  `intent-capture` or `workflow-router`.
