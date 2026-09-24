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
| `intent-capture/solution-in-disguise` | intent files drifting from the template (keys, `null` links, sections, order); the originator's solution leaking into *Problem* instead of *Originator's idea* |
| `learning-loop/reads-known-dead-end` | a bug of a kind the project already hit being diagnosed without the experience log - the entry's recorded dead end is only visible to a run that searched the log. Measured with a no-plugin baseline: 1.00 with the kit, 0.33 without |
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

## Why no case needs a shell

Granting `Bash` to a run requires the OS sandbox (bubblewrap), which fails inside some containers
(`write /proc/self/uid_map: Operation not permitted`) and needs extra setup on GitHub's Ubuntu runners.
So every case works with read-only tools plus `Write`/`Edit`: the review fixtures hand the reviewer
`review.diff`, the way CI hands it a PR diff, instead of expecting it to run `git`.

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

`skills/solution-design-principles/evals/` is a different kind of eval set: skill-creator's trigger
queries for tuning that one skill's `description` by hand. It is not part of this suite or of CI.
