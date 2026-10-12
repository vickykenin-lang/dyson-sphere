"""Turns a commit into a versioned artifact that can be rebuilt and rolled back. Package P1.02.

LA-DEP-05: "A deployment shall be reproducible from private source control and shall have a rollback artifact."

The artifact is deterministic: the same commit always produces the same bytes and the same digest, on any
machine, in any order. That is what makes a rollback provable rather than hopeful. Rolling back means checking
out the earlier commit, building again, and seeing the same digest the manifest recorded.

Run:  python3 tools/build_artifact.py                       (build from the working tree)
      python3 tools/build_artifact.py --out dist
      python3 tools/build_artifact.py --verify dist/manifest-<version>.json
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# What ships. Scaffolding never does: Sync removes it at S.03 (rule W7).
EXCLUDE_DIRS = {".git", "__pycache__", "dist", ".github", "scaffold", ".pytest_cache"}
EXCLUDE_SUFFIX = (".pyc", ".tar.gz")
FIXED_MTIME = 0  # a timestamp in the archive would make two builds of one commit differ


def run(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def commit():
    return run("git", "rev-parse", "HEAD") or "unknown"


def tree_is_clean():
    return run("git", "status", "--porcelain") == ""


def files_to_ship():
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for n in sorted(names):
            if n.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(base, n)
            rel = os.path.relpath(full, ROOT)
            if any(part in EXCLUDE_DIRS for part in rel.split(os.sep)):
                continue
            out.append(rel)
    return sorted(out)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build(out_dir):
    sha = commit()
    version = sha[:12]
    files = files_to_ship()
    per_file = {rel: sha256(os.path.join(ROOT, rel)) for rel in files}

    os.makedirs(out_dir, exist_ok=True)
    tar_path = os.path.join(out_dir, "dyson-layer-a-%s.tar.gz" % version)

    # A deterministic archive: sorted entries, no timestamps, no owner, no gzip mtime.
    import gzip
    raw = tar_path[:-3]
    with tarfile.open(raw, "w") as tar:
        for rel in files:
            info = tar.gettarinfo(os.path.join(ROOT, rel), arcname=rel)
            info.mtime = FIXED_MTIME
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if rel.endswith(".sh") else 0o644
            with open(os.path.join(ROOT, rel), "rb") as f:
                tar.addfile(info, f)
    with open(raw, "rb") as f_in, gzip.GzipFile(tar_path, "wb", mtime=0) as f_out:
        f_out.write(f_in.read())
    os.remove(raw)

    digest = sha256(tar_path)
    manifest = {
        "version": version,
        "commit": sha,
        "clean_tree": tree_is_clean(),
        "artifact": os.path.basename(tar_path),
        "artifact_sha256": digest,
        "file_count": len(files),
        "files": per_file,
        "built_by": "tools/build_artifact.py",
        "note": "Deterministic. The same commit rebuilds to the same artifact_sha256 on any machine.",
    }
    man_path = os.path.join(out_dir, "manifest-%s.json" % version)
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    print("version        %s" % version)
    print("commit         %s" % sha)
    print("clean tree     %s" % manifest["clean_tree"])
    print("files          %d" % len(files))
    print("artifact       %s" % tar_path)
    print("sha256         %s" % digest)
    print("manifest       %s" % man_path)
    if not manifest["clean_tree"]:
        print("\nWARNING: the working tree has uncommitted changes, so this artifact does not match any commit.")
    return manifest


def verify(manifest_path):
    man = json.load(open(manifest_path, encoding="utf-8"))
    out_dir = os.path.dirname(os.path.abspath(manifest_path))
    tar_path = os.path.join(out_dir, man["artifact"])
    if not os.path.exists(tar_path):
        print("MISSING: %s" % tar_path)
        return 1
    actual = sha256(tar_path)
    same = actual == man["artifact_sha256"]
    print("version   %s" % man["version"])
    print("commit    %s" % man["commit"])
    print("expected  %s" % man["artifact_sha256"])
    print("actual    %s" % actual)
    print("result    %s" % ("MATCH" if same else "DIFFERENT"))
    return 0 if same else 1


def main():
    ap = argparse.ArgumentParser(description="Build or verify a Dyson Layer A artifact")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--verify", metavar="MANIFEST")
    args = ap.parse_args()
    if args.verify:
        return verify(args.verify)
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
