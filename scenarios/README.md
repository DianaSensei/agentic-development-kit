# Scenarios

End-to-end regression runs for the kit's orchestration: the behaviour that only shows when a whole
workflow runs with real agents in real worktrees. `evals/` checks single responses cheaply, and the
unit tests check the scripts and hooks. Neither can check that the lead snapshots between waves,
dispatches units with their lanes and tickets on the right model, and never moves the user's branch.
Each scenario here is a real headless Claude Code session with this plugin loaded, on a small
repository its fixture builds, followed by a check of what the session did.

| Scenario | What it guards | Last run |
|---|---|---|
| `waves-and-resume` | units built in dependency waves; wave 1 dispatched together with lanes and tickets on `models.build`; a unit that meets an open decision asks and is resumed with `SendMessage`, and the result follows the person's answer | $1.17, 5 min |
| `compare-builds` | both proposals built side by side as candidates, the one failing the product team's contract tests reported, B recommended from the facts, nothing applied before the person picks | $0.85, 3 min |
| `rubric-checkpoint` | the architect on `models.plan`, its proposals checked by `check_proposals.py`, all seven rubric dimensions at the Checkpoint, no code before the choice | $2.37, 13 min |
| `tickets-dispatch` | the rules read before dispatch, the wave-2 snapshot, three units with lane and ticket on `sonnet`, conformance checked, tests pass, branch unmoved, nothing left behind | $1.69, 7 min |
| `specialist-routing` | a project's code-writing specialist (`route_through_units`) gets its unit through `unit-implementer` with `specialist` and `specialist_path`, lane and `sonnet` - never dispatched straight to the specialist | $1.13, 6 min |
| `tests-bite` | the self-check runs `mutate_changed.py` on a change whose test is hollow, and the tests written in its place kill every mutant; the rule under test is left as written | $0.16, 2 min |

Each came from a live run that found something: a lead dispatching without reading
`parallel-units.md` and committing on the user's branch, units unable to record their lane, a
tight ticket built on the session's model. A change that brings one of those back fails here.

## Run

From the repository root, with Claude Code signed in or `ANTHROPIC_API_KEY` set:

```bash
python3 scenarios/run.py                          # all six, about $7.5 and 40 minutes
python3 scenarios/run.py tickets-dispatch --keep  # one, keeping its repo and transcript
```

Before a release that touches `skills/feature-development/`, `agents/`, or the hooks, run all of them.
The [Scenarios workflow](../.github/workflows/scenarios.yml) runs them by hand from the Actions tab.

## Reading a result

Each check prints `PASS`, `FAIL`, or `WARN`:
- **FAIL** is a `must`: the workflow broke a rule the kit promises - a unit on the wrong model, the
  branch moved, a worktree left behind. The scenario fails.
- **WARN** is an `expect`: behaviour the model shows in most runs but not every one - the lead running
  each candidate's suite itself, a unit asking about the open decision rather than guessing it. It
  is reported so a trend is visible, and does not fail the run.

A failed scenario keeps its directory (the path is printed): `repo/` as the session left it,
`transcript.jsonl` (stream-json), `stderr.txt`.

## Add one

A directory with:
- `fixture.sh <dir>` - builds the repository and commits its starting point. `_shop/base.sh` is a
  shared base.
- `prompt.md` - what the person says.
- `check.py <transcript> <repo> <start-sha>` - assertions, with `lib.py`'s `Run` (the lead's tool
  calls, the agents it dispatched and whether a hook denied them, the final report) and `Checks`.

Check the checker before paying for a run: point `check.py` at a transcript you already have, from
a run that did the right thing and one that did not.
