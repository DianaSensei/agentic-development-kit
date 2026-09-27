# Tickets

How the approved design becomes work a developer can follow without redesigning it. After the
CHECKPOINT, the senior who drew the path (`solution-architect`) writes one ticket per task of the
chosen proposal. Each ticket is precise enough that the implementer's job is to build it, not to
decide it. The implementer stops and reports where the path turns out to be wrong, instead of
improvising around it.

Tickets are written once the person has chosen, never before, so no ticket is written for a proposal
that loses. They are written at full depth only: at light depth the lead builds the change itself, from
the inline proposal.

## A ticket

One per `task_breakdown` item of the chosen proposal, same `id`, `files`, `depends_on`:

| Field | What it holds | Example |
|---|---|---|
| `interface` | every function, class, endpoint, column or config key the task adds or changes, with its exact signature | `shop.dashboard.render(conn, customer_id) -> dict` with keys `name`, `order_count` |
| `follow_pattern` | existing code to copy the shape of: `{"what", "at": "path:line"}` | how a write is wrapped in a transaction: `src/shop/orders.py:12` |
| `tests` | each test the task must add, as Given / When / Then | Given a customer with 3 orders, 1 cancelled, when the dashboard renders, then `order_count` is 2 |
| `must_not` | what is out of bounds: files, behaviour, decisions | change `cancel_order`'s signature; add a dependency |
| `done_when` | the command that proves it, and what it must show | `python3 -m unittest discover -s tests -t .` passes |
| `stop_if` | conditions specific to this task that mean the plan is wrong | the `customers` row is not already read by `render` |

- `interface` may be empty only for a task that adds no callable surface (an index, a data backfill),
  with `no_interface_reason`.
- `follow_pattern` may be empty only when the codebase has nothing like it yet, with
  `no_pattern_reason`. That is itself worth knowing: the implementer is setting a pattern, not
  following one.
- Every `path:line` is one the architect read. A ticket citing code it did not read sends the
  implementer after something that is not there.

## When the path is wrong: stop, never improvise

A ticket followed faithfully into a wall does more harm than no ticket. These always hold, on top of
the ticket's own `stop_if`. The implementer stops, commits what it has (`WIP`), and returns
`plan_mismatch` with what it expected, what it found, and where:

- a name, file, signature or line the ticket cites does not exist, or is not what the ticket says;
- the code at `follow_pattern` does not do what the ticket says it does;
- a listed test cannot pass without changing the `interface`, or without touching a path outside
  `files`;
- the ticket contradicts `CLAUDE.md`, an owning skill, or another ticket.

The lead then handles the mismatch like a unit's question (`parallel-units.md`): answer it from the
plan when the plan settles it, and resume the agent. A mismatch that changes the interface, a file
list or an acceptance criterion changes the approved plan, so it goes back to the person as a
CHECKPOINT.

## Checking tickets

`solution-architect` has no shell, so the lead checks its tickets:

```bash
python3 <this skill's dir>/scripts/check_tickets.py <tickets.json>
```

Run it from the project root: it also opens every `follow_pattern` file and rejects a citation of a file
that is not there or a line past its end - the cheapest place to catch a ticket that would send an
implementer after code that does not exist. It lists what is missing, then grades each ticket. A ticket is **tight** when it has an interface (or
a reason for none), a pattern with a `path:line` (or a reason for none), at least one test in Given /
When / Then, and a `done_when`. Anything else is **loose**. A problem of wording alone - a test already
stated, just not as Given / When / Then - you may reword without changing what it asks. Anything that
takes knowledge of the code - a missing interface, pattern or test, a wrong `path:line` - goes back to
the architect once (`SendMessage`): filling it in yourself is designing the ticket without having read
what the architect read. A ticket that stays loose is built by the lead's model, never handed down as if it
were tight.

## Who builds what: model tiers

The person who draws the path should be the strongest engineer in the room. A tight ticket is what makes
it safe to hand the work to a cheaper, faster one. `models` in `.claude/quality-check.config.json`
(defaults in the kit's own config):

| Key | Used for | Default |
|---|---|---|
| `models.plan` | `business-analyst` and `solution-architect`: the requirement, the design, the tickets | `opus` |
| `models.build` | `unit-implementer` on a **tight** ticket | `sonnet` |

- Pass the value as the Agent tool's `model` when dispatching. `inherit` means pass none, so the agent
  runs on the session's model.
- A **loose** ticket's unit is dispatched with no `model`, so it runs on the session's model: a vague
  ticket needs the judgment the cheap model was chosen to save.
- The lead, the self-review and the independent reviewer are not downgraded. Checking the work is the
  senior's job.

## In the plan

The plan gets a `## Tickets` section after the CHECKPOINT: one sub-heading per ticket with its fields,
and its tier. The Step 4 report names each unit's tier and model, every `plan_mismatch` raised, and
how it was resolved.
