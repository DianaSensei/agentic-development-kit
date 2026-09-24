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

- Class: <kebab-case name for the KIND of mistake, e.g. unbounded-retry, wrong-test-command>
- Source: fix-loop | user-correction
- Area: <paths or modules it happened in>
- Cause: ...
- Attempts used: X/5 (n/a for a user correction)
- Outcome: Fixed | Not fixed (raised to user)
- Fix applied (if resolved) / Approaches tried that did NOT work (so they aren't retried next time)
```

Append one entry per issue encountered in the fix loop, whether or not it was resolved - an unresolved
issue's "approaches that didn't work" list is exactly what saves time the next time a similar issue
appears, in this project or another. Also append one entry per **user correction** in this run: each
time the user told you a convention, command, assumption, or piece of output was wrong. Those are the
mistakes most likely to happen again, because nothing in the code records them.

**`Class` is what makes a repeat findable.** Name the kind of mistake, not this instance, and reuse an
existing class when one fits - check first with `grep -h '^- Class:' docs/knowledge/experience-log.md |
sort | uniq -c`. Two entries that describe the same mistake under different classes are a repeat nobody
will notice.

**Never overwrite this file** - it's a cumulative log across every feature/bug worked on. Always append.

## Reading the Log (every workflow's Step 0)

If `docs/knowledge/experience-log.md` exists, search it - don't read it whole, it only grows - for
entries whose `Area` overlaps the files you are about to touch, or whose `Class` or cause matches the
problem at hand (`grep -n -i -A8 '<path or keyword>'`). For each match:
- An approach listed as "did NOT work" is ruled out. Retry it only if you can say what differs this
  time, and say it.
- A fix that worked is the first candidate, not a certainty - check it still fits the current code.
- Name the entries you relied on in the plan or report, so the reader can see the log was used.

## Promoting a Repeat to CLAUDE.md (every workflow's knowledge-capture step)

After appending, count each class you just wrote:
`grep -c '^- Class: <class>$' docs/knowledge/experience-log.md`.

At 2 or more - the same mistake has now happened twice - and when no line in `CLAUDE.md` already covers
it, propose one rule for `CLAUDE.md`:
- **One line, imperative, specific**: where it applies and what to do. "In `src/billing/`, pass an
  idempotency key to every `gateway.charge` call" - not "be careful with payments".
- **Ask before writing it** - `AskUserQuestion` with `header` `"CLAUDE.md"`, the exact line as the
  question, options "Add it" / "Not now". `CLAUDE.md` is read by every future session and every
  teammate, so it changes only with a person's yes.
- **Yes** → append the line under a `## Common mistakes` heading in the project-root `CLAUDE.md`
  (create the heading, or the file, if missing) and add `- Promoted: CLAUDE.md` to this log entry.
- **Not now** → add `- Promotion: declined <date>` to this log entry, and ask again only when the
  class reaches its next occurrence.

This is the playbook's rule - when Claude makes the same mistake twice, the correction goes into
`CLAUDE.md` - with the log as the memory that makes "twice" countable.
