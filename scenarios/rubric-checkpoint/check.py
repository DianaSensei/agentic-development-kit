"""rubric-checkpoint: priorities first, every proposal rated on the rubric with evidence, the architect's
output checked by script, and no code before the person chooses."""
import re

from lib import Checks, args, git

DIMENSIONS = ["correctness_risk", "reversibility", "performance_and_scale", "operational_load",
              "convention_fit", "native_approach", "cost_to_build"]
run, repo, start = args()
c = Checks("rubric-checkpoint")

architects = [d for d in run.dispatches("solution-architect") if not d["denied"]]
c.must(bool(architects), "solution-architect designed the proposals")
c.must(all(d["input"].get("model") in (None, "opus") for d in architects),
       "the architect runs on models.plan (opus), not a cheaper model",
       ", ".join(str(d["input"].get("model")) for d in architects))
c.must(bool(run.bash(r"check_proposals\.py")), "the lead checked the proposals with check_proposals.py")
text = run.lead_text()
missing = [d for d in DIMENSIONS if d not in text]
c.must(not missing, "the Checkpoint shows all seven rubric dimensions", "missing: " + ", ".join(missing))
c.expect(bool(re.search(r"performance_and_scale[^\n]{0,200}(?i:decid)|(?i:decid)[^\n]{0,200}performance_and_scale", text)),
         "the recommendation names performance_and_scale - first for this project - as what decided it")
changed = git(repo, "status", "--porcelain", "--", "src", "db", "tests")
c.must(not changed, "no code written before the person chose", changed)
c.branch_untouched(repo, start)
raise SystemExit(c.report())
