---
name: mcp-developer
description: Use when building, debugging, or extending an MCP (Model Context Protocol) server or client - protocol lifecycle and JSON-RPC 2.0 message shapes, version negotiation, choosing and configuring stdio vs Streamable HTTP transport, OAuth 2.1 authorization for remote servers, and debugging protocol-compliance failures. Covers the protocol itself; the SDKs' concrete APIs change too fast to snapshot, so those come from the live SDK docs at implementation time.
metadata:
  domain: api-architecture
  triggers: MCP server, MCP client, Model Context Protocol, JSON-RPC, MCP authorization, Streamable HTTP, MCP Inspector, protocol version negotiation
  role: specialist
  scope: implementation
  output-format: code
  related-skills: rust-engineer, java-spring-skill, security-skill, security-audit, toolbox-connections
---

# MCP Developer

Building a server or client that speaks the Model Context Protocol.

> **Read the live SDK docs before writing handler code.** This skill owns the protocol - lifecycle,
> message shapes, version negotiation, transports, authorization - which changes slowly and is worth
> writing down. The TypeScript and Python SDKs' registration APIs change fast enough that a snapshot
> here would be wrong more often than right, so fetch them from
> [modelcontextprotocol.io](https://modelcontextprotocol.io) or the SDK repo at the point of use, and
> pin the SDK version in the project's manifest.

## Core Workflow

1. **Analyze requirements** - data sources, tools needed, client apps, and whether the server runs
   locally (stdio) or remotely (Streamable HTTP, which requires authorization).
2. **Initialize** - scaffold with the SDK's current recommended command. Confirm the SDK version
   actually supports the protocol version this server targets (`references/protocol.md`).
3. **Design the protocol surface** - resource URIs, tool input schemas, prompt templates. Decide these
   before writing handlers; they're the contract clients see.
4. **Implement** - register tools/resources/prompts via the SDK's current high-level API, and configure
   the transport. Validate every tool input with the SDK's schema layer (Zod in TypeScript, Pydantic in
   Python) rather than hand-checking arguments.
5. **Test** - `npx @modelcontextprotocol/inspector` verifies protocol compliance interactively: tools
   appear, schemas accept valid input and reject invalid, errors come back as well-formed JSON-RPC 2.0.
   **Feedback loop:** schema validation failing → read the Zod/Pydantic error → fix the schema → re-run.
   Malformed response → check transport serialization → fix the handler → re-test.
6. **Deploy** - OAuth 2.1 for any remote or multi-tenant server (`references/authorization.md`), plus
   rate limiting, env vars, and monitoring.

## Constraints

- Log to **stderr** on stdio transport - stdout is reserved for protocol traffic, and anything written
  there corrupts the session. This is the single most common way a working server appears broken.
- Advertise a protocol version the server actually supports; never assume the client's. Use the version
  from the server's `initialize` response for anything version-conditional afterward.
- Never deploy a remote server without OAuth 2.1 authorization and rate limiting.
- Never expose secrets in resource content, and never return unstructured errors to clients.
- Don't build on the deprecated dual-endpoint HTTP+SSE transport - Streamable HTTP replaced it.

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Protocol | `references/protocol.md` | Message types, lifecycle, JSON-RPC 2.0, version negotiation, transports |
| Authorization | `references/authorization.md` | Securing a remote/Streamable HTTP server with OAuth 2.1 |

For SDK APIs (registering tools/resources/prompts, transport setup, client construction), use the live
docs - not a copy kept here.

## Output

Server/client implementation file; schema definitions for tools, resources and prompts; configuration
(transport, auth); and a brief explanation of the design decisions.

## Boundaries

- Implements the MCP layer itself - protocol handling, registration, transport, authorization. The
  business logic a tool calls into (a database query, an external API call) belongs to whichever
  language/framework skill owns it (`java-spring-skill`, `rust-engineer`, ...); this skill wires that
  logic into MCP rather than replacing the skill that owns it.
- A full security review of a server exposed to untrusted clients (threat modeling, dependency auditing,
  secret handling beyond the OAuth flow) is `security-audit`'s.
- Packaging, containerizing and operating a deployed server (CI/CD, infrastructure, scaling) is out of
  scope - this covers what the server needs at runtime, not how it ships.
- Configuring this plugin's own bundled toolbox MCP is `toolbox-connections`'s. Connecting an
  already-built third-party server is plain `claude mcp add` - check `claude mcp --help` for current
  flags rather than relying on any written-down summary of that CLI.
- **The spec moves.** Before citing a protocol version, transport name, or SDK API as current, verify
  against `references/protocol.md` or the live spec. These files are a snapshot.
