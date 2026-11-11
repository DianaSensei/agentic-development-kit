#!/usr/bin/env bash
# A proposal for a non-technical approver. Measures what technical-proposal-writer adds: the standard structure with real alternatives and risks, opening on the problem.
set -euo pipefail
echo "# Reports" > README.md
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm init
