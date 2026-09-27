# Compare Builds

When two proposals are close and reading them cannot settle it, build both and compare what was built.
Each is implemented by a `unit-implementer` in its own worktree from the same starting commit; the
results are measured the same way; the user picks; one is applied and the others are discarded.

It costs one implementation per candidate - roughly double for two - so it is **opt-in**, offered only
at full depth, and never the default. It pays when the difference between the proposals is something a
build shows and a document does not: behavior on the project's real tests, how much code each needs,
whether one fights the codebase's conventions, a performance or edge case the plan only guessed at.

## When to offer it

At the Step 2 CHECKPOINT, add the option **"Build the top two and compare"** only when all hold:

- full depth, and `solution-architect` returned two or more proposals the user could reasonably pick
  between - not one strong proposal and a straw man;
- the difference between them is measurable by building: tests, checks, size, a benchmark the project
  already has - not a matter of product direction or taste, which no build settles;
- the change is small enough to build twice: a unit, or a plan of a few units, not a whole subsystem.

Say the cost in the option's description ("builds both: about twice the implementation time and
tokens"). The user choosing it approves both candidates' plans at once.

## Build

- `base_commit` as for parallel units (HEAD, or the current wave's snapshot).
- One `unit-implementer` (`subagent_type` `adk-adlc:unit-implementer`) per candidate, **in a single message**, each with the same `unit` (id suffixed
  `-a`, `-b`), the same `files`, acceptance criteria and `skill_paths`, and its own proposal as
  `plan_excerpt`. Tell each which candidate it is and that another agent builds the alternative: it
  builds its proposal faithfully, not a blend.
- Candidates have no tickets - no proposal is chosen yet - so they run on your model, not
  `models.build`. The winner's tickets are written after the choice, for whatever is left to build.
- Questions from a candidate are answered as in `parallel-units.md`; an answer that applies to both goes
  to both.

## Measure - the same way for every candidate

In each candidate's worktree, after it reports:

| Measure | How |
|---|---|
| Tests | the project's documented test command, **run by you** in the worktree - the **whole** suite, not only the candidate's own tests. A candidate's `test_run_result` is its claim, not the measure |
| Checks | every `checks` entry in `.claude/quality-check.config.json`, file scope on the changed files and project scope |
| Acceptance criteria | each AC met / not met, from the candidate's tests and a read of its diff - not from its own report alone |
| Size | `git diff --shortstat <base_commit> <branch>`; new dependencies, if any |
| Review | a fresh read-only review of each diff against `code-review-skill`'s checklist - one `Explore` agent per candidate, or yourself if the diffs are small; severe findings only |
| Anything the plan named | a benchmark or scenario the proposals disagreed about, when the project can run it |

A measure one candidate cannot run (a missing tool) is "not measured" for both - never a win by default.

## Decide - the user does

Present one table: the measures in rows, a column per candidate, facts only - numbers, pass/fail, the
review's findings with their lines. Then a recommendation of one line, from the table and nothing else:
a candidate that fails a test or a check the other passes loses unless the user says otherwise.
`AskUserQuestion`, `header` `"Compare"`, one option per candidate plus "Neither - revise".

Then:
1. Apply the chosen candidate's diff to the working tree exactly as `parallel-units.md` → "Bringing the
   units back" applies a unit, and continue Step 3 from there.
2. Remove every candidate's worktree and branch, chosen or not.
3. In `docs/plans/<feature-slug>.md`, the chosen proposal gets a line "Chosen after building both: <the
   deciding facts>"; the other stays under its `Rejected:` block with the same facts - the next person
   to wonder "why not B?" finds the measured answer, not an opinion. In the plan's `## Tradeoffs`
   table, a rating the build measured takes its result as evidence (`measured: B 12/12 tests, A 10/12`).

## Report

Step 4's report says the proposals were built and compared, the table, the user's choice, and what the
comparison cost (the candidates' run costs, when known).
