"""waves-and-resume: units built in dependency waves; a unit that asks is answered and resumed."""
from lib import Checks, args, python, tests_pass

run, repo, start = args()
c = Checks("waves-and-resume")

c.must(run.read("feature-development/references/parallel-units.md"), "the lead read parallel-units.md")
units = [d for d in run.dispatches("unit-implementer") if not d["denied"]]
by_message = {}
for d in units:
    by_message.setdefault(d["msg"], []).append(d)
c.must(any(len(v) >= 2 for v in by_message.values()), "wave 1's units dispatched together, in one message",
       f"{len(units)} dispatch(es) in {len(by_message)} message(s)")
c.must(all("lane:" in d["input"].get("prompt", "") for d in units), "every unit carries its lane")
c.must(all(d["input"].get("model") == "sonnet" for d in units), "tight tickets built on models.build (sonnet)",
       ", ".join(str(d["input"].get("model")) for d in units))
c.expect(bool(run.calls_named("SendMessage")), "the unit that asked was resumed with SendMessage, not redone")

ok, out = tests_pass(repo)
c.must(ok, "the whole test suite passes", out)
ok, out = python(repo, "from textkit import slugify; print(slugify('hello wonderful world', max_length=12))")
c.must(ok and out == "hello", "slugify follows the user's decision: never cuts inside a word", out)
ok, out = python(repo, "from textkit import summary, top_words, word_frequencies; print(summary(''), '|', summary('b a b'))")
c.must(ok and out == "top: - | top: b (2), a (1)", "summary built on top_words, exported", out)
c.expect(bool(run.bash(r"check_conformance\.py")), "conformance checked against the tickets")
c.branch_untouched(repo, start)
c.nothing_left_behind(repo)
raise SystemExit(c.report())
