#!/usr/bin/env bash
# PreToolUse (Edit|Write|MultiEdit|NotebookEdit), for unit-implementer only - keeps
# a unit inside its lane as it works, not only when its patch is applied.
#
# A unit owns the paths in its ticket's `files`; other units are writing the rest
# at the same moment, in their own worktrees. The scope check when the lead
# applies a unit's patch catches a stray edit after the work is done. This stops
# it at the first write, while the unit can still report the need in
# `outside_files_needed` instead of building on it.
#
# The lane is written by the unit itself in its Step 0: one path per line (a path
# ending in / covers everything under it) in `adk-lane` in its worktree's own git
# directory, where it is never committed, never shows in `git status`, and goes
# away with the worktree.
#
# It runs as a plugin hook, not from the agent's frontmatter: Claude Code does not
# run hooks declared in a plugin agent's frontmatter. The hook input names the
# calling agent (`agent_type`), so every other caller - the lead, other agents -
# passes straight through.
#
# Bash can still write files; this guards the edit tools, which is where the work
# is done. The apply-time scope check in parallel-units.md stays as the backstop.
#
# `mode.lane_guard`: block (default) denies the write with the reason; warn lets
# it through with the reason; off disables it.

. "${0%/*}/common.sh" || exit 0

case "$(jq_in '.agent_type')" in
  *unit-implementer) ;;
  *) exit 0 ;;
esac

MODE="$(mode_of lane_guard block)"
[ "$MODE" = "off" ] && exit 0

FILE_PATH="$(jq_in '.tool_input.file_path' "$(jq_in '.tool_input.notebook_path')")"
[ -n "$FILE_PATH" ] || exit 0
CWD="$(jq_in '.cwd' "$PWD")"
case "$FILE_PATH" in /*) ;; *) FILE_PATH="$CWD/$FILE_PATH" ;; esac

WT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$WT" ] || exit 0
# Resolve symlinks (/tmp on macOS) so a path and the worktree compare equal.
WT="$(cd "$WT" && pwd -P)"
# The file may not exist yet, nor its directory: resolve the deepest one that does.
DIR="$(dirname "$FILE_PATH")"
while [ ! -d "$DIR" ]; do DIR="$(dirname "$DIR")"; done
ABS="$(cd "$DIR" && pwd -P)${FILE_PATH#"$DIR"}"

LEAD="$(cd "$PROJECT_DIR" 2>/dev/null && pwd -P || true)"

deny() {
  if [ "$MODE" = "block" ]; then
    jq -nc --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
    exit 0
  fi
  warn "$1"
}

case "$ABS" in
  "$WT"/*) REL="${ABS#"$WT"/}" ;;
  *)
    if [ -n "$LEAD" ] && [ "$LEAD" != "$WT" ] && case "$ABS" in "$LEAD"/*) true ;; *) false ;; esac; then
      deny "[lane-guard] $FILE_PATH is in the lead agent's working tree, not your worktree ($WT). Write the same relative path under your worktree: the lead applies your commit to its tree itself."
    fi
    exit 0
    ;;
esac

LANE="$(git -C "$WT" rev-parse --absolute-git-dir 2>/dev/null)/adk-lane"
if [ ! -s "$LANE" ]; then
  deny "[lane-guard] No lane recorded for this unit. Step 0: write the unit's \`files\`, one per line, to \"\$(git rev-parse --absolute-git-dir)/adk-lane\", then retry."
fi

while IFS= read -r entry || [ -n "$entry" ]; do
  entry="${entry#./}"
  [ -n "$entry" ] || continue
  case "$entry" in
    */) case "$REL" in "$entry"*) exit 0 ;; esac ;;
    *) [ "$REL" = "$entry" ] && exit 0 ;;
  esac
done < "$LANE"

deny "[lane-guard] \`$REL\` is outside this unit's files ($(grep -v '^[[:space:]]*$' "$LANE" | sed 's/^/`/; s/$/`/' | paste -sd, - | sed 's/,/, /g')). Another unit may be writing it right now. Do not edit it: report what it needs in \`outside_files_needed\` - the lead makes that change after applying every unit - or, if the unit cannot be built without it, stop with a \`plan_mismatch\`."
