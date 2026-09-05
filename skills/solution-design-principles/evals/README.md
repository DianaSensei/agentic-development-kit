# Trigger evals - `solution-design-principles`

`trigger-eval.json` checks whether Claude Code selects this skill for the right requests. Claude Code
matches on a skill's `name` + `description` only (the `metadata.triggers` field is a convention of this
repo, not something the matcher reads), so this eval set is what verifies a description change didn't
break selection.

20 queries, 10 positive / 10 negative. The negatives are deliberate near-misses aimed at the skills this
one competes with most directly - `architecture-designer` (service decomposition, deployment topology),
`java-spring-skill` (JPA, package structure), `refactor`, `security-skill`, `monitoring-expert`,
`legacy-modernizer`, `database-skill`. They share vocabulary with this skill ("coupling", "principles",
"boundaries", "lock-in") but each belongs elsewhere, so they test the description's negative-scoping
clause rather than being easy throwaways.

Re-run after any edit to this skill's `description`:

```bash
cd ~/.claude/skills/synced/skill-creator
python -m scripts.run_loop \
  --eval-set <repo>/skills/solution-design-principles/evals/trigger-eval.json \
  --skill-path <repo>/skills/solution-design-principles \
  --model <model-id> --max-iterations 5 --verbose
```

The loop splits train/test and picks the winning description by *test* score, so it doesn't overfit to
the queries it tuned against.

## Measured baseline

First run (3 iterations, holdout 0.4): **precision 100%, test recall 0%** - every negative was correctly
rejected, and no positive ever triggered. Three LLM-generated description rewrites left test recall at
zero, which is what ruled out wording as the cause.

The reachability check that followed found the real problem: the skill was referenced by no orchestrator
(2 files total, vs. 9 for `architecture-designer`), and `workflow-router` legitimately doesn't route it,
since that router handles code-writing requests only. It was fixed by referencing the skill from
`code-review-skill`, `refactor`, and `feature-development` rather than by rewording anything.

Two things to carry into a future run:

- **Interpret recall and precision separately.** Accuracy alone is misleading here: a description that
  never triggers still scores 50% on a balanced set, because it gets all ten negatives right for the
  wrong reason. Read recall first.
- **A failing eval is not automatically a description problem.** If rewrites don't move test recall,
  check reachability before continuing to tune wording - and bear in mind this skill's content is
  general engineering knowledge a model will often answer from directly, which raises the bar for
  autonomous triggering no matter how the description is phrased.

A negative that starts triggering is the opposite signal, and means the "Not for ..." clause at the end
of the description needs tightening.
