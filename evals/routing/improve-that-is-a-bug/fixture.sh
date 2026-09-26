#!/usr/bin/env bash
set -euo pipefail
# The project opted into the kit, as project-setup leaves it - without that the
# kit's session reminders stay silent (hooks/common.sh project_opted_in).
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src
cat > CLAUDE.md <<'MD'
# Demo client
Python. HTTP client code lives in src/.
MD
cat > src/retry.py <<'PY'
import time

import requests


def get_with_retry(url):
    while True:
        response = requests.get(url, timeout=5)
        if response.status_code != 503:
            return response
        time.sleep(1)
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Initial client"
