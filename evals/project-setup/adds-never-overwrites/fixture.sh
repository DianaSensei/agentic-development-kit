#!/usr/bin/env bash
# A repo that already has a hand-written CLAUDE.md and shared settings. Setup
# may add to both; it may not lose a line of either.
set -euo pipefail
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
mkdir -p src/shop tests .claude
cat > CLAUDE.md <<'MD'
# Shop API

Never call the real billing API from tests; use FakeBilling.

## Commands
- Test: `make test`
MD
cat > .claude/settings.json <<'JSON'
{
  "model": "claude-sonnet-5",
  "permissions": {
    "allow": [
      "Bash(make test *)"
    ]
  }
}
JSON
cat > Makefile <<'MK'
test:
	python3 -m pytest -q
MK
cat > src/shop/billing.py <<'PY'
class FakeBilling:
    def charge(self, amount):
        return {"status": "ok", "amount": amount}
PY
printf 'API_KEY=placeholder\n' > .env
printf '.env\n' > .gitignore
git init -q && git add -A && git commit -qm "Shop API with its own Claude setup"
