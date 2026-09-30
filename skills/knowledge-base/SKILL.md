---
name: knowledge-base
description: The system knowledge the code cannot tell - why decisions were made, who owns what, what must stay true, known debt, business rules and agreements between teams - kept in Basic Memory as plain Markdown notes, in a personal project and a team project the team reviews in git. Read at the start of every workflow for the systems a change touches, and written only with the user's yes at knowledge capture. Also sets Basic Memory up on a machine and keeps the notes true. Use when the user asks to set up or connect the knowledge base, record a decision, debt, rule, agreement or owner, "remember why we...", or asks what is known about a system. Not for the user's work style (reflect), a repository's own dead ends (the experience log) or its conventions (CLAUDE.md).
metadata:
  domain: workflow
  triggers: knowledge base, basic memory, remember this decision, record tech debt, who owns, why did we, business rule, team agreement, system context
  role: specialist
  scope: documentation
  output-format: document
  related-skills: feature-development, bug-fix, refactor, independent-review, reflect
---

# Knowledge Base

The code says what a system does. It does not say why it was built that way, who answers for it, which
promise to another team it keeps, what is known to be broken, or what the business means by a word.
An engineer carries that in their head; an agent starts every session without it. This skill keeps
it where both can read and write it: [Basic Memory](https://github.com/basicmachines-co/basic-memory),
plain Markdown notes indexed locally for full-text and semantic search, reached through its MCP server.
No API key, nothing leaves the machine, and a person can open the same notes in any editor.

## Two scopes

- **Personal** - Basic Memory's default project (`main`, in `~/basic-memory`). What the user learned
  and wants to keep, for themselves.
- **Team** - a git repository the team shares, cloned on each machine and registered as a Basic Memory
  project. The notes that bind everyone: decisions, owners, agreements, debt. A change to it is a diff
  the team reviews like code.

A code repository names its team project in its `CLAUDE.md`: `Knowledge base: Basic Memory project
\`<name>\``. Without that line, `list_memory_projects` shows what exists; ask which one is the team's,
once, and offer to add the line.

## What a note is

One note per thing, typed, in the team repository's folder for its type. Each type has a schema in
`schemas/` (Basic Memory checks notes against it) and a complete example in `templates/` - copy the
example's shape, not its content.

| Type | Folder | Holds | Example |
|---|---|---|---|
| `system` | `systems/` | purpose, owner, interfaces, data it owns, what must stay true, what breaks easily | `templates/system.md` |
| `decision` | `decisions/` | the context, what was decided, what lost and why, what it costs, where it was decided | `templates/decision.md` |
| `debt` | `debt/` | what is wrong, what it costs today, the workaround, what fixing it takes | `templates/debt.md` |
| `rule` | `rules/` | a business rule or a domain term: what the business means, examples, exceptions | `templates/rule.md` |
| `agreement` | `agreements/` | a promise between teams - an API shape, an SLA, a release order - and who is bound | `templates/agreement.md` |
| `team` | `teams/` | what a team answers for, how to reach it, what it owns | `templates/team.md` |

A fact is an observation, `- [category] text (source: ...)`; a link is a relation,
`- depends_on [[Tax Rules]]`. Every fact says where it came from - a PR, an incident, an ADR, a
person - so a reader can check it. `verified:` in the frontmatter is the date someone last checked the
note against its source.

**Not a note**: a summary of code (read the code); anything already in a repository's docs (link to
it instead); a secret, credential, customer data or anything personal about a person beyond what they
own; a guess with no source; the user's work style (`reflect`); a repository's dead ends (its
experience log).

## Reading

At every workflow's Step 0 (`feature-development`, `bug-fix`, `refactor`) and when
`independent-review` reads a change's context:

1. Name the systems the request touches, from the request and the code paths it will change.
2. `search_notes` in the team project, then the personal one, with those names and the request's key
   terms. For each system note found, `build_context` on its `memory://` URL (depth 1) brings its
   decisions, debt, rules and agreements. Read the few that bear on the change, not the whole graph.
3. **Use them as constraints with sources.** A decision, rule or agreement the change must respect goes
   into the requirement's or the plan's constraints, cited by title (`[[Money is integer cents across
   services]]`). A proposal that would break one says so, and whether to break it is the user's call at
   the Checkpoint. Known debt in the path is a risk the plan names.
4. **Check before trusting.** A note older than six months (`verified`), or one the code contradicts,
   is a lead to verify, not a fact. The code decides what *is*; a decision, rule or agreement says what
   *should be* - when they disagree, raise it to the user; never pick one silently. Propose the note's
   correction at knowledge capture.

No knowledge base connected (no Basic Memory tools): skip this, and say nothing about it.

## Writing

At knowledge capture (Step 5 of `feature-development`, the equivalent step of `bug-fix` and
`refactor`), never in the middle of a task:

1. **Collect candidates** from this run, each with its source: a decision the user made at the Checkpoint
   that binds beyond this change; debt found and not fixed; a business rule the user clarified; an
   agreement or an owner learned; a note that proved wrong or stale.
2. **Search first**: a note that already covers it gets updated (`edit_note`), never duplicated.
3. **Ask once** (`AskUserQuestion`, `multiSelect`, header `"Knowledge"`): one option per note - its
   title, type, team or personal, and new or updated. Nothing is written without a yes. No way to ask
   (a headless run): write nothing; list the proposed notes in the report.
4. **Write** with `write_note`: `directory` the type's folder, `note_type` the type, `metadata` its
   frontmatter (`status`, `date`, `verified: <today>`), content shaped like the template. Then
   `schema_validate` with that `note_type` and fix what it reports.
5. **Team notes are changes in the team repository's working tree.** Tell the user which files, for them
   to review and commit - or to open a pull request through `code-host`, if they ask. Never commit or
   push the team repository on your own.

## Setting it up

Once per machine, with the user:

1. `uv tool install basic-memory` (or `pipx install basic-memory`).
2. `claude mcp add -s user basic-memory -- basic-memory mcp` - user scope, so every project has it. The
   tools appear in the next session (`/mcp` to check).
3. The personal project exists already: `main`, in `~/basic-memory`.
4. The team project: ask where the team's knowledge repository is. Clone it; if the team has none,
   offer to start one - a new folder, `git init`, the folders above - and let the user create its remote.
   Then:
   ```bash
   mkdir -p <path>/schemas
   cp -n <this skill's dir>/schemas/*.md <path>/schemas/   # -n: never overwrite a schema the team edited
   basic-memory project add <name> <path>
   basic-memory reindex --project <name>
   ```
5. In each code repository, offer the `CLAUDE.md` line that names the team project.

Check: `basic-memory tool search-notes "<a system name>" --project <name>` finds it.

## Keeping it true

- `basic-memory tool schema-validate <type> --project <name>` checks every note of a type against its
  schema: a missing required field or a status outside its values is reported.
- `basic-memory orphans` lists notes nothing links to - usually a system nobody connected.
- A note is re-verified when a change touches it: read it against the code, update what moved, set
  `verified` to today, in the same knowledge-capture question as the rest.

## Boundaries

- **`reflect`** keeps how the user works; **the experience log** keeps a repository's dead ends;
  **`CLAUDE.md`** keeps its conventions; **intents, plans and changelogs** keep its work. This keeps the
  system beyond one repository: why, who, and what must stay true.
- Notes are written by hand or by the agent with a yes. Bulk import - indexing repositories, chat
  history or tickets automatically - is not this skill's job.
- Opening the pull request for a team note is `code-host`'s.
