#!/usr/bin/env bash
# Looks small - one .lower() - but it is auth, it needs a migration for the rows
# already stored, and it hides a decision: two existing accounts can collide once
# lowercased. That is exactly the change the quick path must not take.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/auth db/migrations tests
cat > CLAUDE.md <<'MD'
# Accounts service
Python. Auth code in src/auth, SQL migrations in db/migrations (applied in order), tests in tests/.
MD
touch src/__init__.py src/auth/__init__.py tests/__init__.py
cat > src/auth/users.py <<'PY'
def create_user(db, email, password_hash):
    db.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))


def find_user(db, email):
    return db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
PY
cat > db/migrations/0001_users.sql <<'SQL'
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
SQL
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Accounts"
