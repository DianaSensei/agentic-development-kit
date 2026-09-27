#!/usr/bin/env python3
"""check_proposals.py - hold solution-architect's proposals to the tradeoff rubric.

    check_proposals.py <output.json>           list what the rubric is missing; exit 1 if anything
    check_proposals.py --table <output.json>   print the CHECKPOINT table (priority order, a column
                                               per proposal)

The input is the architect's JSON output, or text holding it in a ```json block. The rubric - the
dimensions, the evidence forms, what a recommendation must name - is
references/tradeoff-rubric.md; this script is its mechanical half, so a proposal cannot reach the
person with a dimension skipped, a rating nobody can check, or a recommendation that hides its costs.
"""

import json
import re
import sys

DIMENSIONS = [
    "correctness_risk",
    "reversibility",
    "convention_fit",
    "native_approach",
    "operational_load",
    "performance_and_scale",
    "cost_to_build",
]
RATINGS = {"good": 3, "fair": 2, "poor": 1, "unknown": None}
MARK = {"good": "✅", "fair": "⚠️", "poor": "❌", "unknown": "❓"}
EVIDENCE_PREFIXES = ("requirement:", "measured:", "assumption:", "doc:")
PATH_LINE = re.compile(r"[\w./-]+\.\w+:\d+")
URL = re.compile(r"https?://\S+")


