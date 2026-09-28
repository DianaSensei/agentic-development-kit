#!/usr/bin/env bash
# PostToolUse (Bash), for unit-implementer only - the lane holds for shell writes too.
#
# lane-guard.sh stops an Edit or Write outside a unit's lane before it happens, but
# a shell command writes files the edit tools never see: `sed -i`, a redirect, a
# code generator, a formatter run over the whole tree. Parsing commands to guess
# what they write is a losing game, so this looks at the result instead: after
# every Bash call it asks git what changed in the unit's worktree - tracked edits,
# deletions, new files, and anything committed since the prompt's `base_commit` -
# and names each changed path outside the lane. The command has already run, so it
# cannot be prevented; the unit is told to undo it before it builds on it.
#
# Ignored files (build output, caches, installed dependencies) never show in git
# status, so they never count. The lane and base_commit come from the unit's
# prompt, like lane-guard.sh. It reports once per distinct set of stray paths.
#
# `mode.lane_guard`: block (default) makes Claude act on it (PostToolUse
# decision: block); warn adds it as context; off disables it.

. "${0%/*}/common.sh" || exit 0

case "$(jq_in '.agent_type')" in
  *unit-implementer) ;;
  *) exit 0 ;;
esac

MODE="$(mode_of lane_guard block)"
[ "$MODE" = "off" ] && exit 0

WT="$(git -C "$(jq_in '.cwd' "$PWD")" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$WT" ] || exit 0
LANE="$(unit_lane)"
[ -n "$LANE" ] || exit 0        # lane-guard.sh already said it cannot read the lane

# Everything the unit has changed: uncommitted (including new, untracked files) and
# committed since the base it started from.
CHANGED="$( {
  git -C "$WT" status --porcelain=v1 --untracked-files=all 2>/dev/null | sed 's/^...//; s/.* -> //'
  BASE="$(prompt_label base_commit | tr -d '`"'"'"' ' | cut -c1-40)"
  if [ -n "$BASE" ] && git -C "$WT" rev-parse -q --verify "$BASE^{commit}" >/dev/null 2>&1; then
    git -C "$WT" diff --name-only "$BASE" HEAD 2>/dev/null
  fi
} | sed 's/^"//; s/"$//' | sort -u)"

STRAY=""
while IFS= read -r path; do
  [ -n "$path" ] || continue
  case "$path" in .claude/*) continue ;; esac
  in_lane "$path" "$LANE" || STRAY="$STRAY
$path"
done <<EOF
$CHANGED
EOF
STRAY="${STRAY#
}"
[ -n "$STRAY" ] || exit 0

# Once per distinct set of stray paths, not after every command.
SEEN="$STATE_DIR/lane-bash-$(jq_in '.agent_id')"
KEY="$(printf '%s' "$STRAY" | cksum | cut -d' ' -f1)"
[ "$(cat "$SEEN" 2>/dev/null)" = "$KEY" ] && exit 0
mkdir -p "$STATE_DIR" 2>/dev/null && printf '%s' "$KEY" > "$SEEN" 2>/dev/null || true

LIST="$(printf '%s\n' "$STRAY" | sed 's/^/- `/; s/$/`/')"
MSG="[lane-guard] Your last command changed paths outside this unit's files:
$LIST
Another unit may own them. Undo each before going on - \`git checkout -- <path>\` for an edited file, delete a new one, \`git reset --soft\` a commit that carried one - and report what it needed in \`outside_files_needed\`, or stop with a \`plan_mismatch\` if the unit cannot be built without it. A generated file that belongs in no commit belongs in .gitignore, not your lane."

if [ "$MODE" = "block" ]; then
  jq -nc --arg r "$MSG" '{decision: "block", reason: $r}'
  exit 0
fi
warn "$MSG"
