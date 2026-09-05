#!/usr/bin/env bash
# PreToolUse (Edit|Write|MultiEdit|NotebookEdit) - enforce feature-development
# Step 3.1: the technical SKILL.md that owns a file must have been read, within
# the scope of the current request, before that file is edited.
#
# "Within the current request" is the part that matters and the part the model
# cannot self-police: the skill file may have changed since the previous turn,
# so a read carried over from an earlier request does not count.

. "${0%/*}/common.sh" || exit 0

MODE="$(mode_of skill_gate warn)"
[ "$MODE" = "off" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path')"
[ -n "$FILE_PATH" ] || exit 0

# Normalise to a repo-relative path so the config's patterns stay portable.
REL="${FILE_PATH#"$PROJECT_DIR"/}"

# Which skill owns this file? First matching row wins.
SKILL=""
# NB: @tsv escapes the backslashes inside the regexes, so emit each pair as two
# plain lines instead and keep the patterns byte-exact.
while read -r pattern && read -r skill; do
  [ -n "$pattern" ] || continue
  if printf '%s' "$REL" | grep -Eq "$pattern"; then SKILL="$skill"; break; fi
done < <(jq -r '.skill_map[]? | .match, .skill' "$CONFIG_FILE" 2>/dev/null)

[ -n "$SKILL" ] || exit 0

SKILL_MD="$(resolve_skill "$SKILL")"
[ -n "$SKILL_MD" ] || exit 0   # skill not installed here - nothing to enforce

TRANSCRIPT="$(jq_in '.transcript_path')"
[ -f "$TRANSCRIPT" ] || exit 0  # cannot verify - fail open

# Start of the current request = the last genuine user message (see common.sh).
START="$(last_user_message_line "$TRANSCRIPT")"

# Did anything in the current request actually load this skill? Either a Read of
# its SKILL.md, or an invocation of it through the Skill tool. Merely naming the
# path is not a read - see skill_ref_pattern in common.sh for why that matters.
if transcript_tail_from "$TRANSCRIPT" "$START" \
   | grep -qE "$(skill_ref_pattern "$SKILL")"; then
  exit 0
fi

MSG="[skill-gate] \`$REL\` is owned by the \`$SKILL\` skill, which has not been read in this request. Read \`${SKILL_MD#"$PROJECT_DIR"/}\` in full, then make the edit (feature-development Step 3.1 - a read from an earlier request does not carry over)."

if [ "$MODE" = "block" ]; then
  jq -nc --arg r "$MSG" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $r
    }
  }'
  exit 0
fi

# warn mode: nag at most once per REQUEST per skill, so a long feature does not
# repeat the same advisory on every file it touches - but a later request that
# still hasn't read the skill is warned again.
#
# Keying this to the session instead (as it did) silently cancelled the rule this
# gate exists for: after one warning, every following request in that session was
# free to edit without reading the skill, which is exactly the carried-over read
# the header comment above says must not count.
SEEN="$STATE_DIR/$(jq_in '.session_id' unknown).skillgate.$SKILL"
[ "$(cat "$SEEN" 2>/dev/null)" = "req-${START:-0}" ] && exit 0
printf '%s' "req-${START:-0}" > "$SEEN" 2>/dev/null || true
warn "$MSG"
