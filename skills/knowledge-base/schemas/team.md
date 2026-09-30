---
title: team
type: schema
entity: team
version: 1
schema:
  responsibility(array): string, what the team answers for
  contact?(array): string, how to reach it - a channel, an on-call rotation
  owns?(array): System, the systems it owns
settings:
  validation: warn
---

# team

Who owns what, and how to reach them. Referenced by systems and agreements.
