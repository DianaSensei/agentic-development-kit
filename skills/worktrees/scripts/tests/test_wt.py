#!/usr/bin/env python3
"""skills/worktrees/scripts/wt.py: task workspaces across repositories, and nothing that holds work lost.

Run: python3 -m unittest discover -s skills/worktrees/scripts/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wt.py")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = os.path.realpath(self.tmp.name)
        self.root = os.path.join(self.base, "worktrees")
        self.env = dict(ENV, HOME=self.base, ADK_WORKTREES_CONFIG=os.path.join(self.base, "cfg.json"))
        self.env.pop("ADK_WORKTREES_ROOT", None)
        self.repos = {}
        for name in ("api", "web"):
            self.repos[name] = self.clone(name, {"README.md": f"{name}\n"} |
                                          ({"CLAUDE.md": "api rules\n"} if name == "api" else {}))
        self.wt("init", "--root", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    # -- helpers
    def git(self, cwd, *args, check=True):
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, env=ENV)
        if check and r.returncode:
            raise AssertionError(f"git {args}: {r.stderr}")
        return r.stdout.strip()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def read(self, path):
        with open(path) as f:
            return f.read()

    def clone(self, name, files):
        origin = os.path.join(self.base, "origin", f"{name}.git")
        self.git(self.base, "init", "-q", "--bare", "-b", "main", origin)
        seed = os.path.join(self.base, "seed", name)
        self.git(self.base, "clone", "-q", origin, seed)
        for rel, text in files.items():
            self.write(os.path.join(seed, rel), text)
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", "init")
        self.git(seed, "push", "-q", "origin", "HEAD:main")
        checkout = os.path.join(self.base, "code", name)
        self.git(self.base, "clone", "-q", origin, checkout)
        return checkout

    def commit_upstream(self, name, rel, text):
        """A teammate's commit lands on origin/main."""
        seed = os.path.join(self.base, "seed", name)
        self.git(seed, "pull", "-q", "origin", "main")
        self.write(os.path.join(seed, rel), text)
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", f"upstream {rel}")
        self.git(seed, "push", "-q", "origin", "HEAD:main")

    def wt(self, *args, ok=True):
        r = subprocess.run(["python3", SCRIPT, *args], capture_output=True, text=True, env=self.env, timeout=60)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def task_path(self, task, repo=""):
        return os.path.join(self.root, task, repo) if repo else os.path.join(self.root, task)

    def commit_in(self, task, repo, rel="change.txt", text="x\n"):
        path = self.task_path(task, repo)
        self.write(os.path.join(path, rel), text)
        self.git(path, "add", "-A")
        self.git(path, "commit", "-qm", f"work on {rel}")

    def status(self, task):
        out = json.loads(self.wt("status", task, "--json").stdout)
        return out["tasks"][0]["repos"]

    # -- creating
    def test_a_task_holds_a_worktree_of_each_repo_on_one_branch(self):
        out = self.wt("new", "billing-feat-abc", self.repos["api"], self.repos["web"], "--note", "Invoice totals").stdout
        self.assertIn("registered api", out)
        for repo in ("api", "web"):
            path = self.task_path("billing-feat-abc", repo)
            self.assertEqual(self.git(path, "branch", "--show-current"), "billing-feat-abc")
            self.assertEqual(self.git(path, "rev-parse", "HEAD"), self.git(self.repos[repo], "rev-parse", "origin/main"))
        claude = self.read(os.path.join(self.task_path("billing-feat-abc"), "CLAUDE.md"))
        self.assertIn("Invoice totals", claude)
        self.assertIn("@api/CLAUDE.md", claude)          # api has instructions of its own
        self.assertNotIn("@web/CLAUDE.md", claude)       # web has none
        self.assertIn("git -C <folder>", claude)

    def test_registered_names_work_after_first_use(self):
        self.wt("repo", "add", "backend", self.repos["api"])
        self.wt("new", "t1", "backend", "--no-fetch")
        self.assertTrue(os.path.isdir(self.task_path("t1", "backend")))

    def test_an_unknown_repo_is_named_with_the_ones_that_exist(self):
        self.wt("repo", "add", "backend", self.repos["api"])
        r = self.wt("new", "t18", "frontend", "--no-fetch", ok=False)
        self.assertIn("frontend: not a registered repository (backend)", r.stderr)
        self.assertFalse(os.path.exists(self.task_path("t18")))

    def test_creating_is_all_or_none(self):
        self.git(self.repos["web"], "checkout", "-q", "-b", "busy")   # web's main checkout holds the branch
        r = self.wt("new", "busy", self.repos["api"], self.repos["web"], "--no-fetch", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.task_path("busy")))
        self.assertEqual(self.git(self.repos["api"], "worktree", "list").count("\n"), 0)
        self.assertEqual(self.git(self.repos["api"], "branch", "--list", "busy"), "")

    def test_an_existing_remote_branch_is_picked_up_not_recreated(self):
        seed = os.path.join(self.base, "seed", "api")
        self.git(seed, "checkout", "-q", "-b", "shared")
        self.write(os.path.join(seed, "shared.txt"), "s\n")
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", "shared work")
        self.git(seed, "push", "-q", "origin", "shared")
        self.wt("new", "shared", self.repos["api"])
        path = self.task_path("shared", "api")
        self.assertTrue(os.path.isfile(os.path.join(path, "shared.txt")))
        self.assertEqual(self.git(path, "rev-parse", "--abbrev-ref", "@{u}"), "origin/shared")

    def test_add_brings_in_a_repo_and_keeps_the_users_notes(self):
        self.wt("new", "t2", self.repos["api"], "--no-fetch")
        md = os.path.join(self.task_path("t2"), "CLAUDE.md")
        self.write(md, self.read(md) + "\nMy notes: ask Lan about rounding.\n")
        self.wt("add", "t2", self.repos["web"], "--no-fetch")
        text = self.read(md)
        self.assertIn("My notes: ask Lan about rounding.", text)
        self.assertIn("`web/`", text)
        self.assertEqual(text.count("# Task: t2"), 1)

    def test_copy_and_setup_prepare_each_new_worktree(self):
        self.write(os.path.join(self.repos["api"], ".env"), "SECRET=1\n")
        self.wt("repo", "add", "api", self.repos["api"], "--copy", ".env", "--setup", "echo ready > setup.log")
        self.wt("new", "t3", "api", "--no-fetch")
        self.assertEqual(self.read(os.path.join(self.task_path("t3", "api"), ".env")), "SECRET=1\n")
        self.assertTrue(os.path.isfile(os.path.join(self.task_path("t3", "api"), "setup.log")))

    def test_the_base_is_origins_default_branch(self):
        seed = os.path.join(self.base, "seed", "api")
        self.git(seed, "push", "-q", "origin", "HEAD:develop")
        self.git(self.repos["api"], "fetch", "-q", "origin")
        self.git(self.repos["api"], "remote", "set-head", "origin", "develop")
        out = self.wt("new", "t14", self.repos["api"]).stdout
        self.assertIn("(base origin/develop)", out)
        self.assertNotIn("fetch", out)                    # a fetch that worked says nothing

    def test_a_repo_without_a_remote_branches_from_its_local_default(self):
        local = os.path.join(self.base, "code", "tool")
        self.git(self.base, "init", "-q", "-b", "main", local)
        self.write(os.path.join(local, "a.txt"), "a\n")
        self.git(local, "add", "-A")
        self.git(local, "commit", "-qm", "init")
        self.git(local, "checkout", "-q", "-b", "elsewhere")   # the main checkout is on another branch
        out = self.wt("new", "t15", local).stdout
        self.assertIn("(base main)", out)
        self.git(local, "branch", "-q", "-m", "main", "trunk")  # no main, no master: its current branch
        self.assertIn("(base elsewhere)", self.wt("new", "t16", "tool").stdout)

    def test_an_unreachable_origin_warns_and_goes_on(self):
        self.git(self.repos["web"], "remote", "set-url", "origin", os.path.join(self.base, "nowhere.git"))
        out = self.wt("new", "t17", self.repos["web"]).stdout
        self.assertIn("web: fetch failed", out)
        self.assertTrue(os.path.isdir(self.task_path("t17", "web")))

    def test_the_config_is_user_scoped(self):
        env = {k: v for k, v in self.env.items() if k not in ("ADK_WORKTREES_CONFIG", "XDG_CONFIG_HOME")}
        subprocess.run(["python3", SCRIPT, "init", "--root", self.root], env=env, check=True, capture_output=True)
        self.assertTrue(os.path.isfile(os.path.join(self.base, ".config", "adk", "worktrees.json")))
        xdg = os.path.join(self.base, "xdg")
        subprocess.run(["python3", SCRIPT, "init", "--root", self.root], env=dict(env, XDG_CONFIG_HOME=xdg),
                       check=True, capture_output=True)
        self.assertTrue(os.path.isfile(os.path.join(xdg, "adk", "worktrees.json")))

    def test_without_a_root_the_user_is_asked(self):
        env = dict(self.env, ADK_WORKTREES_CONFIG=os.path.join(self.base, "other.json"))
        r = subprocess.run(["python3", SCRIPT, "status"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Ask the user where task folders should live", r.stderr)

    # -- seeing
    def test_status_tells_each_state_apart(self):
        self.wt("new", "t4", self.repos["api"], self.repos["web"])
        self.assertEqual({r["state"] for r in self.status("t4").values()}, {"new"})
        self.write(os.path.join(self.task_path("t4", "api"), "wip.txt"), "w\n")
        self.commit_in("t4", "web")
        s = self.status("t4")
        self.assertEqual(s["api"]["state"], "uncommitted")
        self.assertEqual((s["web"]["state"], s["web"]["ahead"], s["web"]["unpushed"]), ("unpushed", 1, 1))
        self.git(self.task_path("t4", "web"), "push", "-q", "-u", "origin", "t4")
        self.assertEqual(self.status("t4")["web"]["state"], "pushed")

    def test_the_overview_shows_worktrees_outside_the_root(self):
        self.wt("new", "t5", self.repos["api"], "--no-fetch")
        stray = os.path.join(self.base, "elsewhere")
        self.git(self.repos["api"], "worktree", "add", "-q", "-b", "stray", stray)
        unit = os.path.join(self.repos["api"], ".claude", "worktrees", "agent-u1")
        self.git(self.repos["api"], "worktree", "add", "-q", "-b", "unit", unit)
        out = self.wt("status").stdout
        self.assertIn("t5  branch t5", out)
        self.assertIn(stray, out)
        self.assertNotIn("agent-u1", out)                # the kit's own unit worktrees are feature-development's

    # -- keeping up
    def test_sync_merges_the_base_into_each_repo(self):
        self.wt("new", "t6", self.repos["api"], self.repos["web"])
        self.commit_in("t6", "api")
        self.commit_upstream("api", "upstream.txt", "u\n")
        out = self.wt("sync", "t6").stdout
        self.assertIn("api: merged origin/main (1 commit(s))", out)
        self.assertIn("web: up to date", out)
        self.assertTrue(os.path.isfile(os.path.join(self.task_path("t6", "api"), "upstream.txt")))

    def test_a_conflict_leaves_the_repo_as_it_was(self):
        self.wt("new", "t7", self.repos["api"])
        self.commit_in("t7", "api", "README.md", "mine\n")
        self.commit_upstream("api", "README.md", "theirs\n")
        head = self.git(self.task_path("t7", "api"), "rev-parse", "HEAD")
        r = self.wt("sync", "t7", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("conflicts with origin/main in README.md", r.stdout)
        path = self.task_path("t7", "api")
        self.assertEqual(self.git(path, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(path, "status", "--porcelain"), "")

    def test_sync_skips_uncommitted_work_and_will_not_rebase_a_pushed_branch(self):
        self.wt("new", "t8", self.repos["api"], self.repos["web"])
        self.write(os.path.join(self.task_path("t8", "api"), "wip.txt"), "w\n")
        self.commit_in("t8", "web")
        self.git(self.task_path("t8", "web"), "push", "-q", "-u", "origin", "t8")
        self.commit_upstream("api", "u.txt", "u\n")
        self.commit_upstream("web", "u.txt", "u\n")
        out = self.wt("sync", "t8", "--rebase", ok=False).stdout
        self.assertIn("api: skipped - 1 uncommitted change(s)", out)
        self.assertIn("web: skipped - the branch is pushed", out)

    def test_run_runs_in_each_repo_and_reports_failures(self):
        self.wt("new", "t9", self.repos["api"], self.repos["web"], "--no-fetch")
        out = self.wt("run", "t9", "--", "git", "branch", "--show-current").stdout
        self.assertEqual(out.count("t9"), 2)
        r = self.wt("run", "t9", "--", "test -f CLAUDE.md", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed in: web (1)", r.stdout)

    # -- removing
    def test_remove_refuses_work_that_would_be_lost(self):
        self.wt("new", "t10", self.repos["api"], self.repos["web"])
        self.write(os.path.join(self.task_path("t10", "api"), "wip.txt"), "w\n")
        self.commit_in("t10", "web")
        r = self.wt("remove", "t10", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("api: 1 uncommitted", r.stderr)
        self.assertIn("web: 0 uncommitted, 1 unpushed", r.stderr)
        self.assertTrue(os.path.isdir(self.task_path("t10", "api")))

    def test_force_keeps_the_work_itself(self):
        self.wt("new", "t11", self.repos["api"], self.repos["web"])
        self.write(os.path.join(self.task_path("t11", "api"), "wip.txt"), "w\n")
        self.commit_in("t11", "web")
        out = self.wt("remove", "t11", "--force").stdout
        patch = os.path.join(self.root, ".removed", "t11", "api.patch")
        self.assertIn("wip.txt", self.read(patch))
        self.assertIn("kept branch t11 (1 unpushed commit(s))", out)
        self.assertEqual(self.git(self.repos["web"], "branch", "--list", "t11"), "t11")
        self.assertFalse(os.path.exists(self.task_path("t11")))

    def test_a_clean_task_goes_with_its_branches(self):
        self.wt("new", "t12", self.repos["api"])
        self.wt("remove", "t12")
        self.assertFalse(os.path.exists(self.task_path("t12")))
        self.assertEqual(self.git(self.repos["api"], "branch", "--list", "t12"), "")
        self.assertEqual(self.git(self.repos["api"], "worktree", "list").count("\n"), 0)

    def test_the_users_own_files_in_a_task_folder_are_kept(self):
        self.wt("new", "t13", self.repos["api"], "--no-fetch")
        self.write(os.path.join(self.task_path("t13"), "notes.md"), "n\n")
        out = self.wt("remove", "t13").stdout
        self.assertIn("still holds notes.md", out)
        self.assertTrue(os.path.isfile(os.path.join(self.task_path("t13"), "notes.md")))

    def test_prune_removes_only_what_is_already_in_its_base(self):
        self.wt("new", "merged", self.repos["api"])
        self.commit_in("merged", "api")
        self.git(self.task_path("merged", "api"), "push", "-q", "origin", "HEAD:main")   # merged
        self.wt("new", "open", self.repos["web"])
        self.commit_in("open", "web")
        self.wt("new", "squashed", self.repos["api"])
        self.commit_in("squashed", "api", "sq.txt")
        path = self.task_path("squashed", "api")
        self.git(path, "push", "-q", "-u", "origin", "squashed")
        self.git(path, "push", "-q", "origin", "--delete", "squashed")                  # merged by squash, deleted
        out = self.wt("prune").stdout
        self.assertIn("would remove merged", out)
        self.assertNotIn("would remove open", out)
        self.assertIn("check squashed", out)
        self.assertTrue(os.path.isdir(self.task_path("merged")))
        self.wt("prune", "--yes")
        self.assertFalse(os.path.exists(self.task_path("merged")))
        self.assertTrue(os.path.isdir(self.task_path("open")))
        self.assertTrue(os.path.isdir(self.task_path("squashed")))

    # -- the manifest, dependencies, checks
    def manifest(self, task):
        return json.loads(self.read(os.path.join(self.task_path(task), "task.json")))

    def tag(self, name, tag):
        seed = os.path.join(self.base, "seed", name)
        self.git(seed, "tag", tag)
        self.git(seed, "push", "-q", "origin", tag)

    def test_a_dependency_is_pinned_not_branched(self):
        self.tag("web", "v1")
        self.commit_upstream("web", "later.txt", "l\n")             # main moves on past v1
        self.wt("new", "t20", self.repos["api"], "--dep", self.repos["web"] + "@v1")
        web = self.task_path("t20", "web")
        v1 = self.git(self.repos["web"], "rev-parse", "v1^{commit}")
        self.assertEqual(self.git(web, "rev-parse", "HEAD"), v1)
        self.assertEqual(self.git(web, "branch", "--show-current"), "")          # detached
        self.assertEqual(self.git(self.repos["web"], "branch", "--list", "t20"), "")
        m = self.manifest("t20")["repositories"]
        self.assertEqual((m["web"]["role"], m["web"]["ref"], m["web"]["commit"]), ("dependency", "v1", v1))
        self.assertEqual((m["api"]["role"], m["api"]["base"]), ("edit", "origin/main"))
        self.assertTrue(m["api"]["url"].endswith("api.git"))
        claude = self.read(os.path.join(self.task_path("t20"), "CLAUDE.md"))
        self.assertIn("dependency - do not edit", claude)
        self.assertIn("Dependencies are pinned", claude)

    def test_a_dependency_by_branch_follows_origin_and_is_left_alone_by_sync(self):
        self.commit_upstream("web", "fresh.txt", "f\n")                # the local main is now stale
        self.wt("new", "t21", self.repos["api"], "--dep", self.repos["web"] + "@main")
        pinned = self.git(self.task_path("t21", "web"), "rev-parse", "HEAD")
        self.assertEqual(pinned, self.git(self.repos["web"], "rev-parse", "origin/main"))
        self.commit_upstream("web", "newer.txt", "n\n")
        out = self.wt("sync", "t21").stdout
        self.assertIn("web: a dependency, pinned at origin/main", out)
        self.assertEqual(self.git(self.task_path("t21", "web"), "rev-parse", "HEAD"), pinned)
        self.wt("pin", "t21", "web", "main")
        self.assertEqual(self.git(self.task_path("t21", "web"), "rev-parse", "HEAD"),
                         self.git(self.repos["web"], "rev-parse", "origin/main"))
        self.assertEqual(self.manifest("t21")["repositories"]["web"]["commit"],
                         self.git(self.repos["web"], "rev-parse", "origin/main"))

    def test_each_edit_repo_can_have_its_own_base(self):
        seed = os.path.join(self.base, "seed", "web")
        self.git(seed, "push", "-q", "origin", "HEAD:release")
        out = self.wt("new", "t22", self.repos["api"], self.repos["web"] + "@origin/release").stdout
        self.assertIn("api: t22/api on t22 (base origin/main)", out)
        self.assertIn("web: t22/web on t22 (base origin/release)", out)

    def test_a_changed_dependency_shows_and_is_not_lost(self):
        self.wt("new", "t23", self.repos["api"], "--dep", self.repos["web"])
        web = self.task_path("t23", "web")
        self.write(os.path.join(web, "build-output.bin"), "b\n")         # untracked: what a build leaves
        self.assertEqual(self.status("t23")["web"]["state"], "pinned")
        self.write(os.path.join(web, "README.md"), "edited\n")
        self.assertEqual(self.status("t23")["web"]["state"], "modified")
        r = self.wt("remove", "t23", ok=False)
        self.assertIn("web: a dependency with 1 changed file(s)", r.stderr)
        self.wt("remove", "t23", "--force")
        self.assertIn("edited", self.read(os.path.join(self.root, ".removed", "t23", "web.patch")))

    def test_run_skips_dependencies_unless_asked(self):
        self.wt("new", "t24", self.repos["api"], "--dep", self.repos["web"], "--no-fetch")
        self.assertNotIn("== web", self.wt("run", "t24", "--", "true").stdout)
        self.assertIn("== web", self.wt("run", "t24", "--all", "--", "true").stdout)

    def test_check_runs_the_task_as_a_whole_and_records_every_commit(self):
        self.wt("new", "t25", self.repos["api"], "--dep", self.repos["web"],
                "--build", "test -f api/README.md && test -f web/README.md",
                "--test", "echo $ADK_TASK:$COMPOSE_PROJECT_NAME > ran.txt")
        out = self.wt("check", "t25").stdout
        self.assertIn("passed", out)
        self.assertEqual(self.read(os.path.join(self.task_path("t25"), "ran.txt")), "t25:t25\n")
        lines = self.read(os.path.join(self.task_path("t25"), "checks.jsonl")).splitlines()
        rec = json.loads(lines[-1])
        self.assertEqual(rec["result"], "passed")
        self.assertEqual(rec["repositories"]["api"]["commit"], self.git(self.task_path("t25", "api"), "rev-parse", "HEAD"))
        self.assertEqual(rec["repositories"]["web"]["role"], "dependency")
        self.commit_in("t25", "api")
        st = json.loads(self.wt("status", "t25", "--json").stdout)["tasks"][0]["last_check"]
        self.assertEqual((st["result"], st["changed_since"]), ("passed", ["api"]))
        r = self.wt("check", "t25", "--", "exit 3", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed", r.stdout)

    def test_check_without_commands_says_where_to_put_them(self):
        self.wt("new", "t26", self.repos["api"], "--no-fetch")
        r = self.wt("check", "t26", ok=False)
        self.assertIn("has no build or test commands", r.stderr)
        self.assertIn("task.json", r.stderr)

    def test_each_task_has_an_environment_of_its_own(self):
        self.wt("new", "t27", self.repos["api"], "--no-fetch")
        self.wt("new", "t28", self.repos["web"], "--no-fetch")
        a, b = self.manifest("t27")["runtime"]["port_offset"], self.manifest("t28")["runtime"]["port_offset"]
        self.assertNotEqual(a, b)
        m = self.manifest("t27")
        m["env"] = {"MAVEN_OPTS": "-Dmaven.repo.local=${ADK_TASK_CACHE}/m2"}
        self.write(os.path.join(self.task_path("t27"), "task.json"), json.dumps(m))
        self.wt("refresh", "t27")
        env = self.read(os.path.join(self.task_path("t27"), "task.env"))
        self.assertIn(f"ADK_PORT_OFFSET={a}", env)
        self.assertIn("-Dmaven.repo.local=" + os.path.join(self.task_path("t27"), ".cache", "m2"), env)
        out = self.wt("run", "t27", "--", "echo $MAVEN_OPTS").stdout
        self.assertIn(os.path.join(self.task_path("t27"), ".cache", "m2"), out)

    def test_extras_are_copied_not_linked_and_go_with_the_task(self):
        data = os.path.join(self.base, "data", "fixtures")
        self.write(os.path.join(data, "sample.json"), "{}\n")
        self.wt("new", "t29", self.repos["api"], "--extra", data, "--no-fetch")
        copied = os.path.join(self.task_path("t29"), "fixtures", "sample.json")
        self.assertTrue(os.path.isfile(copied))
        self.assertFalse(os.path.islink(os.path.dirname(copied)))
        self.assertEqual(self.manifest("t29")["external_paths"], [{"source": data, "destination": "fixtures"}])
        self.wt("remove", "t29")
        self.assertFalse(os.path.exists(self.task_path("t29")))
        self.assertTrue(os.path.isfile(os.path.join(data, "sample.json")))
        r = self.wt("new", "t30", self.repos["api"], "--extra", data + ":api", "--no-fetch", ok=False)
        self.assertIn("api: the task folder already uses that name", r.stderr)
        self.assertFalse(os.path.exists(self.task_path("t30")))

    def test_restore_rebuilds_a_task_from_its_manifest(self):
        self.tag("web", "v1")
        self.wt("new", "t31", self.repos["api"], "--dep", self.repos["web"] + "@v1", "--test", "true")
        self.commit_in("t31", "api")
        self.git(self.task_path("t31", "api"), "push", "-q", "-u", "origin", "t31")
        out = self.wt("remove", "t31").stdout
        kept = os.path.join(self.root, ".removed", "t31", "task.json")
        self.assertIn(f"wt.py restore {kept}", out)
        self.wt("restore", kept)
        api = self.task_path("t31", "api")
        self.assertTrue(os.path.isfile(os.path.join(api, "change.txt")))             # the pushed branch, picked up
        self.assertEqual(self.git(self.task_path("t31", "web"), "rev-parse", "HEAD"),
                         self.git(self.repos["web"], "rev-parse", "v1^{commit}"))
        self.assertEqual(self.manifest("t31")["test"], ["true"])

    def test_restore_on_another_machine_clones_what_is_missing(self):
        self.wt("new", "t32", self.repos["api"], "--dep", self.repos["web"], "--no-fetch")
        manifest = os.path.join(self.base, "shared-task.json")
        self.write(manifest, self.read(os.path.join(self.task_path("t32"), "task.json")))
        other = dict(self.env, ADK_WORKTREES_CONFIG=os.path.join(self.base, "other.json"))
        def wt2(*args, ok=True):
            r = subprocess.run(["python3", SCRIPT, *args], capture_output=True, text=True, env=other, timeout=60)
            if ok:
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r
        m = json.loads(self.read(manifest))
        for r in m["repositories"].values():
            r["source"] = "/nowhere"                                        # a path from the other machine
        self.write(manifest, json.dumps(m))
        wt2("init", "--root", os.path.join(self.base, "root2"))
        r = wt2("restore", manifest, ok=False)
        self.assertIn("wt.py init --sources", r.stderr)
        wt2("init", "--sources", os.path.join(self.base, "src2"))
        out = wt2("restore", manifest).stdout
        self.assertIn("cloning", out)
        self.assertTrue(os.path.isdir(os.path.join(self.base, "src2", "api", ".git")))
        self.assertTrue(os.path.isdir(os.path.join(self.base, "root2", "t32", "web")))

    def test_an_untouched_task_is_not_pruned_even_after_sync(self):
        self.wt("new", "fresh", self.repos["api"])
        self.commit_upstream("api", "u.txt", "u\n")
        self.wt("sync", "fresh")
        self.assertEqual(self.status("fresh")["api"]["state"], "new")
        out = self.wt("prune", "--yes").stdout
        self.assertIn("kept fresh: nothing done in it yet", out)
        self.assertTrue(os.path.isdir(self.task_path("fresh")))

    def test_a_missing_base_is_not_taken_for_pushed(self):
        local = os.path.join(self.base, "code", "tool")
        self.git(self.base, "init", "-q", "-b", "main", local)
        self.write(os.path.join(local, "a.txt"), "a\n")
        self.git(local, "add", "-A")
        self.git(local, "commit", "-qm", "init")
        self.wt("new", "t33", local)
        self.commit_in("t33", "tool")
        m = self.manifest("t33")
        m["repositories"]["tool"]["base"] = "gone-branch"
        self.write(os.path.join(self.task_path("t33"), "task.json"), json.dumps(m))
        self.assertEqual(self.status("t33")["tool"]["state"], "unknown")
        r = self.wt("remove", "t33", ok=False)
        self.assertIn("its base gone-branch is gone", r.stderr)

    def test_a_task_made_by_0_21_is_read_and_migrated(self):
        self.wt("new", "old", self.repos["api"], "--no-fetch")
        d = self.task_path("old")
        m = self.manifest("old")
        legacy = {"task": "old", "branch": "old", "created": m["created"],
                  "repos": {"api": {"source": m["repositories"]["api"]["source"], "base": "origin/main"}}}
        os.remove(os.path.join(d, "task.json"))
        self.write(os.path.join(d, ".adk-task.json"), json.dumps(legacy))
        self.assertEqual(self.status("old")["api"]["role"], "edit")
        self.wt("refresh", "old")
        self.assertFalse(os.path.exists(os.path.join(d, ".adk-task.json")))
        self.assertEqual(self.manifest("old")["repositories"]["api"]["role"], "edit")


if __name__ == "__main__":
    unittest.main()
