#!/usr/bin/env bash
# SessionStart — inject the routing + self-check rules that the skill library
# depends on but cannot enforce on its own.
#
# On SessionStart, stdout is shown to Claude as plain text. Keep it short: this
# cost is paid once per session, but it is paid every session.

. "${0%/*}/common.sh" || exit 0

[ "$(mode_of session_context warn)" = "off" ] && exit 0

# General engineering/style guidelines — independent of whether this kit's own
# skills are installed here, so this block does not gate on resolve_skill.
# A project can turn just this block off (keeping the kit-specific rules below)
# via .claude/quality-check.config.json: {"session_context":{"general_guidelines":false}}.
if [ "$(jq_cfg '.session_context.general_guidelines' true)" = "true" ]; then
  cat <<'TXT'
[agentic-development-kit] General Guidelines:
- Never use the em dash "—". Use plain dash "-" instead.
- When writing commit messages, NEVER auto-add your agent name as co-author.
- Never manually modify CHANGELOG.md files or any files that are marked as auto-generated.
- When writing or substantially editing long Markdown files, put each full sentence on its own line.
  Preserve normal Markdown structure, but avoid wrapping multiple sentences onto one physical line.
- When making technical decisions, do not give much weight to development cost. Instead, prefer
  quality, simplicity, robustness, scalability, and long term maintainability.
- When doing bug fixes, always start with reproducing the bug in an E2E setting as closely aligned
  with how an end user would experience it. This makes sure you find the real problem so your fix
  will actually solve it.
- When end-to-end testing a product, be picky about the UI you see and be obsessed with pixel
  perfection. If something clearly looks off, even if it is not directly related to what you are
  doing, try to get it fixed alongside it.
- Apply that same high standard to engineering excellence: lint, test failures, and test flakiness.
  If you see one, even if it is not caused by what you are working on right now, still get it fixed.
TXT
fi

# Only speak up about the kit's own rules if the skill library is actually installed here.
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
