---
name: security-skill
description: Writes secure code while a feature is being built - authentication/authorization, input validation and sanitization, password hashing (bcrypt/argon2), parameterized queries, CORS/CSP headers, JWT/session handling, OWASP Top 10 prevention. Produces secure CODE. Use when implementing any of those controls, or hardening code being written. To audit existing code or infrastructure for vulnerabilities instead, use `security-audit`.
metadata:
  domain: security
  triggers: secure coding, OAuth, JWT, password hashing, input validation, OWASP prevention, CSP, CORS, session management
  role: specialist
  scope: implementation
  output-format: code
  related-skills: security-audit, code-review-skill, architecture-designer, api-contract-skill
---

# Secure Code

Produces the security controls as a feature is built.

## Workflow

1. **Threat model** - attack surface and threats for this feature.
2. **Design** - the security controls that answer them.
3. **Implement** - defense in depth; code examples below.
4. **Validate** - the checkpoints below, per control implemented.
5. **Document** - the security decisions made.

### Validation checkpoints

- **Authentication**: brute-force protection actually triggers (lockout/rate limit), session fixation
  resistance, token expiry, and invalid-credential errors that don't leak whether the user exists.
- **Authorization**: horizontal *and* vertical privilege escalation blocked - test with tokens from
  different roles and different users.
- **Input handling**: SQL injection payloads (`' OR 1=1--`) rejected; XSS payloads
  (`<script>alert(1)</script>`) escaped or rejected.
- **Headers/CORS**: verified with a scanner (`curl -I`, Mozilla Observatory) - headers present, CORS
  origin allowlist correct.

## Constraints

- bcrypt/argon2 for passwords. Never MD5/SHA-1/unsalted, never plaintext or reversible encryption.
- Parameterized queries only. Never string-interpolated SQL.
- Secrets in environment variables or a secret manager, never in source.
- Never expose sensitive data in logs or error responses; never use MD5/SHA-1/DES/ECB.

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| OWASP | `references/owasp-prevention.md` | OWASP Top 10 patterns |
| Authentication | `references/authentication.md` | Password hashing, JWT |
| Input Validation | `references/input-validation.md` | Zod, SQL injection |
| XSS/CSRF | `references/xss-csrf.md` | XSS prevention, CSRF |
| Headers | `references/security-headers.md` | Helmet, rate limiting |

## Code Examples

### Password Hashing (bcrypt)

```typescript
import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12; // minimum 10; 12 balances security and performance

export async function hashPassword(plaintext: string): Promise<string> {
  return bcrypt.hash(plaintext, SALT_ROUNDS);
}

export async function verifyPassword(plaintext: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plaintext, hash);
}
```

### Parameterized SQL Query (Node.js / pg)

```typescript
// NEVER: `SELECT * FROM users WHERE email = '${email}'`
// ALWAYS: use positional parameters
import { Pool } from 'pg';
const pool = new Pool();

export async function getUserByEmail(email: string) {
  const { rows } = await pool.query(
    'SELECT id, email, role FROM users WHERE email = $1',
    [email]  // value passed separately - never interpolated
  );
  return rows[0] ?? null;
}
```

### Input Validation with Zod

```typescript
import { z } from 'zod';

const LoginSchema = z.object({
  email: z.string().email().max(254),
  password: z.string().min(8).max(128),
});

export function validateLoginInput(raw: unknown) {
  const result = LoginSchema.safeParse(raw);
  if (!result.success) {
    // Return generic error - never echo raw input back
    throw new Error('Invalid credentials format');
  }
  return result.data;
}
```

### JWT Validation

```typescript
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET!; // never hardcode

export function verifyToken(token: string): jwt.JwtPayload {
  // Throws if expired, tampered, or wrong algorithm
  const payload = jwt.verify(token, JWT_SECRET, {
    algorithms: ['HS256'],   // explicitly allowlist algorithm
    issuer: 'your-app',
    audience: 'your-app',
  });
  if (typeof payload === 'string') throw new Error('Invalid token payload');
  return payload;
}
```

### Securing an Endpoint - Full Flow

```typescript
import express from 'express';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';

const app = express();
app.use(helmet()); // sets CSP, HSTS, X-Frame-Options, etc.
app.use(express.json({ limit: '10kb' })); // limit payload size

const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10,                   // 10 attempts per window per IP
  standardHeaders: true,
  legacyHeaders: false,
});

app.post('/api/login', authLimiter, async (req, res) => {
  // 1. Validate input
  const { email, password } = validateLoginInput(req.body);

  // 2. Authenticate - parameterized query, constant-time compare
  const user = await getUserByEmail(email);
  if (!user || !(await verifyPassword(password, user.passwordHash))) {
    // Generic message - do not reveal whether email exists
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  // 3. Authorize - issue scoped, short-lived token
  const token = jwt.sign(
    { sub: user.id, role: user.role },
    JWT_SECRET,
    { algorithm: 'HS256', expiresIn: '15m', issuer: 'your-app', audience: 'your-app' }
  );

  // 4. Secure response - token in httpOnly cookie, not body
  res.cookie('token', token, { httpOnly: true, secure: true, sameSite: 'strict' });
  return res.json({ message: 'Authenticated' });
});
```

## Output

The secure implementation code, security considerations noted, configuration requirements (env vars,
headers), and testing recommendations.

## Boundaries

- Auditing code that already exists is `security-audit`'s - deliberately a separate skill, because it
  runs with no `Edit`/`Write` tool so an audit cannot quietly become a rewrite.
- Design-level security posture (where the trust boundaries sit, which pillar matters) is
  `architecture-designer`'s and `solution-design-principles`'s; this skill implements the controls.
- Authentication schemes as an API *contract* (which scheme, which scopes per endpoint) belong to
  `api-contract-skill`; implementing that scheme is this skill's.
