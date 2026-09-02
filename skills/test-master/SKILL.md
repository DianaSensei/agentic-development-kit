---
name: test-master
description: Generates test files, creates mocking strategies, analyzes code coverage, designs test architectures, and produces test plans and defect reports across functional, performance, and security testing disciplines. Use when writing unit tests, integration tests, or E2E tests; creating test strategies or automation frameworks; analyzing coverage gaps; performance testing with k6 or Artillery; security testing with OWASP methods; debugging flaky tests; or working on QA, regression, test automation, quality gates, shift-left testing, or test maintenance.
metadata:
  domain: quality
  triggers: test, testing, QA, unit test, integration test, E2E, coverage, performance test, security test, regression, test strategy, test automation, test framework, quality metrics, defect, exploratory, usability, accessibility, localization, manual testing, shift-left, quality gate, flaky test, test maintenance
  role: specialist
  scope: testing
  output-format: report
  related-skills: feature-development, java-spring-skill, tauri-react-skill, testcontainers-skill, code-review-skill, monitoring-expert
---

# Test Master

Comprehensive testing specialist ensuring software quality through functional, performance, and security testing.

## Core Workflow

1. **Define scope** - Identify what to test and which testing types apply
2. **Create strategy** - Plan the test approach across functional, performance, and security perspectives
3. **Write tests** - Implement tests with proper assertions (see example below)
4. **Execute** - Run tests and collect results
   - If tests fail: classify the failure (assertion error vs. environment/flakiness), fix root cause, re-run
   - If tests are flaky: isolate ordering dependencies, check async handling, add retry or stabilization logic
5. **Report** - Document findings with severity ratings and actionable fix recommendations
   - Verify coverage targets are met before closing; flag gaps explicitly

## Quick-Start Example

A minimal Jest unit test illustrating the key patterns this skill enforces:

```js
// ✅ Good: meaningful description, specific assertion, isolated dependency
describe("calculateDiscount", () => {
  it("applies 10% discount for premium users", () => {
    const result = calculateDiscount({ price: 100, userTier: "premium" });
    expect(result).toBe(90); // specific outcome, not just truthy
  });

  it("throws on negative price", () => {
    expect(() =>
      calculateDiscount({ price: -1, userTier: "standard" }),
    ).toThrow("Price must be non-negative");
  });
});
```

Apply the same structure for pytest (`def test_…`, `assert result == expected`) or JUnit5
(`@Test`, `assertEquals(90, result)`) - the shape (isolated setup, one behavior per test, specific
assertion) is what matters, not the framework syntax. See `java-spring-skill/references/testing.md` for
full JUnit5/Mockito patterns.

## Reference Guide

Load detailed guidance based on context:

| Topic                 | Reference                             | Load When                                                           |
| --------------------- | ------------------------------------- | ------------------------------------------------------------------- |
| Unit Testing          | `references/unit-testing.md`          | Jest, Vitest, pytest patterns (Java/JUnit5 → `java-spring-skill`)   |
| Integration           | `references/integration-testing.md`   | API testing, Supertest, httpx (Java → `java-spring-skill`)          |
| E2E                   | `references/e2e-testing.md`           | E2E strategy, user flows (Tauri desktop → `tauri-driver`, see file) |
| Performance           | `references/performance-testing.md`   | k6, load testing                                                    |
| Security              | `references/security-testing.md`      | Security test checklist (Java → `java-spring-skill`)                |
| Reports               | `references/test-reports.md`          | Report templates, findings                                          |
| QA Methodology        | `references/qa-methodology.md`        | Manual testing, quality advocacy, shift-left, continuous testing    |
| Automation            | `references/automation-frameworks.md` | Framework patterns, scaling, maintenance, team enablement           |
| TDD Iron Laws         | `references/tdd-iron-laws.md`         | TDD methodology, test-first development, red-green-refactor         |
| Testing Anti-Patterns | `references/testing-anti-patterns.md` | Test review, mock issues, test quality problems                     |

## Constraints

**MUST DO**

- Test happy paths AND error/edge cases (e.g., empty input, null, boundary values)
- Mock external dependencies - never call real APIs or databases in unit tests
- Use meaningful `it('…')` descriptions that read as plain-English specifications
- Assert specific outcomes (`expect(result).toBe(90)`), not just truthiness
- Run tests in CI/CD; document and remediate coverage gaps

**MUST NOT**

- Use production data in tests - use fixtures or factories instead
- Create order-dependent tests - each test must be independently runnable
- Ignore flaky tests - quarantine and fix them; don't just re-run until green
- Test implementation details (internal method calls) - test observable behaviour

## Output Templates

When creating test plans, provide:

1. Test scope and approach
2. Test cases with expected outcomes
3. Coverage analysis
4. Findings with severity (Critical/High/Medium/Low)
5. Specific fix recommendations

## Knowledge Reference

Unit/integration/E2E test boundaries, test pyramids, mocking/stubbing/fakes, fixtures vs. factories,
flaky-test quarantine, coverage analysis, k6/Artillery load testing, OWASP-based security testing,
shift-left testing, regression/quality gates, defect severity classification.
