---
title: system
type: schema
entity: system
version: 1
schema:
  purpose: string, what it does for the business, in one line
  owner: string, the team that owns it and answers for it
  interface?(array): string, how other systems call it - endpoints, events, libraries
  data?(array): string, data it owns or is the source of truth for
  constraint?(array): string, what must stay true - latency, exactness, ordering, legal
  risk?(array): string, what breaks easily or has broken before
  depends_on?(array): System, what it calls or needs
  owned_by?: Team, the owning team's note
settings:
  validation: warn
  frontmatter:
    verified: string, the date someone last checked this note against the code
---

# system

A service, application, library or shared module: what it is for, who owns it, how others reach it,
and what must stay true about it. Not a summary of its code - the code says that better.
