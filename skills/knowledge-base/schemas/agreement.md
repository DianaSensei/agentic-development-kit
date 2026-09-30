---
title: agreement
type: schema
entity: agreement
version: 1
schema:
  term(array): string, what each side promised - an API shape, an SLA, a data format, an order of release
  contact?(array): string, who to ask on each side
  source?(array): string, where it was agreed
  party(array): Team, the teams bound by it
  governs?(array): System, the systems it covers
settings:
  validation: warn
  frontmatter:
    status(enum): [proposed, active, retired]
    verified: string, the date someone last confirmed it with the other side
---

# agreement

A promise between teams: an interface, an SLA, a release order, a data contract. Breaking one
breaks someone else's system, so a change that touches a governed system reads it first.
