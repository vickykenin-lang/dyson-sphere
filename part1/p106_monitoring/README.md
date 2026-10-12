# P1.06 Monitoring and Health Controller (E)

E watches the Receptors, keeps their status, KPIs and failures, escalates repeated-failure, offline and pause
conditions to the Governance Core, and serves read-only views to the Founder Dashboard. It never acts.

`CHARTER.md` says what E is, what it may not do, and what it has to be honest about. Read that first.

## Files

| File | What it is |
| --- | --- |
| `CHARTER.md` | the charter, the five contract calls, and the three conditions |
| `src/monitor.py` | the controller. Standard library only |
| `tests/test_monitor.py` | 47 tests, including the two "done when" cases end to end |

## Run the tests

```
python3 -m unittest discover -s part1/p106_monitoring/tests -t part1/p106_monitoring/tests
```

The pipeline runs the same command. There is nothing to install.

## How it was checked

47 tests pass. Beyond that, the implementation was deliberately broken twelve ways and the tests were run
against each break, to show the tests would actually notice:

| What was broken | Caught |
| --- | --- |
| The repeated-failure threshold moved from three to four | yes |
| A healthy report no longer cleared the failure count | yes |
| A Receptor that stopped answering kept its last healthy status | yes |
| An escalation the Governance Core refused was dropped instead of queued | yes |
| A view never admitted it was stale | yes |
| `pause_receptor` returned success instead of refusing | yes |
| A pause condition was not escalated | yes |
| A reply with no `escalation_id` was treated as a successful send | yes |
| The same condition was escalated on every later report | yes |
| Any status string was accepted, not just the four | yes |
| A `stopped` task was accepted with no `stop_reason` | yes |
| The escalation idempotency key was made random rather than derived | yes |

The last one survived the first run. The tests compared the retry's key against the first attempt's key,
which still matched when both were random, so nothing noticed that a restarted monitor would escalate the
same condition under a new key and the Governance Core would see it twice. A test was added for that exact
case: two separate monitors observing the same condition must produce the same key. It fails on the broken
version and passes on this one.

## Status

| Item | State |
| --- | --- |
| Needs first: open item 6 | closed by the Founder, 12 Oct 2026 |
| Built against | the contract stubs in `contracts/` |
| Waiting for Sync (S.02) | the real monitoring lane, and the evidence store behind `evidence_ref` |
| AMD-3 stage reached | 4, test passed. Not 5, because nothing is deployed |
