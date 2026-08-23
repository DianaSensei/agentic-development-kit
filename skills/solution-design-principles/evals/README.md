# Trigger evals — `solution-design-principles`

`trigger-eval.json` checks whether Claude Code selects this skill for the right requests. Claude Code
matches on a skill's `name` + `description` only (the `metadata.triggers` field is a convention of this
repo, not something the matcher reads), so this eval set is what verifies a description change didn't
break selection.

20 queries, 10 positive / 10 negative. The negatives are deliberate near-misses aimed at the skills this
one competes with most directly — `architecture-designer` (service decomposition, deployment topology),
`java-spring-skill` (JPA, package structure), `refactor`, `security-reviewer`, `monitoring-expert`,
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
the queries it tuned against. A negative that starts triggering is the signal that the "Not for ..."
clause at the end of the description needs tightening.
