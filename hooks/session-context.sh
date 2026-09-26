#!/usr/bin/env bash
# SessionStart - inject the routing + self-check rules that the skill library
# depends on but cannot enforce on its own.
#
# On SessionStart, stdout is shown to Claude as plain text. Keep it short: this
# cost is paid once per session, but it is paid every session.

. "${0%/*}/common.sh" || exit 0

# Once per session is the right cadence for this, and SessionStart is the only
# hook that runs exactly that often.
prune_state

[ "$(mode_of session_context warn)" = "off" ] && exit 0

# Nothing is injected into a project that did not opt in: a user-scope install
# reaches every repository on the machine, most of which never asked for these
# rules. project-setup opts a project in.
project_opted_in || exit 0

# General engineering/style guidelines - one team's conventions, off unless a
# project turns them on in .claude/quality-check.config.json:
# {"session_context":{"general_guidelines":true}}.
if [ "$(jq_cfg '.session_context.general_guidelines' false)" = "true" ]; then
  cat <<'TXT'
[adk-sdlc] General Guidelines:
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

# Gate each rule on the skill it actually describes, not on one skill standing in
# for the whole kit. Announcing a rule whose skill isn't installed here is noise;
# worse, using one skill's presence as the proxy for all of them means removing or
# renaming that one silently takes the unrelated rules down with it, with no error
# anywhere. quality-gate.sh already gates on the skill it needs - same idea here.
ROUTER="$(resolve_skill workflow-router)"
REVIEW_SKILL="$(jq_cfg '.quality_gate.review_skill' 'code-review-skill')"
REVIEW="$(resolve_skill "$REVIEW_SKILL")"

# The SKILL.md-read and CHECKPOINT rules are enforced by hooks carried in the
# orchestrators' own frontmatter, so they apply as soon as any orchestrator is here.
ORCHESTRATORS=""
for s in feature-development bug-fix refactor; do
  [ -n "$(resolve_skill "$s")" ] && { ORCHESTRATORS=1; break; }
done

# None of the kit's skills resolve here - stay quiet rather than describe rules
# that nothing will enforce.
[ -n "${ROUTER}${ORCHESTRATORS}${REVIEW}" ] || exit 0

echo "[adk-sdlc] Rules enforced by hooks in this project:"

[ -n "$ROUTER" ] && cat <<'TXT'
- Any request to WRITE OR CHANGE code starts at the `workflow-router` skill, which classifies it and
  hands off to `feature-development` / `bug-fix` / `refactor`. Pure questions and read-only
  exploration skip this.
TXT

[ -n "$ORCHESTRATORS" ] && cat <<'TXT'
- Before editing a file that a technical skill owns, Read that skill's SKILL.md in full, within the
  scope of the CURRENT request (a read from an earlier request does not count).
- Inside `feature-development`/`bug-fix`/`refactor`, a CHECKPOINT is not satisfied by presenting a
  proposal - it requires an actual `AskUserQuestion` call with `header` set exactly to
  `"Checkpoint"`. A PreToolUse hook checks the transcript for this before Step 3/4 may write code.
TXT

[ -n "$REVIEW" ] && cat <<TXT
- Before reporting any code change done, run the \`$REVIEW_SKILL\` self-check on the diff and fix
  severe findings. A Stop hook checks that the skill was read after your last code edit.
TXT

# The last conditional above may be false; never let that become the hook's exit code.
exit 0
