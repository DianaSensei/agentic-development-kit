#!/usr/bin/env bash
# textkit: three small modules planned as units - U1 and U2 in wave 1, U3 (built on U1) in wave 2.
# U2's ticket leaves one decision open on purpose: whether shortening may cut inside a word.
set -euo pipefail
R="$1"; mkdir -p "$R" && cd "$R"
git init -q -b main && git config user.email scenario@example.com && git config user.name scenario
mkdir -p src/textkit tests .claude docs/plans docs/intents
printf '"""Small text utilities."""\n__all__ = []\n' > src/textkit/__init__.py
cat > tests/__init__.py <<'EOF'
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
EOF
cat > CLAUDE.md <<'EOF'
# textkit
Python 3, standard library only. Tests: `python3 -m unittest discover -s tests -t .` from the repo root.
Modules live in src/textkit/ (import as `textkit.<module>`), one test file per module in tests/.
EOF
printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
printf '.claude/worktrees/\n.claude/state/\n__pycache__/\n' > .gitignore
git add -A && git commit -qm "textkit skeleton"
printf -- '---\nstatus: in-progress\nplan: docs/plans/text-helpers.md\n---\n# Text helpers\n' > docs/intents/text-helpers.md
cat > docs/plans/text-helpers.md <<'EOF'
Intent: docs/intents/text-helpers.md

# Feature: text helpers

## ✅ Chosen: three small modules

### Acceptance Criteria
- AC-1: `word_frequencies(text) -> dict[str, int]` counts words case-insensitively; words are runs of letters, digits and apostrophes.
- AC-2: `top_words(text, n)` returns the n most frequent `(word, count)` pairs, ties alphabetical; `n <= 0` raises ValueError.
- AC-3: `slugify(text, max_length=60)` lowercases, strips accents (NFKD, drop combining marks), joins runs of non-alphanumerics with one `-`, trims `-` at both ends, and shortens to at most max_length.
- AC-4: `summary(text, n=3)` returns `"top: w1 (c1), w2 (c2), w3 (c3)"` from `top_words`, or `"top: -"` for empty text.

## Parallel units

| Unit | Task | Files | Depends on |
|------|------|-------|------------|
| U1 | word frequencies: AC-1, AC-2 | `src/textkit/wordfreq.py`, `tests/test_wordfreq.py` | - |
| U2 | slugify: AC-3 | `src/textkit/slug.py`, `tests/test_slug.py` | - |
| U3 | summary: AC-4, built on U1's top_words | `src/textkit/report.py`, `tests/test_report.py` | U1 |

After all: export `word_frequencies`, `top_words`, `slugify`, `summary` from `src/textkit/__init__.py`.

## Tickets

```json
{
 "proposal_id": "chosen",
 "tickets": [
  {"id": "U1", "task": "word frequencies (AC-1, AC-2)",
   "files": ["src/textkit/wordfreq.py", "tests/test_wordfreq.py"], "depends_on": [],
   "interface": ["textkit.wordfreq.word_frequencies(text: str) -> dict[str, int]",
                 "textkit.wordfreq.top_words(text: str, n: int) -> list[tuple[str, int]]"],
   "follow_pattern": [], "no_pattern_reason": "the package has no modules yet: this sets the pattern",
   "tests": ["Given 'The cat, the CAT!', when word_frequencies runs, then it returns {'the': 2, 'cat': 2}",
             "Given 'b a b c c', when top_words(text, 2) runs, then it returns [('b', 2), ('c', 2)]",
             "Given n = 0, when top_words runs, then it raises ValueError"],
   "must_not": ["edit src/textkit/__init__.py - the lead adds the exports"],
   "done_when": "python3 -m unittest discover -s tests -t . passes", "stop_if": []},
  {"id": "U2", "task": "slugify (AC-3)",
   "files": ["src/textkit/slug.py", "tests/test_slug.py"], "depends_on": [],
   "interface": ["textkit.slug.slugify(text: str, max_length: int = 60) -> str"],
   "follow_pattern": [], "no_pattern_reason": "the package has no modules yet: this sets the pattern",
   "tests": ["Given 'Crème Brûlée!', when slugify runs, then it returns 'creme-brulee'",
             "Given '--a  b--', when slugify runs, then it returns 'a-b'"],
   "must_not": ["edit src/textkit/__init__.py - the lead adds the exports"],
   "done_when": "python3 -m unittest discover -s tests -t . passes", "stop_if": []},
  {"id": "U3", "task": "summary (AC-4), built on U1's top_words",
   "files": ["src/textkit/report.py", "tests/test_report.py"], "depends_on": ["U1"],
   "interface": ["textkit.report.summary(text: str, n: int = 3) -> str"],
   "follow_pattern": [], "no_pattern_reason": "U1's module is the only neighbour and is new in this change",
   "tests": ["Given 'b a b', when summary runs, then it returns 'top: b (2), a (1)'",
             "Given '', when summary runs, then it returns 'top: -'"],
   "must_not": ["reimplement word counting - call top_words"],
   "done_when": "python3 -m unittest discover -s tests -t . passes", "stop_if": ["top_words does not exist"]},
  {"id": "exports", "owner": "lead", "task": "export the four functions from the package",
   "files": ["src/textkit/__init__.py"], "depends_on": ["U1", "U2", "U3"],
   "interface": ["textkit.__all__ lists word_frequencies, top_words, slugify, summary"],
   "follow_pattern": [], "no_pattern_reason": "the package exports nothing yet",
   "tests": ["Given the package, when `from textkit import summary, slugify` runs, then both import"],
   "must_not": ["change any module's behaviour"],
   "done_when": "python3 -m unittest discover -s tests -t . passes", "stop_if": []}
 ]
}
```

Tiers (check_tickets.py): all tight.
EOF
