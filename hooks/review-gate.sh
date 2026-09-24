#!/usr/bin/env bash
# Stop - an independent review may not end before it has read the checklist it
# grades against.
#
# independent-review Step 4 says to Read code-review-skill's SKILL.md, and its
# summary ends with a "Checklists applied" line. Both are honour-system: in a
# test run the reviewer skipped the read and still wrote "Checklists applied:
# code-review-skill". This checks the transcript for the read itself.
#
# Registered globally (hooks.json) rather than in the skill's frontmatter:
# frontmatter hooks only register when a skill is invoked through the Skill
# tool, and the CI workflow's reviewer may only Read the SKILL.md. For the same
# reason the CI workflow also registers it through `settings`, in case the plugin
# itself is not loaded there. Running twice is harmless - see the lock below.

. "${0%/*}/common.sh" || exit 0

# ADK_REVIEW_GATE lets CI make this one gate binding without QUALITY_CHECK_MODE,
# which would switch every other gate to block as well.
MODE="${ADK_REVIEW_GATE:-$(mode_of review_gate warn)}"
[ "$MODE" = "off" ] && exit 0

# Claude Code sets this when the turn is already continuing because of a Stop
# hook. Re-blocking here is how sessions get stuck in a loop.
[ "$(jq_in '.stop_hook_active' false)" = "true" ] && exit 0

TRANSCRIPT="$(jq_in '.transcript_path')"
[ -f "$TRANSCRIPT" ] || exit 0   # cannot verify anything - fail open

# The most recent independent review in this session - invoked as a skill or its
# SKILL.md read directly. None: this session is not reviewing, nothing to gate.
START="$(last_line_matching "$TRANSCRIPT" "$(skill_ref_pattern independent-review)")"
[ -n "$START" ] || exit 0

CHECKLIST="$(jq_cfg '.quality_gate.review_skill' 'code-review-skill')"
transcript_tail_from "$TRANSCRIPT" "$START" \
  | grep -qE "$(skill_ref_pattern "$CHECKLIST")" && exit 0

# Speak once per review run. mkdir is atomic, so when the gate is registered
# twice (plugin hooks.json and CI settings) exactly one instance acts, and a
# review that stops again after the block is let go rather than trapped.
SESSION="$(jq_in '.session_id' unknown)"
mkdir "$STATE_DIR/$SESSION.reviewgate.$START" 2>/dev/null || exit 0

CHECKLIST_MD="$(resolve_skill "$CHECKLIST")"
REASON="[review-gate] This independent review has not read \`$CHECKLIST\`, the checklist its findings are graded against (independent-review Step 1).
Read \`${CHECKLIST_MD:-$CHECKLIST/SKILL.md}\` in full now, plus the SKILL.md of any technical skill that owns a changed file. Re-check the diff against them, update the findings and counts if anything changes, and make the *Checklists applied* line list only what was actually read."

if [ "$MODE" != "block" ]; then
  warn "$REASON"
fi

printf '%s\n' "$REASON" >&2
exit 2
