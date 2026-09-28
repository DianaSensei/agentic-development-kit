#!/usr/bin/env bash
# leftovers.sh - unit worktrees and wave snapshots a stopped run left behind.
#
#   leftovers.sh list          what is there: each unit worktree (branch, its commits
#                              not in HEAD, uncommitted changes) and each snapshot ref
#   leftovers.sh clean         remove what holds nothing: worktrees with no uncommitted
#                              change whose branch has no commit of its own, and the
#                              snapshot refs once no unit worktree is left
#   leftovers.sh clean --all   also remove the rest, keeping the work: uncommitted
#                              changes saved as a patch under .claude/state/leftovers/,
#                              and a branch with commits of its own kept (only its
#                              worktree goes)
#
# A run that is stopped mid-wave - killed, timed out, the session closed - never
# reaches the cleanup in parallel-units.md: its worktrees stay under
# .claude/worktrees/ (locked by Claude Code), their branches stay, and so do the
# refs/adk/waves/* snapshots. Only paths this workflow creates are ever touched:
# worktrees under .claude/worktrees/, and refs/adk/waves/*. Nothing is removed that
# holds work unless --all is given, and then the work is kept.
#
# A unit worktree can belong to a run still going in another session: `list` says
# so, `clean` never removes a worktree with uncommitted changes, and `--all` is for
# when you know no run is going.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
MODE="${1:-list}"
ALL="${2:-}"

units() {
  git worktree list --porcelain | awk '
    /^worktree / { wt = substr($0, 10) }
    /^branch /   { br = substr($0, 8); sub("refs/heads/", "", br) }
    /^$/         { if (wt ~ /\/\.claude\/worktrees\//) print wt "\t" br; wt = ""; br = "" }
    END          { if (wt ~ /\/\.claude\/worktrees\//) print wt "\t" br }'
}

own_commits() {     # commits on the branch that neither HEAD nor a snapshot holds
  [ -n "$1" ] || { echo 0; return; }
  git rev-list --count "$1" --not HEAD $(git for-each-ref --format='%(refname)' refs/adk/waves/) 2>/dev/null || echo 0
}

dirty() { git -C "$1" status --porcelain --untracked-files=all 2>/dev/null | grep -c . || true; }

case "$MODE" in
  list)
    found=0
    while IFS=$'\t' read -r wt br; do
      [ -n "$wt" ] || continue
      found=1
      echo "worktree ${wt#"$ROOT"/}  branch ${br:-<detached>}  own commits $(own_commits "$br")  uncommitted $(dirty "$wt")"
    done < <(units)
    for ref in $(git for-each-ref --format='%(refname)' refs/adk/waves/); do
      found=1; echo "snapshot $ref $(git rev-parse --short "$ref")"
    done
    [ "$found" = 1 ] || echo "Nothing left behind."
    [ "$found" = 0 ] || echo "A worktree can belong to a run still going in another session. 'clean' removes only those that hold nothing."
    ;;
  clean)
    kept=0
    while IFS=$'\t' read -r wt br; do
      [ -n "$wt" ] || continue
      n_own="$(own_commits "$br")"; n_dirty="$(dirty "$wt")"
      if [ "$n_dirty" != 0 ] || [ "$n_own" != 0 ]; then
        if [ "$ALL" != "--all" ]; then
          echo "kept ${wt#"$ROOT"/}: $n_dirty uncommitted, $n_own own commit(s) - 'clean --all' keeps the work and removes the worktree"
          kept=1; continue
        fi
        if [ "$n_dirty" != 0 ]; then
          mkdir -p .claude/state/leftovers
          patch=".claude/state/leftovers/$(basename "$wt").patch"
          git -C "$wt" add -A -N . 2>/dev/null || true
          git -C "$wt" diff --binary HEAD > "$patch"
          echo "saved ${wt#"$ROOT"/}'s uncommitted changes to $patch"
        fi
      fi
      git worktree remove -f -f "$wt"
      if [ -n "$br" ]; then
        if [ "$n_own" = 0 ]; then git branch -D -q "$br"; echo "removed ${wt#"$ROOT"/} and branch $br"
        else echo "removed ${wt#"$ROOT"/}; kept branch $br ($n_own commit(s) of its own)"; fi
      fi
    done < <(units)
    if [ "$kept" = 0 ] && [ -z "$(units)" ]; then
      for ref in $(git for-each-ref --format='%(refname)' refs/adk/waves/); do
        git update-ref -d "$ref"; echo "dropped $ref"
      done
    fi
    git worktree prune
    ;;
  *)
    echo "usage: leftovers.sh list | clean [--all]" >&2
    exit 2
    ;;
esac
