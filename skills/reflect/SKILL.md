---
name: reflect
description: Keeps a personal profile of how the user works - how they weigh tradeoffs, design, write code, review and want to be worked with - learned from their corrections, Checkpoint choices, rewrites of agent-written code and review comments, and loaded into every session from their own private repository. Sets the profile up on a machine, notes a signal as it happens, and consolidates signals into profile changes the user approves one by one. Use when the user says "reflect", "learn from this", "remember that I prefer...", "what do you know about how I work", "set up my profile", or after a workflow's knowledge capture when new signals are waiting. Not for a project's conventions (CLAUDE.md, REVIEW.md and checks - the workflows' learning loop owns those) and never for anything outside work style.
metadata:
  domain: workflow
  triggers: reflect, learn my style, remember my preference, personal profile, how I work, what do you know about me
  role: specialist
  scope: documentation
  output-format: document
  related-skills: feature-development, bug-fix, refactor, code-host, knowledge-base
---

# Reflect

The model does not learn from working with someone; what it is given to read does. This skill keeps
that reading short, true and the user's own: a profile of how they work, grown from evidence, written
only with their yes, in a private repository they control. Format, evidence rules and budget:
`references/profile-format.md` - read it before writing either file.

`PROFILE` below is where the user says their profile is checked out, else `$ADK_PROFILE_DIR` if set,
else `~/.claude/adk-profile`.

## Rules that hold throughout

- **Nothing is written without a yes.** Not the profile, not `~/.claude/CLAUDE.md`, not a push. The
  profile steers every future session; the user decides what goes in it.
- **Private and personal.** The profile repository must be private, and nothing from it is ever
  written to a project repository, a pull request or an issue. It holds work style only - never
  anything about the person's life, and never client code, data or credentials beyond a generalised
  line of example.
- **The project wins.** A preference that conflicts with the project's `CLAUDE.md`, `REVIEW.md` or
  checks is never applied over them; the agent follows the project and says so.
- **Evidence or nothing.** Every profile line carries the evidence behind it. A guess about the user is
  not a preference.

## Mode: Set up (once per machine)

1. `PROFILE` exists and is a git repository → `git -C PROFILE pull --ff-only`, then go to step 4.
2. Ask for the user's private profile repository URL (`AskUserQuestion`, `header` `"Profile repo"`,
   options "I have one" / "Create it locally first"; the URL comes as free text). Ask them to confirm it
   is **private** - if it is not, stop: the profile must not be published.
   - Have one → `git clone <url> PROFILE`.
   - Create locally → create `PROFILE` with `profile.md` (the header from the reference, empty
     sections), an empty `signals.md` and a `README.md` ("my working profile for Claude Code, kept by
     the agentic development kit's `reflect` skill - private"), `git init`, commit. Tell the user to
     create an empty private repository and give its URL; then `git remote add origin <url>` and push
     only with their yes.
3. On a second machine the same step 2 with "I have one" is all it takes: the clone brings everything.
4. `~/.claude/CLAUDE.md` must contain the line `@~/.claude/adk-profile/profile.md` (the path to
   `PROFILE/profile.md` when `ADK_PROFILE_DIR` moves it). Missing → show the line and ask
   (`header` `"Load profile"`) before adding it; create the file if there is none, append otherwise,
   never rewrite what is there.

## Mode: Note a signal (as work happens)

When the user states a preference, corrects the agent's work in a way that is about *them* rather than
the project, or chooses at a Checkpoint and says why: append one line to `PROFILE/signals.md` in the
reference's format. No approval needed for the inbox - it changes nothing until a reflect - but say
in one line that it was noted. The workflows do this at their knowledge-capture step for experience
log entries with `Scope: personal` and for Checkpoint choices. No profile set up → skip silently.

## Mode: Reflect (consolidate)

1. **Sync first**: `git -C PROFILE pull --ff-only`, so what another machine learned is here.
2. **Gather** what is new since the last `## reflected` marker:
   - `PROFILE/signals.md` lines after the marker;
   - in the current repository, if any: `docs/knowledge/experience-log.md` entries with
     `Scope: personal`; Checkpoint choices in `docs/plans/*.md` (the chosen proposal, the rejected ones,
     the reason) and intents' Decision logs;
   - **your rewrites**: `python3 <this skill's dir>/scripts/followup_edits.py --since "<last reflect date,
     or 90 days ago>"` in the current repository - the lines the user rewrote that the agent wrote.
     Read each pair for the *pattern* (error handling, naming, structure, API shape), not the instance.
     No shell in this session → use a scan the user hands over (its output saved to a file), or ask
     them to run the command and paste it;
   - review comments the user left on the agent's pull requests, through `code-host`'s read operations,
     when its server is connected and the user wants them included.
   Record each piece of new evidence found outside `signals.md` as a signal line, so the inbox holds all
   of it.
3. **Read `PROFILE/profile.md`**, then work out the changes by the reference's evidence table:
   - **add**: a preference with enough evidence and no line yet;
   - **strengthen**: new evidence for an existing line - update its trailer;
   - **revise**: evidence against a line, or a context it holds only in;
   - **retire**: a line with no evidence for 6 months, or one the user now contradicts;
   - **ask**: contradicting signals - which holds, or when each does.
   A preference a machine could check ("never `except Exception:`") is also worth a project check, but
   only as a suggestion for the project's team: the profile stays personal. Checkpoint signals that
   name the dimensions they traded ("reversibility over performance_and_scale") become "How I decide"
   lines in the tradeoff rubric's words and the context they held in ("Prefer `reversibility` over
   `performance_and_scale`, except on a request path"), because `feature-development` reads those
   lines to order the next design's priorities.
4. **Present** the changes as a table - change, the exact line, the evidence (dates, kinds, one
   example each) - then `AskUserQuestion`, `header` `"Profile"`, `multiSelect`, one option per change
   (rewording comes through "Other"). No changes → say what the evidence was and why nothing reaches a
   line yet.
5. **Write** the approved ones to `profile.md`, within the 60-line budget: past it, propose the merges or
   retirements that make room, in the same way. Append `## reflected <date>` to `signals.md`.
6. **Commit** in `PROFILE` ("Reflect <date>: +2 ~1 -1") and ask before pushing (`header` `"Sync"`) -
   the push is what reaches the user's other machines.

## Mode: Show

"What do you know about how I work" → print `profile.md` as it is, with the number of signals waiting
since the last reflect. Offer a reflect if there are any.

## Boundaries

- The project's conventions are the workflows' learning loop (`feature-development`'s
  `references/report-and-logs.md` → "Promoting a Repeat"): `CLAUDE.md` lines and checks, for everyone.
  This skill is one person's working profile, for their sessions only.
- Reading the user's git history for rewrites happens only here, on their request, in the repository
  they are in, and its output stays on the machine except as generalised signal lines.
