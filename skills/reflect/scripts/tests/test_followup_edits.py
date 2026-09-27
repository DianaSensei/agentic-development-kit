#!/usr/bin/env python3
"""skills/reflect/scripts/followup_edits.py: your rewrites of agent-written lines.

Run: python3 -m unittest discover -s skills/reflect/scripts/tests
"""

import importlib.util
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("followup_edits", os.path.join(HERE, "..", "followup_edits.py"))
fe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fe)

ME = "me@example.com"
TRAILER = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"


class FollowupEditsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.git("init", "-q", "-b", "main")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, email=ME):
        env = dict(os.environ, GIT_AUTHOR_NAME="me", GIT_AUTHOR_EMAIL=email,
                   GIT_COMMITTER_NAME="me", GIT_COMMITTER_EMAIL=email)
        return subprocess.run(["git", "-C", self.repo, *args], check=True, capture_output=True, text=True,
                              env=env).stdout

    def commit(self, path, text, message, email=ME):
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text)
        self.git("add", "-A", email=email)
        self.git("commit", "-q", "-m", message, email=email)

    def pairs(self, **kw):
        return fe.pairs(self.repo, "1 year ago", kw.get("author", ME), fe.AGENT_PATTERN, 40)

    BASE = "def load(path):\n    return open(path).read()\n"
    AGENT = BASE + "\n\ndef parse(text):\n    try:\n        return int(text)\n    except Exception:\n        return None\n"

    def test_a_rewrite_of_agent_lines_is_a_pair(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.AGENT, "Add parse" + TRAILER)
        mine = self.AGENT.replace("    except Exception:\n        return None\n",
                                  "    except ValueError as e:\n        raise ParseError(text) from e\n")
        self.commit("src/io.py", mine, "Parse errors are raised, not swallowed")
        found = self.pairs()
        self.assertEqual(len(found), 1)
        p = found[0]
        self.assertEqual(p["file"], "src/io.py")
        self.assertEqual(p["agent_wrote"], ["    except Exception:", "        return None"])
        self.assertEqual(p["you_made_it"], ["    except ValueError as e:", "        raise ParseError(text) from e"])
        self.assertEqual(p["your_subject"], "Parse errors are raised, not swallowed")
        self.assertEqual(p["agent_subject"], "Add parse")

    def test_rewriting_your_own_lines_is_not_a_pair(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.BASE.replace("open(path).read()", "Path(path).read_text()"), "Use pathlib")
        self.assertEqual(self.pairs(), [])

    def test_the_agent_rewriting_its_own_lines_is_not_a_pair(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.AGENT, "Add parse" + TRAILER)
        self.commit("src/io.py", self.AGENT.replace("Exception", "ValueError"), "Narrow the except" + TRAILER)
        self.assertEqual(self.pairs(), [])

    def test_someone_elses_rewrite_is_not_yours(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.AGENT, "Add parse" + TRAILER)
        self.commit("src/io.py", self.AGENT.replace("return None", "return 0"), "Default to 0",
                    email="colleague@example.com")
        self.assertEqual(self.pairs(), [])

    def test_pure_additions_next_to_agent_code_are_not_pairs(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.AGENT, "Add parse" + TRAILER)
        self.commit("src/io.py", self.AGENT + "\n\ndef dump(x):\n    return str(x)\n", "Add dump")
        self.assertEqual(self.pairs(), [])

    def test_markdown_shows_the_diff(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.AGENT, "Add parse" + TRAILER)
        self.commit("src/io.py", self.AGENT.replace("return None", "return 0"), "Default to 0")
        md = fe.markdown(self.pairs())
        self.assertIn("-        return None", md)
        self.assertIn("+        return 0", md)
        self.assertIn("No lines of an agent commit", fe.markdown([]))

    def test_session_trailer_marks_an_agent_commit_too(self):
        self.commit("src/io.py", self.BASE, "Initial loader")
        self.commit("src/io.py", self.AGENT, "Add parse\n\nClaude-Session: https://claude.ai/code/session_x\n")
        self.commit("src/io.py", self.AGENT.replace("return None", "return 0"), "Default to 0")
        self.assertEqual(len(self.pairs()), 1)


if __name__ == "__main__":
    unittest.main()
