# Analysis Checklist

Use this after running the exploration patterns in `references/analysis-process.md` to confirm coverage
is complete before writing the specification — this file tracks completeness, it does not repeat the
Glob/Grep patterns themselves.

## Analysis Phases

### Phase 1: Structure Discovery
- [ ] Identify technology stack
- [ ] Map directory structure
- [ ] Find entry points
- [ ] List all modules/packages

### Phase 2: API Surface
- [ ] Document all endpoints
- [ ] Note HTTP methods and paths
- [ ] Identify request/response formats
- [ ] Find authentication requirements

### Phase 3: Data Layer
- [ ] Map all data models
- [ ] Document relationships
- [ ] Find migrations
- [ ] Note validation rules

### Phase 4: Business Logic
- [ ] Trace main flows
- [ ] Identify business rules
- [ ] Document state transitions
- [ ] Find external integrations

### Phase 5: Security
- [ ] Check authentication method
- [ ] Review authorization patterns
- [ ] Find input validation
- [ ] Note security configurations

### Phase 6: Quality & Testing
- [ ] Review existing tests
- [ ] Note test coverage
- [ ] Document error handling
- [ ] Find logging patterns

## Verification Questions

Before finalizing specification:

- [ ] All endpoints documented?
- [ ] All models mapped?
- [ ] Authentication flow clear?
- [ ] Error responses documented?
- [ ] External dependencies listed?
- [ ] Uncertainties flagged?
