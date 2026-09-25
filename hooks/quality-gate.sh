#!/usr/bin/env bash
# Stop - the gate that makes code-review-skill's "ALWAYS run this before
# reporting done" actually true.
#
# It does not judge the change; it refuses to let the turn end while
# uncommitted code changes exist that no review has vouched for. It clears
# itself once the transcript shows the review skill loaded after the last code
# edit - self-healing: the block tells Claude exactly what to do, and doing it
# unblocks it. mark-reviewed.sh records a review by hand, outside a session.

. "${0%/*}/common.sh" || exit 0

# Defaults to warn, like every other gate here. This is the only gate that can
# halt a turn, so a missing or malformed config must not be what turns it into a
# blocker - see the FAIL OPEN rule at the top of common.sh. Set
# `mode.quality_gate` to "block" in quality-check.config.json to make it binding.
MODE="$(mode_of quality_gate warn)"
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

SESSION="$(jq_in '.session_id' unknown)"
COUNTER="$STATE_DIR/$SESSION.blocks"

# The review is visible in the transcript: the review skill was loaded after the
# last edit to a code file. Record it here, so clearing the gate never depends
# on Claude running a script from the plugin directory - which lies outside the
# project and needs a permission a narrow allowlist or a non-interactive
# session does not have. Hooks run outside Claude's permission system.
TRANSCRIPT="$(jq_in '.transcript_path')"
if [ -f "$TRANSCRIPT" ]; then
  REVIEW_LINE="$(last_line_matching "$TRANSCRIPT" "$(skill_ref_pattern "$REVIEW_SKILL")")"
  EDIT_LINE="$(last_code_edit_line "$TRANSCRIPT")"
  if [ -n "$REVIEW_LINE" ] && [ "$REVIEW_LINE" -gt "${EDIT_LINE:-0}" ]; then
    printf '%s' "$HASH" > "$MARKER" 2>/dev/null || true
    rm -f "$COUNTER" 2>/dev/null || true
    exit 0
  fi
fi

# A session may be held at this gate only so many times. Past that it warns and
# lets go: a quality gate that can trap a session is worse than one that misses.
COUNT="$(cat "$COUNTER" 2>/dev/null || echo 0)"
MAX="$(jq_cfg '.quality_gate.max_blocks' 2)"

REASON="[quality-gate] Uncommitted code changes have not been reviewed.
Before reporting this work done:
1. Read \`${REVIEW_SKILL}\`'s SKILL.md and run its checklist against the current diff (\`git diff HEAD\`
   plus any untracked files), applying only the per-technology sections the change actually touches.
2. Fix every severe finding - a self-review is less objective than an independent one, which is a
   reason to be stricter with it, not more lenient.
Reading the skill after your last code edit is what clears this gate - nothing else to run. Editing
code afterwards invalidates it, which is intended: the next review covers the new state."

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
