#!/usr/bin/env bash
# Records that the current uncommitted code changes have been reviewed, which
# releases the Stop gate. Run it only AFTER actually running the review skill's
# checklist and fixing what it found - recording a review that did not happen
# defeats the only thing this gate does.
HOOK_NO_STDIN=1
. "${0%/*}/common.sh" || exit 0

HASH="$(code_change_hash)"
if [ -z "$HASH" ]; then
  echo "No uncommitted code changes to record."
  exit 0
fi
printf '%s' "$HASH" > "$STATE_DIR/reviewed"

# Clear only THIS session's block counter when the id is given (quality-gate puts
# it in the command it prints). Without it, fall back to clearing every session's
# counter - which resets the bounded-blocking allowance of other sessions working
# in the same repo, sessions that never ran a review.
if [ -n "${1:-}" ]; then
  rm -f "$STATE_DIR/$1.blocks" 2>/dev/null || true
else
  rm -f "$STATE_DIR"/*.blocks 2>/dev/null || true
fi
echo "Review recorded for the current code changes (${HASH:0:12})."
