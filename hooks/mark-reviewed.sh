#!/usr/bin/env bash
# Records that the current uncommitted code changes have been reviewed, which
# releases the Stop gate. Run it only AFTER actually running the review skill's
# checklist and fixing what it found — recording a review that did not happen
# defeats the only thing this gate does.
HOOK_NO_STDIN=1
. "${0%/*}/common.sh" || exit 0

HASH="$(code_change_hash)"
if [ -z "$HASH" ]; then
  echo "No uncommitted code changes to record."
  exit 0
fi
printf '%s' "$HASH" > "$STATE_DIR/reviewed"
rm -f "$STATE_DIR"/*.blocks 2>/dev/null || true
echo "Review recorded for the current code changes (${HASH:0:12})."
