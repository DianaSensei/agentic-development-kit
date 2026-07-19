# Interview Questions (Step 1 — Requirements Analysis)

## PM Hat Questions

Focus on user value and business goals.

| Area | Questions |
|------|-----------|
| **Problem** | What problem does this solve? Who experiences this problem? How often? |
| **Users** | Who are the target users? What are their goals? Technical level? |
| **Value** | How will users benefit? What's the business value? ROI? |
| **Scope** | What's in scope? What's explicitly out of scope? MVP vs full version? |
| **Success** | How will we measure success? Key metrics? |
| **Priority** | Is this a must-have, should-have, or nice-to-have? |

### Example PM Questions

```markdown
For a "User Export" feature:
- Who needs to export data and why?
- What format do they need (CSV, JSON, Excel)?
- How much data? 100 rows or 1 million?
- Is this for compliance (GDPR) or convenience?
- How often will this be used?
- What's the deadline?
```

## Dev Hat Questions

Focus on technical feasibility and edge cases.

| Area | Questions |
|------|-----------|
| **Integration** | What systems does this touch? APIs, databases, services? |
| **Security** | Authentication required? Data sensitivity (PII, PCI)? |
| **Performance** | Expected load? Response time requirements? Async OK? |
| **Edge Cases** | What happens when X fails? Empty states? Limits? |
| **Data** | What's stored? Retention period? Backup needs? |
| **Dependencies** | External services? Rate limits? Costs? |

### Example Dev Questions

```markdown
For a "User Export" feature:
- What fields to include? Are any sensitive (passwords, tokens)?
- Max export size? Need streaming or background job?
- Should include soft-deleted records?
- What happens if export fails midway?
- File retention - how long to keep generated files?
- Need progress indicator for large exports?
```

Interview from both hats for every non-trivial feature — the PM hat alone misses feasibility/edge-case
risk, and the Dev hat alone misses whether the feature is worth building at all.

## Tool Usage: AskUserQuestions

Use the structured-elicitation tool when questions have a finite set of likely answers. Use open-ended
follow-up when answers are unbounded.

### When to Use Structured Options

| Question Pattern | Example | Options Style |
|-----------------|---------|---------------|
| Priority/ranking | "Is this must-have or nice-to-have?" | Single select: Must-have, Should-have, Nice-to-have |
| Format selection | "What export format?" | Multi-select: CSV, JSON, Excel, PDF |
| Scope decisions | "MVP or full version?" | Single select: MVP, Full, Phased |
| Yes/No with nuance | "Auth required?" | Single select: Public, Authenticated, Role-based |

### When to Use Open-Ended

- "Describe the user journey in your own words"
- "What problem does this solve?"
- "Walk me through the workflow"

### Example: Structured Elicitation

For a "User Export" feature, batch related choices:

**Question 1** (header: "Export scope"): "What data should users be able to export?"
Options: "Own data only", "Team data", "Organization-wide", multi-select enabled

**Question 2** (header: "Format"): "Which export formats should be supported?"
Options: "CSV", "JSON", "Excel (.xlsx)", "PDF", multi-select enabled

**Question 3** (header: "Priority"): "How critical is this feature?"
Options: "Must-have (blocking)", "Should-have (important)", "Nice-to-have (future)"

---

## Interview Flow

### Phase 1: Discovery
Open-ended questions to understand the problem space:
1. "Tell me about this feature in your own words"
2. "What problem are we solving?"

Then narrow down with structured choices: target users (single select from identified personas),
usage frequency (Daily, Weekly, Monthly, Rarely), priority (Must-have, Should-have, Nice-to-have).

### Phase 2: Details
Structured choices for scope and constraints: Scope (MVP vs Full vs Phased, single select), key
capabilities (multi-select from discovered items). Then open-ended: "Walk me through the user journey."

### Phase 3: Edge Cases
Structured choices for technical trade-offs: error handling approach (Retry, Fail fast, Queue, Notify),
data limits (multi-select thresholds). Then open-ended: "What happens when [X] fails?"

### Phase 4: Validation
Present the proposal summary (this is Step 2's CHECKPOINT), then confirm: "Does this capture your
requirements?" (Yes / Needs changes / Major gaps), with per-requirement priority confirmation if needed.

## Multi-Agent Pre-Discovery

For features spanning multiple domains (auth, database, UI, etc.), launch Task subagents with relevant
skills **before** the interview (i.e. before Step 1) to front-load technical context, so the interview
focuses on decisions rather than exploration.

**When to use:**
- Feature touches 3+ distinct system layers (e.g. auth, database, UI)
- Codebase is unfamiliar or underdocumented
- Concrete technical facts are needed before asking requirements questions
- Stakeholder time is limited and back-and-forth should be minimized

**When NOT to use:**
- Feature is well-scoped to a single domain
- Deep codebase knowledge already exists
- Requirements are purely business/UX (no technical exploration needed)

### Pattern

```
1. Identify domains the feature touches
2. Launch parallel Task subagents, each invoking the relevant skill from the Step 0 skill map
   (e.g. architecture-designer for system-impact assessment, security-reviewer for auth/data
   concerns, Explore for existing codebase patterns)
3. Collect findings from all subagents
4. Begin the Step 1 interview with technical context already loaded
5. Focus the interview on decisions and trade-offs, not exploration
```

### Example

For a "user profile with avatar upload" feature:

```
Subagent 1 (architecture-designer): "Analyze the current user model, storage patterns,
  and image handling in this codebase"
Subagent 2 (security-reviewer): "What security concerns exist for file upload in this stack?"
Subagent 3 (Explore): "How does this project currently handle API endpoints and file storage?"
```

Results feed into the interview, so questions like "Where should we store avatars?" come with context
about existing patterns rather than being asked blind.

---

## Quick Reference

| Phase | Focus | Tool |
|-------|-------|------|
| Pre-Discovery (optional) | Technical context | Task subagents with relevant skills |
| Discovery | Problem, users, value | Open-ended → structured choices |
| Details | Journey, scope, constraints | Structured choices → open-ended |
| Edge Cases | Failures, limits, security | Structured choices → open-ended |
| Validation | Summary, gaps | Structured choices (Step 2 CHECKPOINT) |
