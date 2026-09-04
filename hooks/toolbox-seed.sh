#!/usr/bin/env bash
# SessionStart - sync the toolbox MCP's shipped default connections into its
# writable directory. Users install this plugin via the marketplace, not a
# repo clone, so there is no local checkout for them to copy config from.
#
# CLAUDE_PLUGIN_DATA is a per-plugin directory that survives plugin
# updates - the right place for a user's own connections and any they add
# or edit. CLAUDE_PLUGIN_ROOT is the versioned install/cache dir instead:
# wiped and replaced on every update, so it never holds user state, only
# the plugin's own shipped defaults.
#
# Per-file, tracked by a content-hash manifest so an update to one of the
# six defaults can reach connections you never touched, without ever
# clobbering one you customized:
#   - missing entirely           -> added
#   - unchanged since last seed  -> updated to the new default
#   - edited since last seed     -> left alone; the new default is saved
#                                    alongside as "<name>.upstream" for you
#                                    to compare/merge by hand
#
# Fails open (no jq/sha256 -> skip silently) per every hook in this repo.

set -u
[ -n "${CLAUDE_PLUGIN_DATA:-}" ] || exit 0
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || exit 0

DEST="$CLAUDE_PLUGIN_DATA/connections"
SRC="$CLAUDE_PLUGIN_ROOT/mcp/toolbox/connections-defaults"
MANIFEST="$DEST/.seed-manifest.json"

[ -d "$SRC" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

if command -v sha256sum >/dev/null 2>&1; then
  sum() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
  sum() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
  exit 0
fi

mkdir -p "$DEST" 2>/dev/null || exit 0

manifest="{}"
[ -f "$MANIFEST" ] && manifest="$(cat "$MANIFEST" 2>/dev/null)"
printf '%s' "$manifest" | jq -e . >/dev/null 2>&1 || manifest="{}"

added=() updated=() conflicts=()

for src_file in "$SRC"/*.yaml; do
  [ -e "$src_file" ] || continue
  name="$(basename "$src_file")"
  dest_file="$DEST/$name"
  new_hash="$(sum "$src_file")"

  if [ ! -f "$dest_file" ]; then
    cp "$src_file" "$dest_file" 2>/dev/null || continue
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$new_hash" '.[$k] = $v')"
    added+=("$name")
    continue
  fi

  cur_hash="$(sum "$dest_file")"
  [ "$cur_hash" = "$new_hash" ] && {
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$new_hash" '.[$k] = $v')"
    continue
  }

  recorded_hash="$(printf '%s' "$manifest" | jq -r --arg k "$name" '.[$k] // empty')"

  if [ -z "$recorded_hash" ]; then
    # No baseline (pre-manifest seed, or a same-named file the user made
    # themselves) - adopt the current content as the baseline rather than
    # guessing; never overwrite without a recorded "last seeded" hash.
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$cur_hash" '.[$k] = $v')"
    continue
  fi

  if [ "$cur_hash" = "$recorded_hash" ]; then
    cp "$src_file" "$dest_file" 2>/dev/null || continue
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$new_hash" '.[$k] = $v')"
    updated+=("$name")
  else
    cp "$src_file" "$DEST/$name.upstream" 2>/dev/null
    conflicts+=("$name")
  fi
done

printf '%s' "$manifest" > "$MANIFEST" 2>/dev/null

if [ "${#added[@]}" -gt 0 ] || [ "${#updated[@]}" -gt 0 ] || [ "${#conflicts[@]}" -gt 0 ]; then
  echo "[agentic-development-kit] toolbox default connections synced in $DEST:"
  [ "${#added[@]}" -gt 0 ] && echo "- added: ${added[*]}"
  [ "${#updated[@]}" -gt 0 ] && echo "- updated to the new shipped default (you hadn't customized these): ${updated[*]}"
  [ "${#conflicts[@]}" -gt 0 ] && echo "- shipped default changed but you customized these, left as-is; the new version was saved as <name>.upstream next to each for you to compare/merge: ${conflicts[*]}"
fi
exit 0
