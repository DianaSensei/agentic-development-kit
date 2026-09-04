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
# Per file, tracked in a manifest by two hashes - "baseline" (the content we
# ourselves last wrote) and "offered" (the last upstream version we already
# told the user about, so the same change doesn't get re-reported every
# session):
#   - never seeded before                    -> added
#   - on-disk content matches "baseline"      -> untouched since we wrote it
#     (i.e. the user hasn't edited it)           ourselves - safe to update
#   - on-disk content matches neither          -> can't tell customized from
#     "baseline" nor the new shipped default      a pre-existing install with
#                                                  no recorded baseline; NEVER
#                                                  overwritten either way. The
#                                                  new version is offered once
#                                                  as "<name>.upstream" for
#                                                  manual compare/merge.
#   - previously had a recorded baseline,     -> respected as an intentional
#     now missing from disk                      deletion, never recreated
#
# "baseline" is only ever set to content this script itself wrote - never to
# arbitrary on-disk content just because it was seen once - so a genuinely
# customized file can never drift into being treated as safe to overwrite.
# The only way to make such a file eligible for automatic updates again is
# to delete it, which reseeds it fresh from the current shipped default.
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
  baseline="$(printf '%s' "$manifest" | jq -r --arg k "$name" '.[$k].baseline // empty')"
  offered="$(printf '%s' "$manifest" | jq -r --arg k "$name" '.[$k].offered // empty')"

  if [ ! -f "$dest_file" ]; then
    if [ -n "$baseline" ]; then
      # We know we wrote this file before, and it's gone now - the user
      # deleted it on purpose. Never recreate a file the user removed.
      continue
    fi
    cp "$src_file" "$dest_file" 2>/dev/null || continue
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$new_hash" '.[$k] = {baseline: $v, offered: null}')"
    added+=("$name")
    continue
  fi

  cur_hash="$(sum "$dest_file")"

  if [ "$cur_hash" = "$new_hash" ]; then
    # Matches the current shipped default exactly - confirm/refresh it as
    # the trusted baseline (covers first sync, and a file the user brought
    # back in sync themselves, e.g. by applying a .upstream diff by hand).
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$new_hash" '.[$k] = {baseline: $v, offered: null}')"
    continue
  fi

  if [ -n "$baseline" ] && [ "$cur_hash" = "$baseline" ]; then
    # Unchanged since we last wrote it ourselves - the divergence from the
    # shipped default is purely an upstream change, safe to apply.
    cp "$src_file" "$dest_file" 2>/dev/null || continue
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg v "$new_hash" '.[$k] = {baseline: $v, offered: null}')"
    updated+=("$name")
    continue
  fi

  # Doesn't match anything we recognize as ours - never overwrite. Only
  # report it if this is a NEW upstream version since the last time we
  # already surfaced one, so an unresolved conflict doesn't nag every
  # session.
  if [ "$offered" != "$new_hash" ]; then
    cp "$src_file" "$DEST/$name.upstream" 2>/dev/null
    manifest="$(printf '%s' "$manifest" | jq --arg k "$name" --arg bv "$baseline" --arg v "$new_hash" \
      '.[$k] = {baseline: (if $bv == "" then null else $bv end), offered: $v}')"
    conflicts+=("$name")
  fi
done

printf '%s' "$manifest" > "$MANIFEST" 2>/dev/null

if [ "${#added[@]}" -gt 0 ] || [ "${#updated[@]}" -gt 0 ] || [ "${#conflicts[@]}" -gt 0 ]; then
  echo "[agentic-development-kit] toolbox default connections synced in $DEST:"
  [ "${#added[@]}" -gt 0 ] && echo "- added: ${added[*]}"
  [ "${#updated[@]}" -gt 0 ] && echo "- updated to the new shipped default (you hadn't customized these): ${updated[*]}"
  [ "${#conflicts[@]}" -gt 0 ] && echo "- shipped default changed but this doesn't match what we last wrote (customized, or an install from before this tracking existed) - left as-is; the new version was saved as <name>.upstream next to each for you to compare/merge, or delete the file to reseed it fresh: ${conflicts[*]}"
fi
exit 0
