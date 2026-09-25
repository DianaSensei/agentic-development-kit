# REVIEW.md

The project's review policy, read by `independent-review` on every pull request after the
`code-review-skill` checklist. It **adds** to that checklist - required checks, stricter severities,
paths to skip - and never removes a check. The tech lead owns it and tunes it as review findings show
what matters here.

## Shape

```markdown
# Review policy

Read by the independent reviewer on every pull request, on top of `code-review-skill`'s checklist.
Adds to that checklist; never removes from it.

## Always check
- <path or area>: <what to verify there, every time>

## Severity
- <condition> is **blocking**.

## Skip
- `<path or glob>` - <why: generated, vendored, fixtures>
```

## Filling it in

Only from what the repo shows. Leave a section's single example commented out rather than invent
policy nobody decided:

- **Always check**: areas with visible risk - migration directories ("every migration is reversible and
  safe to run against the live table size"), auth or permission code, payment or billing code, public
  API definitions (OpenAPI files, `.proto`), infrastructure as code.
- **Severity**: only where the repo already states a rule, e.g. `CLAUDE.md` or `CONTRIBUTING.md` says
  every change needs a test → "a behavior change without a test is **blocking**".
- **Skip**: generated output, vendored code, lockfiles, snapshots, large fixtures. The reviewer still
  lists skipped paths under *Not checked*, so skipping is visible, not silent.

If none of the three sections has anything real, write the file with the header and three commented
examples: the reviewer and the tech lead both know where policy goes from day one.

## An existing REVIEW.md

Never rewrite it. Add a missing section heading only; add nothing under it that the repo does not show.
