# Charter: the Monitoring and Health Controller (E)

Package P1.06. Requirements LA-MON-01 to LA-MON-06.

## What E is

E is the component that knows what is actually happening. Every Receptor reports to it on the Monitoring and
Health lane, and E keeps the status, the KPIs and the failures, notices when something is going wrong
repeatedly, and tells the Governance Core and the Founder Dashboard.

That is the whole job. E is the system's eyes, and nothing else.

## What E may not do

E has no authority to act on a Receptor (LA-MON-05). It cannot pause one, stop one, resume one, or move a
task to a different Receptor. When it sees a problem it records what it saw and escalates to the Governance
Core (2A.05), which decides.

This is not a promise in a document. `src/monitor.py` has four methods shaped like actions, and every one of
them exists only to refuse:

| Method | What it does |
| --- | --- |
| `pause_receptor` | Refuses. Records nothing, decides nothing, escalates instead |
| `stop_receptor` | Refuses. Emergency STOP is the Founder's red path, not a monitoring action |
| `resume_receptor` | Refuses. A resume after a stop needs the Founder's authorization |
| `reassign_task` | Refuses. The Orchestrator (2A.09) owns task placement |

A test reads the module's own source and fails if monitoring ever gains a way to reach out: no `subprocess`,
no `socket`, no `urllib`, no `os.system`. The only thing that leaves E is an escalation, and it leaves
through a callable the caller supplies.

## What E must be honest about

Monitoring that hides bad news is worse than no monitoring, so LA-MON-06 is a hard requirement rather than a
nicety. Three cases, and what E does with each:

| Situation | What E reports |
| --- | --- |
| A Receptor does not answer a poll | `offline`. Not its last healthy status, not unknown |
| A Receptor answers with something that is not in the contract | `offline`. An answer E cannot read is not an answer |
| A view is older than its freshness bound | the rows, with `stale` set to true, so the dashboard can say so |
| A model, tool, Receptor or the Core is not verified | `unverified`, which is a different thing from working |
| The Governance Core did not accept an escalation | the condition stays queued and shows as unescalated |

The last one matters most. If E could not reach the Governance Core, the condition is not gone. It is kept,
retried with the same idempotency key, and counted on the dashboard row so that a dropped escalation is
visible rather than silent.

## The five calls E takes part in

From `contracts/CONTRACTS.md`. E serves three of these and makes two.

| Operation | Direction | What it is for |
| --- | --- | --- |
| MON-01 `POST /v1/health-reports` | a Receptor calls E | the Receptor reports status, KPIs and failures |
| MON-02 `GET /v1/health` | E calls a Receptor | E polls, so an absent Receptor is reported as offline |
| MON-03 `POST /v1/task-status` | the Orchestrator calls E | a task's state, so views show the truth |
| ESC-01 `POST /v1/escalations` | E calls the Governance Core | a condition is handed to whoever decides |
| ESC-02 `GET /v1/health-views/{view}` | the Dashboard calls E | read-only health and KPI views |

## What counts as a condition

| Condition | When E raises it |
| --- | --- |
| `repeated-failure` | three consecutive bad observations of the same Receptor |
| `offline` | a poll that did not come back, or a Receptor reporting itself offline |
| `pause-condition` | a task reported as `held`, or as `stopped` with reason `pause` |

Three, to match plan rule 7. Only a healthy observation with nothing failing clears the count, and clearing
it also clears the Receptor's open conditions, so the same condition can be raised again if the trouble
returns. A condition is escalated once, not on every later report, because an alert that fires every ten
seconds is an alert nobody reads.

The `pause-condition` rule follows the Founder's closure decisions: a pause arrives as `stopped` with
`stop_reason` `pause`, and `held` is the QA and QC hold. A `stopped` task with any other reason is not
mistaken for a pause.

## What is not here yet

E is built against the contract stubs, because no Receptor exists to poll and no Governance Core exists to
escalate to. `escalate_to` is a callable the caller supplies, and `poll` takes the fetch as an argument, so
the same code runs against the stubs now and against real components at Sync (S.02) without changing.

Two things wait for Sync:

- the real monitoring lane transport, once 2A.06 and the Receptor lanes exist
- the real evidence store behind `evidence_ref`, once 2B.02 exists. Until then it names E's own observations

## Done when

> Failures of a Test T0 stub are detected and escalated; an offline Receptor is reported as offline.

Both are tested end to end in `tests/test_monitor.py`, in the `DoneWhen` class.
