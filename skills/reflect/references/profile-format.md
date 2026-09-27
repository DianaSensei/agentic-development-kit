# The personal profile

Where it lives: `$ADK_PROFILE_DIR`, by default `~/.claude/adk-profile/` - a clone of the user's own
**private** Git repository, the same on every machine they work on. Nothing in it is ever written to
a project repository.

```
~/.claude/adk-profile/
  profile.md    loaded in every session (imported from ~/.claude/CLAUDE.md) - kept small
  signals.md    the inbox: raw evidence, appended as work happens, read only by reflect
  README.md     what this repository is, for the user
```

`~/.claude/CLAUDE.md` holds one line that loads it: `@~/.claude/adk-profile/profile.md`.

## profile.md

```markdown
# How <name> works
<!-- Personal preferences, learned from working together and approved one by one.
A project's CLAUDE.md, REVIEW.md and checks override anything here: when they
conflict, follow the project and say so. -->

## How I decide
- Prefer reversible changes over faster ones when the two conflict. _(3 Checkpoints; 2026-09 to 2026-11)_

## Design
- Fail fast at a boundary; no silent retries on money or state changes. _(2 Checkpoints, 1 correction; 2026-10)_

## Code style
- Raise a domain error with the cause chained; never return None for a failure. _(4 rewrites; 2026-09 to 2026-12)_

## Review bar
## Working with me
- Lead with the recommendation, then the reasons; no survey of options I did not ask for. _(3 corrections)_

## Not for me
- ORM lazy loading in request paths - rejected twice, N+1 in production. _(2 Checkpoints)_
```

Rules for every line:
- **One preference, stated as an instruction** the agent can follow, specific enough to be wrong. "Likes
  clean code" is not a preference; "keeps functions under one screen, extracts by responsibility" is.
- **Evidence in the trailer**: kinds and counts, and the date range - so a reader can judge its weight
  and `reflect` can age it. The evidence itself stays in `signals.md` and git history.
- **Work only.** How the person decides, designs, writes, reviews and wants to be worked with. Nothing
  about their life, health, politics or anything else personal, even when a signal mentions it.
- **Budget: 60 lines** below the header. Loaded in every session, so every line costs tokens everywhere.
  Past the budget, merge and generalise before adding; the least-evidenced, oldest line goes first.

## signals.md

Append-only. One line per signal, newest last:

```
- 2026-09-27 | correction | shop-api | "don't return None on a parse failure, raise ParseError" | experience-log: parse-error-swallowed
- 2026-09-27 | checkpoint | shop-api | chose "fail fast" over "retry with backoff" - "retries can double-charge" | docs/plans/checkout-timeout.md
- 2026-09-28 | rewrite | shop-api | agent's `except Exception: return None` -> `except ValueError as e: raise ParseError(text) from e` | a1b2c3d4e5
- 2026-09-28 | review | shop-api | "prefer a table over prose in PR summaries" | PR #41
- 2026-09-28 | statement | - | "always show me the recommendation first" | conversation
## reflected 2026-09-30
```

- `kind`: `correction` (the user said the agent's work was wrong for them), `checkpoint` (a choice
  between proposals, with their reason in their words), `rewrite` (lines they rewrote that the agent
  wrote), `review` (their comment on the agent's pull request), `statement` (they stated a preference
  outright).
- **Describe the pattern, keep code minimal.** At most one short line of code per signal, with
  business names generalised. The profile repository is private, but it is not the project's: client
  code, data, credentials and personal details of anyone never go into it.
- `## reflected <date>` marks where the last `reflect` stopped; the lines after it are new.

## Weighing evidence

| Evidence | Enough for a profile line |
|---|---|
| a `statement` ("always...", "I prefer...") | yes, alone |
| two or more signals of the same preference, from different occasions | yes |
| one `correction`, `checkpoint`, `rewrite` or `review` | not yet - it waits in `signals.md` |
| signals that contradict each other | no line; ask which holds, or whether it depends on context, and write the context in |

Evidence against an existing line - a later choice or rewrite the other way - is proposed as a
revision, never ignored. A line with no new evidence for 6 months is proposed for retirement: people
change, and a profile that only grows fossilises.