def load(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    block = re.search(r"```json\s*\n(.*?)\n```", text, re.S)
    if not block:
        raise SystemExit(f"{path}: neither JSON nor a ```json block")
    return json.loads(block.group(1))


def evidence_ok(evidence):
    if not isinstance(evidence, str) or not evidence.strip():
        return False
    e = evidence.strip()
    return e.lower().startswith(EVIDENCE_PREFIXES) or bool(PATH_LINE.search(e)) or bool(URL.search(e))


def assumed(entry):
    return str(entry.get("evidence", "")).strip().lower().startswith("assumption:")


def score(entry):
    """A comparable rating, or None: unknown, or resting on an assumption."""
    if not isinstance(entry, dict) or assumed(entry):
        return None
    return RATINGS.get(entry.get("rating"))


def priority_order(data, problems):
    given = data.get("priorities")
    if not isinstance(given, list) or not given:
        problems.append("priorities: missing - state the order and its source before the proposals")
        return list(DIMENSIONS)
    order = [p.get("dimension") if isinstance(p, dict) else p for p in given]
    unknown = [d for d in order if d not in DIMENSIONS]
    missing = [d for d in DIMENSIONS if d not in order]
    if unknown:
        problems.append(f"priorities: not rubric dimensions: {', '.join(map(str, unknown))}")
    if missing:
        problems.append(f"priorities: missing {', '.join(missing)}")
    if len(set(order)) != len(order):
        problems.append("priorities: a dimension appears twice")
    if any(not isinstance(p, dict) or not str(p.get("source", "")).strip() for p in given):
        problems.append("priorities: every entry needs its source (requirement, project, profile or default)")
    return [d for d in order if d in DIMENSIONS] + missing


def check(data):
    problems, notes = [], []
    order = priority_order(data, problems)
    proposals = data.get("proposals")
    if not isinstance(proposals, list) or not proposals:
        return ["proposals: none"], notes, order

    for p in proposals:
        pid = p.get("id") or p.get("title") or "?"
        tradeoffs = p.get("tradeoffs")
        if not isinstance(tradeoffs, dict):
            problems.append(f"{pid}: no tradeoffs")
            continue
        for d in DIMENSIONS:
            entry = tradeoffs.get(d)
            if not isinstance(entry, dict):
                problems.append(f"{pid}: {d} missing - rate it, or rate it good and say why it does not apply")
                continue
            if entry.get("rating") not in RATINGS:
                problems.append(f"{pid}: {d} rating {entry.get('rating')!r} is not good/fair/poor/unknown")
            if not str(entry.get("why", "")).strip():
                problems.append(f"{pid}: {d} has no why")
            if not evidence_ok(entry.get("evidence")):
                problems.append(f"{pid}: {d} evidence {entry.get('evidence')!r} is not a path:line, a URL, "
                                "or requirement:/measured:/doc:/assumption:")
        extra = sorted(set(tradeoffs) - set(DIMENSIONS))
        if extra:
            problems.append(f"{pid}: not rubric dimensions: {', '.join(extra)}")

    if len(proposals) == 1:
        p = proposals[0]
        alts = p.get("alternatives_rejected") or []
        if not alts and not str(p.get("no_alternative_reason", "")).strip():
            problems.append("one proposal and no alternatives_rejected or no_alternative_reason - "
                            "name what it beat, or why there is nothing to beat")
        for a in alts:
            name = a.get("approach", "?") if isinstance(a, dict) else "?"
            if not isinstance(a, dict) or not a.get("loses_on") or any(d not in DIMENSIONS for d in a.get("loses_on", [])):
                problems.append(f"alternative {name!r}: loses_on must name rubric dimensions")
            elif not evidence_ok(a.get("evidence")):
                problems.append(f"alternative {name!r}: no evidence")

    recommended = [p for p in proposals if p.get("recommended")]
    if len(recommended) > 1:
        problems.append("more than one proposal is recommended")
    if len(recommended) == 1 and len(proposals) > 1:
        rec = recommended[0]
        rid = rec.get("id") or rec.get("title")
        others = [p for p in proposals if p is not rec]
        deciding = rec.get("deciding_dimensions") or []
        if not deciding or any(d not in DIMENSIONS for d in deciding):
            problems.append(f"{rid}: recommended without deciding_dimensions naming rubric dimensions")

        def s(p, d):
            return score((p.get("tradeoffs") or {}).get(d))

        hidden = [d for d in DIMENSIONS
                  if s(rec, d) is not None and any(s(o, d) is not None and s(o, d) > s(rec, d) for o in others)
                  and d not in (rec.get("costs") or [])]
        if hidden:
            problems.append(f"{rid}: recommended, but another proposal is better on {', '.join(hidden)} "
                            "and costs does not say so")

        for d in order:
            scores = [s(p, d) for p in proposals]
            known = [x for x in scores if x is not None]
            if len(set(known)) > 1 or (known and None in scores):
                if None in scores:
                    notes.append(f"{d}: the top priority where the proposals differ rests on an unknown or "
                                 "an assumption - ask before recommending")
                    break
                best = max(known)
                if s(rec, d) != best:
                    if str(rec.get("priority_override", "")).strip():
                        notes.append(f"{rid}: recommended against the priority order ({d}): "
                                     f"{rec['priority_override']}")
                    else:
                        problems.append(f"{rid}: recommended, but {d} - the top priority where the proposals "
                                        "differ - favours another; fix the ratings, the recommendation, or give "
                                        "priority_override")
                break

        if s(rec, "correctness_risk") == RATINGS["poor"] and \
                any((s(o, "correctness_risk") or 0) > RATINGS["poor"] for o in others) and \
                not str(rec.get("risk_accepted", "")).strip():
            problems.append(f"{rid}: recommended while poor on correctness_risk and another is not - only with "
                            "risk_accepted citing where the person accepted it")
    return problems, notes, order


def cell(entry):
    if not isinstance(entry, dict):
        return "❓ missing"
    rating = entry.get("rating", "unknown")
    text = str(entry.get("why", "")).replace("|", "\\|").replace("\n", " ")
    tag = " _(assumed)_" if assumed(entry) else ""
    return f"{MARK.get(rating, '❓')} {rating}{tag} - {text}"


def table(data, order):
    proposals = data.get("proposals") or []
    heads = [(p.get("title") or p.get("id") or "?") + (" ★" if p.get("recommended") else "") for p in proposals]
    lines = ["| Priority | " + " | ".join(h.replace("|", "\\|") for h in heads) + " |",
             "|---|" + "---|" * len(proposals)]
    for i, d in enumerate(order, 1):
        lines.append(f"| {i}. `{d}` | " + " | ".join(cell((p.get("tradeoffs") or {}).get(d)) for p in proposals) + " |")
    rec = [p for p in proposals if p.get("recommended")]
    if rec:
        r = rec[0]
        costs = ", ".join(r.get("costs") or []) or "none"
        lines += ["", f"★ Recommended: {r.get('title') or r.get('id')} - decided on "
                  f"{', '.join(r.get('deciding_dimensions') or []) or '?'}; costs: {costs}."]
    return "\n".join(lines)


def main(argv):
    args = [a for a in argv if a != "--table"]
    if len(args) != 1:
        print("usage: check_proposals.py [--table] <output.json>", file=sys.stderr)
        return 2
    data = load(args[0])
    problems, notes, order = check(data)
    if "--table" in argv:
        print(table(data, order))
        return 0
    for n in notes:
        print(f"note: {n}")
    for p in problems:
        print(f"problem: {p}")
    if problems:
        return 1
    print(f"OK: {len(data['proposals'])} proposal(s), {len(DIMENSIONS)} dimensions each")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
