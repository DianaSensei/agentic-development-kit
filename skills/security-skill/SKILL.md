---
name: security-skill
description: Security work in two modes. IMPLEMENT - writing secure code while building a feature: authentication/authorization, input validation and sanitization, password hashing (bcrypt/argon2), parameterized queries, CORS/CSP headers, JWT/session handling, OWASP Top 10 prevention. AUDIT - finding vulnerabilities in code or infrastructure that already exists and reporting them with CVSS severity and remediation: SAST scans, dependency and secrets scanning, penetration testing, cloud/DevSecOps and compliance review. Use for any request to secure code being written, or to review/scan/audit existing code, dependencies, or infrastructure for vulnerabilities.
metadata:
  domain: security
  triggers: vulnerability, secure coding, OAuth, vulnerability scan, code audit, security analysis, compliance audit, pentest, SAST
  role: specialist
  scope: implementation-and-review
  output-format: code-or-report
  related-skills: code-review-skill, architecture-designer, api-contract-skill, mcp-developer
---

# Security

Two modes. **Implement** produces secure code as a feature is built. **Audit** produces a findings
report on code or infrastructure that already exists. Pick the mode from the request, and say which one
you're in - they have different outputs and different rules.

> **Audit mode does not fix.** It locates, rates, and recommends; the fix is a separate, explicitly
> requested change (usually Implement mode, or the owning technical skill). Don't quietly edit code
> during an audit - the report is the deliverable.

## Mode A - Implement

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

### Non-negotiables

- bcrypt/argon2 for passwords. Never MD5/SHA-1/unsalted, never plaintext or reversible encryption.
- Parameterized queries only. Never string-interpolated SQL.
- Secrets in environment variables or a secret manager, never in source.
- Never expose sensitive data in logs or error responses; never use MD5/SHA-1/DES/ECB.

## Mode B - Audit

1. **Scope** - map the attack surface and critical paths. **Confirm written authorization and rules of
   engagement before going further.**
2. **Scan** - SAST, dependency, and secrets tooling:
   `semgrep --config=auto .` · `bandit -r ./src` · `gitleaks detect --source=.` ·
   `npm audit --audit-level=moderate` · `trivy fs .`
3. **Review manually** - auth, input handling, crypto. **Tools miss context, so this pass is mandatory
   even when every scan comes back clean.**
4. **Test and classify** - **verify written scope authorization before any active testing.** Validate
   findings, rate severity (Critical/High/Medium/Low/Info) with CVSS. Confirm exploitability with a
   proof of concept and stop there.
5. **Report** - confirm findings with the stakeholder before finalizing; document location, impact, and
   remediation. Report critical findings immediately.

### Non-negotiables

- Rate every finding, Info and Low included - never drop one for being minor.
- Stop at proof of concept. Never exploit further, disrupt a service, or destroy data.
- Never test outside the defined scope, and never on production without authorization.
- Never publish detailed exploits.

## Reference Guide

| Mode | Topic | Reference | Load When |
|---|-------|-----------|-----------|
| Implement | OWASP | `references/owasp-prevention.md` | OWASP Top 10 patterns |
| Implement | Authentication | `references/authentication.md` | Password hashing, JWT |
| Implement | Input Validation | `references/input-validation.md` | Zod, SQL injection |
| Implement | XSS/CSRF | `references/xss-csrf.md` | XSS prevention, CSRF |
| Implement | Headers | `references/security-headers.md` | Helmet, rate limiting |
| Audit | SAST Tools | `references/sast-tools.md` | Running automated scans |
| Audit | Vulnerability Patterns | `references/vulnerability-patterns.md` | SQL injection, XSS, manual review |
| Audit | Secret Scanning | `references/secret-scanning.md` | Gitleaks, finding hardcoded secrets |
| Audit | Penetration Testing | `references/penetration-testing.md` | Active testing, reconnaissance, exploitation |
| Audit | Infrastructure Security | `references/infrastructure-security.md` | DevSecOps, cloud security, compliance |
| Audit | Report Template | `references/report-template.md` | Writing the security report |

## Code Examples (Implement mode)

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

**Implement mode**: the secure implementation code, security considerations noted, configuration
requirements (env vars, headers), and testing recommendations.

**Audit mode**: executive summary with risk assessment; findings table with severity counts; detailed
findings; prioritized recommendations. Full template in `references/report-template.md`.

```
ID: FIND-001
Severity: High (CVSS 8.1)
Title: SQL Injection in user search endpoint
File: src/api/users.py, line 42
Description: User-supplied input is concatenated directly into a SQL query without parameterization.
Impact: An attacker can read, modify, or delete database contents.
Remediation: Use parameterized queries or an ORM. Replace `cursor.execute(f"SELECT * FROM users WHERE name='{name}'")`
             with `cursor.execute("SELECT * FROM users WHERE name=%s", (name,))`.
References: CWE-89, OWASP A03:2021
```

## Boundaries

- Design-level security posture (which pillar matters, where the trust boundaries sit) is
  `architecture-designer`'s and `solution-design-principles`'s; this skill implements the controls and
  audits the result.
- A general correctness/quality review of a diff is `code-review-skill`'s, not an audit - Audit mode is
  specifically a vulnerability hunt.
- Authentication schemes as an API *contract* (which scheme, which scopes per endpoint) belong to
  `api-contract-skill`; implementing that scheme is this skill's.
