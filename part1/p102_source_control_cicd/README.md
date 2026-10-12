# P1.02 Source control and CI/CD

**Build:** private repository, review rules, build pipeline, rollback artifact. No pull request or Action in
the runtime loop.

**Done when:** A reviewed change becomes a rebuilt artifact that can be rolled back.

**Requirements:** LA-SEC-06, LA-DEP-05.

## What this package produced

| Piece | Where | What it does |
| --- | --- | --- |
| Repository layout | the four top folders | Each part has one folder and writes nowhere else (rule W2) |
| Review rules | `.github/CODEOWNERS` plus the branch protection in `FOUNDER_SETTINGS.md` | A change reaches main only through a reviewed pull request |
| Ownership guard | `tools/ownership_guard.py` | Refuses a branch that writes outside its own folder, and a runtime file that reaches GitHub |
| Build pipeline | `.github/workflows/ci.yml` | Runs the guard and the contract tests, builds the artifact, and proves it rebuilds to the same bytes |
| Rollback artifact | `tools/build_artifact.py`, `tools/rollback.py` | A deterministic artifact with a manifest, and a rollback that rebuilds from source control and compares digests |

## Why the artifact is deterministic

A rollback is only worth something if you can show that what you are rolling back to is what was built then.
The archive is written with sorted entries, no timestamps and no owner, so the same commit always produces the
same digest. `tools/rollback.py --to <version> --check-only` rebuilds at that commit and compares.

If the digests ever differ, something outside source control changed the build. That is not a rollback
problem, it is a supply chain problem, and it stops there.

## Rollback drill

P1.09 writes the drill. Until then, the commands in this README are the procedure.
