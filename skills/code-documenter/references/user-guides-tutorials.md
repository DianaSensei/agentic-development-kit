# User Guides & Tutorials

## Content Types and When to Use Each

| Content Type | Best For | Key Elements |
|---------------|----------|---------------|
| Quick Start | New users, minimal time investment | Prerequisites, minimal working example, a way to verify it worked |
| Tutorial | Learning by doing, a specific outcome | Numbered steps, checkpoints, working code at every step |
| How-To Guide | An experienced user solving one specific task | Goal, steps, troubleshooting for that task |
| Reference | Looking up a specific detail | Comprehensive, organized for scanning/searching, not narrative |
| Explanation/Concept | Understanding *why*, not *how* | Prose, rationale, trade-offs - no step list |

Match the content type to what the reader actually needs - a reader looking for one config flag's
meaning does not want to read a tutorial to find it, and a first-time user following a quick start does
not want the full reference's exhaustive detail.

## Quick Start Structure

A quick start earns its name by getting a new user to a working result in minutes:

```markdown
# Getting Started

## Prerequisites
- [ ] {runtime/tool the reader needs installed}
- [ ] {a credential, e.g. an API key, if required}

## Quick Start
1. {Install/setup step - one command or action}
2. {The single smallest thing that demonstrates the product working}
3. {How to verify it worked - the exact expected output}

## Next Steps
- {Link to the next most likely thing the reader needs}
```

Every quick start needs an explicit "how to verify it worked" step with the exact expected output -
without it, a reader who made a mistake has no way to know before moving on and compounding the error.

## Tutorial Structure

A tutorial teaches a skill through a realistic, complete task - not just a demonstration:

```markdown
# Tutorial: {realistic outcome, e.g. "Building a Dashboard"}

**What you'll learn:** {bulleted list of sub-skills}
**Time:** {realistic estimate}
**Level:** {Beginner/Intermediate/Advanced}

## Step 1: {action}
{Instructions.}
**What's happening:** {the *why* behind the step - not just what command to run}

## Step 2: {action}
...

## Checkpoint
- [x] {completed so far}
- [ ] {remaining}

## Next Steps
{link to what naturally follows}
```

Every step needs a "what's happening" explanation, not just an instruction - a reader who only copies
commands without understanding them can't adapt the tutorial to their own situation afterward, which
defeats the purpose of a tutorial versus a reference.

## Information Architecture

Organize a documentation site's navigation by the content types above, not by internal project
structure - a reader doesn't know or care how the underlying code/modules are organized:

```
Documentation/
├── Getting Started/        (Quick Start, Installation, Authentication)
├── Guides/                 (How-To guides, one per task)
├── Reference/               (Exhaustive, organized for lookup)
├── Tutorials/                (Learning-by-doing, longer-form)
└── Resources/                (Troubleshooting, FAQ, Migration Guides)
```

## Progressive Disclosure

When a topic has a simple default path and one or more advanced paths (e.g. a simple default
configuration vs. several advanced options), lead with the simple path in full, then collapse the
advanced paths behind an expandable section or a clearly separate "Advanced" subsection - don't force
every reader through the advanced material to reach the common case, and don't hide the common case
behind advanced material either.

## Troubleshooting Guides (Problem-Solution Format)

```markdown
## {Error message or symptom}

**Symptoms:** {what the user observes}

**Causes:**
1. {most common cause}
2. {next most common}

**Solutions:**
1. {most likely fix, with the specific check/action}
2. {next fix if the first doesn't apply}

**Still not working?** {escalation path}
```

Order causes and solutions by actual likelihood, most common first - a troubleshooting guide that
lists causes in an arbitrary order wastes the reader's time on rare cases before common ones.

## FAQ Structure

Group by theme (not a flat alphabetical or chronological list), and keep each answer genuinely short -
an FAQ entry that needs several paragraphs to answer belongs in a guide instead, with the FAQ entry
linking to it.

## Visual Communication

- Use diagrams for anything a reader would otherwise have to reconstruct mentally from prose - a
  request flow across multiple components, a data model's relationships. A sequence diagram or an
  entity-relationship diagram (e.g. authored in Mermaid, which renders from plain text and works
  regardless of the underlying project's language) usually communicates this faster and more
  accurately than a paragraph attempting the same thing.
- Screenshots need numbered annotations tied to a numbered explanation list below the image - an
  unannotated screenshot forces the reader to guess what's being pointed at.

## Writing Techniques

| Principle | Technique |
|-----------|-----------|
| Clarity | Active voice, short sentences, one idea per sentence |
| Scannability | Headings, lists, code blocks - readers scan before they read |
| Completeness | State prerequisites, next steps, and related links explicitly |
| Accuracy | Every code example must actually run (see `SKILL.md` Core Workflow step 5); version-specific claims must state which version they apply to |

## Boundary

This file covers the structure and writing method for guides/tutorials, independent of the product's
implementation language or the reader's technical stack. Any code sample used *inside* a tutorial must
be written in whatever language the tutorial's actual product/API uses - this file doesn't prescribe
which language that is.
