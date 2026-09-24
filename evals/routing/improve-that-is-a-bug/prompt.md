---
description: '"Improve" wording on behavior that is wrong today must route to bug-fix, and no code may change before its Checkpoint is confirmed - which a headless run can never get.'
tags: [routing, checkpoint]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Improve the retry mechanism in src/retry.py - right now it loops forever when the server keeps returning 503.
