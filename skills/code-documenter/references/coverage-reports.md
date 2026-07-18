# Documentation Coverage Reports

## Purpose

A coverage report answers three questions for whoever requested the documentation pass: how much of
the public surface is documented now, how much was documented before, and what's still missing. Treat
it as a deliverable, not an afterthought — "I documented some things" isn't verifiable; a before/after
count is.

## Report Structure

```markdown
# Documentation Report: {project_name}

## Summary
- Files analyzed: {count}
- Functions/methods documented: {n}/{total} ({percent}%)
- Classes/types documented: {n}/{total} ({percent}%)
- API endpoints documented: {n}/{total} ({percent}%)

## Coverage Before/After
- Before: {percent}%
- After: {percent}%

## Files Modified
| File | Entries Added | Notes |
|------|----------------|-------|
| {path} | {count} | {what was added, e.g. "all public methods", "added examples"} |

## Documentation Style Used
- Inline doc-comment style: {the convention this codebase already uses, or the one agreed with the user}
- API documentation format: {e.g. OpenAPI, GraphQL SDL, AsyncAPI, protobuf — whichever the project uses}

## Missing Documentation
| File | Missing | Priority |
|------|---------|----------|
| {path} | {count} entries | {High/Medium/Low} |

## Recommendations
1. Run the project's existing doc-linter/coverage tool, if one is configured, to keep this from regressing.
2. If no doc-coverage tool is configured, consider adding one appropriate to the language/ecosystem.
3. Add a documentation-coverage check to CI so new public surface can't ship undocumented.
```

## Coverage Metrics

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Function/method coverage | >90% | 70-90% | <70% |
| Class/type coverage | 100% | >90% | <90% |
| API endpoint coverage | 100% | 100% | <100% |
| Example coverage (non-trivial entries) | >50% | 30-50% | <30% |

100% is the bar for classes/types and API endpoints because a caller has no way to discover an
undocumented public type or endpoint exists except by reading source — unlike a function, where a
clear name can partially substitute for documentation.

## Checklist During Documentation

```markdown
### Before Starting
- [ ] Confirmed doc-comment format/convention (matched to what the codebase already uses, or agreed with the user if none exists)
- [ ] Identified files to exclude (tests, generated code, vendored dependencies)
- [ ] Identified the API documentation format already in use, if any

### Functions/Methods
- [ ] All public functions documented
- [ ] Parameters described with types
- [ ] Return values documented
- [ ] Exceptions/errors documented
- [ ] Examples added for non-trivial behavior

### Classes/Types
- [ ] Purpose described
- [ ] Constructor/initializer parameters documented
- [ ] Public methods documented
- [ ] Important fields/attributes explained

### API Endpoints
- [ ] All endpoints have summaries
- [ ] Request bodies/parameters documented
- [ ] Response schemas defined
- [ ] Error responses documented
- [ ] Authentication/authorization requirements noted

### Final Checks
- [ ] Ran the project's doc-validation/lint tooling, if configured
- [ ] Verified generated documentation renders correctly
- [ ] No inaccurate or untested documentation
- [ ] Coverage report generated
```

## Boundary

This file defines the report format and coverage checklist, independent of language or ecosystem. The
specific tool used to measure or enforce coverage (a doc-linter, a coverage script, a CI check) depends
on what the project's language/ecosystem already provides or has configured — use whatever is already
set up in the project; if nothing is configured, note that as a recommendation rather than guessing at
a specific tool to introduce.
