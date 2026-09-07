#!/usr/bin/env bash
# PreToolUse (Read) - the routing gate from the Spotify "Portal" write-up this
# kit borrows: a whole-file Read past a line threshold is intercepted before it
# lands in the expensive model's context, and redirected to the `bulk-reader`
# Task subagent (cheap model, own context, returns only the bullets that answer
# a specific question).
#
# Why a hook and not a written instruction: a rule living in a skill or
# CLAUDE.md is advisory - the model reads it, agrees, and still does the full
# Read when it judges that faster. This has to sit in front of the tool call
# to actually change what happens, the same reasoning that put skill_gate and
# checkpoint_gate here instead of in prose.
#
# What is deliberately let through, no delegation attempted:
# - A TARGETED read (`offset` and/or `limit` set on the Read call). Claude
#   already knows which section it needs; wrapping that in a subagent round
#   trip (10-30s) would cost more than it saves.
# - Anything at or under the line threshold.
# - A file resolve_agent can't find `bulk-reader` for (nothing installed to
#   delegate to - see common.sh's fail-open rule).
# - Any Read made from INSIDE a Task subagent. Hooks apply inside subagents too
#   (a plugin PreToolUse hook fires for every tool call a subagent makes, not
#   just the main thread), and this gate exists to keep a large file out of the
#   MAIN thread's expensive, persistent context. A subagent's context is
#   disposable - it is discarded the moment the agent reports back, so the file
#   never reaches the caller either way and there is no saving left to make.
#   Delegating from there would only add a round trip.
#
#   That is also the difference between a rule and a trap: not one agent in this
#   plugin carries the `Task` tool (`bulk-reader` least of all - it has only
#   `Read`, and reading the whole file IS its job). Without this exemption,
#   `block` mode denies any subagent's read of a large file and tells it to
#   dispatch a delegate it has no way to dispatch.
#
#   `agent_type`/`agent_id` on the hook's stdin JSON identify the running
#   subagent when the call originates inside one, and are absent on the main
#   thread. A session started with `--agent` also carries `agent_type`, which
#   turns this gate off for that session - the fail-open direction, consistent
#   with every other hook here.

. "${0%/*}/common.sh" || exit 0

MODE="$(mode_of bulk_read_gate warn)"
[ "$MODE" = "off" ] && exit 0

# Inside a subagent - either field being present is enough to say so.
[ -n "$(jq_in '.agent_type')" ] && exit 0
[ -n "$(jq_in '.agent_id')" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path')"
[ -n "$FILE_PATH" ] || exit 0
[ -f "$FILE_PATH" ] || exit 0

# A targeted read: Claude already named the section it wants. Let it through.
OFFSET="$(jq_in '.tool_input.offset')"
LIMIT="$(jq_in '.tool_input.limit')"
[ -n "$OFFSET" ] && exit 0
[ -n "$LIMIT" ] && exit 0

AGENT_MD="$(resolve_agent bulk-reader)"
[ -n "$AGENT_MD" ] || exit 0   # nothing to delegate to - nothing to enforce

REL="${FILE_PATH#"$PROJECT_DIR"/}"

EXCLUDE="$(jq_cfg '.bulk_read_gate.exclude[]?' '')"
if [ -n "$EXCLUDE" ]; then
  while IFS= read -r pattern; do
    [ -n "$pattern" ] || continue
    printf '%s' "$REL" | grep -Eq "$pattern" && exit 0
  done <<< "$EXCLUDE"
fi

THRESHOLD="$(jq_cfg '.bulk_read_gate.line_threshold' 350)"
LINES="$(wc -l < "$FILE_PATH" 2>/dev/null | tr -d '[:space:]')"
[ -n "$LINES" ] || exit 0
[ "$LINES" -gt "$THRESHOLD" ] 2>/dev/null || exit 0

MSG="[bulk-read-gate] \`$REL\` is $LINES lines (over the $THRESHOLD-line threshold) and this is a whole-file read, not a targeted one. Dispatch the \`bulk-reader\` Task subagent instead: pass it the file path and the specific question you need answered, and use only the bullets it returns. If you genuinely need the full file verbatim (about to edit most of it, or the question can't be scoped), re-issue the Read with an \`offset\`/\`limit\` that targets the section you need, or state why the whole file is required."

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

warn "$MSG"
