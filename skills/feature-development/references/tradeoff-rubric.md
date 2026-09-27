# Tradeoff Rubric

Every design proposal is weighed on the same fixed dimensions, each with a rating and the evidence the
rating rests on. The priorities that decide between the proposals are stated before any proposal is
read. The most common design failure is a plausible answer with no alternatives weighed - or with
alternatives weighed on whatever the author happened to think of - and a free-text "tradeoff analysis"
lets both through.

## The dimensions

| Key | The question | Good | Poor |
|---|---|---|---|
| `correctness_risk` | What can this get wrong, how likely, and how much breaks if it does? | few ways to fail, each caught by a test or a type | a failure that is silent, or corrupts data or money |
| `reversibility` | What does undoing it cost once it has shipped? | a revert | a data migration, a published API or event schema, a one-way door |
| `performance_and_scale` | What does it cost on the paths that matter, now and at 10x the load? | no new work on a hot path | N+1, unbounded memory, a lock or a call per request that grows with the data |
| `operational_load` | What does it add to run: infrastructure, config, jobs, alerts, failure modes? | nothing new to run | a new service, queue, cron job or secret, or a new way to page someone |
| `convention_fit` | Does it follow how this codebase already solves this kind of problem? | the same pattern as `path:line` | a second way of doing something the code already does one way |
| `native_approach` | Does it use the stack's built-in way, or hand-roll one? | the framework's own mechanism, cited | a custom version of what the framework or standard library provides |
| `cost_to_build` | How much has to change: files, modules, new dependencies, tests? | a few files in one module | many modules, or a new dependency |

A dimension that does not apply to a proposal is rated `good`, with the reason ("no new work on a request
path: runs once at startup"). It is never left out: leaving it out and "not considered" read the same.

## Rating and evidence

Each dimension of each proposal gets:

- `rating`: `good`, `fair`, `poor`, or `unknown`. The rating is about this proposal on this
  dimension, not relative to the others. The table shows the comparison.
- `why`: one sentence, specific to this proposal.
- `evidence`: what the rating rests on, in one of these forms:
  - a `path:line` in the project;
  - a URL or a named document (the framework's docs, an ADR);
  - `requirement: <AC id or constraint>` from Step 1;
  - `measured: <what and the result>` (a benchmark, or a build compared in `compare-builds.md`);
  - `plan: <what this proposal itself adds or touches>` - for a fact about the proposal rather than
    the code: "plan: 3 files, no new dependency", "plan: adds no job, service or config". It must match
    the proposal's own `task_breakdown`;
  - `assumption: <what is assumed> - confirm by <how>`.

`unknown` is honest and allowed. Its evidence says what would tell, and a decision that hinges on an
`unknown` goes to the user as a question, never as a guess. A rating whose evidence is only an assumption
counts as `unknown` when the proposals are compared.

## Priorities: stated before the proposals

The order of the dimensions decides between proposals. It comes from, in this order:

1. **This change's requirement.** A constraint or acceptance criterion from Step 1 or the intent ("must
   not double-charge", "p95 under 200 ms") puts its dimension first.
2. **The project.** `tradeoffs.priorities` in `.claude/quality-check.config.json` (an ordered list of the
   keys above), or what `CLAUDE.md` says about how the project decides.
3. **The person.** Lines under "How I decide" in their profile (`reflect`), such as "Prefer reversible
   changes over faster ones". The project wins where the two conflict. Say so when they do.
4. **The default:** `correctness_risk`, `reversibility`, `convention_fit`, `native_approach`,
   `operational_load`, `performance_and_scale`, `cost_to_build`.

The lead agent works out the order and passes it to `solution-architect` as `priorities`, each with its
source. The architect's output repeats the order with the sources. The CHECKPOINT shows it, so the person
sees *why* one proposal is recommended and can reorder when the order is wrong.

## Recommending

A proposal is `recommended` because it is better on the highest-priority dimension where the proposals
differ. `deciding_dimensions` names that dimension, and `costs` names every dimension where the
recommended proposal is worse than another. A recommendation that hides its costs is a sales pitch.

- Where the proposals differ only on `unknown`s, recommend nothing and ask the question that would
  settle it. When a build would settle it, that is `compare-builds.md`.
- A proposal rated `poor` on `correctness_risk` is not recommended over one that is not, whatever the
  priorities say, unless the person has already accepted that risk in writing.

## One proposal

One proposal still names the alternatives it beat: `alternatives_rejected`, each with the dimension it
loses on and the evidence. When there is genuinely one sensible way, say so in `no_alternative_reason`
("the framework has exactly one mechanism for this: <doc>"). An empty list with no reason is the failure
this rubric exists to catch.

## Checking it

`solution-architect` has no shell, so the lead agent checks its output before presenting it:

```bash
python3 <this skill's dir>/scripts/check_proposals.py <architect-output.json>          # problems, exit 1
python3 <this skill's dir>/scripts/check_proposals.py --table <architect-output.json>  # the CHECKPOINT table
```

The first command lists every missing dimension, rating without evidence, recommendation without a
deciding dimension or with its costs hidden, and single proposal with no alternative. With problems,
resume the architect with the list (`SendMessage`) once. Anything still missing is shown at the
CHECKPOINT as `unknown`, never filled in by you from memory. The second command prints the table: the
dimensions as rows in priority order, a column per proposal, each cell the rating and its `why`.

## At the CHECKPOINT and after

- Show the priorities with their sources, the table, the recommendation with its deciding dimension and
  costs, then ask.
- Put the same table in the plan (`## Tradeoffs`), so the rejected proposals keep their reasons.
- When the person picks against the recommendation, or reorders the priorities, that is the most
  valuable signal there is about how they decide. Record it as a `checkpoint` signal naming the
  dimensions: `chose "<A>" over "<B>" - <dimension> over <dimension> - "<their words>"`. `reflect` turns
  repeated ones into a "How I decide" line, and that line becomes a priority the next time.
