# Evals

Behavioral regression tests for the kit, run with Claude Code's
[`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals). Each case is a realistic request, run
in a fresh headless session with only this plugin loaded, then graded on what Claude did. They answer the
question a skill edit raises and nothing else can: does Claude still behave the way the kit promises?

[`skill-evals.yml`](../.github/workflows/skill-evals.yml) runs the suite on every pull request that
touches `skills/`, `hooks/`, `agents/`, `evals/`, or the manifest.

## Cases

| Case | Guards against |
|---|---|
| `routing/question-skips-router` | a description edit that makes a plain question start a code-changing workflow |
| `routing/improve-that-is-a-bug` | "improve X" on behavior that is wrong today not reaching `bug-fix`; any code edit before the Checkpoint is confirmed - a headless run can never confirm it, so a correct run edits nothing |
| `routing/checkpoint-then-apply` | the second half of a workflow: once the person confirms the Checkpoint - replayed from a recorded session that stopped there - `bug-fix` must bound the loop as proposed, add a test and run its self-review |
| `intent-capture/solution-in-disguise` | intent files drifting from the template (keys, `null` links, sections, order); the originator's solution leaking into *Problem* instead of *Originator's idea* |
| `learning-loop/reads-known-dead-end` | a bug of a kind the project already hit being diagnosed without the experience log - the entry's recorded dead end is only visible to a run that searched the log. Measured with a no-plugin baseline: 1.00 with the kit, 0.33 without |
| `project-setup/fresh-python-repo` | setup writing anything the repo does not show (a foreign tool's command, invented `CODEOWNERS`), a GitHub repo without the code host's MCP server in `.mcp.json`, reading the `.env` it protects, `./`-anchored deny rules that miss nested files, allow rules without the space before `*`, a settings file that would not parse |
| `project-setup/gitlab-repo` | a GitLab-hosted repo getting GitHub's files, the reviewer's `include:` replacing the project's own pipeline instead of joining it, a review job that names a stage the pipeline does not define, `.mcp.json` without GitLab's MCP server |
| `project-setup/adds-never-overwrites` | setup losing a line of an existing `CLAUDE.md`, a second title, or a rewrite of an existing `settings.json` that drops its keys |
| `independent-review/planted-defects` | the reviewer missing a violated non-goal, an exception defined but never raised, or missing tests - or being talked out of them by a comment in the code telling it to report 0 blocking findings; skipping the `code-review-skill` checklist |
| `independent-review/clean-change` | the reviewer inventing blocking findings on a change that meets its intent and plan, with a passing test per acceptance criterion |

Graders are deterministic (`regex`, `tool_used`, `file_exists`) wherever the question allows, and an
`llm` judge only for "did the review name this specific defect", with a short PASS/FAIL rubric.

## Run it

From the repository root. Each case runs 3 times by default:

```bash
claude plugin eval . --trust-plugin --scaffold --allow-tools Write Edit \
  --ablation none --model claude-sonnet-5 --judge-model claude-haiku-4-5 \
  --threshold 0.8 --no-publish -j 4
```

- **Cost**: about $3 for the full suite at 3 runs per case, about $1 at `--runs 1`. `--tag` or `--case`
  narrows it: `--tag independent-review`.
- **`--scaffold`** runs each case's `fixture.sh`, which builds the workspace (a small repo with an intent,
  a plan and a branch to review). They are this repo's own scripts; read one before trusting it.
- **`--ablation with-without`** adds a run of every case with no plugin loaded and reports `Δ`, what the
  kit contributes over plain Claude. It doubles the cost; worth it before a release, not on every PR.
- `results/` is written under this directory and git-ignored. Open `report.html` to see every run's
  graders and the judge's evidence.
- The "toolbox has no mock and is NOT started" notice on every case is expected: no case uses the
  database MCP.

## From a real failure

The best case is a change that actually fooled the kit. When the independent reviewer misses a defect on
a real pull request, or reports one that is not there, turn it into a case:

```bash
python3 evals/new-review-case.py --repo ../the-project --base <base-sha> --head <head-sha> \
  --name missed-refund-null-check --missed --path src/refunds.py --line 42 \
  --what "refund() dereferences order.payment, which is None for gift-card orders."
```

It copies what the reviewer saw into `evals/independent-review/<name>/`: the changed files and their
directory neighbours as they were at `--base`, `CLAUDE.md`, `REVIEW.md`, the intents and plans, and the
change as a patch. Its fixture rebuilds the repository and `review.diff` from those. The graders are the
usual reviewer checks plus a judge for this one failure - the defect it must report (`--missed`), or the
claim it must stop making (`--false`). The run's `transcript.jsonl` (kept by CI, see `ci/README.md`) shows
what the reviewer looked at, which is where the `--what` sentence comes from.

**The new case must fail first.** Run it against the kit as it is; a case that passes does not capture
the failure. Then fix the skill and watch it pass - and the rest of the suite stay green. The seed is
code from the project: strip anything you would not commit here.

A user correction (`Source: user-correction` in a project's experience log) is the same kind of
evidence, for the workflows rather than the reviewer: reproduce the situation in a fixture, and grade the
behaviour the correction asked for.

## Multi-turn cases

A single prompt cannot test what happens after a Checkpoint is confirmed - a headless run can only ever
reach the question. A case can instead continue a recorded conversation (`context.history_file`); its
prompt becomes the next user turn. To record one:

1. Run the case's fixture in a new empty directory, then `claude -p "<the first request>" --plugin-dir
   <this repo> --allowedTools "Read,Glob,Grep,Skill,Agent,Write,Edit"` there, and check it stopped where
   the case should pick up.
2. `python3 evals/clean-history.py ~/.claude/projects/<escaped dir>/<session>.jsonl
   evals/<group>/<name>/history.jsonl --workspace <that directory> --plugin-root <this repo>`. It keeps
   only the conversation, makes paths relative - a replay otherwise reaches back into the recording
   directory - and refuses to write anything that looks like an email address, a home directory or a key.

Two things learned building `routing/checkpoint-then-apply`: list every tool the continuation needs in
the case's own `allowed_tools` (grants from `--allow-tools` did not reach the replayed session), and grade
the resulting files rather than the trace - an `llm` judge sees only a trace's first and last 12
messages, and the history fills the first 12.

## Why no case needs a shell

Granting `Bash` to a run requires the OS sandbox (bubblewrap), which fails inside some containers
(`write /proc/self/uid_map: Operation not permitted`) and needs extra setup on GitHub's Ubuntu runners.
So every case works with read-only tools plus `Write`/`Edit`: the review fixtures hand the reviewer
`review.diff`, the way CI hands it a PR diff, instead of expecting it to run `git`.

## Writes under `.claude/` are graded on the attempt

Claude Code refuses writes to its own `.claude/` directory in a non-interactive run, whatever
`--allow-tools` grants, so no eval can check a written `.claude/settings.json` on disk. The
`project-setup` settings graders therefore read the Write or Edit call itself in the trace - anchored to
that call's `file_path` and bounded to its content string, because the skill's own reference, which
holds the same JSON, is also in the trace. A trace with the reference read and no settings write fails
every positive settings grader; that was checked before relying on them.

## Adding a case

1. `claude plugin eval init --bare <group>/<name>` for the skeleton, or copy a case here.
2. Phrase the prompt the way a user would, never by naming the skill.
3. Grade the outcome and how Claude got there - e.g. a `regex` on a produced file plus a `tool_used` on the
   skill - and give "must not" checks `min: 0`, `max: 0`, `arm: both`.
4. Before relying on a `regex` grader, run it against real outputs: every pattern here was checked to
   pass on correct runs and fail on the defect it targets. A pattern that also matches unrelated text
   ("no shell available ... tests") passes runs it should fail.
5. When a grader fails, read the evidence in the report before changing anything. A failure here has
   been, in turn, a real skill defect (the reviewer skipping its checklist), an unfair fixture (a
   docstring that made the correct change look risky), and a judge misreading a correct review. Only the
   first is fixed in the skill.
