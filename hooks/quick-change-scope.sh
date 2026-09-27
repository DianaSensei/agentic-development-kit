#!/usr/bin/env bash
# Stop, while `quick-change` runs - the fast path's guard.
#
# The quick path skips the analyst, the architect, the plan and the Checkpoint
# because the change is small, local and has one obvious form. That judgement is
# made before the work starts; this checks it against what was actually done.
# A diff that outgrew it - too many files or lines, or a path where a mistake is
# expensive (a migration, auth, payments, CI, an API contract, a dependency) - is
# sent back to workflow-router for the full workflow, or to the user to decide.
#
# Config (`.claude/quality-check.config.json`, `quick_change`): max_files (3),
# max_lines (60), sensitive_paths (EREs on repo-relative paths; the defaults
# below). `mode.quick_change_scope`: warn (default) tells the user; block sends
# Claude back to escalate before it may finish.

. "${0%/*}/common.sh" || exit 0

MODE="$(mode_of quick_change_scope warn)"
[ "$MODE" = "off" ] && exit 0
[ "$(jq_in '.stop_hook_active' false)" = "true" ] && exit 0

ROOT="$(git_repo_root)"
[ -n "$ROOT" ] || exit 0

MAX_FILES="$(jq_cfg '.quick_change.max_files' 3)"
MAX_LINES="$(jq_cfg '.quick_change.max_lines' 60)"
SENSITIVE="$(jq_cfg '(.quick_change.sensitive_paths // empty) | join("|")' \
  '(^|/)(migrations?|db/migrate|alembic|flyway|liquibase)/|\.sql$|(^|/)(auth|authn|authz|security|crypto|payments?|billing|checkout)(/|\.|_)|(^|/)\.github/|(^|/)\.gitlab-ci\.yml$|(openapi|asyncapi|swagger)[^/]*\.(ya?ml|json)$|\.proto$|(^|/)(package\.json|pom\.xml|build\.gradle(\.kts)?|Cargo\.toml|go\.mod|pyproject\.toml|Gemfile|composer\.json)$|(^|/)requirements[^/]*\.txt$|(^|/)\.claude/|(^|/)CLAUDE\.md$')"

# Tracked changes with their line counts, plus untracked files counted whole;
# binary files (numstat "-") count as files, and the kit's own state never counts.
STATS="$( { git -C "$ROOT" diff --numstat HEAD 2>/dev/null
            git -C "$ROOT" ls-files --others --exclude-standard 2>/dev/null \
              | while IFS= read -r f; do printf '%s\t0\t%s\n' "$(wc -l < "$ROOT/$f" 2>/dev/null | tr -d ' ')" "$f"; done
          } | awk -F'\t' 'NF>=3 && $3 !~ /^\.claude\/(state|worktrees)\//' )"
[ -n "$STATS" ] || exit 0

FILES="$(printf '%s\n' "$STATS" | wc -l | tr -d ' ')"
LINES="$(printf '%s\n' "$STATS" | awk -F'\t' '{n += ($1 == "-" ? 0 : $1) + ($2 == "-" ? 0 : $2)} END {print n+0}')"
HITS="$(printf '%s\n' "$STATS" | cut -f3 | grep -E "$SENSITIVE" | head -n 5)"

REASONS=""
[ "$FILES" -gt "$MAX_FILES" ] && REASONS="${REASONS}
- $FILES files changed (the quick path allows $MAX_FILES)"
[ "$LINES" -gt "$MAX_LINES" ] && REASONS="${REASONS}
- $LINES lines changed (the quick path allows $MAX_LINES)"
[ -n "$HITS" ] && REASONS="${REASONS}
- paths where a mistake is expensive: $(printf '%s' "$HITS" | sed 's/^/`/; s/$/`/' | paste -sd, - | sed 's/,/, /g')"
[ -n "$REASONS" ] || exit 0

# Once per state of the diff, not on every stop.
HASH="$( { git -C "$ROOT" diff HEAD 2>/dev/null
           printf '%s\n' "$STATS" | cut -f3 | while IFS= read -r f; do cat "$ROOT/$f" 2>/dev/null; done
         } | cksum | cut -d' ' -f1)"
SEEN="$STATE_DIR/quickscope"
[ "$(cat "$SEEN" 2>/dev/null)" = "$HASH" ] && exit 0
printf '%s' "$HASH" > "$SEEN" 2>/dev/null || true

MSG="[quick-change] This change outgrew the quick path:$REASONS
Stop and hand it to \`workflow-router\` for the full workflow, with what you learned so far - its
analysis and CHECKPOINT exist for exactly this kind of change. If the user explicitly asked for the
quick path on this change, tell them what makes it risky and let them decide."

if [ "$MODE" = "block" ]; then
  printf '%s\n' "$MSG" >&2
  exit 2
fi
warn "$MSG"
