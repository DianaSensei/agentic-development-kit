---
title: debt
type: schema
entity: debt
version: 1
schema:
  debt: string, what is wrong or missing, in one line
  impact: string, what it costs today - incidents, slowness, risk
  cause?: string, how it came to be
  workaround?(array): string, what people do around it now
  fix?: string, what paying it down would take
  source?(array): string, where it was found - an incident, a PR, a review
  in?(array): System, the systems that carry it
settings:
  validation: warn
  frontmatter:
    status(enum): [open, paying-down, resolved]
    verified: string, the date someone last checked it is still there
---

# debt

Known technical debt: what is wrong, what it costs, what people do around it, and what fixing it
would take. A change that touches the system reads it before planning.
