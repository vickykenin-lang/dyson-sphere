"""Refuses a change that breaks the side-by-side rules. Package P1.02.

Three parts build at the same time. Rule W2 says each writes only in its own folder, and rule LA-SEC-06 says
no GitHub Action sits in the runtime loop. A promise that nobody checks is not a rule, so the pipeline checks
both on every change.

Run:  python3 tools/ownership_guard.py                 (compares against the default branch)
      python3 tools/ownership_guard.py --base <ref>
      python3 tools/ownership_guard.py --files a.py b.py

Exit code 0 means the change is allowed. 1 means it is refused, and the reason is printed.
"""
import argparse
import os
import re
import subprocess
import sys

# Who may write where (rule W2 and the ownership table of section 2.2 of every work order).
OWNERSHIP = [
    ("part1/", "part1"),
    ("part2a/", "part2a"),
    ("part2b/", "part2b"),
    ("contracts/", "part1"),   # Part 1 owns the contracts
    ("tools/", "part1"),       # root files belong to Part 1
    (".github/", "part1"),
]
PART_BRANCH_PREFIX = {"part1": "part1/", "part2a": "part2a/", "part2b": "part2b/"}
# A runtime component must not reach GitHub: GitHub is source control, never the command bus (LA-SEC-06).
RUNTIME_DIRS = ("part1/", "part2a/", "part2b/")
RUNTIME_FORBIDDEN = re.compile(
    r"api\.github\.com|github\.com/[\w.-]+/[\w.-]+/(actions|dispatches)|workflow_dispatch|repository_dispatch")


class CannotCheck(Exception):
    """The guard could not work out what changed, so it refuses rather than reporting Allowed."""


def run(*args):
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode != 0:
        raise CannotCheck("%s failed: %s" % (" ".join(args), done.stderr.strip() or "no reason given"))
    return done.stdout.strip()


def owner_of(path):
    for prefix, part in OWNERSHIP:
        if path.startswith(prefix):
            return part
    return "part1"  # anything at the root belongs to Part 1


def part_of_branch(branch):
    for part, prefix in PART_BRANCH_PREFIX.items():
        if branch.startswith(prefix):
            return part
    return None


def changed_files(base):
    try:
        merge_base = run("git", "rev-parse", "--verify", base)
    except CannotCheck:
        raise CannotCheck(
            "%s is not a revision this clone has, so the guard cannot see what changed. A guard that "
            "cannot see a diff must not report Allowed. Run `git fetch origin main:refs/remotes/origin/main` "
            "first, or set GUARD_BASE to a revision that exists." % base)
    merge_base = run("git", "merge-base", merge_base, "HEAD")
    out = run("git", "diff", "--name-only", merge_base, "HEAD")
    return [f for f in out.split("\n") if f]


def check(files, branch):
    problems = []
    part = part_of_branch(branch)

    if part is None:
        problems.append(
            "Branch %r has no part prefix. A branch starts with part1/, part2a/ or part2b/ (rule W2). "
            "Nothing is merged from a branch whose owner cannot be read." % branch)
    else:
        for f in files:
            owner = owner_of(f)
            if owner != part:
                problems.append(
                    "%s belongs to %s, but this branch belongs to %s. Read any folder; write only in yours "
                    "(rule W2). Ask for the change by change note instead." % (f, owner, part))

    for f in files:
        if not f.startswith(RUNTIME_DIRS) or not os.path.exists(f):
            continue
        if "/scaffold/" in f or "/tests/" in f or f.endswith(".md"):
            continue
        try:
            with open(f, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        hit = RUNTIME_FORBIDDEN.search(text)
        if hit:
            problems.append(
                "%s reaches GitHub (%r). GitHub is private source control and controlled CI/CD only; no pull "
                "request or Action may sit in the runtime response loop (LA-SEC-06)." % (f, hit.group(0)))
    return problems


def main():
    ap = argparse.ArgumentParser(description="Refuse a change that breaks rule W2 or LA-SEC-06")
    ap.add_argument("--base", default=os.environ.get("GUARD_BASE", "origin/main"))
    ap.add_argument("--branch", default=os.environ.get("GUARD_BRANCH"))
    ap.add_argument("--files", nargs="*")
    args = ap.parse_args()

    try:
        branch = args.branch or run("git", "rev-parse", "--abbrev-ref", "HEAD")
        files = args.files if args.files is not None else changed_files(args.base)
    except CannotCheck as problem:
        print("ownership guard: CANNOT CHECK. %s" % problem)
        return 2

    if not files:
        print("ownership guard: nothing changed against %s. Allowed." % args.base)
        return 0

    print("ownership guard: branch %r, %d changed file(s)" % (branch, len(files)))
    problems = check(files, branch)
    if problems:
        print("\nREFUSED. %d problem(s):\n" % len(problems))
        for p in problems:
            print("  - " + p)
        print("\nIf two owners seem to disagree, stop and ask the Founder (rule W8).")
        return 1
    print("Allowed. Every file is inside this branch's own folder, and no runtime file reaches GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
