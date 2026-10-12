"""Rolls a deployment back to an earlier version, and proves it is the same thing. Package P1.02.

A rollback here is not "keep a copy and hope". It rebuilds from private source control at the commit the
earlier manifest names, and compares the digest. If the digests match, the artifact you are rolling back to is
byte for byte the one that was built then (LA-DEP-05).

Run:  python3 tools/rollback.py --list
      python3 tools/rollback.py --to <version>
      python3 tools/rollback.py --to <version> --check-only
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")


def run(*args, cwd=ROOT):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def manifests():
    out = []
    for p in sorted(glob.glob(os.path.join(DIST, "manifest-*.json"))):
        try:
            out.append((p, json.load(open(p, encoding="utf-8"))))
        except ValueError:
            pass
    return out


def list_versions():
    found = manifests()
    if not found:
        print("No versions in %s. Build one first: python3 tools/build_artifact.py" % DIST)
        return 1
    print("%-14s %-42s %s" % ("version", "commit", "artifact sha256"))
    for _p, m in found:
        print("%-14s %-42s %s" % (m["version"], m["commit"], m["artifact_sha256"]))
    return 0


def rollback(version, check_only):
    match = [m for _p, m in manifests() if m["version"] == version]
    if not match:
        print("No manifest for version %s. Run --list to see what exists." % version)
        return 1
    man = match[0]

    print("Rolling back to %s (commit %s)" % (version, man["commit"]))
    print("Rebuilding from source control to prove the artifact is the same one.\n")

    work = tempfile.mkdtemp(prefix="dyson-rollback-")
    try:
        code, _o, err = run("git", "worktree", "add", "--detach", work, man["commit"])
        if code != 0:
            print("Could not check out %s: %s" % (man["commit"], err))
            print("Fetch more history and try again: git fetch --depth=1000 origin main")
            return 1
        out_dir = os.path.join(work, "dist")
        code, out, err = run(sys.executable, "-I", os.path.join(work, "tools", "build_artifact.py"),
                             "--out", out_dir, cwd=work)
        if code != 0:
            print("The rebuild failed:\n%s\n%s" % (out, err))
            return 1
        rebuilt = json.load(open(os.path.join(out_dir, "manifest-%s.json" % version), encoding="utf-8"))
        same = rebuilt["artifact_sha256"] == man["artifact_sha256"]
        print("recorded  %s" % man["artifact_sha256"])
        print("rebuilt   %s" % rebuilt["artifact_sha256"])
        print("result    %s\n" % ("MATCH, the rollback target is proven" if same else "DIFFERENT, STOP"))
        if not same:
            print("Do not deploy this. The commit no longer rebuilds to the artifact that was recorded, so "
                  "something outside source control changed the build. Report it to the Founder (rule W8).")
            return 1
        if check_only:
            print("--check-only: nothing was changed.")
            return 0
        shutil.copy2(os.path.join(out_dir, man["artifact"]), os.path.join(DIST, man["artifact"]))
        shutil.copy2(os.path.join(out_dir, "manifest-%s.json" % version), DIST)
        print("dist/%s is the rollback artifact. Deploy that." % man["artifact"])
        print("Record this rollback in the evidence registry at its AMD-3 stage.")
        return 0
    finally:
        run("git", "worktree", "remove", "--force", work)
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Roll back to an earlier Dyson Layer A version")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--to", metavar="VERSION")
    ap.add_argument("--check-only", action="store_true", help="prove the match without replacing anything")
    args = ap.parse_args()
    if args.list or not args.to:
        return list_versions()
    return rollback(args.to, args.check_only)


if __name__ == "__main__":
    sys.exit(main())
