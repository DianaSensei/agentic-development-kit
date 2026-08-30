#!/usr/bin/env bash
# PreToolUse (Edit|Write|MultiEdit|NotebookEdit) — enforce the CHECKPOINT that
# feature-development/bug-fix/refactor each describe in prose ("wait for the
# user to confirm before proceeding"). Prose is not enforcement: nothing stops
# the model from just continuing past it. This hook makes the checkpoint an
# observable event instead of a promise — the three skills are told to ask it
# via `AskUserQuestion` with a fixed header, and this hook checks the
# transcript for that literal call before code may be written.
#
# Unlike skill-gate's "since the last user message" scope, a checkpoint can
# legitimately be answered several user turns before Step 3 starts (a Step 1
# interview can span multiple replies). So this scopes instead to "since this
# workflow skill was last invoked" — long enough to span the whole workflow,
# short enough that an approval from an EARLIER, separate feature request
# doesn't silently satisfy a new one.

. "${0%/*}/common.sh" || exit 0

MODE="$(mode_of checkpoint_gate warn)"
[ "$MODE" = "off" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path')"
[ -n "$FILE_PATH" ] || exit 0

TRANSCRIPT="$(jq_in '.transcript_path')"
[ -f "$TRANSCRIPT" ] || exit 0  # cannot verify — fail open

# Only gate the three workflows that actually document a CHECKPOINT this way.
# If none of them was ever invoked in this transcript, this edit is out of
# scope for this gate entirely (a direct edit outside any workflow, or a
# technical skill invoked on its own).
WORKFLOWS="$(jq_cfg '.checkpoint_gate.workflows[]?' 'feature-development
bug-fix
refactor')"
WF_PATTERN="$(printf '%s' "$WORKFLOWS" | paste -sd'|' -)"
[ -n "$WF_PATTERN" ] || exit 0

WF_START="$(last_line_matching "$TRANSCRIPT" \
  "(${WF_PATTERN})/SKILL\.md|\"skill\"[[:space:]]*:[[:space:]]*\"(${WF_PATTERN})\"")"
[ -n "$WF_START" ] || exit 0   # not inside a gated workflow — nothing to check

HEADER="$(jq_cfg '.checkpoint_gate.header' 'Checkpoint')"

# The exact call the skills are instructed to make: an AskUserQuestion tool_use
# whose question carries this literal header, case-insensitive. Each transcript
# line is one complete JSON event, so both fields land on the same line.
if transcript_tail_from "$TRANSCRIPT" "$WF_START" \
   | grep -qiE "\"name\"[[:space:]]*:[[:space:]]*\"AskUserQuestion\".*\"header\"[[:space:]]*:[[:space:]]*\"${HEADER}\""; then
  exit 0
fi

REL="${FILE_PATH#"$PROJECT_DIR"/}"
MSG="[checkpoint-gate] \`$REL\` is being edited, but no \`AskUserQuestion\` with header \"$HEADER\" was seen since this workflow started. Present the proposal/fix direction and ask for confirmation via \`AskUserQuestion\` (header exactly \"$HEADER\") before writing code — never proceed on the assumption that presenting is the same as confirming."

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

# warn mode: nag at most once per session — this is a single coarse gate per
# workflow run, not a per-file check like skill-gate.
SEEN="$STATE_DIR/$(jq_in '.session_id' unknown).checkpointgate"
[ -f "$SEEN" ] && exit 0
: > "$SEEN" 2>/dev/null || true
warn "$MSG"
