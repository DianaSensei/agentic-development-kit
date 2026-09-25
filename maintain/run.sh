#!/usr/bin/env bash
# run.sh - one pass of the maintain loop, on any CI and any code host this kit
# has a profile for (codehost/providers/). Run from the repository root.
#
#   1. detect, deterministically: control bands (check-bands.py) and, when the
#      CI says so, a failed pipeline on the default branch
#   2. only if a `propose` problem was found: Claude writes each one up as a
#      `proposed` intent under docs/intents/ (propose-intents.md) - no MCP
#      server, no shell beyond the intent checker, no writes elsewhere
#   3. verify: nothing outside docs/intents/ changed, every intent passes
#      check-intent.sh - or nothing is published
#   4. publish: commit to the standing triage branch, push with git, and open
#      its pull/merge request through the provider's MCP server if none is open
#
# The CI templates (.github/workflows/maintain.yml, ci/gitlab/maintain.yml)
# map their variables onto the environment below and call this script.
#
# Publishing needs: ADK_PROVIDER, ADK_PROJECT, ADK_CODEHOST_TOKEN
#   (+ ADK_CODEHOST_URL for GitLab), a Claude credential, and an `origin`
#   remote this job can push to.
# Optional: ADK_BANDS_FILE (bands.yaml), BANDS_ENV (NAME=value lines for the
#   band commands - exported to the check only, every value redacted from the
#   evidence), ADK_FAILED_NAME / ADK_FAILED_URL / ADK_FAILED_REF /
#   ADK_FAILED_SHA / ADK_FAILED_LOG_FILE (a failed pipeline to record),
#   ADK_DEFAULT_BRANCH (else asked of the remote), ADK_QUEUE_BRANCH,
#   ADK_RUN_URL, ADK_MODEL, ADK_GIT_NAME, ADK_GIT_EMAIL, ADK_CODEHOST_BOT_LOGIN,
#   ADK_WORK_DIR, ADK_REDACT (more values to redact, one per line).
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${ADK_WORK_DIR:-$(mktemp -d)}"
mkdir -p "$WORK"
RESULTS="$WORK/results.json"
SUMMARY="$WORK/summary.md"
QUEUE_BRANCH="${ADK_QUEUE_BRANCH:-maintain/proposed-intents}"

note() { # note <level> <title> <text>
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then echo "::$1 title=$2::$3"; else echo "$1: $2 - $3" >&2; fi
}
summary() { cat "$SUMMARY"; [ -n "${GITHUB_STEP_SUMMARY:-}" ] && cat "$SUMMARY" >> "$GITHUB_STEP_SUMMARY"; return 0; }

# 1. Detect. No model runs here.
bands="${ADK_BANDS_FILE:-bands.yaml}"
if [ -f "$bands" ]; then
  (
    if [ -n "${BANDS_ENV:-}" ]; then set -a; source /dev/stdin <<<"$BANDS_ENV"; set +a; fi
    CHECK_BANDS_REDACT="$(printf '%s\n' "${BANDS_ENV:-}" | sed -n 's/^[A-Za-z_][A-Za-z0-9_]*=//p'
                          printf '%s\n' "${ADK_CODEHOST_TOKEN:-}" "${ADK_REDACT:-}")"
    export CHECK_BANDS_REDACT
    unset ADK_CODEHOST_TOKEN ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN
    python3 "$KIT/maintain/check-bands.py" "$bands" --out "$RESULTS" > /dev/null
  )
else
  echo "No $bands in this repository - only a failed pipeline, if any, is checked."
  echo '[]' > "$RESULTS"
fi

if [ -n "${ADK_FAILED_URL:-}" ]; then
  python3 - "$RESULTS" <<'EOF'
import json, os, re, sys
path = sys.argv[1]
with open(path) as f:
    results = json.load(f)
name = os.environ.get("ADK_FAILED_NAME") or "pipeline"
ref, sha = os.environ.get("ADK_FAILED_REF", "?"), os.environ.get("ADK_FAILED_SHA", "")
tail = ""
log = os.environ.get("ADK_FAILED_LOG_FILE")
if log and os.path.isfile(log):
    with open(log, errors="replace") as f:
        tail = "\n".join(f.read().splitlines()[-60:])
results.append({
    "name": "ci-" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "pipeline"),
    "status": "breach", "tier": "propose", "value": None, "min": None, "max": None,
    "reason": f'"{name}" failed on {ref}' + (f" at {sha[:7]}" if sha else ""),
    "command": "(CI run)", "output": tail, "url": os.environ["ADK_FAILED_URL"],
    "owner": None, "runbook": None,
})
with open(path, "w") as f:
    json.dump(results, f, indent=1)
EOF
fi

propose="$(python3 - "$RESULTS" "$SUMMARY" <<'EOF'
import json, sys
with open(sys.argv[1]) as f:
    results = json.load(f)
problems = [r for r in results if r["status"] != "ok"]
rows = [f"### Maintain: {len(problems)} problem(s) in {len(results)} check(s)", "",
        "| Check | Status | Value | Range | Tier | Detail |", "|---|---|---|---|---|---|"]
for r in results:
    rng = f"{r.get('min') if r.get('min') is not None else ''} .. {r.get('max') if r.get('max') is not None else ''}"
    value = "-" if r.get("value") is None else r["value"]
    rows.append(f"| {r['name']} | {r['status']} | {value} | {rng} | {r['tier']} | {r.get('reason') or ''} |")
with open(sys.argv[2], "w") as f:
    f.write("\n".join(rows) + "\n")
