#!/usr/bin/env python3
"""scenarios/run.py: a session that hangs or overruns is stopped, with everything it started.

Run: python3 -m unittest discover -s scenarios/tests
"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import run  # noqa: E402


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    with open(f"/proc/{pid}/stat") as f:          # a zombie is gone for our purposes
        return f.read().split(")")[-1].split()[0] != "Z"


class Supervise(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.transcript = os.path.join(self.tmp.name, "transcript.jsonl")
        self.pidfile = os.path.join(self.tmp.name, "child.pid")
        run.POLL = 0.2

    def tearDown(self):
        run.POLL = 5
        self.tmp.cleanup()

    def session(self, script, timeout=60, idle=60):
        with open(self.transcript, "w") as out, open(os.path.join(self.tmp.name, "err"), "w") as err:
            began = time.time()
            run.supervise(["bash", "-c", script], self.tmp.name, out, err, self.transcript, "s", timeout, idle)
            return time.time() - began

    def test_a_session_that_finishes_is_left_alone(self):
        self.assertLess(self.session("echo '{}'"), 2)

    def test_a_silent_session_is_stopped_with_what_it_started(self):
        took = self.session(f"echo '{{}}'; sleep 300 & echo $! > {self.pidfile}; wait", idle=1)
        self.assertLess(took, 10)
        with open(self.pidfile) as f:
            child = int(f.read())
        self.assertFalse(alive(child), "a process the session started outlived it")

    def test_a_session_that_keeps_talking_is_stopped_at_the_timeout(self):
        took = self.session("while true; do echo '{}'; sleep 0.1; done", timeout=2, idle=1)
        self.assertLess(took, 10)
        self.assertGreaterEqual(took, 2)


if __name__ == "__main__":
    unittest.main()
