#!/usr/bin/env bash
# SessionStart - seed the toolbox MCP's writable connections directory on
# first run. Users install this plugin via the marketplace, not a repo
# clone, so there is no local checkout for them to copy config from.
#
# CLAUDE_PLUGIN_DATA is a per-plugin directory that survives plugin
# updates - the right place for a user's own connections and any they add
# or edit. CLAUDE_PLUGIN_ROOT is the versioned install/cache dir instead:
# wiped and replaced on every update, so it never holds user state, only
# the plugin's own shipped defaults.
#
# Never overwrites - once the destination exists (seeded, or the user made
# it another way), this is a no-op forever, so local edits/additions/
# deletions in there always survive plugin updates untouched.

set -u
[ -n "${CLAUDE_PLUGIN_DATA:-}" ] || exit 0
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || exit 0

DEST="$CLAUDE_PLUGIN_DATA/connections"
SRC="$CLAUDE_PLUGIN_ROOT/mcp/toolbox/connections-defaults"

[ -d "$DEST" ] && exit 0
[ -d "$SRC" ] || exit 0

mkdir -p "$DEST" && cp "$SRC"/*.yaml "$DEST"/ 2>/dev/null || exit 0

cat <<TXT
[agentic-development-kit] Seeded the toolbox MCP's default database connections into
$DEST (persists across plugin updates). Configure connection details via this plugin's
settings (/plugin), or ask Claude to add/edit/remove a connection file directly - see
mcp/toolbox/README.md.
TXT
