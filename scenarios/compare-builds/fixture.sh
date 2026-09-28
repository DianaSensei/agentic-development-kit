#!/usr/bin/env bash
# accounts: two close proposals for duplicate-email detection, and the product team's acceptance
# examples, which only Proposal B (NFKC + casefold) passes. The user chose "Build the top two and compare".
set -euo pipefail
R="$1"; mkdir -p "$R" && cd "$R"
git init -q -b main && git config user.email scenario@example.com && git config user.name scenario
mkdir -p src/accounts tests .claude docs/plans docs/intents
cat > tests/__init__.py <<'EOF'
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
EOF
touch src/accounts/__init__.py
cat > CLAUDE.md <<'EOF'
# accounts
Python 3, standard library only. Tests: `python3 -m unittest discover -s tests -t .` from the repo root.
Code in src/accounts/ (import as `accounts.<module>`).
EOF
printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
printf '.claude/worktrees/\n.claude/state/\n__pycache__/\n' > .gitignore
cat > tests/test_contract.py <<'EOF'
"""The product team's acceptance examples for duplicate detection - written before the code."""
import unittest

from accounts.dedupe import find_duplicate_accounts


class Contract(unittest.TestCase):
    def test_case_only_difference(self):
        self.assertEqual(find_duplicate_accounts(["Bob@X.com", "bob@x.com", "amy@x.com"]),
                         [["Bob@X.com", "bob@x.com"]])

    def test_german_sharp_s(self):
        self.assertEqual(find_duplicate_accounts(["STRASSE@x.de", "straße@x.de"]),
                         [["STRASSE@x.de", "straße@x.de"]])

    def test_fullwidth_characters(self):
        self.assertEqual(find_duplicate_accounts(["ｂｏｂ@x.com", "bob@x.com"]),
                         [["ｂｏｂ@x.com", "bob@x.com"]])

    def test_no_duplicates(self):
        self.assertEqual(find_duplicate_accounts(["a@x.com", "b@x.com"]), [])
EOF
git add -A && git commit -qm "Accounts: acceptance examples for duplicate detection"
cat > docs/plans/dedupe.md <<'EOF'
Intent: docs/intents/dedupe.md

# Feature: find duplicate accounts by email

Acceptance: `find_duplicate_accounts(emails) -> list[list[str]]` in `src/accounts/dedupe.py` groups
addresses that are the same person, in input order, groups of two or more only, in order of first
appearance. The product team's examples are in `tests/test_contract.py`.

## Proposal A: lower-case comparison
Group by `email.lower()`. Simple, obvious, fast. Tradeoff: only ASCII case folding.

## Proposal B: Unicode-normalised comparison
Group by `unicodedata.normalize("NFKC", email).casefold()`. Handles more of Unicode. Tradeoff: slightly
more code, and a reader must know what NFKC and casefold do.

## Parallel units
| Unit | Task | Files | Depends on |
|------|------|-------|------------|
| U1 | find_duplicate_accounts | `src/accounts/dedupe.py`, `tests/test_dedupe.py` | - |

## Decision log
- CHECKPOINT: the user chose "Build the top two and compare" (A and B).
EOF
printf -- '---\nstatus: in-progress\nplan: docs/plans/dedupe.md\n---\n# Dedupe accounts\n' > docs/intents/dedupe.md
