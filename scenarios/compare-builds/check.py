"""compare-builds: both proposals built side by side, measured the same way, and nothing applied before
the person picks."""
import os
import re

from lib import Checks, args

run, repo, start = args()
c = Checks("compare-builds")

units = [d for d in run.dispatches("unit-implementer") if not d["denied"]]
by_message = {}
for d in units:
    by_message.setdefault(d["msg"], []).append(d)
c.must(any(len(v) >= 2 for v in by_message.values()), "both candidates dispatched together, in one message",
       f"{len(units)} dispatch(es)")
c.must(all("candidate" in d["input"].get("prompt", "") for d in units), "each dispatch says it is a candidate")
c.must(not os.path.exists(os.path.join(repo, "src/accounts/dedupe.py")),
       "neither candidate applied to the working tree before the person chose")
text = run.final_text()
c.must(bool(re.search(r"sharp|ß|straße|STRASSE|fullwidth", text, re.I)),
       "the comparison reports the contract tests only one candidate passes")
c.must(bool(re.search(r"(?i:recommend)\w*[^.\n]{0,120}\b(B|Proposal B|Candidate B)\b"
                     r"|\b(B|Candidate B|Proposal B)\b[^.\n]{0,60}(?i:recommend)", text)),
       "the recommendation is B, from the measured facts")
c.expect(any(re.search(r"worktrees?/", cmd) and "unittest" in cmd for cmd in run.bash(r"unittest")),
         "the lead ran each candidate's whole suite itself")
c.branch_untouched(repo, start)
raise SystemExit(c.report())
