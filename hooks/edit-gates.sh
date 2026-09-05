#!/usr/bin/env bash
# PreToolUse (Edit|Write|MultiEdit|NotebookEdit) - the two checks that must pass
# before a workflow may write code. They live in one script because they run on
# the same event with the same matcher and need the same inputs: the stdin JSON,
# the config, and the transcript. As two scripts they paid for a second bash
# start, a second jq parse and a second read of the transcript on every edit.
#
# They stay independently configurable - `mode.skill_gate` and
# `mode.checkpoint_gate` are still separate, and either can be off while the
# other blocks.
#
# GATE 1 - the technical SKILL.md that owns a file must have been read, within
# the scope of the current request. "Within the current request" is the part that
# matters and the part the model cannot self-police: the skill file may have
# changed since the previous turn, so a read carried over does not count.
#
# GATE 2 - the CHECKPOINT that feature-development/bug-fix/refactor each describe
# in prose ("wait for the user to confirm") is not enforcement on its own; nothing
# stops the model continuing past it. The three skills are told to ask via
# `AskUserQuestion` with a fixed header, and this checks the transcript for that
# literal call.
#
# Gate 2 scopes differently from gate 1 on purpose: a checkpoint can legitimately
# be answered several user turns before Step 3 starts (a Step 1 interview can span
# replies), so it scopes to "since this workflow was last invoked" rather than
# "since the last user message".
#
# Only CODE writes are gated. Step 2 must write the plan document
# (docs/plans/<slug>.md) BEFORE the checkpoint by design - present it, then ask -
# so a non-code write is never in scope. Found by running the workflow end to end,
# not reasoned out in advance: the first version fired on that exact write.

. "${0%/*}/common.sh" || exit 0

SKILL_MODE="$(mode_of skill_gate warn)"
CP_MODE="$(mode_of checkpoint_gate warn)"
[ "$SKILL_MODE" = "off" ] && [ "$CP_MODE" = "off" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path')"
[ -n "$FILE_PATH" ] || exit 0
REL="${FILE_PATH#"$PROJECT_DIR"/}"

TRANSCRIPT="$(jq_in '.transcript_path')"
[ -f "$TRANSCRIPT" ] || exit 0   # cannot verify anything - fail open
SESSION="$(jq_in '.session_id' unknown)"

BLOCK_MSG=""
WARN_MSG=""
add_msg() {   # <mode> <text>
  if [ "$1" = "block" ]; then BLOCK_MSG="${BLOCK_MSG}${BLOCK_MSG:+
}$2"; else WARN_MSG="${WARN_MSG}${WARN_MSG:+
}$2"; fi
}

# ---------------------------------------------------------------- gate 1
if [ "$SKILL_MODE" != "off" ]; then
  # Which skill owns this file? First matching row wins.
  # NB: @tsv escapes the backslashes inside the regexes, so emit each pair as two
  # plain lines instead and keep the patterns byte-exact.
  SKILL=""
  while read -r pattern && read -r skill; do
    [ -n "$pattern" ] || continue
    if printf '%s' "$REL" | grep -Eq "$pattern"; then SKILL="$skill"; break; fi
  done < <(jq -r '.skill_map[]? | .match, .skill' "$CONFIG_FILE" 2>/dev/null)

  if [ -n "$SKILL" ]; then
    SKILL_MD="$(resolve_skill "$SKILL")"
    if [ -n "$SKILL_MD" ]; then   # skill not installed here - nothing to enforce
      START="$(last_user_message_line "$TRANSCRIPT")"
      # Did the current request actually load this skill? A Read of its SKILL.md,
      # or an invocation through the Skill tool. Merely naming the path is not a
      # read - see skill_ref_pattern in common.sh for why that matters.
      if ! transcript_tail_from "$TRANSCRIPT" "$START" \
           | grep -qE "$(skill_ref_pattern "$SKILL")"; then
        MSG="[skill-gate] \`$REL\` is owned by the \`$SKILL\` skill, which has not been read in this request. Read \`${SKILL_MD#"$PROJECT_DIR"/}\` in full, then make the edit (feature-development Step 3.1 - a read from an earlier request does not carry over)."
        if [ "$SKILL_MODE" = "block" ]; then
          add_msg block "$MSG"
        else
          # Nag at most once per REQUEST per skill, so a long feature does not
          # repeat the advisory on every file it touches - but a later request
          # that still hasn't read the skill is warned again. Keying this to the
          # session instead silently cancelled the rule this gate exists for.
          SEEN="$STATE_DIR/$SESSION.skillgate.$SKILL"
          if [ "$(cat "$SEEN" 2>/dev/null)" != "req-${START:-0}" ]; then
            printf '%s' "req-${START:-0}" > "$SEEN" 2>/dev/null || true
            add_msg warn "$MSG"
          fi
        fi
      fi
    fi
  fi
fi

# ---------------------------------------------------------------- gate 2
if [ "$CP_MODE" != "off" ] && printf '%s' "$FILE_PATH" | grep -qE "$(code_ext)"; then
  # Only the workflows that actually document a CHECKPOINT this way. If none was
  # ever invoked in this transcript, the edit is out of scope entirely (a direct
  # edit outside any workflow, or a technical skill invoked on its own).
  WORKFLOWS="$(jq_cfg '.checkpoint_gate.workflows[]?' 'feature-development
bug-fix
refactor')"
  WF_PATTERN="$(printf '%s' "$WORKFLOWS" | paste -sd'|' -)"

  if [ -n "$WF_PATTERN" ]; then
    WF_START="$(last_line_matching "$TRANSCRIPT" "$(skill_ref_pattern "$WF_PATTERN")")"
    if [ -n "$WF_START" ]; then   # inside a gated workflow
      HEADER="$(jq_cfg '.checkpoint_gate.header' 'Checkpoint')"
      # The exact call the skills are instructed to make: an AskUserQuestion
      # tool_use whose question carries this literal header, case-insensitive.
      # Each transcript line is one complete JSON event, so both fields land on
      # the same line.
      if ! transcript_tail_from "$TRANSCRIPT" "$WF_START" \
           | grep -qiE "\"name\"[[:space:]]*:[[:space:]]*\"AskUserQuestion\".*\"header\"[[:space:]]*:[[:space:]]*\"${HEADER}\""; then
        MSG="[checkpoint-gate] \`$REL\` is being edited, but no \`AskUserQuestion\` with header \"$HEADER\" was seen since this workflow started. Present the proposal/fix direction and ask for confirmation via \`AskUserQuestion\` (header exactly \"$HEADER\") before writing code - never proceed on the assumption that presenting is the same as confirming."
        if [ "$CP_MODE" = "block" ]; then
          add_msg block "$MSG"
        else
          # Once per workflow RUN, not once per session: a second feature in the
          # same session gets its own warning rather than inheriting the silence.
          SEEN="$STATE_DIR/$SESSION.checkpointgate"
          if [ "$(cat "$SEEN" 2>/dev/null)" != "wf-$WF_START" ]; then
            printf '%s' "wf-$WF_START" > "$SEEN" 2>/dev/null || true
            add_msg warn "$MSG"
          fi
        fi
      fi
    fi
  fi
fi

# ---------------------------------------------------------------- report
# A deny carries a single reason, so when one gate blocks and the other only
# warns, both go in - the reader needs to fix everything before retrying.
if [ -n "$BLOCK_MSG" ]; then
  jq -nc --arg r "$BLOCK_MSG${WARN_MSG:+
$WARN_MSG}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $r
    }
  }'
  exit 0
fi

[ -n "$WARN_MSG" ] && warn "$WARN_MSG"
exit 0
