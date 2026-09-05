#!/usr/bin/env bash
# Shared helpers for the quality-check hooks.
#
# Design rule for every hook in this directory: FAIL OPEN. A hook that cannot do
# its job (no jq, unreadable transcript, not a git repo, bad config) must exit 0
# silently and let the user's work continue. A quality gate is never allowed to
# become the reason someone cannot get work done.

set -u

# PROJECT_DIR is the project these hooks are running against - where the git
# repo, its state, and any per-project override live. PLUGIN_ROOT is where this
# plugin's own files (skills/, the bundled default config) live, which is a
# different place once this ships as a plugin installed into someone else's
# project. The fallback lets these scripts still work run by hand, or under the
# older standalone (non-plugin) layout.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)}"
PLUGIN_ROOT="${PLUGIN_ROOT:-$PROJECT_DIR}"
STATE_DIR="$PROJECT_DIR/.claude/state"

# The bundled config ships with the plugin; a project can override it without
# forking the plugin by dropping its own copy at .claude/quality-check.config.json.
CONFIG_FILE="$PROJECT_DIR/.claude/quality-check.config.json"
[ -f "$CONFIG_FILE" ] || CONFIG_FILE="$PLUGIN_ROOT/hooks/quality-check.config.json"

# No jq -> we cannot parse hook input at all. Fail open.
command -v jq >/dev/null 2>&1 || exit 0

# Hooks are fed their JSON on stdin. Helper scripts run by hand set
# HOOK_NO_STDIN=1 so sourcing this file never blocks on a terminal.
if [ "${HOOK_NO_STDIN:-0}" = "1" ]; then HOOK_INPUT="{}"; else HOOK_INPUT="$(cat)"; fi

# jq_in <filter> [default] - read a field out of the hook's stdin JSON.
jq_in() {
  local out
  out="$(printf '%s' "$HOOK_INPUT" | jq -r "$1 // empty" 2>/dev/null)" || out=""
  [ -n "$out" ] && printf '%s' "$out" || printf '%s' "${2-}"
}

# jq_cfg <filter> [default] - read a field out of quality-check.config.json.
# Uses `select(. != null)` rather than `// empty`: jq's `//` treats a literal
# `false` value the same as missing/null, which would make a config field that
# defaults to true impossible to turn off. `select` only filters true nulls.
jq_cfg() {
  local out
  [ -f "$CONFIG_FILE" ] || { printf '%s' "${2-}"; return; }
  out="$(jq -r "($1) | select(. != null)" "$CONFIG_FILE" 2>/dev/null)" || out=""
  [ -n "$out" ] && printf '%s' "$out" || printf '%s' "${2-}"
}

# mode_of <gate-name> <default> - "off" | "warn" | "block".
# QUALITY_CHECK_MODE in the environment overrides every gate, for a quick escape
# hatch without editing committed config.
mode_of() {
  if [ -n "${QUALITY_CHECK_MODE:-}" ]; then printf '%s' "$QUALITY_CHECK_MODE"; return; fi
  jq_cfg ".mode.$1" "$2"
}

# json_str <text> - JSON-encode a string (quotes included).
json_str() { printf '%s' "$1" | jq -Rs .; }

# warn <text> - non-blocking advisory. systemMessage surfaces it in the
# transcript; additionalContext is the field Claude reads where the event
# supports it. Emitting both is deliberate: which one lands depends on the event.
warn() {
  jq -nc --arg m "$1" '{systemMessage: $m, additionalContext: $m}'
  exit 0
}

