# contracts/ — package P1.10

The interfaces, stubs and contract tests that let Part 1, Part 2A and Part 2B build at the same time without
reading each other's code. Part 1 owns this folder. Everyone else reads it and proposes changes by change note
(rule W4).

## What is here

| File | What it is |
| --- | --- |
| `CONVENTIONS.md` | The conventions note. Language, repository layout, id format, timestamp format, error format, idempotency key, versioning, and how to start a stub |
| `TASK_STATES.md` | The one task-state set, carrying the Founder's decisions on open items 1, 2 and 3 |
| `CONTRACTS.md` | All 21 contracts for a person to read |
| `registry.json` | The same contracts for a machine. The stubs and the tests both read this file |
| `build_registry.py` | Writes `registry.json` and `CONTRACTS.md` from one source, so the two can never disagree |
| `stubs/` | A deterministic stand-in for every component |
| `tests/` | The contract tests |

## Start the stubs

```
bash contracts/run_stubs.sh
```

Every stub starts, each on the port `registry.json` gives it. Nothing to install. One component only:

```
python3 contracts/stubs/server.py --component 2A.07
```

See what is served:

```
python3 contracts/stubs/server.py --list
```

## Run the contract tests

```
bash contracts/run_tests.sh
```

They run against the stubs. To test a real component instead, point its base URL at the real one. Anything
not overridden stays a stub, so a part can test its own component while the others are still stand-ins:

```
DYSON_BASE_2A07=https://tool-hub.internal.example bash contracts/run_tests.sh
```

At Sync (S.01) every base URL is a real component and the same tests run unchanged. **A test that passes only
against a stub is a defect in the test**, not a passing test.

## What the contracts cover

21 contracts and 31 operations:

- **5 lanes** — the five ways Layer A meets a Receptor (PRD section 8)
- **15 component boundaries** — one per path drawn in the Master Architecture, except two that are outside the
  baseline: the optional receptor-to-receptor path and the customer payment path. Both are named in
  `registry.json` with the reason
- **1 internal contract** — G asking the Supply Chain Gate whether a tool is admitted. The Gate is drawn
  inside card A rather than as its own path, but G cannot satisfy LA-TOOL-03 without it. Marked Derived

Each operation states its caller, its callee, the request and response fields, who authorizes the call, what
happens when the other side is down, what happens when STOP is active, the errors it may answer, and the
requirements it rests on.

## Changing a contract

Do not edit this folder if you are not Part 1. Write a change note (Appendix C of your work order), stop work
on the packages that depend on that contract, and send the note to the Founder. Work resumes when every
affected side has accepted it in writing (rule 6).

## Stub honesty

A stub makes no model call, no call to the outside network, and holds no real data. Its state is in memory and
`POST /v1/_stub/reset` clears it. `X-Dyson-Stub-Force: <code>` makes an operation answer with one of the errors
its own contract documents, so a caller can test its error handling; an undocumented code is refused.

The stubs run in one process and share one store, which stands in for the calls between real components. A
contract test therefore asserts what each component's own HTTP surface does, which is true of the stub now and
of the real component at Sync. The calls between real components are wired and shown at S.01 and S.02.

All of this is scaffolding under rule W7 and Sync removes it at S.03.
