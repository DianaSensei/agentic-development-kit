# MCP Protocol Specification

## Protocol Overview

MCP is built on JSON-RPC 2.0 and enables bidirectional communication between clients (like Claude Desktop) and servers that provide resources, tools, and prompts.

## Message Types

### Request/Response

```typescript
// Request format
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}

// Success response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_weather",
        "description": "Get weather for a location",
        "inputSchema": {
          "type": "object",
          "properties": {
            "location": { "type": "string" }
          },
          "required": ["location"]
        }
      }
    ]
  }
}

// Error response
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": { "details": "location is required" }
  }
}
```

### Notifications

```typescript
// Server sends notification (no response expected)
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "uri": "file:///project/data.json"
  }
}
```

## Connection Lifecycle

```
1. Client initiates connection (stdio/HTTP/SSE)
2. Client sends initialize request
   → Server responds with capabilities
3. Client sends initialized notification
4. Normal operation (requests/notifications)
5. Client/server can ping for keepalive
6. Client sends shutdown request
7. Connection closes
```

### Initialize Handshake

```typescript
// Client initialize request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    },
    "clientInfo": {
      "name": "claude-desktop",
      "version": "1.0.0"
    }
  }
}

// Server response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "resources": { "subscribe": true, "listChanged": true },
      "tools": { "listChanged": true },
      "prompts": { "listChanged": true }
    },
    "serverInfo": {
      "name": "my-mcp-server",
      "version": "1.0.0"
    }
  }
}

// Client sends initialized notification
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

### Version Negotiation

The client sends the latest protocol version it supports. The server does not have to match it - the
server replies with the version it will actually speak: its own latest version if it supports the
client's request, or otherwise the latest version it does support. If the client does not support the
version the server returned, the client must disconnect rather than proceed with a version mismatch.
Never assume the negotiated version equals what either side initially requested - always use the value
in the server's `initialize` response for anything version-conditional afterward (for HTTP transports,
this value is also expected on the `MCP-Protocol-Version` header of subsequent requests).

## Core Methods

### Resources

```typescript
// List available resources
resources/list → { resources: Resource[] }

// Read resource content
resources/read { uri: string } → { contents: ResourceContent[] }

// Subscribe to resource updates (if supported)
resources/subscribe { uri: string } → {}

// Unsubscribe
resources/unsubscribe { uri: string } → {}

// Server notifies of changes
notifications/resources/list_changed → {}
notifications/resources/updated { uri: string } → {}
```

### Tools

```typescript
// List available tools
tools/list → { tools: Tool[] }

// Execute tool
tools/call {
  name: string,
  arguments: object
} → { content: ToolResponse[] }

// Server notifies of tool changes
notifications/tools/list_changed → {}
```

### Prompts

```typescript
// List available prompts
prompts/list → { prompts: Prompt[] }

// Get prompt with arguments
prompts/get {
  name: string,
  arguments?: object
} → { messages: PromptMessage[] }

// Server notifies of prompt changes
notifications/prompts/list_changed → {}
```

## Error Codes

Standard JSON-RPC 2.0 codes plus MCP-specific:

```typescript
const ERROR_CODES = {
  // JSON-RPC 2.0 standard
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,

  // MCP-specific (implementation defined)
  RESOURCE_NOT_FOUND: -32001,
  TOOL_EXECUTION_ERROR: -32002,
  UNAUTHORIZED: -32003,
  RATE_LIMIT_EXCEEDED: -32004
};
```

## Transport Mechanisms

### stdio (Standard Input/Output, local servers)

```typescript
// Server reads from stdin, writes to stdout
// Each message is newline-delimited JSON
// Used for local integration (Claude Desktop default)
// Log to stderr only - stdout is reserved for protocol messages
```

### Streamable HTTP (remote servers)

Streamable HTTP is the current spec-recommended transport for remote servers, replacing the older,
now-deprecated separate HTTP+SSE transport. A single endpoint handles both directions:

```typescript
// Client POSTs a JSON-RPC request to the single MCP endpoint
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2025-11-25

{"jsonrpc":"2.0","id":1,"method":"tools/list"}

// Server replies with either a plain JSON response, or upgrades to an
// SSE stream on the same response (for long-running calls / server-initiated
// notifications) - the client does not open a second, separate connection.
Content-Type: text/event-stream

event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}
```

Remote servers exposed over Streamable HTTP must implement OAuth 2.1 authorization - see
`references/authorization.md`. Do not build a new server on the legacy dual-endpoint HTTP+SSE
transport; only maintain it if required for backward compatibility with an old client.

## Protocol Versions

Current stable version: `2025-11-25`. The spec has revised several times since the original
`2024-11-05` release - notably `2025-03-26` (added the OAuth 2.1 authorization framework; replaced
HTTP+SSE with Streamable HTTP) and `2025-06-18` (structured tool output, elicitation, hardened OAuth
requirements). Do not hardcode a version string as "current" in server code without checking the
live spec - this changes faster than most protocol versions do. See "Version Negotiation" above for
how a server should actually behave when a client requests a different version.

Servers must declare their negotiated version in the initialize response. Clients must verify
compatibility and disconnect if the server's returned version is unsupported.

## Best Practices

1. **Validation**: Always validate params with JSON Schema
2. **Error handling**: Return structured errors with helpful messages
3. **Versioning**: Negotiate protocol version in initialize; never hardcode it as fixed
4. **Timeouts**: Implement request timeouts (30s recommended)
5. **Logging**: Log all protocol messages to stderr, never stdout, for debugging
6. **Stateless**: Design tools/resources to be stateless
7. **Idempotency**: Make tool calls idempotent when possible
8. **Notifications**: Use notifications for real-time updates
9. **Authorization**: For any remote (Streamable HTTP) server, implement OAuth 2.1 per the MCP
   authorization spec - see `references/authorization.md`; do not roll a custom auth scheme
