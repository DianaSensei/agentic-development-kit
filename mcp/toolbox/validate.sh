#!/usr/bin/env bash
# Safe-apply helper for editing files in the toolbox MCP's live connections
# directory - snapshot before changing, validate after, roll back on
# failure.
#
# toolbox parses/validates an entire --config-folder as one unit: one file
# with a mistake (a typo'd field, a missing required value, a bad tool type)
# fails the WHOLE server, not just the connection being added - every other
# connection goes down with it, with no useful detail surfaced in `/mcp`
# (see mcp/toolbox/README.md's "Why PostgreSQL, MySQL, and TiDB are
# read-only" section's neighbor, and this repo's own commit history, for how
# expensive that class of bug is to diagnose blind). Use this instead of
# writing/editing a file there directly and hoping.
#
# Usage:
#   validate.sh snapshot <connections-dir>   # save current state before editing
#   validate.sh check    <connections-dir>   # does it still parse cleanly?
#   validate.sh restore  <connections-dir>   # revert to the last snapshot
#
# Typical flow when adding or editing a connection/tool file:
#   1. ./validate.sh snapshot <dir>
#   2. write/edit the file in <dir>
#   3. ./validate.sh check <dir>
#   4a. PASSES -> done; tell the user to reconnect (`/mcp`, or start a new session)
#   4b. FAILS  -> ./validate.sh restore <dir>, read the printed error, fix the
#       file's content, and try again from step 2
#
# Find <connections-dir> with:
#   claude mcp list | grep '^plugin:agentic-development-kit:toolbox' \
#     | grep -oE -- '--config-folder [^ ]+' | awk '{print $2}'

set -u

usage() {
  echo "Usage: $0 {snapshot|check|restore} <connections-dir>" >&2
  exit 2
}

[ $# -eq 2 ] || usage
cmd="$1"
dir="$2"
snapshot_dir="$dir/.validate-snapshot"

# The connections directory may not exist yet (e.g. adding the very first
# connection on a fresh install) - create it rather than requiring it
# pre-exist, so `snapshot` also works as the bootstrap step.
mkdir -p "$dir" 2>/dev/null || { echo "Cannot create or access directory: $dir" >&2; exit 2; }

command -v toolbox >/dev/null 2>&1 || {
  echo "toolbox binary not found on PATH - install it first (see mcp/toolbox/README.md)." >&2
  exit 2
}

case "$cmd" in
  snapshot)
    rm -rf "$snapshot_dir"
    mkdir -p "$snapshot_dir"
    find "$dir" -maxdepth 1 -type f -name '*.yaml' ! -name '*.upstream' -exec cp {} "$snapshot_dir/" \;
    n="$(find "$snapshot_dir" -maxdepth 1 -type f | wc -l | tr -d ' ')"
    echo "Snapshot saved ($n file(s)) at $snapshot_dir."
    ;;

  check)
    out="$(mktemp)"
    toolbox --config-folder "$dir" --stdio < /dev/null > "$out" 2>&1 &
    pid=$!
    sleep 3
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null

    if grep -q ' ERROR ' "$out"; then
      echo "FAIL - toolbox could not parse \"$dir\":" >&2
      grep -A5 ' ERROR ' "$out" >&2
      rm -f "$out"
      exit 1
    fi
    if ! grep -q 'Initialized [0-9]* sources' "$out"; then
      echo "FAIL - toolbox did not confirm it initialized. Full output:" >&2
      cat "$out" >&2
      rm -f "$out"
      exit 1
    fi
    echo "OK - $(grep -o 'Initialized [0-9]* sources[^"]*' "$out" | head -1)."
    rm -f "$out"
    ;;

  restore)
    [ -d "$snapshot_dir" ] || { echo "No snapshot found at $snapshot_dir - nothing to restore." >&2; exit 1; }
    find "$dir" -maxdepth 1 -type f -name '*.yaml' ! -name '*.upstream' -delete
    find "$snapshot_dir" -maxdepth 1 -type f -exec cp {} "$dir/" \;
    echo "Restored $dir from snapshot."
    ;;

  *)
    usage
    ;;
esac