import os
for r in results:
    if r["status"] == "error":
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Broken detector::{r['name']}: {r.get('reason')}", file=sys.stderr)
        else:
            print(f"warning: broken detector {r['name']}: {r.get('reason')}", file=sys.stderr)
print(sum(1 for r in results if r["tier"] == "propose" and r["status"] in ("breach", "error")))
EOF
)"

if [ "$propose" = "0" ]; then
  summary
  echo "Nothing to propose."
  exit 0
fi

# 2. Write the intents - only with everything needed to publish them.
has_credential=""
for v in ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN ANTHROPIC_AUTH_TOKEN CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX CLAUDE_CODE_USE_FOUNDRY; do
  [ -n "${!v:-}" ] && has_credential=1
done
[ "${ADK_CLAUDE_AUTH:-}" = "preconfigured" ] && has_credential=1
missing=""
[ -n "$has_credential" ] || missing="a Claude credential (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN)"
for v in ADK_PROVIDER ADK_PROJECT ADK_CODEHOST_TOKEN; do
  [ -n "${!v:-}" ] || missing="${missing:+$missing, }$v"
done
if [ -n "$missing" ]; then
  summary
  note warning "Maintain: intents not proposed" "Problems were found (see the summary) but nothing was written up - missing: $missing."
  exit 0
fi
command -v claude >/dev/null || { note error "Maintain" "Claude Code is not installed"; exit 1; }

# The queue branch carries intents proposed in earlier runs that nobody has
# triaged yet; starting from it lets this run update those instead of
# duplicating them. Merging the default branch in brings intents already
# accepted there into view for the same reason.
default_branch="${ADK_DEFAULT_BRANCH:-}"
if [ -z "$default_branch" ]; then
  git remote set-head origin --auto >/dev/null 2>&1 || true
  default_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')"
fi
[ -n "$default_branch" ] || { note error "Maintain" "Could not tell the default branch - set ADK_DEFAULT_BRANCH"; exit 1; }
git config user.name "${ADK_GIT_NAME:-adk-maintain}"
git config user.email "${ADK_GIT_EMAIL:-adk-maintain@users.noreply.invalid}"
git fetch --quiet origin "$default_branch"
if git ls-remote --exit-code --heads origin "$QUEUE_BRANCH" > /dev/null; then
  git fetch --quiet origin "$QUEUE_BRANCH"
  git checkout --quiet -B "$QUEUE_BRANCH" "origin/$QUEUE_BRANCH"
  git merge --quiet --no-edit "origin/$default_branch"
else
  git checkout --quiet -B "$QUEUE_BRANCH" "origin/$default_branch"
fi

model_args=()
[ -n "${ADK_MODEL:-}" ] && model_args=(--model "$ADK_MODEL")
(
  # Claude needs no code-host access to write files; keep every token out of its environment.
  unset ADK_CODEHOST_TOKEN BANDS_ENV GH_TOKEN GITHUB_TOKEN GITLAB_TOKEN ADK_GITLAB_TOKEN
  claude -p "Follow ${KIT}/maintain/propose-intents.md.
The results file is ${RESULTS}. The kit is at ${KIT}.
Run URL: ${ADK_RUN_URL:-(none)}" \
    --plugin-dir "$KIT" --add-dir "$KIT" --add-dir "$WORK" \
    --strict-mcp-config \
    --allowedTools "Read,Glob,Grep,Skill,Edit(docs/intents/**),Bash(bash ${KIT}/skills/intent-capture/scripts/check-intent.sh *)" \
    "${model_args[@]}" > "$WORK/claude.txt"
) || { note error "Maintain" "Claude did not finish writing the intents"; cat "$WORK/claude.txt" 2>/dev/null || true; exit 1; }
cat "$WORK/claude.txt"

# 3. The model's output is checked, not trusted.
outside="$(git status --porcelain --untracked-files=all | awk '{print $NF}' | grep -v '^docs/intents/' || true)"
if [ -n "$outside" ]; then
  note error "Maintain" "Files outside docs/intents/ changed - nothing published: $(echo $outside)"
  exit 1
fi
changed="$(git status --porcelain --untracked-files=all -- docs/intents | awk '{print $NF}')"
if [ -z "$changed" ]; then summary; echo "No intent changed."; exit 0; fi
# shellcheck disable=SC2086
bash "$KIT/skills/intent-capture/scripts/check-intent.sh" $changed

# 4. Publish.
git add docs/intents
git commit --quiet -m "Maintain: propose intents from monitoring ($(date -u +%Y-%m-%d))"
git push --quiet origin "HEAD:refs/heads/$QUEUE_BRANCH"

cat > "$WORK/change-body.md" <<'EOF'
Problems found by the maintain loop, each written up as a `proposed` intent. Triage them here: accept (`intent-capture` Decide mode, or edit `status`), reject with a reason, or edit before merging. Merging records the decisions; accepted intents then go through the normal workflows. New findings keep arriving on this branch until it is merged.
EOF
bash "$KIT/codehost/install.sh" "$ADK_PROVIDER" "$WORK/bin"
PATH="$WORK/bin:$PATH" python3 "$KIT/codehost/codehost.py" ensure-change \
  --head "$QUEUE_BRANCH" --base "$default_branch" \
  --title "Proposed intents from monitoring" --body-file "$WORK/change-body.md"

{ echo; echo "Proposed or updated:"; printf -- '- `%s`\n' $changed; } >> "$SUMMARY"
summary
