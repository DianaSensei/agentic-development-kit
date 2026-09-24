# CLAUDE.md

The file every session reads first. The playbook's bar: one page, covering build and test commands,
conventions, architecture, and common mistakes - curated, not generated and forgotten. A long file is
skimmed, and a skimmed rule is a rule nobody follows.

## Shape

```markdown
# <project name>

<One or two sentences: what this is and who uses it.>

## Commands
- Install: `<command>`
- Test: `<command>`
- Lint: `<command>`
- Run locally: `<command>`

## Layout
- `<dir>/` - <what lives there>

## Conventions
- <a convention the code actually follows, e.g. "HTTP handlers return errors through `ApiError`, never raw exceptions">

## Workflow
- Changes start as an intent in `docs/intents/`; plans live in `docs/plans/`, lessons in `docs/knowledge/experience-log.md`.
- Every PR gets an independent review against `REVIEW.md`.

## Common mistakes
```

## Filling it in

- **Commands**: only ones a file in the repo names, written exactly as it names them (`make test`, not
  `pytest` when the Makefile wraps pytest). Put the source next to any you could not run:
  `- Test: \`make test\` (from Makefile, not run)`. Leave out a line with no command rather than
  guessing one.
- **Layout**: top-level directories that matter to someone changing code; skip the obvious (`.git`).
  Name generated and vendored directories as such, so no one edits them by hand.
- **Conventions**: two to five, each backed by what the code visibly does in more than one place. None
  found → omit the section. A convention invented here becomes a rule the reviewer enforces.
- **Common mistakes**: leave the heading, empty. The workflows' learning loop appends a line here each
  time the same mistake has happened twice and a person agrees it should become a rule.

## An existing CLAUDE.md

Never rewrite it. Add only what is missing, at the end:
- a `## Common mistakes` heading, if there is none - without it the learning loop has nowhere to write;
- the `## Workflow` lines, if nothing in the file mentions intents or `REVIEW.md`;
- a command the repo names that the file does not, under a heading the file already uses for commands.

List each addition in the report. If the existing file contradicts the repo (a command that no longer
exists), report it and leave it alone - the file's owner decides.
