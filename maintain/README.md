# Maintain loop

The playbook's last stage: problems in production start the development loop on their own. A
deterministic check finds a problem, and only then is Claude invoked - to write the problem up as a
`proposed` intent. The intents collect on one pull request, which is the triage queue. A person
accepts or rejects each one; accepted intents then go through `workflow-router` like any other.

```
bands.yaml ──► check-bands.py ──► breach / broken detector ─┐
failed pipeline on main ────────────────────────────────────┼─► Claude: intent-capture (machine-raised)
                                                             │        writes docs/intents/ only
                                                             └─► verify ─► git push ─► one triage request
                                                                              (opened through MCP)
```

What Claude may do here: read the repository and write under `docs/intents/`, nothing else - no shell
beyond the intent checker, no MCP server, no token in its environment. It does not diagnose past the
evidence and does not fix anything. [`run.sh`](./run.sh) checks that: if a file outside
`docs/intents/` changed, or an intent fails `check-intent.sh`, nothing is published. Publishing is
`git push` and [`codehost.py ensure-change`](../codehost/README.md), which finds or opens the triage
request through the provider's MCP server - the same script on GitHub Actions and GitLab CI.

## Setup

**`bands.yaml`** at the repository root - start from [`bands.example.yaml`](./bands.example.yaml).
Each band is a command that prints one number, and the range it must stay in (`min`, `max`, or both).
Quote a command that contains `": "`, or YAML will not parse it.

### GitHub Actions

1. **The caller**: copy [`ci/maintain.yml`](../ci/maintain.yml) to `.github/workflows/maintain.yml`,
   and list your CI workflows' names under `workflow_run.workflows` so a failure on the default branch
   becomes an intent too.
2. **Secrets**:
   - `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` - the same one the CI reviewer uses.
   - `BANDS_ENV` (optional) - what the band commands need, as `NAME=value` lines
     (`PROM_URL=...`, `PROM_TOKEN=...`). It is exported for the check step only, never to Claude's
     step, and every value in it is replaced with `[redacted]` in the evidence before anything is
     written - a CI masks secrets in its logs, not in committed files.
3. **Repository setting**: Settings → Actions → General → "Allow GitHub Actions to create and approve
   pull requests", or the triage PR cannot be opened.

### GitLab CI

1. **The include**, in `.gitlab-ci.yml`:

   ```yaml
   include:
     - remote: https://raw.githubusercontent.com/DianaSensei/agentic-development-kit/main/ci/gitlab/maintain.yml
       inputs:
         kit_ref: main
   ```

   It adds two jobs: `adk-maintain`, which runs on a schedule, and `adk-maintain-on-failure`, which runs
   in `.post` when a push pipeline on the default branch fails and records that failure.
2. **A schedule** (Build → Pipeline schedules), every 6 hours for example, with the variable
   `ADK_MAINTAIN` = `true`. Give your other jobs a rule that skips scheduled pipelines if they should
   not run on it.
3. **Masked CI/CD variables**: `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`; `ADK_GITLAB_TOKEN` - a
   project access token with the **Developer** role and the **`api`** and **`write_repository`** scopes,
   which pushes the triage branch and opens its merge request; optionally `BANDS_ENV`, as for GitHub.

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

## Bets: did the change work?

An intent is a bet: a problem, and a *Success signal* that says whether solving it worked. `done` only
says the change shipped. When an intent's `signal_band` names a band in `bands.yaml`, each run of the
loop also judges it - deterministically, with no model - once it has been `done` for
`ADK_RESOLVE_AFTER_DAYS` days (default 14):

| The band | The intent gets |
|---|---|
| in range | `resolution: met` |
| out of range | `resolution: not-met` - shipped, but the problem is still there: a candidate for a new intent |
| broken, or not in `bands.yaml` | nothing; listed in the job summary |

The verdict lands in the frontmatter and a Decision log line, on the same triage branch and request as
proposed intents, so a person sees it before it is merged. [`resolve-bets.py`](./resolve-bets.py) does
it; it needs code-host access to publish but no Claude credential. `metrics/` reports the share of
judged bets that were met, and how many shipped intents have no signal band at all - changes whose
outcome nobody will ever check.

A signal band is an ordinary band. Give it `tier: observe` when being out of range should not also
raise a new intent on its own.

## Traces

When Claude writes intents, its full trajectory is kept as `transcript.jsonl` with the run (the
`adk-maintain-run` artifact on GitHub, `adk-artifacts/` on GitLab), and the job summary ends with the
run's cost. An OpenTelemetry collector works the same way as for the reviewer - see
[`ci/README.md`](../ci/README.md#traces-and-cost); runs are labelled `adk.run=maintain`.

## Cost and schedule

The caller checks every 6 hours. The check itself is free; Claude runs only when a `propose` band is
out of range or a CI run failed, once per run however many problems there are.
