# Quality-check hooks

The skill library states rules it cannot enforce: `code-review-skill` is described as the self-check
Claude *always* runs before reporting done, and `feature-development` Step 3.1 says the owning
`SKILL.md` *must* be read before code is written. Both are honour-system - a model that forgets or
decides it already knows breaks them silently.

These hooks close that gap. They are deterministic: they run whether or not the model remembers.

## What these hooks check, and what they leave alone

| | Example | Owned by |
|---|---|---|
| Mechanically observable | Was `java-spring-skill/SKILL.md` read in this request? Are there unreviewed code changes? Is there an API key in what was just written? | these hooks |
| Needs judgement | Is the transaction boundary right? Is there an N+1? Does the lock have a TTL? | `code-review-skill`, read and applied by Claude |

The hooks never re-implement the review checklist as regexes. Their job is to make sure the skill that
owns that judgement actually runs.

## The gates

| Hook | Event | Default | What it does |
|---|---|---|---|
| `session-context.sh` | `SessionStart` | on | Injects a fixed set of general engineering/style guidelines, plus (if this kit's skills are installed) the routing + self-check rules, once per session. Non-blocking. |
| `skill-gate.sh` | `PreToolUse` on edits | `warn` | Maps the edited file to its owning skill via `skill_map`, then checks the transcript for a read of that `SKILL.md` **since the last user message**. A read from an earlier request does not count - the file may have changed since. |
| `checkpoint-gate.sh` | `PreToolUse` on **code** edits | `warn` | Inside `feature-development`/`bug-fix`/`refactor` only: checks the transcript, since that workflow skill was last invoked, for an `AskUserQuestion` call with `header` exactly `"Checkpoint"`. Presenting a proposal and moving on without asking no longer passes silently. Never fires on a documentation write (the plan doc itself is written before the checkpoint, by design). |
| `write-lint.sh` | `PostToolUse` on edits | `warn` | Scans only the newly written text for hardcoded secrets and leftover placeholders. Advisory by protocol: `PostToolUse` cannot block. |
| `quality-gate.sh` | `Stop` | `warn` | Flags - or, set to `block`, refuses to end - a turn that leaves uncommitted **code** changes no review has vouched for. |
| `mark-reviewed.sh` | - | - | Run after the review to record it and satisfy the gate. |

`quality-gate.sh` fingerprints the changed code rather than setting a boolean, so editing code after a
review invalidates it - the next review covers the new state. Documentation-only turns never trip it.

### Not a quality-check hook: `toolbox-seed.sh`

`hooks.json` also registers `toolbox-seed.sh` on `SessionStart`, alongside `session-context.sh` - it has
nothing to do with the review gates above. It syncs the bundled `toolbox` MCP's six default database
connections into `${CLAUDE_PLUGIN_DATA}/connections/`, since a marketplace-installed plugin has no local
repo clone for the user to copy config from. See [`mcp/toolbox/README.md`](../mcp/toolbox/README.md).
Runs every session but is a no-op once everything is already in sync; per file, tracked by a manifest
recording the content this hook itself last wrote, so a plugin update can still reach a default you never
touched (auto-updated) without ever overwriting one that doesn't match what it wrote - whether that's a
real customization or a pre-existing install this tracking has no history for, both are treated the same:
left alone, with the new version saved alongside as `<name>.upstream` to compare/merge by hand (reported
once per upstream version, not every session). Deleting a file it previously wrote is respected as
intentional and never recreated; deleting one it never trusted (still unresolved) reseeds it fresh from
the current default instead. Fails open the same as every other hook here.

### About the defaults

Every gate ships as `warn`, so installing this kit changes what you are *told*, not what you are
*allowed to do*. That is the safe starting point: watch each gate on your own project before letting
it interrupt anything.

`quality_gate` is the one built to block, and switching it is a one-word config edit. The difference
is not cosmetic:

- `warn` - the turn ends normally and the notice lands in the transcript, for **you** to read.
  `additionalContext` is only delivered to Claude on blocking events, so in `warn` the gate reports
  that the review did not happen; it does not cause it to happen.
- `block` - the turn is held and the reason goes to Claude, which names the skill to read, the diff to
  read it against, and the command that releases the gate. This is the mode in which
  "review before reporting done" is actually enforced.

`skill_gate` and `checkpoint_gate` are the two to be most careful about promoting to `block`: both infer
from transcript structure, which is the likeliest source of a false positive here. `checkpoint_gate`
in particular depends on the workflow skill actually using the literal header `"Checkpoint"` - if you
edit the CHECKPOINT wording in `feature-development`/`bug-fix`/`refactor`, keep that exact string (or
update `checkpoint_gate.header` in config to match).

In `warn`, each gate speaks once per distinct state - per session per skill for `skill-gate`, once per
session for `checkpoint-gate`, per fingerprint of the change for `quality-gate` - rather than repeating
on every turn.

### Why `checkpoint-gate` scopes differently than `skill-gate`

`skill-gate` resets on every user message on purpose - a skill's content can change between requests, so
only a read *in this request* counts. A CHECKPOINT is different: Step 1's interview can span several
user replies before the proposal is even ready, so scoping to "since the last user message" would make
the gate fire on Step 3's very first edit even when the checkpoint was properly asked two turns earlier.
`checkpoint-gate` instead scopes to "since this workflow skill was last invoked" - long enough to cover
a whole workflow run, but short enough that an approval from an *earlier, separate* feature request
doesn't silently satisfy a brand new one once the skill is invoked again.

It also only gates **code** writes (the same `code_extensions` pattern `quality-gate` uses), never
documentation. This was a real bug caught by actually running the wired-up workflow end to end, not
something reasoned out in advance: Step 2 itself must write `docs/plans/<slug>.md` *before* the
checkpoint runs - present the proposal, then ask - and the first version of this gate fired on that
exact write, because it didn't yet distinguish a plan document from an implementation file.

That same test run also showed the gate earning its keep: `solution-architect` returned two proposals
requiring a real architectural decision (cache strategy for a promotion-evaluation hot path), the main
thread wrote up the checkpoint clearly as a 3-option question in its final chat message - but never
actually called `AskUserQuestion` with `header: "Checkpoint"`, presenting it as prose instead. In
`block` mode, this gate would have caught exactly that gap and held Step 3 until the literal call was
made; in the default `warn` mode it recorded the gap without stopping anything. That's the gap this
hook exists to catch - presenting a checkpoint clearly is not the same as the transcript proving it was
actually asked.

## Where each gate is configured

Split deliberately:

- **`hooks/hooks.json`** (this plugin's own hook manifest) - `session-context` and `write-lint`.
  Global, cheap, never blocks, so they are harmless in a session that is only answering questions.
  Registered automatically wherever the plugin is enabled, no per-project setup.
- **Frontmatter of `feature-development`, `bug-fix`, `refactor`** - `skill-gate`, `checkpoint-gate`, and
  `quality-gate`. Frontmatter hooks are registered when the skill is invoked, so the blocking gates apply
  exactly while a code-changing workflow is running, and the rule lives next to the prose it enforces.

Every command in both places is written as `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh` - the plugin
install directory, resolved by Claude Code at hook-invocation time - never `${CLAUDE_PROJECT_DIR}`.
The scripts themselves still act on `${CLAUDE_PROJECT_DIR}` (the project the plugin is enabled in) for
everything project-specific: git state, `.claude/state/`, and a project's own config override.

## Configuration

`quality-check.config.json`, all keys optional. The plugin ships a default at `hooks/quality-check.config.json`;
a project overrides it without forking the plugin by dropping its own copy at
`.claude/quality-check.config.json` in the project root - if that file exists, it wins over the
bundled default entirely (not merged field-by-field).

- `mode.<gate>` - `off` | `warn` | `block`.
- `session_context.general_guidelines` - `true`/`false`. The fixed engineering/style block
  `session-context.sh` injects every session (em dash, commit co-author, CHANGELOG.md, Markdown
  one-sentence-per-line, quality over dev cost, E2E-first bug fixes, pixel-perfect UI, fix
  adjacent lint/test issues you notice). This is a specific team's conventions, not something every
  installer necessarily wants - set to `false` in a project's own config to keep the kit's
  routing/checkpoint reminders below without these.
- `skill_map` - ordered `{match, skill}` rows; first ERE match against the repo-relative path wins.
  **Edit this per project**: remove stacks you do not use, add your own.
- `checkpoint_gate.header`, `.workflows` - the exact `AskUserQuestion` header to look for, and which
  workflow skills' Step 3/4 it gates.
- `code_extensions` - what the Stop gate counts as code.
- `quality_gate.review_skill`, `.max_blocks`, `.require_changelog`, `.require_experience_log`.
  The artifact checks are off by default: a small refactor legitimately produces neither file.
- `write_lint.secret_patterns`, `.placeholder_patterns` - POSIX ERE, matched case-insensitively.

Overrides, in order of bluntness: `QUALITY_CHECK_MODE=off` in the environment forces every gate off;
a project's own `.claude/quality-check.config.json` overrides the mode/skill_map/patterns for that
project only; `.claude/settings.local.json` (gitignored) can disable or reconfigure the plugin's hooks
on one machine; disabling the plugin (`/plugin`) or `"disableAllHooks": true` turns off everything.

## Operating rules these scripts follow

- **Fail open, always.** No `jq`, an unreadable transcript, no git repo, malformed config - exit 0
  silently. A quality gate must never be the reason someone cannot get work done. This is verified for
  each script.
- **Bounded blocking.** `quality_gate.max_blocks` (default 2) caps how many times one session may be
  held; `stop_hook_active` is honoured. A gate that can trap a session is worse than one that misses.
- **No network, no writes outside the target project's `.claude/state/`.** These scripts run with the
  user's permissions in every project the plugin is enabled in, so they stay short and readable on
  purpose, and never touch the plugin's own install directory.

State lives in the target project's `.claude/state/` (gitignored there): `reviewed` holds the
fingerprint of the last reviewed change; `<session>.blocks` counts holds; `warned` and
`<session>.skillgate.<skill>` suppress repeat warnings.

## How a project adopts this without forking it

Nothing to copy. Enable the plugin (see the root [`README.md`](../README.md#install)) and its skills,
agents, and hooks are active in that project immediately. To tune the hooks for that project's actual
stack, drop a `.claude/quality-check.config.json` in the project root with just the overrides needed -
see Configuration above; the plugin's bundled `hooks/quality-check.config.json` stays untouched as the
fallback for every project that doesn't override it.

Requires `bash`, `git`, and `jq` on the machine running Claude Code. Without `jq` every hook silently
does nothing.

## Checking them

`/hooks` lists what is registered and which file it came from. `CLAUDE_CODE_DEBUG=1` logs execution.
To exercise one by hand, feed it the event JSON on stdin:

```bash
echo '{"hook_event_name":"Stop","session_id":"t","stop_hook_active":false}' \
  | CLAUDE_PROJECT_DIR=$PWD CLAUDE_PLUGIN_ROOT=/path/to/agentic-development-kit \
    /path/to/agentic-development-kit/hooks/quality-gate.sh; echo "exit=$?"
```

Run from inside a checkout of this plugin itself, `CLAUDE_PLUGIN_ROOT` can be omitted - the scripts
fall back to resolving it from their own location on disk.
