# Quality-check hooks

The skill library states rules it cannot enforce: `code-review-skill` is described as the self-check
Claude *always* runs before reporting done, and `feature-development` Step 3.1 says the owning
`SKILL.md` *must* be read before code is written. Both are honour-system — a model that forgets or
decides it already knows breaks them silently.

These hooks close that gap. They are deterministic: they run whether or not the model remembers.

## What is enforced, and what is not

| | Example | Handled by |
|---|---|---|
| Mechanically observable | Was `java-spring-skill/SKILL.md` read in this request? Are there unreviewed code changes? Is there an API key in what was just written? | these hooks |
| Needs judgement | Is the transaction boundary right? Is there an N+1? Does the lock have a TTL? | `code-review-skill`, read and applied by Claude |

The hooks never re-implement the review checklist as regexes. Their job is to make sure the skill that
owns that judgement actually runs.

## The gates

| Hook | Event | Default | What it does |
|---|---|---|---|
| `session-context.sh` | `SessionStart` | on | Injects the routing + self-check rules once per session. Non-blocking. |
| `skill-gate.sh` | `PreToolUse` on edits | `warn` | Maps the edited file to its owning skill via `skill_map`, then checks the transcript for a read of that `SKILL.md` **since the last user message**. A read from an earlier request does not count — the file may have changed since. |
| `write-lint.sh` | `PostToolUse` on edits | `warn` | Scans only the newly written text for hardcoded secrets and leftover placeholders. Advisory by protocol: `PostToolUse` cannot block. |
| `quality-gate.sh` | `Stop` | `block` | Refuses to end the turn while uncommitted **code** changes exist that no review has vouched for. |
| `mark-reviewed.sh` | — | — | Run by Claude after the review to release the gate. |

`quality-gate.sh` fingerprints the changed code rather than setting a boolean, so editing code after a
review invalidates it — the next review covers the new state. Documentation-only turns never trip it.

### Why the defaults differ

`quality_gate` blocks because the block is self-healing: it names the skill to read, the diff to read
it against, and the command that releases it. `skill_gate` only warns by default because it infers
from transcript structure, which is the most likely thing here to produce a false positive; switch it
to `block` once you have watched it behave on your own project.

## Where each gate is configured

Split deliberately:

- **`.claude/settings.json`** — `session-context` and `write-lint`. Global, cheap, never blocks, so
  they are harmless in a session that is only answering questions.
- **Frontmatter of `feature-development`, `bug-fix`, `refactor`** — `skill-gate` and `quality-gate`.
  Frontmatter hooks are registered when the skill is invoked, so the blocking gates apply exactly
  while a code-changing workflow is running, and the rule lives next to the prose it enforces.

## Configuration

`quality-check.config.json`, all keys optional:

- `mode.<gate>` — `off` | `warn` | `block`.
- `skill_map` — ordered `{match, skill}` rows; first ERE match against the repo-relative path wins.
  **Edit this per project**: remove stacks you do not use, add your own.
- `code_extensions` — what the Stop gate counts as code.
- `quality_gate.review_skill`, `.max_blocks`, `.require_changelog`, `.require_experience_log`.
  The artifact checks are off by default: a small refactor legitimately produces neither file.
- `write_lint.secret_patterns`, `.placeholder_patterns` — POSIX ERE, matched case-insensitively.

Overrides, in order of bluntness: `QUALITY_CHECK_MODE=off` in the environment forces every gate off;
`.claude/settings.local.json` (gitignored) overrides project settings on one machine;
`"disableAllHooks": true` turns off everything.

## Operating rules these scripts follow

- **Fail open, always.** No `jq`, an unreadable transcript, no git repo, malformed config — exit 0
  silently. A quality gate must never be the reason someone cannot get work done. This is verified for
  each script.
- **Bounded blocking.** `quality_gate.max_blocks` (default 2) caps how many times one session may be
  held; `stop_hook_active` is honoured. A gate that can trap a session is worse than one that misses.
- **No network, no writes outside `.claude/state/`.** These scripts run with the user's permissions on
  every machine that installs this kit, so they stay short and readable on purpose.

State lives in `.claude/state/` (gitignored): `reviewed` holds the fingerprint of the last reviewed
change; `<session>.blocks` counts holds; `<session>.skillgate.<skill>` suppresses repeat warnings.

## Installing into another project

Copy `.claude/hooks/` and merge `.claude/settings.json`, alongside the skills themselves. The scripts
resolve skills in both `.claude/skills/<name>/SKILL.md` and `skills/<name>/SKILL.md`, and no-op for any
skill that is not installed. Then trim `skill_map` to the project's real stack.

Requires `bash`, `git`, and `jq`. Without `jq` every hook silently does nothing.

## Checking them

`/hooks` lists what is registered and which file it came from. `CLAUDE_CODE_DEBUG=1` logs execution.
To exercise one by hand, feed it the event JSON on stdin:

```bash
echo '{"hook_event_name":"Stop","session_id":"t","stop_hook_active":false}' \
  | CLAUDE_PROJECT_DIR=$PWD .claude/hooks/quality-gate.sh; echo "exit=$?"
```
