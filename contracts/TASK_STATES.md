# Task-state contract (P1.10)

Version 1.0, 11 Oct 2026. Owner: Part 1, package P1.10.

This is the one task-state set for the task engine (2A.09), the Governance Core (2A.05), the STOP bus (2A.06),
the Direct Founder Controls (2A.04), the app (P1.05), the dashboard (P1.07) and every API between them. It
carries the Founder's decisions on open items 1, 2 and 3, recorded on 11 Oct 2026. No component may name a
state differently, add a state, or add a transition that is not in section 4.

## 1. The Founder's decisions

| Open item | The question | The Founder's decision, 11 Oct 2026 |
| --- | --- | --- |
| 1 | Task state names differ between Closure §9 and card D | Adopt the closure names. `Closed` stays as a housekeeping state only |
| 2 | PAUSE has no task state of its own | PAUSE maps to `stopped`. `held` stays for QA/QC holds only |
| 3 | A Founder Reject has no named end state | A Reject goes to `stopped`, then `Closed` |

What decision 1 means in code: the state field carries the closure name, lowercase, exactly as section 2
spells it. The card D label is a display word only, and no interface ever sends it.

What decision 2 means in code: a PAUSE and a STOP both put the task in `stopped`. They are told apart by
`stop_reason`, not by a different state, and `held` is never used for a PAUSE. Section 3 sets out
`stop_reason`.

What decision 3 means in code: a Founder Reject on an `approval-needed` task sets `stopped` with
`stop_reason` `reject`, and the task then moves to `Closed` once the outcome is recorded. A Reject never goes
to `failed`: nothing failed, the Founder declined.

## 2. The states (PRD section 9, verbatim)

| Closure state | Diagram label (card D) | Meaning |
| --- | --- | --- |
| `accepted` | Pending | Instruction received and acknowledged; task ID assigned |
| `approval-needed` | Approval Needed | Waiting for an authenticated Founder approval or another required approval |
| `running` | Running | Executing through the Governed Tool Hub |
| `held` | Held | Not progressing until a human reviewer decides, for example after three consecutive QA/QC failures |
| `stopped` | Stopped | Ended by STOP / PAUSE |
| `failed` | Failed | Execution or verification failed; retry and escalation logic applies |
| `completed-verified` | Verified | Independent verification proved the intended real output |
| Not in the closure list | Closed | Final housekeeping state drawn on card D |

The wire value of `Closed` is `closed`, lowercase, like every other state.

Active states are `accepted`, `approval-needed`, `running`, `held` and `failed`. Final states are
`completed-verified`, `stopped` and `closed`. "Any active state" in section 4 means exactly those five.

## 3. The `stop_reason` field (Derived from the Founder's decision on open item 2)

A task in `stopped` carries `stop_reason`. It is how PAUSE, STOP, a breach and a Reject are told apart without
adding a state, and it is what decides whether a RESUME is allowed.

| `stop_reason` | Set by | May a RESUME return the task to `running`? |
| --- | --- | --- |
| `pause` | A PAUSE from the Governance Core (2A.05) on the red path | Yes, with an authenticated Founder authorization |
| `stop` | A STOP from the Governance Core (2A.05) on the red path | Yes, with an authenticated Founder authorization |
| `breach` | A STOP raised for a serious security or financial breach | Never automatically. It needs an explicit, separately authenticated Founder authorization naming the incident (`inc_`) |
| `reject` | A Founder Reject through the Direct Founder Controls (2A.04) | No. A Reject is final; a new task is needed |

No RESUME is ever automatic, whatever the reason (LA-SAF-04, LA-GOV-08). A component that cannot read
`stop_reason` treats the task as not resumable.

## 4. The allowed transitions

Rows 1 to 12 are PRD section 9, verbatim. Rows 13 and 14 are Derived from the Founder's decision on open item
3. Any move that is not in this table is refused with `invalid_request`, and the refusal is audited.

