"""tickets-dispatch: units handed down by the rules - snapshot, lane, ticket, model by tier - and the
result checked against the tickets."""
from lib import Checks, args, python, tests_pass

run, repo, start = args()
c = Checks("tickets-dispatch")

c.must(run.read("feature-development/references/parallel-units.md"), "the lead read parallel-units.md")
units = [d for d in run.dispatches("unit-implementer") if not d["denied"]]
by_message = {}
for d in units:
    by_message.setdefault(d["msg"], []).append(d)
c.must(any(len(v) >= 3 for v in by_message.values()), "wave 2's three units dispatched together",
       f"{len(units)} dispatch(es) in {len(by_message)} message(s)")
c.must(all("lane:" in d["input"].get("prompt", "") and "ticket" in d["input"].get("prompt", "") for d in units),
       "every unit carries its lane and its ticket")
c.must(all(d["input"].get("model") == "sonnet" for d in units), "tight tickets built on models.build (sonnet)",
       ", ".join(str(d["input"].get("model")) for d in units))
c.must(bool(run.bash(r"snapshot\.sh take")), "wave 2 started from a snapshot of wave 1")
c.must(bool(run.bash(r"check_conformance\.py")), "conformance checked against the tickets")

ok, out = tests_pass(repo)
c.must(ok, "the whole test suite passes", out)
ok, out = python(repo, "from shop import db, orders, dashboard\n"
                       "c = db.connect(); i = orders.create_customer(c, 'Ada')\n"
                       "a = orders.place_order(c, i, 1); orders.place_order(c, i, 1); orders.cancel_order(c, a)\n"
                       "print(dashboard.render(c, i))")
c.must(ok and out == "{'name': 'Ada', 'order_count': 1}", "the dashboard shows the live count", out)
c.branch_untouched(repo, start)
c.nothing_left_behind(repo)
raise SystemExit(c.report())
