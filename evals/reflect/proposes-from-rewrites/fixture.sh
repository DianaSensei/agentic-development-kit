#!/usr/bin/env bash
# A repository where the user twice rewrote agent code the same way - a failure
# returned as None became a raised domain error - and a profile whose inbox holds
# one related correction. Two rewrites plus a correction is enough evidence for a
# profile line; a headless run can only propose it, never write it.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
git init -q -b main
printf "profile/\nrewrites.md\n" > .git/info/exclude
git config user.email me@example.com && git config user.name me
mkdir -p src/orders
commit() { git add -A && git commit -qm "$1"; }
cat > src/orders/parse.py <<'PY'
def quantity(text):
    return int(text)
PY
commit "Orders: parse quantities"
cat >> src/orders/parse.py <<'PY'


def price(text):
    try:
        return float(text)
    except Exception:
        return None
PY
commit "Parse prices

Co-Authored-By: Claude <noreply@anthropic.com>"
python3 - <<'PY'
p = "src/orders/parse.py"
s = open(p).read().replace("    except Exception:\n        return None\n",
                           "    except ValueError as e:\n        raise InvalidOrder(f\"bad price: {text!r}\") from e\n")
open(p, "w").write("class InvalidOrder(ValueError):\n    pass\n\n\n" + s)
PY
commit "Price parsing raises InvalidOrder instead of returning None"
cat >> src/orders/parse.py <<'PY'


def discount(text):
    try:
        return int(text.rstrip("%"))
    except Exception:
        return None
PY
commit "Parse discounts

Co-Authored-By: Claude <noreply@anthropic.com>"
python3 - <<'PY'
p = "src/orders/parse.py"
s = open(p).read()
i = s.rindex("    except Exception:\n        return None\n")
s = s[:i] + "    except ValueError as e:\n        raise InvalidOrder(f\"bad discount: {text!r}\") from e\n"
open(p, "w").write(s)
PY
commit "Discount parsing raises too"
# Runs get no shell (see evals/README.md), so hand over the rewrite scan the way
# the reviewer cases hand over review.diff: what skills/reflect/scripts/followup_edits.py
# prints for this history.
cat > rewrites.md <<'MD'
### src/orders/parse.py - Price parsing raises InvalidOrder instead of returning None
Rewrites lines from "Parse prices" (agent commit)

```diff
-    except Exception:
-        return None
+    except ValueError as e:
+        raise InvalidOrder(f"bad price: {text!r}") from e
```

### src/orders/parse.py - Discount parsing raises too
Rewrites lines from "Parse discounts" (agent commit)

```diff
-    except Exception:
-        return None
+    except ValueError as e:
+        raise InvalidOrder(f"bad discount: {text!r}") from e
```
MD
# The profile, checked out where the prompt names it (inside the workspace, so the
# run can read it; for real it lives at ~/.claude/adk-profile).
P="profile"
mkdir -p "$P"
cat > "$P/profile.md" <<'MD'
# How I work
<!-- Personal preferences, learned from working together and approved one by one.
A project's CLAUDE.md, REVIEW.md and checks override anything here. -->

## How I decide
## Design
## Code style
## Review bar
## Working with me
## Not for me
MD
cat > "$P/signals.md" <<'MD'
- 2026-09-20 | correction | billing | "don't hand back None when parsing fails - the caller never checks it" | experience-log: none-on-failure
MD
git -C "$P" init -q && git -C "$P" add -A && git -C "$P" -c user.email=me@example.com -c user.name=me commit -qm "Profile"
