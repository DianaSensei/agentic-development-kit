---
title: decision
type: schema
entity: decision
version: 1
schema:
  context: string, the problem and the forces at the time
  decision: string, what was decided, in one line
  alternative?(array): string, what else was weighed and why it lost
  consequence?(array): string, what follows from it - costs accepted, rules it sets
  source?(array): string, where it was decided - a PR, an ADR, a meeting, a person
  affects?(array): System, the systems it binds
  supersedes?: Decision, the earlier decision it replaces
settings:
  validation: warn
  frontmatter:
    status(enum): [proposed, accepted, superseded]
    date: string, when it was decided
---

# decision

A choice that binds future work - why it was made, what lost, and what it costs. A decision that
spans repositories or teams lives here; one inside a single repository can stay in its
docs/decisions/ and be linked from here.
