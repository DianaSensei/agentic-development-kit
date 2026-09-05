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

# One grep per category, not one per pattern. This hook runs after every single
# write, so the patterns are joined into a single alternation up front: the old
# loop spawned a grep per pattern and made this the slowest hook in the kit while
# doing the least work. Only the first hit per category is reported either way.
scan() {
  local re hit
  re="$(jq -r "[.write_lint.$1[]?] | join(\"|\")" "$CONFIG_FILE" 2>/dev/null)"
  [ -n "$re" ] || return 0
  hit="$(printf '%s' "$CONTENT" | grep -Ein "$re" 2>/dev/null | head -n 1)"
  [ -n "$hit" ] && add "$2 (line ${hit%%:*} of the text just written, not of the file) - $3"
  return 0
}

scan secret_patterns \
  "possible hardcoded secret" \
  "move it to configuration/env, never commit it"
scan placeholder_patterns \
  "an elided or unfinished block was left in the written content" \
  "write the real code before reporting done"

[ -n "$FINDINGS" ] || exit 0
warn "[write-lint] \`$REL\`:$FINDINGS"
