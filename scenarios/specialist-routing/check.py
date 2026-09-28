"""specialist-routing: a code-writing specialist's task goes through a unit - with its ticket, lane
and model - never straight to the specialist."""
from lib import Checks, args, python, tests_pass

run, repo, start = args()
c = Checks("specialist-routing")

direct = [d for d in run.dispatches("python-engineer") if not d["denied"]]
c.must(not direct, "the specialist was never dispatched directly", f"{len(direct)} direct dispatch(es)")
units = [d for d in run.dispatches("unit-implementer") if not d["denied"]]
routed = [d for d in units if "specialist" in d["input"].get("prompt", "")
          and "python-engineer" in d["input"].get("prompt", "")]
c.must(bool(routed), "U2 went through a unit-implementer naming python-engineer as its specialist")
c.must(all("lane:" in d["input"].get("prompt", "") for d in routed), "the routed unit carries its lane")
c.must(all(d["input"].get("model") == "sonnet" for d in routed), "the routed unit runs on models.build (sonnet)",
       ", ".join(str(d["input"].get("model")) for d in routed))
ok, out = tests_pass(repo)
c.must(ok, "the whole test suite passes", out)
ok, out = python(repo, "from textkit import slugify; print(slugify('hello wonderful world', max_length=12))")
c.must(ok and out == "hello", "slugify follows the user's decision", out)
c.branch_untouched(repo, start)
c.nothing_left_behind(repo)
raise SystemExit(c.report())
