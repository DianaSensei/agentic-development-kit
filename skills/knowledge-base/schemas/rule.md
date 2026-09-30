---
title: rule
type: schema
entity: rule
version: 1
schema:
  rule: string, the business rule or the meaning of a domain term, in one line
  example?(array): string, a concrete case
  exception?(array): string, when it does not hold
  source?(array): string, who or what says so - a policy, a contract, a product owner
  applies_to?(array): System, where it is enforced
settings:
  validation: warn
  frontmatter:
    verified: string, the date someone last confirmed it with its source
---

# rule

A business rule or a domain term - what the business means, independent of how any system
implements it. The code shows what is done; this says what should be.
