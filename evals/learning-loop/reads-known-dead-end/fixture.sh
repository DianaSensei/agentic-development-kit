#!/usr/bin/env bash
# A project that already fixed one unbounded retry loop and logged what did
# not work. The new bug is the same kind of mistake in a different file.
set -euo pipefail
# The project opted into the kit, as project-setup leaves it - without that the
# kit's session reminders stay silent (hooks/common.sh project_opted_in).
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
mkdir -p src docs/knowledge
cat > CLAUDE.md <<'MD'
# Demo client
Python. HTTP client code lives in src/.
MD
cat > src/retry.py <<'PY'
import time

import requests

MAX_ATTEMPTS = 5


class RetryExhausted(Exception):
    pass


def get_with_retry(url):
    for attempt in range(MAX_ATTEMPTS):
        response = requests.get(url, timeout=5)
        if response.status_code != 503:
            return response
        time.sleep(2 ** attempt)
    raise RetryExhausted(f"{url} still answered 503 after {MAX_ATTEMPTS} attempts")
PY
cat > src/poll.py <<'PY'
import time

import requests


def wait_for_status(url):
    while True:
        response = requests.get(url, timeout=5)
        if response.status_code != 429:
            return response.json()
        time.sleep(1)
PY
cat > docs/knowledge/experience-log.md <<'MD'
# Experience log

## [2026-08-02] retry-503 - get_with_retry loops forever on 503

- Class: unbounded-retry
- Source: fix-loop
- Area: src/retry.py
- Cause: a while True loop retried every 503 with no attempt limit and no deadline.
- Attempts used: 2/5
- Outcome: Fixed
- Approaches tried that did NOT work: exponential backoff on its own - while the server keeps failing the loop still never ends, it only slows down.
- Fix applied: cap attempts (MAX_ATTEMPTS = 5) and raise RetryExhausted after the last one.
MD
git init -q && git add -A && git commit -qm "Client with retry fix and experience log"