| # | From | To | Trigger | Basis |
| --- | --- | --- | --- | --- |
| 1 | New instruction | `accepted` | Task ID and idempotency key assigned; honest acknowledgment shown | Closure §5, §9 |
| 2 | `accepted` | `approval-needed` | Policy, risk or spend rules require approval | Closure §3, §5 |
| 3 | `approval-needed` | `running` | Authenticated Founder approval recorded and all Tool Hub checks pass | Closure §3, §5 |
| 4 | `accepted` | `running` | No approval required and all Tool Hub checks pass | Closure §3; Derived |
| 5 | `running` | `completed-verified` | Independent verification proves the intended real output | Closure §9 |
| 6 | `running` | `failed` | Execution error or failed verification | Diagram; Derived |
| 7 | `failed` | `running` | Retry with the same idempotency key, within retry limits | Closure §9; Derived |
| 8 | `running` or `failed` | `held` | Three consecutive QA/QC failures; human reviewer / Founder notified | AMD-3 |
| 9 | Any active state | `stopped` | STOP or PAUSE from the Governance Core | AMD-5 |
| 10 | `stopped` | `running` | RESUME with authorization; never automatic after a serious security or financial breach | AMD-5; Derived |
| 11 | `held` | `running` or Closed | Decision by the human reviewer or Founder | AMD-3, AMD-5; Derived |
| 12 | `completed-verified`, final `failed`, `stopped` | Closed | Housekeeping after the outcome is recorded | Diagram; Derived |
| 13 | `approval-needed` | `stopped` with `stop_reason` `reject` | A Founder Reject through the Direct Founder Controls | Founder decision on open item 3, 11 Oct 2026 |
| 14 | `stopped` with `stop_reason` `reject` | Closed | Housekeeping after the Reject is recorded | Founder decision on open item 3, 11 Oct 2026 |

Three readings that the table fixes, so that no component has to guess:

- Row 10 does not apply when `stop_reason` is `reject` (section 3). Rows 13 and 14 are the whole life of a
  rejected task.
- Row 12 covers a `stopped` task whatever its reason, but only after the outcome is recorded in the evidence
  registry (2B.02).
- Row 5 is the only way into `completed-verified`, and only the QA/QC Controller (2B.06) can trigger it
  (LA-ORC-06, LA-IF-04). A Receptor's own report never triggers it.

## 5. The wire shape of a task

```json
{
  "task_id": "tsk_01K77H3QZJ4R8V2M9X6Y0B5N7C",
  "state": "stopped",
  "stop_reason": "pause",
  "receptor_id": "rcp_01K77H3R0A1B2C3D4E5F6G7H8J",
  "idempotency_key": "idem_01K77H3R1K2L3M4N5P6Q7R8S9T",
  "created_at": "2026-10-11T16:21:04.512Z",
  "updated_at": "2026-10-11T16:24:51.004Z",
  "qa_failure_count": 0,
  "approval_id": null,
  "evidence_ids": [],
  "display_label": "Stopped"
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `task_id` | yes | Minted by D only (conventions note, section 4) |
| `state` | yes | One of the eight wire values in section 2 |
| `stop_reason` | only when `state` is `stopped` | One of the four values in section 3. Absent otherwise |
| `receptor_id` | no | Absent for a task that touches no Receptor |
| `idempotency_key` | yes | The key the instruction arrived with |
| `created_at`, `updated_at` | yes | RFC 3339 UTC with milliseconds |
| `qa_failure_count` | yes | Consecutive QA/QC failures. Three sends the task to `held` (row 8) |
| `approval_id` | yes, may be null | The `apr_` ID while in or after `approval-needed` |
| `evidence_ids` | yes, may be empty | `evd_` IDs in the evidence registry. `completed-verified` requires at least one |
| `display_label` | no | The card D label for a person to read. Never used in a decision |

A reader that sees a `state` it does not know treats the task as active and not verified, and says so rather
than guessing (LA-EVD-04, LA-MON-06).

## 6. What a component must not do

- Report `completed-verified` on its own output, or on a Receptor's own report (LA-IF-04, LA-QA-05).
- Resume a `stopped` task without an authorization, or resume a `breach` stop automatically (LA-SAF-04).
- Use `held` for a PAUSE, or `failed` for a Reject (the Founder's decisions on open items 2 and 3).
- Mint a `tsk_` ID anywhere but in D, or change a task's state by writing to the store instead of calling D.
- Show an acknowledgment as a completion (LA-APP-04).
