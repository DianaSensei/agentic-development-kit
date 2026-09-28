#!/usr/bin/env bash
# PreToolUse (Agent|Task) - the rules for handing a unit down are read, and the
# prompt carries what the unit and the lane guard need, before any unit starts; and
# a code-writing Tier-2 specialist is not dispatched around them.
#
# parallel-units.md holds the rules that keep parallel units safe: snapshot the
# tree so a later wave sees the earlier one, pass the ticket inline (the plan is
# not in the unit's worktree), pick the model by the ticket's tier, and never
# commit on the user's branch. A headless run that went straight to dispatch
# without reading it broke all four. The skill says "read it in full before
# dispatching"; this is the mechanism behind that sentence.
#
# Checked:
#   - a Read of feature-development's references/parallel-units.md in this session;
#   - the prompt's literal labels: `lane:` with a JSON array of the unit's files
#     (lane-guard.sh reads it), `base_commit:`, and `ticket:` - or `candidate:` for
#     a compare-builds candidate, which has no ticket yet.
#
# Also: within feature-development, a direct dispatch of a specialist named in
# `dispatch_gate.route_through_units` (default java-ecosystem-engineer,
# tauri-react-engineer) is denied - its task goes through a unit-implementer.
#
# `mode.dispatch_gate`: block (default) denies the dispatch with what is missing;
# warn lets it through with the reason; off disables it.

. "${0%/*}/common.sh" || exit 0

TYPE="$(jq_in '.tool_input.subagent_type')"
MODE="$(mode_of dispatch_gate block)"
[ "$MODE" = "off" ] && exit 0
PROMPT="$(jq_in '.tool_input.prompt')"
TRANSCRIPT="$(jq_in '.transcript_path')"

deny() {
  if [ "$MODE" = "block" ]; then
    jq -nc --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
    exit 0
  fi
  warn "$1"
}

# A Tier-2 specialist that writes code, dispatched directly while feature-development runs, would write
# into the lead's tree with no ticket, no lane and its own fixed model. Within the workflow its task
# goes through a unit-implementer that reads the specialist's file (`specialist`, `specialist_path`).
# Outside the workflow - someone asking for the specialist themselves - it is left alone.
case "$TYPE" in
  *unit-implementer) ;;
  *)
    ROUTE="$(jq_cfg '(.dispatch_gate.route_through_units // empty) | join("|")' 'java-ecosystem-engineer|tauri-react-engineer')"
    printf '%s' "${TYPE##*:}" | grep -qxE "$ROUTE" 2>/dev/null || exit 0
    [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] || exit 0
    if jq -r 'select(.type == "assistant") | .message.content[]? | select(.type == "tool_use" and .name == "Skill")
              | .input.skill // empty' "$TRANSCRIPT" 2>/dev/null | grep -q 'feature-development$' \
       || grep -qE '<command-name>/?[^<]*feature-development' "$TRANSCRIPT" 2>/dev/null; then
      deny "[dispatch-gate] Not dispatching \`$TYPE\` directly: in feature-development its task goes through a \`unit-implementer\` with \`specialist: ${TYPE##*:}\` and \`specialist_path\` - the unit reads the specialist's file and works its way, with its ticket, lane, worktree and the model its tier earns. Or build it yourself, reading that file. (feature-development SKILL.md, \"Tier-2 specialists\".)"
    fi
    exit 0
    ;;
esac

MISSING=""

if [ -z "$TRANSCRIPT" ] || ! jq -r 'select(.type == "assistant") | .message.content[]?
      | select(.type == "tool_use" and .name == "Read") | .input.file_path // empty' "$TRANSCRIPT" 2>/dev/null \
    | grep -q 'feature-development/references/parallel-units\.md$'; then
  MISSING="$MISSING
- read feature-development's \`references/parallel-units.md\` in full: the snapshot between waves, the
  dispatch prompt, the model by ticket tier, and never committing on the user's branch are all there"
fi

LANE_LINE="$(printf '%s\n' "$PROMPT" | sed -n 's/^[[:space:]`*-]*lane[`*]*:[[:space:]]*//p' | head -n 1)"
if [ -z "$LANE_LINE" ] || [ "$(printf '%s' "$LANE_LINE" | jq -r 'if type == "array" and length > 0 then "ok" else "" end' 2>/dev/null)" != "ok" ]; then
  MISSING="$MISSING
- a \`lane:\` line holding the unit's \`files\` as a JSON array, e.g. \`lane: [\"src/shop/orders.py\", \"scripts/\"]\` -
  the lane guard reads it to keep the unit inside its files"
fi
printf '%s\n' "$PROMPT" | grep -qE '(^|[^[:alnum:]_])base_commit[`*]*:' || MISSING="$MISSING
- \`base_commit:\` - HEAD for wave 1, the snapshot for a later wave (\`scripts/snapshot.sh take <n>\`)"
printf '%s\n' "$PROMPT" | grep -qE '(^|[^[:alnum:]_])(ticket|candidate)[`*]*:' || MISSING="$MISSING
- \`ticket:\` - the unit's ticket from the plan's \`## Tickets\`, inline: the plan is not in the unit's worktree"

[ -n "$MISSING" ] || exit 0

deny "[dispatch-gate] Not dispatching this unit yet:$MISSING"
