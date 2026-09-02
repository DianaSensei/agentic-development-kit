#!/usr/bin/env bash
# Stop - the gate that makes code-review-skill's "ALWAYS run this before
# reporting done" actually true.
#
# It does not judge the change; it refuses to let the turn end while
# uncommitted code changes exist that no review has vouched for. Claude clears
# it by running the review skill and then recording the result with
# mark-reviewed.sh - which is self-healing: the block tells it exactly what to
# do, and doing that unblocks it.

. "${0%/*}/common.sh" || exit 0

MODE="$(mode_of quality_gate block)"
[ "$MODE" = "off" ] && exit 0

# Claude Code sets this when the turn is already continuing because of a Stop
# hook. Re-blocking here is how sessions get stuck in a loop.
[ "$(jq_in '.stop_hook_active' false)" = "true" ] && exit 0

HASH="$(code_change_hash)"
[ -n "$HASH" ] || exit 0          # no code changed this turn - nothing to gate

MARKER="$STATE_DIR/reviewed"
[ -f "$MARKER" ] && [ "$(cat "$MARKER" 2>/dev/null)" = "$HASH" ] && exit 0

REVIEW_SKILL="$(jq_cfg '.quality_gate.review_skill' 'code-review-skill')"
[ -n "$(resolve_skill "$REVIEW_SKILL")" ] || exit 0   # skill not installed here

# A session may be held at this gate only so many times. Past that it warns and
# lets go: a quality gate that can trap a session is worse than one that misses.
SESSION="$(jq_in '.session_id' unknown)"
COUNTER="$STATE_DIR/$SESSION.blocks"
COUNT="$(cat "$COUNTER" 2>/dev/null || echo 0)"
MAX="$(jq_cfg '.quality_gate.max_blocks' 2)"

REASON="[quality-gate] Uncommitted code changes have not been reviewed.
Before reporting this work done:
1. Read \`${REVIEW_SKILL}\`'s SKILL.md and run its checklist against the current diff (\`git diff HEAD\`
   plus any untracked files), applying only the per-technology sections the change actually touches.
2. Fix every severe finding - a self-review is less objective than an independent one, which is a
   reason to be stricter with it, not more lenient.
3. Record that it happened by running: \`${PLUGIN_ROOT}/hooks/mark-reviewed.sh\`
Editing code afterwards invalidates the record, which is intended: the next review covers the new state."

# Optional Step-5 artifact checks, off by default - a small refactor legitimately
# produces neither file, so this only fires where a project opts in.
ROOT="$(git_repo_root)"
EXTRA=""
if [ "$(jq_cfg '.quality_gate.require_changelog' false)" = "true" ] \
   && [ -n "$ROOT" ] && [ -z "$(ls -A "$ROOT/docs/changelog" 2>/dev/null)" ]; then
  EXTRA="$EXTRA
Also missing: \`docs/changelog/<slug>.md\` (workflow Step 5 - knowledge capture)."
fi
if [ "$(jq_cfg '.quality_gate.require_experience_log' false)" = "true" ] \
   && [ -n "$ROOT" ] && [ ! -f "$ROOT/docs/knowledge/experience-log.md" ]; then
  EXTRA="$EXTRA
Also missing: \`docs/knowledge/experience-log.md\` (workflow Step 5 - cumulative, append-only)."
fi

if [ "$MODE" != "block" ] || [ "$COUNT" -ge "$MAX" ] 2>/dev/null; then
  # Warn once per distinct state of the change, not once per turn: the gate stays
  # unsatisfied across every following turn, and repeating the same notice each
  # time trains the reader to skip it.
  WARNED="$STATE_DIR/warned"
  [ "$(cat "$WARNED" 2>/dev/null)" = "$HASH" ] && exit 0
  printf '%s' "$HASH" > "$WARNED" 2>/dev/null || true
  warn "$REASON$EXTRA"
fi

echo $((COUNT + 1)) > "$COUNTER" 2>/dev/null || true
printf '%s%s\n' "$REASON" "$EXTRA" >&2
exit 2
