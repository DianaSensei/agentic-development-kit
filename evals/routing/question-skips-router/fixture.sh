#!/usr/bin/env bash
# A project that opted into the kit, so the session reminder "code changes start
# at workflow-router, questions skip it" is present - the case checks the second half.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-sdlc@agentic-development-kit":true}}\n' > .claude/settings.json
