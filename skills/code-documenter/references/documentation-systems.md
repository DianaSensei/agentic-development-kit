# Documentation Systems & Infrastructure

## Choosing a Doc-Site Generator

A documentation site's generator choice is a project decision, not something this skill should default
without asking — many options exist and new ones appear regularly. Decide using the project's actual
constraints rather than defaulting to whatever's most familiar:

| Criterion | What to check |
|-----------|----------------|
| Ecosystem fit | Does a generator already ship with, or is conventional for, this project's primary language/framework? Using the ecosystem-native option usually means less integration friction (build pipeline, dependency management, hosting). |
| Versioning needs | Does this project need multiple documented versions live simultaneously (e.g. a library with several supported major versions)? Not all generators support this equally well. |
| Content authoring format | Does the team want plain Markdown, or is embedding live/interactive code samples in the docs itself a requirement? |
| Search | Hosted/managed search vs. self-hosted/local search — see "Search" below. |
| Hosting | Static output deployable anywhere vs. a generator that expects a specific hosting platform. |

Do not assume a specific generator without checking what the project already uses or asking — if the
repository already has a doc-site configured, use it; don't introduce a second one.

## Multi-Version Documentation

When a project supports multiple versions simultaneously (a library, an API with versioned releases),
the documentation site needs:
- A version switcher exposed in the navigation.
- Each version's docs frozen to match that version's actual behavior — never let a "latest" doc page
  silently describe behavior that changed in a later, undocumented version.
- A migration guide between adjacent versions, structured as: breaking changes, renamed/removed
  APIs (old name → new name, with any semantic change flagged), and a deprecation timeline (when the
  old version stops being supported).

## Search

| Approach | Trade-off |
|----------|-----------|
| Hosted/managed search service | Fast, typo-tolerant, minimal setup; introduces a third-party dependency and (for free tiers) may require the docs to be public. |
| Self-hosted search service | Keeps docs private/internal if needed; requires operating the search infrastructure. |
| Local/offline search (indexed at build time, runs in the browser) | No server dependency, works offline; index size and relevance quality degrade on very large doc sets. |

Pick based on whether the documentation is public or internal-only, and how large the corpus is — a
local index that's fine for a few hundred pages stops being practical for a multi-thousand-page corpus.

## Documentation Testing

Two independent things need testing, not just one:
- **Link checking** — verify every internal and external link in the docs actually resolves; run this
  on a schedule (external links rot even when the docs don't change) as well as on every doc change.
- **Code example testing** — every code sample in the documentation should be extracted and actually
  executed/type-checked as part of CI, using whatever mechanism the language/ecosystem provides for
  that (a doctest-style runner, a script that extracts fenced code blocks and runs them, a type
  checker). See `SKILL.md`'s Core Workflow step 5 — an untested example is a liability, not a bonus.

## Performance & Delivery

Independent of generator choice:
- Split large dependency bundles so a doc-site visitor isn't downloading the whole site's JS/assets to
  read one page.
- Set long cache lifetimes on versioned/hashed static assets, and short (or revalidate-on-request)
  cache lifetimes on the HTML pages themselves, so content updates propagate without waiting out a
  long cache window.
- Serve behind a CDN when the audience is geographically distributed.

## Analytics

If usage analytics are needed, track at minimum: page views (which docs pages get used, which don't),
search queries with zero/low results (a strong signal of a documentation gap), and outbound clicks on
"was this helpful" or similar feedback controls if present. Anonymize IPs/user data by default unless
there's a specific, disclosed reason not to.

## Boundary

This file covers documentation-infrastructure *decisions* (what to weigh, what to test, what to
measure) independent of any specific generator, search provider, or hosting platform. The concrete
setup steps and configuration syntax for whichever tool is chosen belong to that tool's own
documentation, not to this skill.
