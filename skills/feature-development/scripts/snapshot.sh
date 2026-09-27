#!/usr/bin/env bash
# snapshot.sh - a commit of the working tree as it is, for the next wave of
# parallel units to branch from, without touching the user's branch or index.
#
#   snapshot.sh take <name>   print the sha of a commit holding the working tree
#                             (tracked changes and untracked, non-ignored files) on
#                             top of HEAD, kept alive by refs/adk/waves/<name>
#   snapshot.sh drop          delete every refs/adk/waves/* ref this workflow made
#
# Units in wave 2 depend on wave 1's code, which sits uncommitted in the working
# tree - the workflow never commits on the user's branch. A worktree can only
# start from a commit, so this makes one that no branch points to: the files go
# through a temporary index (the user's staging area is left exactly as it was),
# `git commit-tree` records them with HEAD as the parent, and a private ref keeps
# the commit from being garbage-collected until `drop`.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

case "${1:-}" in
  take)
    name="${2:?usage: snapshot.sh take <name>}"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    index="$(git rev-parse --git-path index)"
    [ -f "$index" ] && cp "$index" "$tmp/index"
    GIT_INDEX_FILE="$tmp/index" git add -A -- . ':(exclude).claude/worktrees' ':(exclude).claude/state'
    tree="$(GIT_INDEX_FILE="$tmp/index" git write-tree)"
    sha="$(git commit-tree "$tree" -p HEAD -m "adk: snapshot for wave $name (not on any branch)")"
    git update-ref "refs/adk/waves/$name" "$sha"
    echo "$sha"
    ;;
  drop)
    git for-each-ref --format='%(refname)' refs/adk/waves/ | while read -r ref; do
      git update-ref -d "$ref"
    done
    ;;
  *)
    echo "usage: snapshot.sh take <name> | drop" >&2
    exit 2
    ;;
esac