# git_repo_root - echoes the repo root, or nothing if this is not a git repo.
git_repo_root() { git -C "$PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null || true; }

# last_line_matching <transcript> <ere-pattern> - 1-based line number of the
# LAST line matching pattern in the transcript, or empty if none matched (or
# the transcript can't be read).
last_line_matching() {
  grep -nE "$2" "$1" 2>/dev/null | tail -n 1 | cut -d: -f1
}

# last_user_message_line <transcript> - 1-based line number of the last
# GENUINE user message. Tool results are also recorded as type "user" in the
# transcript, so they're excluded - otherwise every tool call would look like
# the start of a fresh request.
last_user_message_line() {
  grep -n '"type":"user"' "$1" 2>/dev/null | grep -v 'tool_result' | tail -n 1 | cut -d: -f1
}

# transcript_tail_from <transcript> <line-number-or-empty> - the transcript
# content from that line to the end. An empty line number means "the whole
# transcript" (caller had nothing to anchor to).
transcript_tail_from() {
  local transcript="$1" from="${2:-1}"
  tail -n "+$from" "$transcript" 2>/dev/null
}

# resolve_skill <skill-name> - path to that skill's SKILL.md, or nothing.
# Checks the plugin's own `skills/` first (where these skills actually live once
# installed as a plugin), then falls back to a project that vendored the skill
# locally (`.claude/skills/` or `skills/` inside the project itself) - e.g. a
# project-local override of one skill, or the older standalone layout.
resolve_skill() {
  local name="$1" root
  for root in "$PLUGIN_ROOT/skills" "$PROJECT_DIR/.claude/skills" "$PROJECT_DIR/skills"; do
    [ -f "$root/$name/SKILL.md" ] && { printf '%s' "$root/$name/SKILL.md"; return; }
  done
}

# skill_ref_pattern <name|alternation> - ERE matching a transcript line where the
# skill was actually READ or INVOKED, not merely mentioned.
#
# The bare path `<skill>/SKILL.md` is NOT sufficient, which is the whole point of
# this helper: skills/README.md links every skill as `./<name>/SKILL.md`, so any
# turn that reads that file (or a plan doc, or a commit message quoting a path)
# would otherwise look like a read of the skill itself. One real transcript had
# 16 such lines for a single skill. Anchoring to the `file_path` argument of a
# tool call, or to the Skill tool's `skill` argument, matches only real use.
skill_ref_pattern() {
  printf '"file_path"[[:space:]]*:[[:space:]]*"[^"]*/(%s)/SKILL\\.md"|"skill"[[:space:]]*:[[:space:]]*"(%s)"' "$1" "$1"
}

# code_ext - the regex deciding what counts as a code file, for the Stop gate and
# the checkpoint gate alike. Single definition on purpose: it used to be a literal
# duplicated in two scripts, both narrower than the shipped config, so the same
# change counted as code or not depending on whether the config file was found.
code_ext() {
  jq_cfg '.code_extensions' '\.(java|kt|kts|rs|ts|tsx|js|jsx|py|go|rb|php|cs|sql|sh|bash|yaml|yml|tf|gradle|xml|toml)$'
}

mkdir -p "$STATE_DIR" 2>/dev/null || true

# Session-scoped markers are dead once their session is over and nothing else
# prunes them, so STATE_DIR grew without bound. `reviewed` and `warned` are
# deliberately left alone: they track the state of the working tree, not a
# session, and deleting them would silently demand a re-review.
find "$STATE_DIR" -maxdepth 1 -type f \
  \( -name '*.blocks' -o -name '*.skillgate.*' -o -name '*.checkpointgate' \) \
  -mtime +7 -delete 2>/dev/null || true

# code_change_hash - a stable fingerprint of the working tree's uncommitted CODE
# changes (tracked edits and untracked new files alike), or nothing when there
# are none. Documentation-only work therefore never trips the quality gate.
#
# The fingerprint, not a boolean, is what gets recorded as "reviewed": once the
# code changes again, the old review no longer vouches for it.
code_change_hash() {
  local root ext files sum
  root="$(git_repo_root)"; [ -n "$root" ] || return 0
  ext="$(code_ext)"

  files="$(git -C "$root" status --porcelain --untracked-files=all 2>/dev/null \
           | sed 's/^...//' | sed 's/.* -> //' | grep -E "$ext" || true)"
  [ -n "$files" ] || return 0

  if command -v sha256sum >/dev/null 2>&1; then sum=sha256sum
  elif command -v shasum >/dev/null 2>&1; then sum="shasum -a 256"
  else return 0; fi

  { printf '%s\n' "$files"
    printf '%s\n' "$files" | while IFS= read -r f; do
      [ -f "$root/$f" ] && cat "$root/$f"
    done
  } | $sum | cut -d' ' -f1
}
