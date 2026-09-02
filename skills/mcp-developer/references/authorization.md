# MCP Authorization (OAuth 2.1)

Applies to remote servers (Streamable HTTP). A local stdio server launched directly by its client does
not need this - the OS process boundary is the trust boundary. The moment a server accepts connections
over the network from a client it doesn't fully control, it needs this.

## Why MCP Doesn't Roll Its Own Auth

MCP standardizes on OAuth 2.1 rather than defining a bespoke scheme, so that any OAuth-aware client and
any OAuth-aware server interoperate without custom glue. Treat the MCP server as an OAuth 2.1 **Resource
Server** - it does not issue tokens itself; it validates tokens issued by a separate **Authorization
Server** (which can be a third-party IdP or a self-hosted one).

## Required Building Blocks

### 1. Protected Resource Metadata (RFC 9728)

The server exposes a well-known metadata document so clients can discover which Authorization Server(s)
issue valid tokens for it:

```
GET /.well-known/oauth-protected-resource HTTP/1.1

{
  "resource": "https://mcp.example.com",
  "authorization_servers": ["https://auth.example.com"]
}
```

When a client calls the server without a token (or with an invalid one), respond `401` with a
`WWW-Authenticate` header pointing at this metadata document - this is how the client discovers where
to authenticate, without the server needing to embed auth UI or flow logic itself.

### 2. PKCE (mandatory)

Every authorization code flow must use PKCE (Proof Key for Code Exchange), even for confidential
clients - this is a hard MCP requirement, not merely a best practice inherited from OAuth 2.1. A server
or client implementation that supports the authorization-code grant without PKCE is spec-non-compliant.

### 3. Resource Indicators (RFC 8707)

The client must include a `resource` parameter (this server's canonical URI) in both the authorization
request and the token request, and the Authorization Server must bind the issued token to that specific
resource. This exists specifically to stop **token passthrough** attacks: without resource binding, a
token obtained for one MCP server could be replayed against a different one that trusts the same
Authorization Server. Validate the token's audience against your own resource URI on every request -
reject tokens issued for a different resource even if the signature is otherwise valid.

### 4. Token Validation on Every Request

The Resource Server (the MCP server) must independently validate every incoming access token - signature,
expiry, audience (per Resource Indicators above), and required scope for the operation being performed.
Never trust a token merely because it arrived over TLS from a client that "looked" authenticated
earlier in the session; MCP connections can be long-lived and tokens can expire or be revoked mid-session.

## Incremental Scope Consent

When a tool call requires a scope the current token doesn't have, respond with `401` and a
`WWW-Authenticate` header describing the additional scope needed, rather than either silently failing
or requiring all possible scopes to be requested up front. This lets a client re-run just the
authorization step for the missing scope instead of restarting the whole flow.

## What This Skill Does Not Cover

- Standing up or operating the Authorization Server itself (that's a general OAuth/IdP concern, not
  MCP-specific - use whatever IdP the organization already runs, or a managed OAuth provider).
- Full security review of the deployed auth flow (token storage, session fixation, CSRF on the
  authorization redirect) - coordinate with `security-reviewer` for that.

## Boundary

This file covers the MCP-specific authorization requirements (Resource Server behavior, Resource
Indicators, Protected Resource Metadata) that make MCP's use of OAuth 2.1 distinct from a generic OAuth
integration. It assumes familiarity with OAuth 2.1 itself; it does not re-teach the authorization-code
grant from scratch.
