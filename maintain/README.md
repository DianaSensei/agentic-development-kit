# Maintain loop

The playbook's last stage: problems in production start the development loop on their own. A
deterministic check finds a problem, and only then is Claude invoked - to write the problem up as a
`proposed` intent. The intents collect on one pull request, which is the triage queue. A person
accepts or rejects each one; accepted intents then go through `workflow-router` like any other.

```
bands.yaml ──► check-bands.py ──► breach / broken detector ─┐
failed CI run on main ──────────────────────────────────────┼─► Claude: intent-capture (machine-raised)
                                                             │        writes docs/intents/ only
                                                             └─► verify ─► one PR: "Proposed intents from monitoring"
```

What Claude may do here: read the repository and write under `docs/intents/`, nothing else. It does
not diagnose past the evidence and does not fix anything. The workflow checks that: if a file outside
`docs/intents/` changed, or an intent fails `check-intent.sh`, nothing is published.

## Setup

1. **`bands.yaml`** at the repository root - start from [`bands.example.yaml`](./bands.example.yaml).
   Each band is a command that prints one number, and the range it must stay in (`min`, `max`, or
   both). Quote a command that contains `": "`, or YAML will not parse it.
2. **The caller**: copy [`ci/maintain.yml`](../ci/maintain.yml) to `.github/workflows/maintain.yml`,
   and list your CI workflows' names under `workflow_run.workflows` so a failure on the default branch
   becomes an intent too.
3. **Secrets**:
   - `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` - the same one the CI reviewer uses.
   - `BANDS_ENV` (optional) - what the band commands need, as `NAME=value` lines
     (`PROM_URL=...`, `PROM_TOKEN=...`). It is exported for the check step only, never to Claude's
     step, and every value in it is replaced with `[redacted]` in the evidence before anything is
     written - GitHub masks secrets in logs, not in committed files.
4. **Repository setting**: Settings → Actions → General → "Allow GitHub Actions to create and approve
   pull requests", or the triage PR cannot be opened.

Without a Claude credential the checks still run and the job summary lists what they found, with a
warning that nothing was written up.

## Bands

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | Unique; becomes the intent's `originator: monitoring/<name>` and file name |
| `command` | yes | Shell command; its stdout must be exactly one number |
| `min` / `max` | at least one | The band. Outside it is a breach |
| `tier` | no | `propose` (default): write an intent. `observe`: report in the job summary only |
| `timeout_seconds` | no | Default 60 |
| `owner`, `runbook` | no | Carried into the intent's evidence for whoever triages |

A command that fails, times out, or prints anything but one number is reported as `error` - a
detector that cannot measure is a problem too, and a `propose` band's broken detector becomes an
intent of its own. Run the check locally with `python3 maintain/check-bands.py bands.yaml`.

## One problem, one intent

A band that stays out of range is not a new problem each run. Claude first looks for an open intent
from the same band (`draft`, `proposed`, `accepted`, `in-progress`) and adds the new evidence to it
instead of writing another. A band whose earlier intent is `done` or `rejected` has come back: that
gets a new intent, `monitoring-<name>-<date>.md`, which references the old one. The standing branch
`maintain/proposed-intents` carries intents nobody has triaged yet, so a finding is never proposed
twice while its PR is open.

## Cost and schedule

The caller checks every 6 hours. The check itself is free; Claude runs only when a `propose` band is
out of range or a CI run failed, once per run however many problems there are.
