---
name: code-documenter
description: Generates, formats, and validates technical documentation - inline documentation (docstrings/comments), API specs (OpenAPI/Swagger, JSDoc-style annotations), documentation sites, and user guides - for any language or framework. Use when adding documentation to functions or classes, creating API documentation, building documentation sites, or writing tutorials and user guides.
metadata:
  domain: quality
  triggers: API docs, doc site
  role: specialist
  scope: implementation
  output-format: code
  related-skills: spec-miner, code-review-skill, api-contract-skill
---

# Code Documenter

Documentation specialist for inline documentation, API specs, documentation sites, and developer guides, independent of language or framework. Concrete doc-comment syntax and validation tooling vary by language/ecosystem and aren't enumerated here - this file covers the method: what makes documentation worth writing and how to verify it stays true.

## Core Workflow

1. **Discover** - Ask for format preference (or detect the convention already used in the codebase) and exclusions (generated code, vendored files, tests).
2. **Detect** - Identify the language, framework, and existing doc-generation tooling already configured in the project (doc-comment style, API-doc framework, static-site generator). Follow whatever convention is already established in the codebase (e.g. its existing docstring style, its existing JSDoc tag usage) rather than introducing a new one.
3. **Analyze** - Find undocumented or under-documented public functions, classes, and API endpoints. Prioritize public/exported surface area over private internals.
4. **Document** - Apply the format consistently across the codebase. Every entry covers: purpose (what and why, not a restatement of the signature), parameters, return value, exceptions/errors that can propagate to the caller, and - for non-trivial behavior - a runnable example.
5. **Validate** - Every code example in generated documentation must actually run or type-check; a documented example that's silently wrong is worse than no example, because it actively misleads. Use whatever doc-validation tooling the language/ecosystem provides (doctest runners, type checkers, doc-linters, OpenAPI validators). **Feedback loop:** if validation fails, fix the example (not just the assertion) and re-validate before proceeding to Report.
6. **Report** - Generate a coverage summary (see `references/coverage-reports.md`).

## Documentation Principles

These apply regardless of language or doc-comment syntax:

- **State the why, not just the what** - a good name plus a type signature already tells the reader _what_ a parameter is; the doc entry earns its keep by explaining what a signature can't: preconditions, units, edge-case behavior, or why a non-obvious choice was made.
- **Document the failure modes** - every exception/error a caller can observe, and the condition that triggers it, not just the happy path.
- **Match the convention already in the codebase** - if the project already has an established docstring/comment style, follow it instead of introducing a second style; ask before introducing a new one to a codebase that has none yet.
- **Don't document the obvious** - a getter that returns exactly the field its name says doesn't need a doc comment restating that; reserve documentation effort for where it adds information the reader doesn't already have.
- **Keep documentation and code in the same review** - documentation added in a separate, later pass drifts from the code it describes; treat undocumented public API surface as incomplete work, not a follow-up task.

## Reference Guide

Load detailed guidance based on context:

| Topic                   | Reference                             | Load When                                            |
| ----------------------- | ------------------------------------- | ---------------------------------------------------- |
| Coverage Reports        | `references/coverage-reports.md`      | Generating documentation reports                     |
| Documentation Systems   | `references/documentation-systems.md` | Doc sites, static generators, search, testing        |
| Interactive API Docs    | `references/interactive-api-docs.md`  | OpenAPI 3.1, portals, GraphQL, WebSocket, gRPC, SDKs |
| User Guides & Tutorials | `references/user-guides-tutorials.md` | Getting started, tutorials, troubleshooting, FAQs    |

For language- or framework-specific doc-comment syntax (e.g. Python docstring conventions, JSDoc tags,
a specific API framework's doc-generation decorators), rely on the target language/framework's own
documentation and whatever skill in this repo owns that language - this skill's method (Documentation
Principles above) applies regardless of the concrete syntax.

## Output Formats

Depending on the task, provide:

1. **Code Documentation:** Documented files + coverage report
2. **API Docs:** OpenAPI specs + portal configuration
3. **Doc Sites:** Site configuration + content structure + build instructions
4. **Guides/Tutorials:** Structured markdown with examples + diagrams

## Boundaries

- This skill documents behavior that already exists - it does not change the API surface, fix bugs, or
  redesign function signatures to be more documentable. If undocumented code turns out to also be
  wrong or oddly structured, flag it rather than silently fixing it as part of a documentation task.
- Designing a NEW API contract (endpoints, request/response schemas, as a contract-first exercise before
  implementation) is `api-contract-skill`'s job - this skill documents what an existing implementation
  does, not what a not-yet-built one should do.
- Overlaps with `spec-miner` on generating API documentation from source - the difference is the
  starting condition: `spec-miner` is for a legacy/undocumented/inherited system where the spec has to
  be reverse-engineered from behavior with no prior owner; this skill is for a system with a known
  owner, documenting code going forward as part of normal development. Once `spec-miner` has produced
  an initial understanding of a previously undocumented system, ongoing documentation maintenance is
  this skill's job, not a repeated spec-mining pass.
- A documentation pass is not a substitute for code review; correctness/security issues found while
  documenting should be raised, but a deeper review is `code-review-skill`'s job.
