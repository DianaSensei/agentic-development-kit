#!/usr/bin/env python3
"""The playbook's metrics, computed from what the kit's workflows commit.

Reads docs/intents/, docs/plans/, docs/changelog/, docs/postmortems/,
docs/knowledge/experience-log.md and git history. Deterministic, stdlib only,
no network. Metrics that need CI or review data from the code host are listed as not
measured rather than estimated.

Usage: sdlc-metrics.py [repo-root] [--json]
"""
import json
import os
import re
import subprocess
import sys
from datetime import date
from statistics import median

ACCEPTED = {"accepted", "in-progress", "done"}
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def git_dates(root, path):
    """Commit dates (YYYY-MM-DD, oldest first) of commits touching path."""
    try:
        out = subprocess.run(["git", "-C", root, "log", "--follow", "--format=%as", "--", path],
                             capture_output=True, text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return list(reversed(out))


def days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def med(values):
    return round(median(values), 1) if values else None


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        k, sep, v = line.partition(":")
        if sep:
            fm[k.strip()] = v.strip()
    return fm


def decision_log(text):
    """(date, text) pairs from the intent's Decision log section."""
    m = re.search(r"^## Decision log\n(.*)", text, re.S | re.M)
    out = []
    for line in (m.group(1).splitlines() if m else []):
        d = DATE.search(line)
        if line.startswith("- ") and d:
            out.append((d.group(1), line.lower()))
    return out


def intents(root):
    folder = os.path.join(root, "docs", "intents")
    rows = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not name.endswith(".md"):
            continue
        text = read(os.path.join(folder, name))
        fm = frontmatter(text)
        log = decision_log(text)
        created = fm.get("created") or (log[0][0] if log else None)
        decided = next((d for d, l in log if re.search(r"\b(accepted|rejected)\b", l)), None)
        rows.append({
            "slug": name[:-3], "status": fm.get("status", ""), "originator": fm.get("originator", ""),
            "created": created, "decided": decided,
            "seen_again": sum(1 for _, l in log if "seen again" in l),
            "plan": fm.get("plan") or "", "changelog": fm.get("changelog") or "",
            "signal_band": fm.get("signal_band") or "", "resolution": fm.get("resolution") or "",
        })
    return rows


def compute(root):
    rows = intents(root)
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    accepted = sum(1 for r in rows if r["status"] in ACCEPTED)
    rejected = by_status.get("rejected", 0)
    decide = [days(r["created"], r["decided"]) for r in rows if r["created"] and r["decided"]]
    monitoring = [r for r in rows if r["originator"].startswith(("monitoring/", "incident/"))]
    triage = [days(r["created"], r["decided"]) for r in monitoring if r["created"] and r["decided"]]

    # Plan approval to shipped: first commit of the plan to first commit of its changelog.
    shipped, revisions = [], []
    for r in rows:
        if not r["plan"]:
            continue
        plan_dates = git_dates(root, r["plan"])
        if plan_dates:
            revisions.append(len(plan_dates) - 1)
        log_dates = git_dates(root, r["changelog"]) if r["changelog"] else []
        if plan_dates and log_dates:
            shipped.append(days(plan_dates[0], log_dates[0]))

    log = read(os.path.join(root, "docs", "knowledge", "experience-log.md"))
    classes = re.findall(r"^- Class: (\S+)", log, re.M)
    counts = {}
    for c in classes:
        counts[c] = counts.get(c, 0) + 1
    repeated = {c: n for c, n in counts.items() if n >= 2}

    recurring = {}
    for r in monitoring:
        key = r["originator"]
        recurring[key] = recurring.get(key, 0) + 1 + r["seen_again"]

    done = [r for r in rows if r["status"] == "done"]
    met = sum(1 for r in done if r["resolution"] == "met")
    not_met = sum(1 for r in done if r["resolution"] == "not-met")

    return {
        "plan": {
            "intents": len(rows),
            "by_status": by_status,
            "acceptance_rate": round(accepted / (accepted + rejected), 2) if accepted + rejected else None,
            "median_days_to_decision": med(decide),
            "decisions_measured": len(decide),
        },
        "build": {
            "median_days_plan_to_changelog": med(shipped),
            "changes_measured": len(shipped),
            "mean_plan_revisions": round(sum(revisions) / len(revisions), 2) if revisions else None,
        },
        "learning": {
            "experience_log_entries": len(classes),
            "user_corrections": len(re.findall(r"^- Source: user-correction", log, re.M)),
            "repeated_classes": repeated,
            "promoted_to_claude_md": len(re.findall(r"^- Promoted: CLAUDE\.md", log, re.M)),
            "promotions_declined": len(re.findall(r"^- Promotion: declined", log, re.M)),
        },
        "bets": {
            "done": len(done),
            "met": met,
            "not_met": not_met,
            "resolution_rate": round(met / (met + not_met), 2) if met + not_met else None,
            "awaiting_verdict": sum(1 for r in done if r["signal_band"] and not r["resolution"]),
            "unmeasured": sum(1 for r in done if not r["signal_band"]),
        },
        "maintain": {
            "monitoring_intents": len(monitoring),
            "median_days_to_triage": med(triage),
            "repeat_problems": {k: v for k, v in recurring.items() if v >= 2},
        },
        "not_measured": [
            "first-pass CI success rate", "review time per PR", "time to first review",
            "change failure rate", "DORA metrics",
        ],
    }


def show(v):
    return "-" if v is None or v == {} else (", ".join(f"{k}: {n}" for k, n in v.items()) if isinstance(v, dict) else str(v))


def markdown(m):
    p, b, l, mt, bt = m["plan"], m["build"], m["learning"], m["maintain"], m["bets"]
    rows = [
        ("Plan", "Intents", show(p["intents"]), "every change starts as one"),
        ("Plan", "By status", show(p["by_status"]), ""),
        ("Plan", "Acceptance rate", show(p["acceptance_rate"]), "accepted / (accepted + rejected); low means intents are raised before they are ready"),
        ("Plan", "Median days to decision", show(p["median_days_to_decision"]), f"created to accepted or rejected, {p['decisions_measured']} measured"),
        ("Build", "Median days plan to changelog", show(b["median_days_plan_to_changelog"]), f"approved plan to shipped change, {b['changes_measured']} measured"),
        ("Build", "Plan revisions per change", show(b["mean_plan_revisions"]), "commits to a plan after its first; rework in design"),
        ("Outcome", "Bets met", show(bt["resolution_rate"]), f"of shipped intents judged by their signal band: {bt['met']} met, {bt['not_met']} not met"),
        ("Outcome", "Awaiting a verdict", show(bt["awaiting_verdict"]), "done, with a signal band, not judged yet"),
        ("Outcome", "Shipped, never checked", show(bt["unmeasured"]), f"of {bt['done']} done intents, no signal band - nobody will learn whether they worked"),
        ("Learn", "Experience-log entries", show(l["experience_log_entries"]), f"{l['user_corrections']} of them user corrections"),
        ("Learn", "Mistakes seen twice or more", show(l["repeated_classes"]), "class: count"),
        ("Learn", "Promoted to CLAUDE.md", show(l["promoted_to_claude_md"]), f"{l['promotions_declined']} declined"),
        ("Maintain", "Intents raised by monitoring", show(mt["monitoring_intents"]), ""),
        ("Maintain", "Median days to triage", show(mt["median_days_to_triage"]), "monitoring intent created to accepted or rejected"),
        ("Maintain", "Repeat problems", show(mt["repeat_problems"]), "same source raised or seen again"),
    ]
    out = ["| Stage | Metric | Value | Meaning |", "|---|---|---|---|"]
    out += [f"| {a} | {b_} | {c} | {d} |" for a, b_, c, d in rows]
    out += ["", "Not measured here (needs CI and review data from the code host): " + ", ".join(m["not_measured"]) + "."]
    return "\n".join(out)


def main(argv):
    root = next((a for a in argv if not a.startswith("--")), ".")
    m = compute(root)
    print(json.dumps(m, indent=2) if "--json" in argv else markdown(m))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
