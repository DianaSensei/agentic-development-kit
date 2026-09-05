#!/usr/bin/env bash
# Safe-apply helper for editing files in the toolbox MCP's live connections
# directory - snapshot before changing, validate after, roll back on
# failure.
#
# toolbox parses/validates an entire --config-folder as one unit: one file
# with a mistake (a typo'd field, a missing required value, a bad tool type)
# fails the WHOLE server, not just the connection being added - every other
# connection goes down with it, with no useful detail surfaced in `/mcp`
# (see mcp/toolbox/README.md's "Why the SQL templates default to read-only"
# section's neighbor, and this repo's own commit history, for how expensive
# that class of bug is to diagnose blind). Use this instead of writing/editing
# a file there directly and hoping.
#
# Usage:
#   validate.sh snapshot <connections-dir>   # save current state before editing
#   validate.sh check    <connections-dir>   # does the folder still start toolbox cleanly?
#   validate.sh restore  <connections-dir>   # revert to the last snapshot
#
# `check` starts real toolbox against the folder, which means it makes a live
# connection attempt to EVERY configured source, not just the one you just
# changed - and toolbox does not time out a hung connection on its own (a
# blackholed host waits indefinitely). So `check` can FAIL for a reason that
# has nothing to do with the file you edited: an unrelated, already-working
# connection that happens to be slow or briefly unreachable right now looks
# identical to a broken config. If `check` fails, read the printed error
# before assuming your edit is at fault, and before running `restore` on a
# change that might be perfectly fine.
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
    find "$dir" -maxdepth 1 -type f \( -name '*.yaml' -o -name '*.yml' \) -exec cp {} "$snapshot_dir/" \;
    n="$(find "$snapshot_dir" -maxdepth 1 -type f | wc -l | tr -d ' ')"
    echo "Snapshot saved ($n file(s)) at $snapshot_dir."
    ;;

  check)
    out="$(mktemp)"
    toolbox --config-folder "$dir" --stdio < /dev/null > "$out" 2>&1 &
    pid=$!

    # toolbox connects to every configured source at startup and does not
    # time out a hung connection on its own - a blackholed host waits
    # indefinitely (verified: 25s+ with no self-timeout). So SOME ceiling is
    # required or this can hang forever, but a fixed short sleep raced real
    # network I/O and produced a false FAIL for a source that was merely slow
    # to connect. Poll instead: return the moment toolbox says ERROR or
    # Initialized, so the common case (a syntax mistake, or a fast healthy
    # connection) is still fast; only a source that's actually stuck consumes
    # the full ceiling.
    waited=0
    interval=0.2
    ceiling=20
    while kill -0 "$pid" 2>/dev/null; do
      grep -qE ' ERROR |Initialized [0-9]+ sources' "$out" 2>/dev/null && break
      sleep "$interval"
      waited="$(awk -v w="$waited" -v i="$interval" 'BEGIN{print w+i}')"
      awk -v w="$waited" -v c="$ceiling" 'BEGIN{exit !(w>=c)}' && break
    done

    # Snapshot the output at the moment we stopped waiting, BEFORE sending any
    # signal. toolbox logs its own "context canceled" error in response to the
    # kill below, which would otherwise be misread as a config error rather
    # than an artifact of us giving up - judge only what toolbox had actually
    # said on its own by this point.
    snapshot="$(cat "$out")"
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    rm -f "$out"

    if printf '%s' "$snapshot" | grep -q ' ERROR '; then
      echo "FAIL - toolbox reported an error starting \"$dir\":" >&2
      printf '%s' "$snapshot" | grep -A5 ' ERROR ' >&2
      exit 1
    fi
    if ! printf '%s' "$snapshot" | grep -q 'Initialized [0-9]* sources'; then
      echo "FAIL - toolbox did not finish starting within ${ceiling}s. This usually means a configured source is slow or currently unreachable, not necessarily that your edit is wrong - check connectivity to your databases, or retry, before assuming this failure and running restore. Output so far:" >&2
      printf '%s\n' "$snapshot" >&2
      exit 1
    fi
    echo "OK - $(printf '%s' "$snapshot" | grep -o 'Initialized [0-9]* sources[^"]*' | head -1)."
    ;;

  restore)
    [ -d "$snapshot_dir" ] || { echo "No snapshot found at $snapshot_dir - nothing to restore." >&2; exit 1; }
    find "$dir" -maxdepth 1 -type f \( -name '*.yaml' -o -name '*.yml' \) -delete
    find "$snapshot_dir" -maxdepth 1 -type f -exec cp {} "$dir/" \;
    echo "Restored $dir from snapshot."
    ;;

  *)
    usage
    ;;
esac
