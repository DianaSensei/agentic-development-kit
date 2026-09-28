"""tests-bite: the self-check breaks the changed lines, finds the hollow test, and the tests written
in its place catch every mutant."""
import os
import subprocess
import sys

from lib import Checks, args, tests_pass

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
run, repo, start = args()
c = Checks("tests-bite")

c.must(bool(run.bash(r"mutate_changed\.py")), "the self-check ran mutate_changed.py")
ok, out = tests_pass(repo)
c.must(ok, "the whole test suite passes", out)
r = subprocess.run([sys.executable, os.path.join(KIT, "skills/code-review-skill/scripts/mutate_changed.py"),
                    "--test", f"{sys.executable} -m unittest discover -s tests -t ."],
                   cwd=repo, capture_output=True, text=True, timeout=600)
c.must(r.returncode == 0, "the tests now kill every mutant of the change", r.stdout.strip()[-400:])
with open(os.path.join(repo, "src/shop/pricing.py")) as f:
    c.must("total >= 100" in f.read(), "the code under test was left as written - the tests changed, not the rule")
c.branch_untouched(repo, start)
raise SystemExit(c.report())
