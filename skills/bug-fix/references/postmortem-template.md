# Postmortem Template (Step 6.3)

```markdown
# Postmortem: <bug name> - <discovery date>

## Time Discovered

## Timeline of Events
Key milestones from when the bug was discovered to when it was fixed, with concrete timestamps, who
did what, and the outcome of each step.

## Initial Symptoms

## Root Cause

## Impact
Scope of impact and severity.

## How It Was Found/Reproduced

## The Fix

## Tests Added to Prevent Recurrence

## Lessons / Prevention Recommendations
If there's a general pattern that could apply elsewhere. Give the experience-log `Class` of this bug, so
the next occurrence of the same kind of mistake is countable. If the defect came from how an agent
behaved - a skill instruction that was wrong or skipped, a rule that was missing - and the project keeps
an eval suite (`evals/`), name the eval case that would have caught it: that is the regression test for
the agent, the way the test above is for the code.
```

## If Not Reproduced/Fixed

Still create the postmortem, with an "Unresolved" section instead of "The Fix," stating: the
hypotheses already tried, why work stopped (5-attempt limit reached, or missing information), and the
recommended next step for whoever picks this up next.
