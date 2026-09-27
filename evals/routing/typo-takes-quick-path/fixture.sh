#!/usr/bin/env bash
# A one-word typo in a user-facing string: nothing to decide, one file. The full
# workflow (analyst, architect, plan, Checkpoint) is pure cost here.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/shop tests
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest).
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/messages.py <<'PY'
WELCOME = "Welcom to the shop"
GOODBYE = "Thanks for visiting"
PY
cat > tests/test_messages.py <<'PY'
from src.shop import messages


def test_goodbye():
    assert messages.GOODBYE == "Thanks for visiting"
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Shop messages"
