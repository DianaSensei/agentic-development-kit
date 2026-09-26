# Intent Template

Written to `docs/intents/<slug>.md`. Frontmatter keys are flat and always present, so a status or a
missing link can be found with `grep` across the whole directory. Leave a key empty rather than
deleting it or writing `null`. `scripts/check-intent.sh` checks this shape: every key, no extra keys,
valid `status`/`type`, and every section below, in order. `signal_band` and `resolution` came later, so
the check accepts an older intent without them.

```markdown
---
title: <one line naming the problem, not a solution>
status: <draft | proposed | accepted | rejected | in-progress | done | superseded>
type: <feature | bug | refactor | unknown>
originator: <person's name | monitoring/<alert> | incident/<id>>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
plan:
changelog:
superseded_by:
signal_band:
resolution:
---

# <title>

## Problem
Who is affected, what goes wrong for them, and when. No solution words.

## Evidence
- <source - ticket, log, metric, quote>: <what it shows>
- (or) none yet

## Desired outcome
What is true after the change, observable from outside the code.

## Success signal
How someone would check it - a metric, a test, a user behaviour. A target the originator did not
give is written "needs confirmation". When a band in `bands.yaml` measures it, its name goes in
`signal_band`, and the maintain loop judges the bet after the change ships.

## Non-goals
- <what this intent deliberately does not cover>

## Affected systems
| System / area | Why it is affected | Source |
|---|---|---|
| <module, service, screen, data> | <reason> | <path / doc / originator said / not yet checked> |

## Constraints
Deadlines, compliance, compatibility, budget - only the ones actually stated. None → "none stated".

## Originator's idea (non-binding)
A solution the originator already had in mind, if any. Input for design, not a decision.

## Open questions
- <question> - <who can answer it, if known>

## Decision log
- <YYYY-MM-DD> - created as <status> by <originator>
```

## Who fills which key

| Key | Filled by |
|---|---|
| `title` ... `updated`, all sections | `intent-capture` |
| `status: accepted / rejected / superseded`, `superseded_by` | `intent-capture` Decide mode, on a person's decision |
| `status: in-progress`, `plan` | the orchestrator, once its CHECKPOINT is confirmed |
| `status: done`, `changelog` | the orchestrator, at knowledge capture |
| `signal_band` | `intent-capture`, when a band in `bands.yaml` measures the success signal; a person may add it later |
| `resolution: met / not-met` | the maintain loop (`maintain/resolve-bets.py`), from `signal_band`, once the intent has been `done` for a while - never guessed |

`plan` points at `docs/plans/<slug>.md` (`feature-development`), or is left empty for `bug-fix` and
`refactor`, which keep their plan in the conversation. `changelog` points at `docs/changelog/<slug>.md`
(`feature-development`, `refactor`) or `docs/postmortems/<slug>.md` (`bug-fix`).
