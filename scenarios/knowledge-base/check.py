"""knowledge-base: the workflow reads the team's notes on the system it changes before deciding anything,
carries the decision and the rule into its analysis, and raises that the request contradicts the rule
instead of picking a side. A headless run cannot ask, so it writes no note and no code."""
import re

from lib import Checks, args, git

run, repo, start = args()
c = Checks("knowledge-base")

searched = run.mcp("basic-memory", "search_notes") + run.mcp("basic-memory", "build_context")
c.must(bool(searched), "the workflow searched the knowledge base")
text = run.lead_text() + "\n" + "\n".join(str(d["input"].get("prompt", "")) for d in run.dispatches("business-analyst"))
c.must(bool(re.search(r"(?i)member discount", text)) and bool(re.search(r"(?i)flat|10\.00|10 off|10 less", text)),
       "the analysis carries the Member discount rule (a flat 10.00 off)")
CONFLICT = r"conflict|contradict|differ|disagree|mismatch|inconsisten"
c.must(bool(re.search(rf"(?is)10\s*%.{{0,400}}({CONFLICT})|({CONFLICT}).{{0,400}}10\s*%", text)),
       "the request's 10% is raised against the rule, not silently picked")
c.expect(bool(re.search(r"(?i)integer cents|Money is integer cents", text)),
         "the integer-cents decision is carried into the analysis")
analysts = run.dispatches("business-analyst")      # none at light depth: the analysis is inline
c.expect(not analysts or any(re.search(r"(?i)member discount", str(d["input"].get("prompt", ""))) for d in analysts),
         "a business analyst, when there is one, got the notes in its prompt")
c.must(not run.mcp("basic-memory", "write_note") and not run.mcp("basic-memory", "edit_note"),
       "no note written without the user's yes")
c.must(not git(repo, "status", "--porcelain", "--", "src", "tests"), "no code written before the person chose")
c.branch_untouched(repo, start)
raise SystemExit(c.report())
