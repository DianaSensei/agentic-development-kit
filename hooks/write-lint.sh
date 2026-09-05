#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit) - cheap textual checks on the content that
# was just written.
#
# Advisory only, by design and by protocol: PostToolUse cannot block, and the
# things a regex can see (a leaked key, a stray TODO) are the small end of
# review. Anything needing judgement belongs to code-review-skill, not here.

. "${0%/*}/common.sh" || exit 0

MODE="$(mode_of write_lint warn)"
[ "$MODE" = "off" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path')"
[ -n "$FILE_PATH" ] || exit 0
REL="${FILE_PATH#"$PROJECT_DIR"/}"

# Only the newly written text, never the whole file - pre-existing debt in a file
# someone happens to touch is not this hook's business.
CONTENT="$(printf '%s' "$HOOK_INPUT" | jq -r '
  [ .tool_input.content?, .tool_input.new_string?, (.tool_input.edits[]?.new_string?) ]
  | map(select(. != null)) | join("\n")' 2>/dev/null)"
[ -n "$CONTENT" ] || exit 0

FINDINGS=""
add() { FINDINGS="${FINDINGS}
- $1"; }

while IFS= read -r pat; do
  [ -n "$pat" ] || continue
  hit="$(printf '%s' "$CONTENT" | grep -Ein "$pat" 2>/dev/null | head -n 1)"
  [ -n "$hit" ] && add "possible hardcoded secret (line ${hit%%:*} of the text just written, not of the file) - move it to configuration/env, never commit it"
done < <(jq -r '.write_lint.secret_patterns[]?' "$CONFIG_FILE" 2>/dev/null)

while IFS= read -r pat; do
  [ -n "$pat" ] || continue
  hit="$(printf '%s' "$CONTENT" | grep -Ein "$pat" 2>/dev/null | head -n 1)"
  [ -n "$hit" ] && add "placeholder or unfinished marker left in the written content (line ${hit%%:*} of the text just written, not of the file) - finish it or remove it before reporting done"
done < <(jq -r '.write_lint.placeholder_patterns[]?' "$CONFIG_FILE" 2>/dev/null)

[ -n "$FINDINGS" ] || exit 0
warn "[write-lint] \`$REL\`:$FINDINGS"
