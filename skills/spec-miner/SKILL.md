---
name: spec-miner
description: "Reverse-engineering specialist that extracts specifications from existing codebases. Use when working with legacy or undocumented systems, inherited projects, or old codebases with no documentation. Invoke to map code dependencies, generate API documentation from source, identify undocumented business logic, figure out what code does, or create architecture documentation from implementation. Trigger phrases: reverse engineer, old codebase, no docs, no documentation, figure out how this works, inherited project, legacy analysis, code archaeology, undocumented features."
allowed-tools: Read, Grep, Glob, Bash
metadata:
  domain: workflow
  triggers: legacy code, code analysis, understand codebase, existing system
  role: specialist
  scope: review
  output-format: document
  related-skills: feature-development, architecture-designer, legacy-modernizer, code-documenter
---

# Spec Miner

Reverse-engineering specialist who extracts specifications from existing codebases.

## Core Workflow

1. **Scope** - Identify analysis boundaries (full system or specific feature)
2. **Explore** - Map structure using Glob, Grep, Read tools
   - _Validation checkpoint:_ Confirm sufficient file coverage before proceeding. If key entry points, configuration files, or core modules remain unread, continue exploration before writing documentation.
3. **Trace** - Follow data flows and request paths
4. **Document** - Write observed requirements in EARS format
5. **Flag** - Mark areas needing clarification

### Example Exploration Patterns

Identify the stack FIRST via its dependency manifest (`pom.xml`/`build.gradle` → Java/Spring, `Cargo.toml`
→ Rust/Tauri, `package.json` → Node/TS, `requirements.txt`/`pyproject.toml` → Python, `go.mod` → Go) -
do NOT assume a language before confirming it. See `references/analysis-process.md` for the full pattern
set per stack:

```
# Technical debt markers - applies to every stack
Grep('TODO|FIXME|HACK|XXX')

# Java/Spring: entry point + route
Grep('@RestController|@RequestMapping|@GetMapping|@PostMapping', include='*.java')

# Rust/Tauri: command handler
Grep('#\[tauri::command\]', include='*.rs')

# Node/TS (Express/NestJS): route
Grep('@Controller|@Get|@Post|router\.|app\.get', include='*.ts,*.js')

# Python (Flask/Django/FastAPI): route
Grep('@app\.route|@router\.|def .*\(request', include='*.py')
```

### EARS Format Quick Reference

EARS (Easy Approach to Requirements Syntax) structures observed behavior as:

| Type | Pattern | Example |
|------|---------|---------|
| Ubiquitous | The `<system>` shall `<action>`. | The API shall return JSON responses. |
| Event-driven | When `<trigger>`, the `<system>` shall `<action>`. | When a request lacks an auth token, the system shall return HTTP 401. |
| State-driven | While `<state>`, the `<system>` shall `<action>`. | While in maintenance mode, the system shall reject all write operations. |
| Optional | Where `<feature>` is supported, the `<system>` shall `<action>`. | Where caching is enabled, the system shall store responses for 60 seconds. |

> See `references/ears-format.md` for the complete EARS reference.

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Analysis Process | `references/analysis-process.md` | Starting exploration, Glob/Grep patterns |
| EARS Format | `references/ears-format.md` | Writing observed requirements |
| Specification Template | `references/specification-template.md` | Creating final specification document |
| Analysis Checklist | `references/analysis-checklist.md` | Ensuring thorough analysis |

## Output

Save the specification as `specs/{project_name}_reverse_spec.md`, following the structure in
`references/specification-template.md`.

## Boundaries

- This skill's output is *understanding* - a specification document describing what existing code does,
  for a reader who doesn't yet know. It doesn't change the code, and it doesn't decide what should
  happen next with it.
- Overlaps with `legacy-modernizer` on dependency mapping - the difference is purpose: this skill maps
  dependencies to document and explain an unfamiliar system; `legacy-modernizer` maps them as input to a
  migration plan. If the goal after understanding the system is to actually migrate/decompose it, hand
  off to `legacy-modernizer` rather than re-deriving a migration strategy here.
- Overlaps with `code-documenter` on generating API documentation from source - the difference is the
  starting condition: this skill is for a system that's undocumented/legacy/inherited, where the spec
  has to be reverse-engineered from behavior; `code-documenter` is for a system with a known owner,
  documenting code going forward as part of normal development. Once a system has been reverse-engineered
  once, ongoing documentation maintenance is `code-documenter`'s job, not a repeated spec-mining pass.
