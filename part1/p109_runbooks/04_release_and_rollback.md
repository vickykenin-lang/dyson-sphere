# Runbook 4: Release and rollback

Package P1.09. **This one is not a draft.** Every command below was run on 12 Oct 2026 and the output is in
section 6. The deployment steps are marked `TO CONFIRM AT SYNC` because there is nothing deployed yet.

**What this covers:** turning a reviewed change into a released artifact, and getting back to the previous one
when it goes wrong (LA-DEP-05).

**Who runs it:** anyone. The Founder merges.

**How long:** a release takes minutes. A rollback takes about two minutes plus whatever the deploy takes.

**Before you start, know this:** a rollback here is not "keep a copy and hope". It rebuilds from source control
at the earlier commit and compares digests. If they differ, something outside source control changed the build,
and that is a supply chain problem, not a rollback problem.

---

## Release

### 1. Work on your own branch

```
git checkout -b part1/<what-you-are-doing>
```

The branch name decides what you may touch. `part1/` may write in `part1/`, `contracts/`, `tools/` and the
root. It may not write in `part2a/` or `part2b/` (rule W2).

### 2. Check yourself before you ask anyone else

```
python3 tools/ownership_guard.py
bash contracts/run_tests.sh
python3 -m unittest discover -s part1/<package>/tests -t part1/<package>/tests
```

All three must pass. The pipeline runs the same three, so a failure here is a failure there.

### 3. Open a pull request

```
git push -u origin part1/<what-you-are-doing>
gh pr create --fill
```

Say in the body what the package's "Done when" is, and what you ran to show it holds.

### 4. Wait for the pipeline, then the Founder merges

The check named `check` must be green. It runs the ownership guard, the contract tests, the Part 1 package
tests, builds the artifact and proves it rebuilds to the same bytes.

**The Founder presses Merge.** Not the builder (rule 2).

### 5. Build the release artifact

```
python3 tools/build_artifact.py --out dist
```

Write down the version and the sha256. Those two lines are what a rollback needs later.

### 6. Deploy

```
TO CONFIRM AT SYNC: the deploy command, once 2A.01 exists.
```

Then confirm the thing is actually running, not that the deploy command returned zero:

| Check | Expected |
| --- | --- |
| The STOP path answers | yes. If STOP is down, roll back immediately whatever else works |
| The Gateway answers | yes |
| A Test T0 task runs end to end | yes |
| Nothing in the audit log looks wrong | no refusals you cannot explain |

---

## Rollback

### 1. See what you can go back to

```
python3 tools/rollback.py --list
```

### 2. Prove the target before you deploy it

```
python3 tools/rollback.py --to <version> --check-only
```

Expected: `MATCH, the rollback target is proven`.

**If it says DIFFERENT, stop.** The commit no longer rebuilds to what was recorded. Do not deploy it. Report it
to the Founder (rule W8).

### 3. Produce the artifact and deploy it

```
python3 tools/rollback.py --to <version>
TO CONFIRM AT SYNC: the deploy command, once 2A.01 exists.
```

### 4. Check the same four things as a release

STOP path, Gateway, a Test T0 task, the audit log.

### 5. Write it down

Record the rollback in the evidence registry at its AMD-3 stage: which version, why, who decided, how long the
system was on the bad version. That last number matters more than people expect.

---

## 6. Proof that this runbook works

Run on 12 Oct 2026, on the repository as it stood.

**The build is reproducible.** The same commit built twice:

```
first   e0583505defcb84859ac90c1270afe40145c6018d0ded3f9bffe592985c43445
second  e0583505defcb84859ac90c1270afe40145c6018d0ded3f9bffe592985c43445
```

**Two versions exist to move between:**

```
version        commit                                     artifact sha256
58eea54cb53a   58eea54cb53a3329eb8a79a71f3dd9ca569dbfc3   e0583505defcb848...85c43445
7445740b971f   7445740b971f0af3006f87c8182a2ffeaf6424d0   f8eb29ec33d77da9...3f0abb24
```

**The rollback is proven, not assumed:**

```
Rolling back to 58eea54cb53a (commit 58eea54cb53a3329eb8a79a71f3dd9ca569dbfc3)
Rebuilding from source control to prove the artifact is the same one.

recorded  e0583505defcb84859ac90c1270afe40145c6018d0ded3f9bffe592985c43445
rebuilt   e0583505defcb84859ac90c1270afe40145c6018d0ded3f9bffe592985c43445
result    MATCH, the rollback target is proven
```

AMD-3 stage reached: **4, test passed.** Not 5, because nothing is deployed. The deploy steps stay
`TO CONFIRM AT SYNC` until 2A.01 exists.

---

## If a release goes wrong

| What happened | Do this |
| --- | --- |
| The STOP path is down after a deploy | Roll back now. Do not debug first |
| A Test T0 task fails | Roll back, then look |
| The pipeline was red and it was merged anyway | Roll back, then find out how it was merged |
| The rollback says DIFFERENT | Do not deploy it. Report to the Founder |
| Three failed releases in a row | HOLD for Founder review (rule 7) |
