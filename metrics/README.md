# SDLC metrics

The playbook's measures, computed from what the kit's workflows commit - no dashboard, no network, no
estimates:

```bash
python3 metrics/sdlc-metrics.py            # a Markdown table for the current repository
python3 metrics/sdlc-metrics.py path/to/repo --json
```

| Stage | Metric | Read from | What it tells you |
|---|---|---|---|
| Plan | Intents by status, acceptance rate | `docs/intents/*` frontmatter | A low rate means ideas are raised before they are ready, or the bar for "proposed" is unclear |
| Plan | Median days to decision | each intent's *Decision log* | How long ideas wait for a person |
| Build | Median days plan to changelog | git dates of `docs/plans/<slug>.md` and its `changelog` | Approved plan to shipped change - the playbook's "plan approval to merged PR" |
| Build | Plan revisions per change | commits to a plan after its first | Design rework after approval |
| Learn | Experience-log entries, user corrections | `docs/knowledge/experience-log.md` | How often Claude needs correcting |
| Learn | Mistakes seen twice or more, promotions | `Class`, `Promoted`, `Promotion: declined` lines | Whether repeated mistakes turn into `CLAUDE.md` rules |
| Maintain | Intents raised by monitoring, days to triage, repeat problems | `originator: monitoring/...` intents | Whether the maintain loop's findings get handled, and which keep coming back |

The numbers are only as good as the files: an intent whose *Decision log* never records the
acceptance is counted as undecided, and a change shipped without a changelog is not in the plan-to-
changelog median. The table says how many items each median was computed from.

**Not measured here**: first-pass CI success rate, review time, time to first review, change failure
rate, and the DORA metrics. They need CI and review data from the code host rather than files in the
repository; the script lists them instead of approximating them.
