---
name: security-audit
description: Finds vulnerabilities in code or infrastructure that already exists and reports them with CVSS severity and remediation - SAST scans, dependency audits, secrets scanning, penetration testing, cloud/DevSecOps and compliance review. Read-only by design: it locates and rates, it does not fix. Use for any request to audit, scan, or review existing code, dependencies, or infrastructure for vulnerabilities. To write secure code while building a feature, use `security-skill`.
allowed-tools: Read, Grep, Glob, Bash
metadata:
  domain: security
  triggers: vulnerability scan, code audit, security analysis, compliance audit, pentest, SAST, dependency audit, secrets scanning
  role: specialist
  scope: review
  output-format: report
  related-skills: security-skill, code-review-skill, api-contract-skill, mcp-developer
---

# Security Audit

Produces a findings report on code or infrastructure that already exists.

**This skill cannot modify code, and that is deliberate** - its `allowed-tools` carries no
`Edit`/`Write`, so an audit is structurally unable to turn into a silent rewrite. The report is the
deliverable. Fixing what it finds is a separate, explicitly requested change (`security-skill` for the
control itself, or the technical skill owning that code).

## Workflow

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

## Constraints

- Rate every finding, Info and Low included - never drop one for being minor.
- Stop at proof of concept. Never exploit further, disrupt a service, or destroy data.
- Never test outside the defined scope, and never on production without authorization.
- Never publish detailed exploits.

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| SAST Tools | `references/sast-tools.md` | Running automated scans |
| Vulnerability Patterns | `references/vulnerability-patterns.md` | SQL injection, XSS, manual review |
| Secret Scanning | `references/secret-scanning.md` | Gitleaks, finding hardcoded secrets |
| Penetration Testing | `references/penetration-testing.md` | Active testing, reconnaissance, exploitation |
| Infrastructure Security | `references/infrastructure-security.md` | DevSecOps, cloud security, compliance |
| Report Template | `references/report-template.md` | Writing the security report |

## Output

Executive summary with risk assessment; findings table with severity counts; detailed findings;
prioritized recommendations. Full template in `references/report-template.md`.

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

- A general correctness/quality review of a diff is `code-review-skill`'s - this is specifically a
  vulnerability hunt.
- Design-level security posture (trust boundaries, which pillar matters) is `architecture-designer`'s
  and `solution-design-principles`'s.
