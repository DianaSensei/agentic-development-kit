# Report & Knowledge-Capture Templates (Steps 4–5)

## Final Report Template (Step 4)

```markdown
# Feature Report: <feature-slug>

## AC / DoD Status
| Item | Status | Notes |
|------|--------|-------|
| AC-001: <name> | Met / Not Met | |
| DoD: <item> | Met / Not Met | |

## Issues Encountered
| Issue | Resolved? | Attempts Used | Notes |
|-------|-----------|----------------|-------|
| <short description> | Yes / Raised to user | X/5 | |

## Files Changed
- <path> - <what changed, one line>

## Remaining Risk
<anything not fully resolved, or explicitly "None">
```

Report every AC/DoD item individually - a single "all good" summary hides exactly the information the
user needs to spot a gap before it ships.

## Changelog Template (`docs/changelog/<feature-slug>.md`, Step 5.2)

```markdown
# Changelog: <feature-slug>

## Chosen Proposal
<carried over from docs/plans/<feature-slug>.md, updated if the design changed during implementation>

## Diagrams
<carried over, updated if changed>

## Why This Proposal
<rationale for the choice, including trade-offs against the rejected alternatives>

## Final AC / DoD Status
<same table as the Step 4 report - this is the durable record, the Step 4 report is the point-in-time
message to the user>

## Remaining Risk
<carried from the Step 4 report>

## Files Changed
<carried from the Step 4 report>
```

This file is the record of what was **actually built**, distinct from `docs/plans/<feature-slug>.md`
(which only records what was proposed at decision time, before implementation may have deviated from
it). Don't skip updating this if implementation diverged from the chosen proposal - the changelog
should reflect what shipped, not what was originally planned.

## Experience Log Entry Template (`docs/knowledge/experience-log.md`, Step 5.3)

```markdown
## [<date>] <feature-slug> - <short issue description>

- Cause: ...
- Attempts used: X/5
- Outcome: Fixed | Not fixed (raised to user)
- Fix applied (if resolved) / Approaches tried that did NOT work (so they aren't retried next time)
```

Append one entry per issue encountered in Step 3.3, whether or not it was resolved - an unresolved
issue's "approaches that didn't work" list is exactly what saves time the next time a similar issue
appears, in this project or another.

**Never overwrite this file** - it's a cumulative log across every feature/bug worked on. Always append.
