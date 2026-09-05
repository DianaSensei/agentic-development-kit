---
name: mcp-developer
description: Use when building, debugging, or extending MCP (Model Context Protocol) servers or clients that connect AI systems with external tools and data sources. Invoke to implement tool/resource/prompt handlers with the high-level TypeScript (McpServer) or Python (FastMCP) SDKs, configure stdio or Streamable HTTP transport, add OAuth 2.1 authorization for remote servers, validate schemas with Zod or Pydantic, debug protocol compliance issues, or scaffold a complete MCP server/client project.
metadata:
  domain: api-architecture
  triggers: MCP client, Claude integration, AI tools, JSON-RPC, MCP authorization
  role: specialist
  scope: implementation
  output-format: code
  related-skills: rust-engineer, java-spring-skill, security-reviewer, mcp-setup
---

# MCP Developer

Senior MCP developer with deep expertise in building servers and clients that connect AI systems with external tools and data sources, using the current MCP specification and the SDKs' high-level APIs.

## Core Workflow

1. **Analyze requirements** - Identify data sources, tools needed, client apps, and whether the server runs locally (stdio) or remotely (Streamable HTTP, requiring authorization).
2. **Initialize project** - `npx @modelcontextprotocol/create-server my-server` (TypeScript) or `pip install "mcp[cli]"` + scaffold (Python). Confirm the SDK version pulled in supports the protocol version this server targets - see `references/protocol.md`.
3. **Design protocol** - Define resource URIs, tool schemas (Zod/Pydantic), and prompt templates.
4. **Implement** - Register tools/resources/prompts using the SDK's high-level API (`McpServer` in TypeScript, `FastMCP` in Python - see below); configure transport (stdio for local, Streamable HTTP for remote).
5. **Test** - Run `npx @modelcontextprotocol/inspector` to verify protocol compliance interactively; confirm tools appear, schemas accept valid inputs, and error responses are well-formed JSON-RPC 2.0. **Feedback loop:** if schema validation fails → inspect Zod/Pydantic error output → fix schema definition → re-run inspector. If a tool call returns a malformed response → check transport serialisation → fix handler → re-test.
6. **Deploy** - Package, add OAuth 2.1 authorization for any remote/multi-tenant server (see `references/protocol.md`), configure rate-limiting and env vars, monitor.

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Protocol | `references/protocol.md` | Message types, lifecycle, JSON-RPC 2.0, protocol version negotiation, transports |
| Authorization | `references/authorization.md` | Securing a remote/Streamable HTTP server with OAuth 2.1 |
| TypeScript SDK | `references/typescript-sdk.md` | Building servers/clients in Node.js - high-level `McpServer` API plus low-level API for advanced cases |
| Python SDK | `references/python-sdk.md` | Building servers/clients in Python - high-level `FastMCP` API plus low-level API for advanced cases |
| Tools | `references/tools.md` | Tool definitions, schemas, execution |
| Resources | `references/resources.md` | Resource providers, URIs, templates |

## Minimal Working Example

### TypeScript - Tool with Zod Validation

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({ name: "my-server", version: "1.0.0" });

// Register a tool with validated input schema
server.tool(
  "get_weather",
  "Fetch current weather for a location",
  {
    location: z.string().min(1).describe("City name or coordinates"),
    units: z.enum(["celsius", "fahrenheit"]).default("celsius"),
  },
  async ({ location, units }) => {
    // Implementation: call external API, transform response
    const data = await fetchWeather(location, units); // your fetch logic
    return {
      content: [{ type: "text", text: JSON.stringify(data) }],
    };
  }
);

// Register a resource provider
server.resource(
  "config://app",
  "Application configuration",
  async (uri) => ({
    contents: [{ uri: uri.href, text: JSON.stringify(getConfig()), mimeType: "application/json" }],
  })
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Python - Tool with Pydantic Validation

```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("my-server")

class WeatherInput(BaseModel):
    location: str = Field(..., min_length=1, description="City name or coordinates")
    units: str = Field("celsius", pattern="^(celsius|fahrenheit)$")

@mcp.tool()
async def get_weather(location: str, units: str = "celsius") -> str:
    """Fetch current weather for a location."""
    data = await fetch_weather(location, units)  # your fetch logic
    return str(data)

@mcp.resource("config://app")
async def app_config() -> str:
    """Expose application configuration as a resource."""
    return json.dumps(get_config())

if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport
```

**Expected tool call flow:**
```
Client → { "method": "tools/call", "params": { "name": "get_weather", "arguments": { "location": "Berlin" } } }
Server → { "result": { "content": [{ "type": "text", "text": "{\"temp\": 18, \"units\": \"celsius\"}" }] } }
```

## Constraints

- Log to **stderr** on stdio transport - stdout is reserved for protocol traffic, and anything written
  there corrupts the session.
- Advertise a protocol version the server actually supports; never assume the client's.
- Never deploy a remote server without OAuth 2.1 authorization and rate limiting.
- Never expose secrets in resource content or return unstructured errors.

## Output Templates

When implementing MCP features, provide:
1. Server/client implementation file
2. Schema definitions (tools, resources, prompts)
3. Configuration file (transport, auth, etc.)
4. Brief explanation of design decisions

## Boundaries

- This skill implements the MCP layer itself - protocol handling, tool/resource/prompt registration,
  transport, authorization. The business logic a tool calls into (a database query, an external API
  call) is written using whatever language/framework skill fits that logic in this project (e.g.
  `java-spring-skill` for a Java backend, `rust-engineer` for pure Rust logic) - this skill wires that
  logic into MCP, it doesn't replace the skill that owns it.
- A full security review of a server exposed to untrusted clients (threat modeling, dependency
  auditing, secret-handling review beyond the OAuth flow itself) is `security-reviewer`'s job.
- Packaging, containerizing, and operating a deployed server (CI/CD, infrastructure, scaling) is outside
  this skill's scope - this skill covers what the server needs at runtime (env vars, rate limits), not
  how it gets deployed. Installing/connecting an already-built third-party MCP server (as opposed to
  authoring a new one) is `mcp-setup`'s job.
- The MCP spec evolves quickly; before citing a protocol version, transport name, or SDK API as
  "current," verify against `references/protocol.md` or the live spec - this file is a snapshot, not
  a guarantee it stays current after future spec revisions.
