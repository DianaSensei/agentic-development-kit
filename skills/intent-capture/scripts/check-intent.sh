#!/usr/bin/env bash
# Check that intent files have the exact shape references/intent-template.md
# defines. Review mode and the orchestrators find statuses and links by these
# fixed keys and headings, so a file shaped differently is one they miss.
#
# Usage: check-intent.sh <docs/intents/<slug>.md>...
# Prints one line per problem; exits 1 if any file has one.

KEYS="title status type originator created updated plan changelog superseded_by"
SECTIONS="Problem|Evidence|Desired outcome|Success signal|Non-goals|Affected systems|Constraints|Originator's idea (non-binding)|Open questions|Decision log"
STATUSES="draft proposed accepted rejected in-progress done superseded"
TYPES="feature bug refactor unknown"

rc=0
fail() { echo "$1: $2"; rc=1; }
# An empty value would match the padding spaces, so reject it explicitly.
one_of() { [ -n "$1" ] && case " $2 " in *" $1 "*) true ;; *) false ;; esac; }

[ $# -gt 0 ] || { echo "usage: ${0##*/} <intent.md>..." >&2; exit 2; }

for f in "$@"; do
  [ -f "$f" ] || { fail "$f" "no such file"; continue; }
  [ "$(head -n1 "$f")" = "---" ] || { fail "$f" "does not start with a --- frontmatter block"; continue; }

  # Frontmatter is everything between the first two --- lines.
  fm="$(awk 'NR==1{next} /^---$/{exit} {print}' "$f")"
  body="$(awk 'c>=2{print} /^---$/{c++}' "$f")"

  present="$(printf '%s\n' "$fm" | sed -n 's/^\([A-Za-z_]*\):.*/\1/p')"
  for k in $KEYS; do
    printf '%s\n' "$present" | grep -qx "$k" || fail "$f" "missing frontmatter key '$k'"
  done
  for k in $present; do
    one_of "$k" "$KEYS" || fail "$f" "unexpected frontmatter key '$k'$( [ "$k" = slug ] && echo ' (the slug is the filename)')"
  done

  val() { printf '%s\n' "$fm" | sed -n "s/^$1:[[:space:]]*//p" | head -n1; }
  status="$(val status)"
  one_of "$status" "$STATUSES" || fail "$f" "status '$status' is not one of: $STATUSES"
  type="$(val type)"
  one_of "$type" "$TYPES" || fail "$f" "type '$type' is not one of: $TYPES"
  [ -n "$(val title)" ] || fail "$f" "title is empty"
  [ "$status" != "superseded" ] || [ -n "$(val superseded_by)" ] || fail "$f" "superseded without superseded_by"
  for k in plan changelog superseded_by; do
    case "$(val "$k")" in null|'~'|'""'|"''") fail "$f" "$k: leave it empty rather than writing a null" ;; esac
  done
  [ "$status" != "done" ] || [ -n "$(val changelog)" ] || fail "$f" "done without a changelog link"

  printf '%s\n' "$body" | grep -q '^# ' || fail "$f" "missing the '# <title>' heading"

  # Every section present, in template order.
  headings="$(printf '%s\n' "$body" | sed -n 's/^## //p')"
  expected=""; IFS='|'
  for s in $SECTIONS; do
    printf '%s\n' "$headings" | grep -qxF "$s" || fail "$f" "missing section '## $s'"
    printf '%s\n' "$headings" | grep -qxF "$s" && expected="$expected$s
"
  done
  unset IFS
  actual="$(printf '%s\n' "$headings" | grep -xF "$(printf '%s' "$expected")")"
  [ "$actual" = "$(printf '%s' "$expected")" ] || fail "$f" "sections are out of template order"
done

exit $rc
