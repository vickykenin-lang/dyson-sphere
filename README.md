# Dyson Sphere, Layer A

The governed Core: how Dyson decides who may act, how it knows what is true, and how everything stops.

**Status: NOT IMPLEMENTED / NOT TESTED / NOT DEPLOYED.** AMD-1 to AMD-14 are DESIGN LOCKED. Nothing here is
production. Test T0 is the only Receptor and all data is synthetic.

## Layout

| Folder | Who owns it | What is in it |
| --- | --- | --- |
| `contracts/` | Part 1 | The interfaces, stubs and contract tests every part builds against (package P1.10) |
| `part1/` | Part 1 | Simple work: cost guardrails, source control, metrics, app, monitoring, dashboard, runbooks |
| `part2a/` | Part 2A | Control and authority: environment, IAM, Gateway, Founder controls, Governance Core, STOP bus, Tool Hub, Supply Chain Gate, task engine |
| `part2b/` | Part 2B | Truth, memory and money: data foundation, memory and evidence, Model Router, Conversation Engine, Hermes, QA/QC, Test T0, Financial Control |
| `tools/` | Part 1 | The build, the rollback and the ownership guard |

## Working side by side

Three parts are built at the same time by different builders. Two rules keep them from colliding, and the
pipeline enforces both:

- **Write only in your own folder.** Read any folder. A branch starts with `part1/`, `part2a/` or `part2b/`,
  and the guard refuses a change that touches another part's folder.
- **Talk only through `contracts/`.** Never import another part's code. A contract changes only by a change
  note that every affected side accepts.

```
python3 tools/ownership_guard.py          # would this change be allowed?
```

## Build and roll back

The artifact is deterministic: one commit always rebuilds to the same bytes, on any machine. That is what
makes a rollback provable (LA-DEP-05).

```
python3 tools/build_artifact.py                        # build, with a manifest and a digest
python3 tools/build_artifact.py --verify dist/manifest-<version>.json
python3 tools/rollback.py --list                       # what can be rolled back to
python3 tools/rollback.py --to <version> --check-only  # prove the target rebuilds identically
python3 tools/rollback.py --to <version>               # produce the rollback artifact
```

## Contracts and stubs

```
bash contracts/run_tests.sh      # 58 contract tests, nothing to install
bash contracts/run_stubs.sh      # every stub, each on its own port
```

See `contracts/README.md`.

## What GitHub is, and is not

GitHub is private source control, code review, version history and controlled CI/CD. It is **not** the live
intelligence, the conversational runtime, the scheduler or the command bus, and no pull request or Action sits
in the runtime response loop (LA-SEC-06). The guard refuses a runtime file that reaches GitHub.

## Rules that bind every change

1. No gate, no build. A package starts only when the decisions it names are CLOSED.
2. Critical packages close on an independent check by someone who did not build them.
3. Every result is recorded at its AMD-3 stage, with failed and negative evidence kept. A passed test is not a
   deployment.
4. No spend, credential, integration or rule change without the Founder's authenticated approval.
5. The Founder enters every credential. No credential goes into a prompt, this repository, or a chat.
6. Parts build against agreed interfaces and stubs. Wiring happens at Sync.
7. Three consecutive failed checks on one package put it on HOLD for Founder review.
8. Test T0 is the only Receptor. Data is synthetic: no real money, customer data or bank statements.
