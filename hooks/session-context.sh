#!/usr/bin/env bash
# SessionStart — inject the routing + self-check rules that the skill library
# depends on but cannot enforce on its own.
#
# On SessionStart, stdout is shown to Claude as plain text. Keep it short: this
# cost is paid once per session, but it is paid every session.

. "${0%/*}/common.sh" || exit 0

[ "$(mode_of session_context warn)" = "off" ] && exit 0

# Only speak up if the skill library is actually installed here.
[ -n "$(resolve_skill workflow-router)" ] || exit 0

REVIEW_SKILL="$(jq_cfg '.quality_gate.review_skill' 'code-review-skill')"

cat <<TXT
[agentic-development-kit] Rules enforced by hooks in this project:
- Any request to WRITE OR CHANGE code starts at the \`workflow-router\` skill, which classifies it and
  hands off to \`feature-development\` / \`bug-fix\` / \`refactor\`. Pure questions and read-only
  exploration skip this.
- Before editing a file that a technical skill owns, Read that skill's SKILL.md in full, within the
  scope of the CURRENT request (a read from an earlier request does not count).
- Inside \`feature-development\`/\`bug-fix\`/\`refactor\`, a CHECKPOINT is not satisfied by presenting a
  proposal — it requires an actual \`AskUserQuestion\` call with \`header\` set exactly to
  \`"Checkpoint"\`. A PreToolUse hook checks the transcript for this before Step 3/4 may write code.
- Before reporting any code change done, run the \`$REVIEW_SKILL\` self-check on the diff and fix
  severe findings, then record it with the mark-reviewed hook. A Stop hook checks this.
TXT
