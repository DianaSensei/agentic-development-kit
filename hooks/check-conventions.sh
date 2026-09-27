#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit) - the project's own convention checks, run on
# the file that was just written, with the result handed straight back to Claude.
#
# A convention a machine can check (format, lint, a type rule, "no print() in
# src/") belongs in a checker, not in prose: CLAUDE.md is advice that fades over
# a long session, a checker's exit code does not. This hook closes the loop at
# the moment it is cheapest - right after the edit, while the change is in view -
# instead of at review time or in CI.
#
# The checks are the project's, listed in its own .claude/quality-check.config.json:
#
#   "checks": [
#     {"name": "ruff", "match": "\\.py$", "run": "ruff check --quiet {file}"},
#     {"name": "format", "match": "\\.py$", "run": "ruff format --check --quiet {file}"},
#     {"name": "types", "scope": "project", "run": "npx tsc --noEmit"}
#   ]
#
# Only `scope: file` checks (the default) run here, on files matching `match`
# (ERE, repo-relative path); `{file}` becomes the path, shell-quoted. Project-wide
# checks are slower, so the workflows run them with the tests (feature-development
# 3.2) and CI runs all of them.
#
# Never from the plugin's bundled config: running commands is the project's
# decision. A checker this machine does not have (exit 127) is skipped, not a
# failure. `mode.convention_checks`: warn (the default) hands the failure to
# Claude as context; block makes Claude address it before going on.

. "${0%/*}/common.sh" || exit 0

PROJECT_CONFIG="$PROJECT_DIR/.claude/quality-check.config.json"
[ -f "$PROJECT_CONFIG" ] || exit 0
CONFIG_FILE="$PROJECT_CONFIG"
MODE="$(mode_of convention_checks warn)"
[ "$MODE" = "off" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path')"
[ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ] || exit 0
REL="${FILE_PATH#"$PROJECT_DIR"/}"
# A worktree of this project (parallel units) checks its own copy, by its own path.
case "$REL" in .claude/worktrees/*/*) REL="${REL#.claude/worktrees/*/}" ;; esac

# `timeout` is GNU coreutils: macOS has it as gtimeout, or not at all.
TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT=timeout
[ -z "$TIMEOUT" ] && command -v gtimeout >/dev/null 2>&1 && TIMEOUT=gtimeout

FAILURES=""
SKIPPED=""
while IFS= read -r check; do
  [ -n "$check" ] || continue
  name="$(printf '%s' "$check" | jq -r '.name // "check"')"
  match="$(printf '%s' "$check" | jq -r '.match // ""')"
  run="$(printf '%s' "$check" | jq -r '.run // ""')"
  limit="$(printf '%s' "$check" | jq -r '.timeout // 20')"
  [ -n "$run" ] || continue
  [ -z "$match" ] || printf '%s' "$REL" | grep -Eq "$match" || continue

  cmd="${run//\{file\}/$(printf '%q' "$FILE_PATH")}"
  # stdin from /dev/null: the loop reads the check list from its own stdin.
  out="$(cd "$PROJECT_DIR" && ${TIMEOUT:+$TIMEOUT "$limit"} bash -c "$cmd" < /dev/null 2>&1)"
  rc=$?
  case "$rc" in
    0) ;;
    127) SKIPPED="${SKIPPED}${SKIPPED:+, }$name" ;;
    124) FAILURES="${FAILURES}
- \`$name\` did not finish in ${limit}s: \`$run\`" ;;
    *) FAILURES="${FAILURES}
- \`$name\` (\`$run\`, exit $rc):
$(printf '%s\n' "$out" | head -n 30 | sed 's/^/    /')" ;;
  esac
done < <(jq -c '.checks[]? | select((.scope // "file") == "file")' "$PROJECT_CONFIG" 2>/dev/null)

[ -n "$FAILURES" ] || exit 0

MSG="[convention-checks] \`$REL\` fails the project's checks:$FAILURES
Fix what they report in this file before going on - they are the project's conventions, checked by
machine. A finding you believe is wrong is the user's call: say so, never disable the check.${SKIPPED:+
(Skipped, not installed here: $SKIPPED.)}"

if [ "$MODE" = "block" ]; then
  jq -nc --arg r "$MSG" '{decision: "block", reason: $r}'
else
  jq -nc --arg m "$MSG" '{systemMessage: $m, hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $m}}'
fi
exit 0
