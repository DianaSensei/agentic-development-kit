---
description: "A change whose description claims three things its diff does not do: banker's rounding (the diff truncates), added tests (none), and no behavior change for apply_tax (the diff changes it)."
tags: [independent-review]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill]
---

Do an independent review of this branch against main. There is no shell in this session, so the diff is in review.diff, and the pull request's title and description are in change.md.
