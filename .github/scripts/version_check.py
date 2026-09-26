#!/usr/bin/env python3
"""Does this change need a new plugin version, and does it have one?

Installed plugins update only when `version` in their plugin.json changes. The
kit is four plugins from one marketplace (the core at the root, the stack
plugins under plugins/) that share one version. A change to anything the plugin ships, merged without a bump, never
reaches the people who already have it installed - which is how 0.1.2 stayed the
version through eleven feature PRs.

  version_check.py check <base>    exit 1 unless: every manifest agrees on the
                                   version, and it is higher than at <base>
                                   whenever shipped files changed since <base>
  version_check.py shipped <base>  print the shipped files changed since <base>

<base> is any git revision; the comparison starts at its merge base with HEAD.
Standard library only.
"""

import glob
import json
import subprocess
import sys

PLUGIN = ".claude-plugin/plugin.json"
MARKETPLACE = ".claude-plugin/marketplace.json"

# Paths that never reach an installed plugin's behavior: the kit's own tests and
# CI, and repository-level files. Everything else ships.
DEV_ONLY_PREFIXES = ("evals/", ".github/")
DEV_ONLY_FILES = {"README.md", "LICENSE", ".gitignore"}


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def manifests():
    return [PLUGIN, MARKETPLACE] + sorted(glob.glob("plugins/*/.claude-plugin/plugin.json"))


def shipped_changes(base):
    start = git("merge-base", base, "HEAD").strip()
    files = [f for f in git("diff", "--name-only", start, "HEAD").splitlines() if f]
    all_manifests = set(manifests()) | {f for f in files if f.endswith(".claude-plugin/plugin.json")}
    shipped = [f for f in files
               if not f.startswith(DEV_ONLY_PREFIXES) and f not in DEV_ONLY_FILES
               and f not in all_manifests]
    manifest_other = [f for f in sorted(all_manifests)
                      if f in files and manifest_changed_beyond_version(start, f)]
    return start, shipped + manifest_other


def manifest_changed_beyond_version(start, path):
    """A manifest edit that is only the version bump itself does not need another bump."""
    try:
        old = json.loads(git("show", f"{start}:{path}"))
    except subprocess.CalledProcessError:
        return True
    try:
        with open(path, encoding="utf-8") as f:
            new = json.load(f)
    except FileNotFoundError:
        return True
    for d in (old, new):
        d.pop("version", None)
        for p in d.get("plugins", []):
            p.pop("version", None)
    return old != new


def version_at(rev, path):
    text = git("show", f"{rev}:{path}") if rev else open(path, encoding="utf-8").read()
    return json.loads(text)["version"]


def head_versions():
    """Every version the manifests name, as {where: version}."""
    out = {PLUGIN: version_at(None, PLUGIN)}
    with open(MARKETPLACE, encoding="utf-8") as f:
        for p in json.load(f).get("plugins", []):
            out[f"{MARKETPLACE} ({p.get('name')})"] = p.get("version")
    for m in manifests()[2:]:
        out[m] = version_at(None, m)
    return out


def parse(version):
    try:
        parts = tuple(int(x) for x in version.split("."))
    except ValueError:
        parts = ()
    if len(parts) != 3:
        raise SystemExit(f"version {version!r} is not X.Y.Z")
    return parts


def check(base):
    start, shipped = shipped_changes(base)
    versions = head_versions()
    head_plugin = versions[PLUGIN]
    problems = []
    differ = {w: v for w, v in versions.items() if v != head_plugin}
    if differ:
        listed = "\n".join(f"  - {w}: {v}" for w, v in differ.items())
        problems.append(f"{PLUGIN} says {head_plugin}, but these differ - the kit's plugins share one version:\n{listed}")
    base_version = version_at(start, PLUGIN)
    if parse(head_plugin) < parse(base_version):
        problems.append(f"The version went down, from {base_version} to {head_plugin}.")
    elif shipped and parse(head_plugin) == parse(base_version):
        listed = "\n".join(f"  - {f}" for f in shipped[:20]) + ("\n  - ..." if len(shipped) > 20 else "")
        problems.append(
            f"This change touches files the plugin ships, but the version is still {base_version}:\n{listed}\n"
            "Installed plugins update only when the version changes. Bump \"version\" in every "
            f"plugin.json and in each entry of {MARKETPLACE} (patch for a fix, minor for a new capability, major for a "
            "change that needs users to act). Merging to main then tags and releases it.")
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    if shipped:
        print(f"Version {base_version} -> {head_plugin}; {len(shipped)} shipped file(s) changed.")
    else:
        print(f"No shipped file changed; version {head_plugin} needs no bump.")
    return 0


def main(argv):
    if len(argv) != 3 or argv[1] not in ("check", "shipped"):
        print(__doc__, file=sys.stderr)
        return 2
    if argv[1] == "check":
        return check(argv[2])
    for f in shipped_changes(argv[2])[1]:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
