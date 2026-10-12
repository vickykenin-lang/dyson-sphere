# Contracts (P1.10)

Version v1.0, 11 Oct 2026. Owner: Part 1, package P1.10. Built from Layer A Execution Plan, Docs rev 62 and Layer A PRD v1.0, Docs rev 31.

This file is generated from `registry.json` by `build_registry.py`. Read `CONVENTIONS.md` for the formats every contract uses and `TASK_STATES.md` for the one task-state set.

A contract changes only by a change note that every affected part accepts (rule 6). Review the contracts that have one of your own components at either end.

## Components and their stub ports

| Card | Component | Package | Part | Stub port |
| --- | --- | --- | --- | --- |
| - | Dyson app, Web first with Android as the target | P1.05 | Part 1 | 8105 |
| E | Monitoring and Health Controller (E) | P1.06 | Part 1 | 8106 |
| J | Founder Financial Dashboard (J) | P1.07 | Part 1 | 8107 |
| - | Entry Gateway | 2A.03 | Part 2A | 8203 |
| - | Direct Founder Controls | 2A.04 | Part 2A | 8204 |
| A | Governance Core | 2A.05 | Part 2A | 8205 |
| - | STOP / PAUSE / RESUME bus | 2A.06 | Part 2A | 8206 |
| G | Governed Tool Hub (G) | 2A.07 | Part 2A | 8207 |
| - | Supply Chain / Integration Gate | 2A.08 | Part 2A | 8208 |
| D | Task engine (Orchestrator D) | 2A.09 | Part 2A | 8209 |
| I | Memory & Evidence Layer (I) | 2B.02 | Part 2B | 8302 |
| C | Model Router & Fallback (C) | 2B.03 | Part 2B | 8303 |
| B | Conversation Engine (B) | 2B.04 | Part 2B | 8304 |
| 4 (Hermes) | Hermes runtime | 2B.05 | Part 2B | 8305 |
| F | QA/QC Controller (F) | 2B.06 | Part 2B | 8306 |
| - | Test T0 and its independent verifier, built as a minimal fixture | 2B.07 | Part 2B | 8307 |
| H | Financial Control (H) | 2B.08 | Part 2B | 8308 |

| Actor | Who it is |
| --- | --- |
| Founder | The Founder, a person. Authenticated at the Entry Gateway; the only source of authorization |
| Receptor | A Layer B Receptor. In the baseline the only one is Test T0 (2B.07), synthetic and no-money |

| Component | Appears in the contracts as |
| --- | --- |
| 2B.07 | Receptor. Test T0 is a Receptor, so it meets Layer A on the five lanes like any other (open item 4). It has no contract of its own, and it must satisfy every Receptor obligation. |

## 1. The five Layer A to Layer B lanes (PRD section 8)

### LANE-QA  QA/QC & Verification

| | |
| --- | --- |
| Style in the diagram | Green, solid |
| Layer A owner | F Independent QA/QC Controller (2B.06) |
| Direction | Request down to the Receptor, evidence and results back |
| Carries | Quality standards, verification requests, evidence, results, escalations |
| Basis | Diagram; AMD-3 |

#### QA-01  `POST /v1/verifications`

F asks the Receptor to produce the real-output evidence for a task.

| | |
| --- | --- |
| Caller | 2B.06 |
| Callee | Receptor |
| Authorized by | F's own component identity, issued by 2A.02. A Receptor accepts a verification request only from F. |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `stopped`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-IF-01, LA-IF-04, LA-QA-01 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `verification_id` | yes | string, `evd_`-style id minted by F |
| `task_id` | yes | string, `tsk_` |
| `quality_standard` | yes | string, the standard F will judge against |
| `requested_evidence` | yes | array of strings, what the Receptor must produce |
| `deadline_ms` | no | integer, how long F will wait |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `verification_id` | yes | string, echoed |
| `status` | yes | string, `accepted` |
| `accepted_at` | yes | RFC 3339 UTC with milliseconds |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

#### QA-02  `POST /v1/evidence`

The Receptor returns its evidence. The claim is not proof: F verifies the real output itself.

| | |
| --- | --- |
| Caller | Receptor |
| Callee | 2B.06 |
| Authorized by | The Receptor's own identity. It authorizes nothing: it may report, never conclude. |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `not_found`, `idempotency_conflict`, `rate_limited`, `internal` |
| Requirements | LA-IF-04, LA-QA-05, LA-EVD-01, LA-EVD-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `verification_id` | yes | string |
| `task_id` | yes | string, `tsk_` |
| `evidence` | yes | array of objects, each with `kind`, `ref` and `produced_at` |
| `claimed_outcome` | no | string, the Receptor's own claim. Recorded, never trusted |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `evidence_ids` | yes | array of strings, `evd_` ids written to the registry |
| `verdict` | yes | string, always `pending` on arrival. F decides in its own time |
| `self_certification_accepted` | yes | boolean, always false (LA-QA-05) |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

#### QA-03  `POST /v1/escalations`

The Receptor escalates a problem it cannot solve inside its own bounds.

| | |
| --- | --- |
| Caller | Receptor |
| Callee | 2B.06 |
| Authorized by | The Receptor's own identity. |
| Errors | `invalid_request`, `unauthenticated`, `rate_limited`, `internal` |
| Requirements | LA-QA-04, LA-MON-06 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `receptor_id` | yes | string, `rcp_` |
| `severity` | yes | string, `low`, `medium` or `high` |
| `summary` | yes | string, one sentence |
| `task_id` | no | string, `tsk_` if it concerns one task |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `escalation_id` | yes | string |
| `routed_to` | yes | string, `2B.06`, and `2A.05` when severity is high |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### LANE-TASK  Tasks from Orchestrator (via Tool Hub)

| | |
| --- | --- |
| Style in the diagram | Blue, solid |
| Layer A owner | D Orchestrator through G Governed Tool Hub (2A.09) |
| Direction | Tasks down, results back |
| Carries | Task instructions with task ID and idempotency key |
| Basis | Diagram; Closure §9 |

#### TASK-01  `POST /v1/receptor/tasks`

G hands a Receptor one task on D's behalf. G is the only path to a Receptor's task interface.

| | |
| --- | --- |
| Caller | 2A.07 |
| Callee | Receptor |
| Authorized by | G, after it has checked identity and permission, Receptor scope, risk and spend limits, approval status and the current STOP state. A Receptor refuses a task from anyone but G. |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `approval_needed`, `stopped`, `not_admitted`, `spend_limit`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-IF-01, LA-IF-02, LA-TOOL-01, LA-TOOL-02, LA-ORC-03, LA-ORC-05 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `task_id` | yes | string, `tsk_`, minted by D |
| `receptor_id` | yes | string, `rcp_` |
| `instruction` | yes | object, what to do, inside the Receptor's declared scope |
| `scope` | yes | object, the permitted tools and spend for this task |
| `approval_id` | no | string, `apr_` when the action needed a Founder approval |
| `deadline_ms` | no | integer |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `task_id` | yes | string, echoed |
| `state` | yes | string, `accepted` |
| `accepted_at` | yes | RFC 3339 UTC with milliseconds |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

#### TASK-02  `POST /v1/task-results`

The Receptor reports a result. The task does not become completed-verified on this report.

| | |
| --- | --- |
| Caller | Receptor |
| Callee | 2A.07 |
| Authorized by | The Receptor's own identity. It cannot set a task's state. |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `not_found`, `idempotency_conflict`, `rate_limited`, `internal` |
| Requirements | LA-IF-04, LA-ORC-06, LA-EVD-01, LA-EVD-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `task_id` | yes | string, `tsk_` |
| `output_ref` | yes | string, where the real output can be checked |
| `claimed_outcome` | yes | string, the Receptor's own claim |
| `evidence` | no | array of objects, what it can show |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `task_id` | yes | string, echoed |
| `state` | yes | string, `running` until F verifies (LA-IF-04) |
| `verification_required` | yes | boolean, always true |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### LANE-FIN  Financial Reporting

| | |
| --- | --- |
| Style in the diagram | Purple, dashed |
| Layer A owner | H Financial Control & Reconciliation (2B.08) |
| Direction | Receptor to Core |
| Carries | Revenue reports and payment records |
| Basis | Diagram; AMD-2 |

#### FIN-01  `POST /v1/revenue-reports`

The Receptor reports revenue. It stays not final until H matches a Founder-uploaded statement.

| | |
| --- | --- |
| Caller | Receptor |
| Callee | 2B.08 |
| Authorized by | The Receptor's own identity. A report authorizes no payment and moves no money: Layer A never sits in the customer payment flow (LA-IF-06). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `rate_limited`, `internal` |
| Requirements | LA-IF-01, LA-IF-05, LA-IF-06, LA-FIN-01, LA-FIN-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `receptor_id` | yes | string, `rcp_` |
| `period` | yes | string, `YYYY-MM-DD` to `YYYY-MM-DD` |
| `amount_minor` | yes | integer, in the currency's minor unit. No floating point for money |
| `currency` | yes | string, ISO 4217 |
| `payment_records` | no | array of objects, each with `ref` and `amount_minor` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `report_id` | yes | string |
| `status` | yes | string, always `reported-not-final` on arrival (LA-IF-05) |
| `reconciled` | yes | boolean, always false on arrival |
| `bank_statement_required` | yes | boolean, always true |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### LANE-MON  Monitoring / Health

| | |
| --- | --- |
| Style in the diagram | Orange, dashed |
| Layer A owner | E Monitoring & Health Controller (P1.06) |
| Direction | Receptor to Core |
| Carries | Task status, KPIs, health, failures |
| Basis | Diagram; AMD-10 |

#### MON-01  `POST /v1/health-reports`

The Receptor reports its status, KPIs and failures on the monitoring lane.

| | |
| --- | --- |
| Caller | Receptor |
| Callee | P1.06 |
| Authorized by | The Receptor's own identity. A report gives E no authority to act on the Receptor (LA-MON-05). |
| Errors | `invalid_request`, `unauthenticated`, `idempotency_conflict`, `rate_limited`, `internal` |
| Requirements | LA-IF-01, LA-MON-01, LA-MON-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `receptor_id` | yes | string, `rcp_` |
| `status` | yes | string, `healthy`, `degraded`, `failing` or `offline` |
| `reported_at` | yes | RFC 3339 UTC with milliseconds |
| `kpis` | no | object, name to number |
| `failures` | no | array of objects, each with `task_id` and `reason` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `accepted` | yes | boolean |
| `escalated` | yes | boolean, true when a repeated-failure condition is met |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

#### MON-02  `GET /v1/health`

E polls the Receptor's health endpoint, so an offline Receptor is reported as offline.

| | |
| --- | --- |
| Caller | P1.06 |
| Callee | Receptor |
| Authorized by | E's own component identity. A read only. |
| Errors | `unauthenticated`, `not_found`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-MON-01, LA-MON-06 |

**Request**

_None._

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `receptor_id` | yes | string |
| `status` | yes | string, as in MON-01 |
| `checks` | yes | array of objects, each with `name` and `ok` |

**When the callee is down.** E records the Receptor as `offline` and reports it as offline rather than silent (LA-MON-06). It raises a repeated-failure condition if the poll keeps failing.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### LANE-STOP  STOP / PAUSE / RESUME (to all receptors)

| | |
| --- | --- |
| Style in the diagram | Red, solid |
| Layer A owner | A Governance Core (2A.05) |
| Direction | Core to Receptor |
| Carries | Control commands, independent of AI reasoning |
| Basis | Diagram; AMD-5 |

#### STOP-01  `POST /v1/control`

The red path carries STOP, PAUSE and RESUME to every Receptor, with no LLM in its way.

| | |
| --- | --- |
| Caller | 2A.06 |
| Callee | Receptor |
| Authorized by | A, the Governance Core, on the Founder's command. Deterministic control code; no model decides it, and it works when every model and the app are down (LA-GOV-03, LA-DFC-04). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-IF-03, LA-SAF-01, LA-SAF-03, LA-SAF-04, LA-GOV-03, LA-GOV-08, LA-DFC-04 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `command` | yes | string, `stop`, `pause` or `resume` |
| `receptor_id` | yes | string, `rcp_` or `all` |
| `issued_at` | yes | RFC 3339 UTC with milliseconds |
| `incident_id` | no | string, `inc_`, required when the command follows a breach |
| `authorization_id` | no | string, required on `resume` (LA-SAF-04) |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `command` | yes | string, echoed |
| `applied` | yes | boolean |
| `applied_at` | yes | RFC 3339 UTC with milliseconds |
| `in_flight` | yes | array of strings, task ids that were already running when the command arrived |

**When the callee is down.** The bus retries on the red path and raises an incident. A Receptor that cannot be reached is treated as not stopped, reported as such, and isolated at the Tool Hub instead, so no new task reaches it.

**When STOP or PAUSE is active.** A STOP or PAUSE always applies, even while already stopped: the command is idempotent. A `resume` is refused with `forbidden` when it carries no authorization, and after a breach it needs an authorization naming the incident (LA-GOV-08, LA-SAF-04).

## 2. Component boundaries (PRD, paths drawn in the figure)

### BND-01  Founder, Dyson App, Entry Gateway

| | |
| --- | --- |
| Style in the diagram | Blue out, green back |
| Meaning | Voice or text instruction in; answer, report or response out |
| Sides | Founder to P1.05; P1.05 to 2A.03 |

#### GW-01  `POST /v1/sessions`

The Gateway authenticates the Founder for the session and issues a session token.

| | |
| --- | --- |
| Caller | P1.05 |
| Callee | 2A.03 |
| Authorized by | The Founder, authenticated at the Gateway for every session. The app holds no authority of its own (LA-APP-06, LA-SEC-03). |
| Errors | `invalid_request`, `unauthenticated`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-GW-01, LA-GW-02, LA-SEC-03, LA-APP-06 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `authenticator_assertion` | yes | object, the result of the Founder's own authentication. The app never holds or forwards a credential (LA-SEC-01) |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `session_token` | yes | string, opaque, short-lived |
| `expires_at` | yes | RFC 3339 UTC with milliseconds |
| `subject` | yes | string, always `founder` |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller shows the view as unavailable and says so plainly; it never shows stale data as current (LA-EVD-04, LA-MON-06).

**When STOP or PAUSE is active.** Sessions still open while the Core is stopped, so the Founder can see state and use the Direct Founder Controls. No new task is accepted (BND-03 is the path that is never blocked).

#### GW-02  `POST /v1/messages`

One Founder instruction in Hindi, English or Hinglish. The answer is an honest acknowledgment.

| | |
| --- | --- |
| Caller | P1.05 |
| Callee | 2A.03 |
| Authorized by | The session token from GW-01. |
| Errors | `invalid_request`, `unauthenticated`, `idempotency_conflict`, `approval_needed`, `stopped`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-APP-02, LA-APP-03, LA-APP-04, LA-APP-07, LA-PERF-01, LA-GW-03 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `locale` | yes | string, `hi`, `en` or `hi-Latn` for Hinglish |
| `content` | yes | object, `text` or `audio_ref` |
| `transcription_uncertain` | no | boolean, true when speech recognition was not confident (LA-APP-07) |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `acknowledgment` | yes | string, `accepted` or `approval-needed`. Never a completion (LA-APP-04) |
| `task_id` | no | string, `tsk_` when the instruction became a task |
| `thread_id` | yes | string, one history for voice and text (LA-APP-03) |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

### BND-02  Entry Gateway and B

| | |
| --- | --- |
| Style in the diagram | Blue down, green up |
| Meaning | Gateway routes to the Conversation Engine; B's response returns to the Founder |
| Sides | 2A.03 to 2B.04 |

#### CONV-01  `POST /v1/conversation/turns`

The Gateway routes an authenticated instruction to B, which interprets it in thread context.

| | |
| --- | --- |
| Caller | 2A.03 |
| Callee | 2B.04 |
| Authorized by | The Gateway, which has already authenticated the Founder. B holds no authority to execute. |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `stopped`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-GW-03, LA-CONV-01, LA-CONV-03, LA-CONV-07 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `thread_id` | yes | string |
| `locale` | yes | string, as in GW-02 |
| `content` | yes | object, `text` or a transcript of the audio |
| `transcription_uncertain` | no | boolean, carried through from the app |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `reply` | yes | string, what the Founder is told |
| `intent` | yes | string, `answer`, `clarify` or `proposed_action` |
| `proposed_action` | no | object, present only for `proposed_action`, to be checked at BND-04 |
| `completion_claimed` | yes | boolean, always false here (LA-CONV-07) |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller shows the view as unavailable and says so plainly; it never shows stale data as current (LA-EVD-04, LA-MON-06).

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

### BND-03  Direct Founder Controls to A

| | |
| --- | --- |
| Style in the diagram | Red |
| Meaning | Approve / Reject and Emergency STOP / PAUSE go straight to the Governance Core, not through the app or the normal flow |
| Sides | 2A.04 to 2A.05 |

#### DFC-01  `POST /v1/controls/decision`

The Founder approves or rejects one exact action. A Reject ends the task (open item 3).

| | |
| --- | --- |
| Caller | 2A.04 |
| Callee | 2A.05 |
| Authorized by | The Founder alone, on an independently authenticated path that touches no app and no LLM. No model, agent or Receptor can produce this call (LA-DFC-01, LA-GOV-02, LA-AMD-01). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `not_found`, `idempotency_conflict`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-DFC-01, LA-DFC-02, LA-DFC-03, LA-DFC-05, LA-GOV-02, LA-AMD-01 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `approval_id` | yes | string, `apr_` |
| `decision` | yes | string, `approve` or `reject` |
| `bound_action_digest` | yes | string, the digest of the exact action shown to the Founder (LA-DFC-05) |
| `authenticator_assertion` | yes | object, the step-up authentication chosen at gate 3 |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `approval_id` | yes | string, echoed |
| `recorded_at` | yes | RFC 3339 UTC with milliseconds |
| `task_state` | yes | string, `running` on approve, `stopped` with `stop_reason` `reject` on reject |
| `approver` | yes | string, always `founder` |

**When the callee is down.** The control path is the last thing allowed to fail. If A does not answer, the Controls raise an incident, keep the decision unsent, and show the Founder that it was not recorded. A decision is never assumed to have landed.

**When STOP or PAUSE is active.** Always allowed. An approval decision reaches A even while the Core is stopped: that is how a stop is lifted and how a rejected task is closed.

#### DFC-02  `POST /v1/controls/emergency`

Emergency STOP or PAUSE, working whatever the models and the app are doing.

| | |
| --- | --- |
| Caller | 2A.04 |
| Callee | 2A.05 |
| Authorized by | The Founder alone, independently authenticated. Deterministic: no LLM in the path (LA-GOV-03). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-DFC-01, LA-DFC-04, LA-GOV-03, LA-SAF-01, LA-SAF-04 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `command` | yes | string, `stop`, `pause` or `resume` |
| `scope` | yes | string, `all` or `receptor` |
| `receptor_id` | no | string, required when scope is `receptor` |
| `authenticator_assertion` | yes | object, the step-up authentication chosen at gate 3 |
| `incident_id` | no | string, `inc_`, required to resume after a breach |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `incident_id` | yes | string, `inc_` |
| `applied_at` | yes | RFC 3339 UTC with milliseconds |
| `reached` | yes | array of strings, the components and Receptors the command reached |
| `not_reached` | yes | array of strings, reported plainly rather than assumed stopped |

**When the callee is down.** A STOP that cannot be recorded is still carried out: the bus applies it and the failure to record raises an incident. A resume is never applied when A cannot be reached.

**When STOP or PAUSE is active.** Always allowed, and idempotent: a STOP on an already stopped system is accepted.

### BND-04  A and B

| | |
| --- | --- |
| Style in the diagram | Blue, two-way |
| Meaning | Policy / approval checks |
| Sides | 2B.04 to 2A.05 |

#### POL-01  `POST /v1/policy/checks`

B asks A whether a prepared action is allowed, before it is prepared for execution.

| | |
| --- | --- |
| Caller | 2B.04 |
| Callee | 2A.05 |
| Authorized by | B's own component identity. The verdict is A's alone, and A refuses a verdict from any model, agent or Receptor (LA-GOV-02). Every financial action stays blocked until an approval exists (LA-GOV-05). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `stopped`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-GOV-01, LA-GOV-02, LA-GOV-04, LA-GOV-05, LA-CONV-06, LA-AMD-01, LA-AMD-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `proposed_action` | yes | object, what would be done, with its tools and scope |
| `estimated_spend_minor` | no | integer, in the currency's minor unit |
| `receptor_id` | no | string, `rcp_` when the action touches a Receptor |
| `thread_id` | yes | string |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `verdict` | yes | string, `allow`, `approval-needed` or `deny` |
| `policy_version` | yes | string, the version of the rule that decided it (LA-GOV-01) |
| `approval_id` | no | string, `apr_` created when the verdict is `approval-needed` |
| `bound_action_digest` | no | string, present with an approval_id: the digest of the exact action the approval is bound to, which the Founder's controls must send back (LA-DFC-05) |
| `reasons` | yes | array of strings, which rule decided, for the audit log |

**When the callee is down.** B must not proceed. It answers the Founder that the check could not be made, and the task stays where it is. A missing policy check is never read as an allow.

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

### BND-05  B, C, D, E (neighbors)

| | |
| --- | --- |
| Style in the diagram | Blue right, green left |
| Meaning | Neighboring cards exchange requests and responses |
| Sides | 2B.04 to 2B.03; 2B.04 to 2A.09; 2A.09 to P1.06 |

#### RTR-01  `POST /v1/model/completions`

B reaches an external model only through C, inside cost and token limits.

| | |
| --- | --- |
| Caller | 2B.04 |
| Callee | 2B.03 |
| Authorized by | B's own component identity. C is the only approved path to an external model, and no model access exists outside governance (LA-RTR-01). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `stopped`, `spend_limit`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-RTR-01, LA-RTR-02, LA-RTR-04, LA-RTR-05, LA-RTR-07, LA-SEC-07 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `purpose` | yes | string, what the call is for, used to pick a model |
| `input` | yes | object, the prompt material. C applies the gate 6 redaction rules before it leaves |
| `max_cost_minor` | no | integer, the ceiling for this call |
| `task_id` | no | string, `tsk_` when the call belongs to a task |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `model_id` | yes | string, the approved model that answered |
| `output` | yes | object, the model's answer |
| `cost_minor` | yes | integer, what it cost |
| `redaction_applied` | yes | boolean, true when redaction rules changed the input (LA-RTR-07) |
| `fallback_used` | yes | boolean, true when the first choice failed (LA-RTR-04) |

**When the callee is down.** C answers `dependency_down` only after its tested fallback has also failed. Task state and memory survive either way (LA-RTR-04, LA-REL-06).

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

#### ORC-01  `POST /v1/tasks`

B hands a prepared instruction to D, which mints the task and owns its state from then on.

| | |
| --- | --- |
| Caller | 2B.04 |
| Callee | 2A.09 |
| Authorized by | B's own component identity. B prepares and never executes (LA-CONV-02); D routes all tool use through G (LA-ORC-05). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `approval_needed`, `stopped`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-CONV-02, LA-ORC-01, LA-ORC-02, LA-ORC-03, LA-REL-01, LA-REL-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `instruction` | yes | object, the prepared action |
| `thread_id` | yes | string |
| `approval_id` | no | string, `apr_` when BND-04 answered `approval-needed` |
| `receptor_id` | no | string, `rcp_` when the task touches a Receptor |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `task_id` | yes | string, `tsk_`, minted by D and by nobody else |
| `state` | yes | string, `accepted` or `approval-needed` |
| `created_at` | yes | RFC 3339 UTC with milliseconds |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

#### MON-03  `POST /v1/task-status`

D tells E a task's state, so monitoring and the dashboard can show the truth.

| | |
| --- | --- |
| Caller | 2A.09 |
| Callee | P1.06 |
| Authorized by | D's own component identity. E observes and escalates; it never acts (LA-MON-05). |
| Errors | `invalid_request`, `unauthenticated`, `idempotency_conflict`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-MON-02, LA-MON-04, LA-ORC-01 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `task_id` | yes | string, `tsk_` |
| `state` | yes | string, one of the eight task states |
| `stop_reason` | no | string, present when the state is `stopped` |
| `receptor_id` | no | string, `rcp_` |
| `updated_at` | yes | RFC 3339 UTC with milliseconds |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `accepted` | yes | boolean |

**When the callee is down.** D keeps the state in its own durable store and retries. A monitoring outage never changes a task's state or stops the work.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### BND-06  Hermes and C

| | |
| --- | --- |
| Style in the diagram | Blue, two-way |
| Meaning | Approved model access, governed |
| Sides | 2B.05 to 2B.03 |

#### HER-01  `POST /v1/model/completions`

Hermes reaches a model only through C, with its own identity and its own limits.

| | |
| --- | --- |
| Caller | 2B.05 |
| Callee | 2B.03 |
| Authorized by | Hermes's own component identity, which is separate from B's and carries no governance rights. C refuses a call from Hermes that is outside Hermes's approved scope (LA-HER-02, LA-RTR-01). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `stopped`, `spend_limit`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-HER-01, LA-HER-02, LA-RTR-01, LA-DEP-01 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `purpose` | yes | string |
| `input` | yes | object, redaction applies as in RTR-01 |
| `max_cost_minor` | no | integer |
| `task_id` | no | string, `tsk_` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `model_id` | yes | string |
| `output` | yes | object |
| `cost_minor` | yes | integer |
| `redaction_applied` | yes | boolean |
| `fallback_used` | yes | boolean |

**When the callee is down.** As in RTR-01. Hermes has no other path to a model and does not fall back on its own.

**When STOP or PAUSE is active.** Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).

### BND-07  D and G; Hermes and G

| | |
| --- | --- |
| Style in the diagram | Blue, two-way |
| Meaning | All tool use passes through the hub |
| Sides | 2A.09 to 2A.07; 2B.05 to 2A.07 |

#### TOOL-01  `POST /v1/tool-calls`

Every tool call, from D or from Hermes, is authorized one call at a time by G.

| | |
| --- | --- |
| Caller | 2A.09 or 2B.05 |
| Callee | 2A.07 |
| Authorized by | G alone, and deterministically: no LLM sits in its decision path (LA-TOOL-07). G is the only path to any tool, API, plugin or MCP connector, for D and for Hermes alike (LA-TOOL-02, LA-HER-03). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `approval_needed`, `stopped`, `not_admitted`, `spend_limit`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-TOOL-01, LA-TOOL-02, LA-TOOL-04, LA-TOOL-06, LA-TOOL-07, LA-SAF-02, LA-HER-03 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `tool_id` | yes | string, `tool_`, an entry in G's governed registry |
| `arguments` | yes | object, the call's own arguments |
| `task_id` | yes | string, `tsk_` |
| `receptor_id` | no | string, `rcp_` when the call acts on a Receptor |
| `estimated_spend_minor` | no | integer |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `tool_call_id` | yes | string |
| `result` | yes | object, present on success |
| `checks` | yes | object, the five checks and their outcome: identity, scope, risk and spend, approval, STOP state (LA-TOOL-01) |
| `audited` | yes | boolean, always true, on success and on refusal (LA-TOOL-04) |

**When the callee is down.** The caller gets `dependency_down`. It does not reach the tool another way: there is no other way. The task stays in its state and the attempt is recorded.

**When STOP or PAUSE is active.** Refuse with `stopped` (409) and audit the refusal. G checks the STOP state on every single call, so a stop takes effect on the next call with no restart (LA-SAF-02).

### BND-08  F, G, H, I (neighbors)

| | |
| --- | --- |
| Style in the diagram | Blue right, green left |
| Meaning | Neighboring cards exchange requests and responses |
| Sides | 2B.06 to 2B.02; 2B.08 to 2B.02; 2B.06 to 2A.07 |

#### EVD-01  `POST /v1/evidence`

F writes an evidence record at its exact AMD-3 stage, with the failed evidence kept.

| | |
| --- | --- |
| Caller | 2B.06 |
| Callee | 2B.02 |
| Authorized by | F's own component identity. I is a controlled store, not an authority: writing evidence grants no permission (LA-MEM-08). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-EVD-03, LA-QA-06, LA-MEM-08, LA-MEM-07 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `capability` | yes | string, what was tested |
| `provider` | yes | string, by whom |
| `stage` | yes | integer, 1 to 8, the AMD-3 stage reached |
| `environment` | yes | string, where it ran |
| `observed_at` | yes | RFC 3339 UTC with milliseconds |
| `expires_at` | no | RFC 3339 UTC with milliseconds |
| `outcome` | yes | string, `pass` or `fail`. A failure is kept, never dropped |
| `task_id` | no | string, `tsk_` |
| `detail` | yes | object, what was actually run and seen |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `evidence_id` | yes | string, `evd_` |
| `stage` | yes | integer, echoed |
| `immutable` | yes | boolean, always true: a record is appended, never edited |

**When the callee is down.** F holds the evidence in its own queue and retries. It never reports a verification as done while the record is unwritten.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

#### FIN-02  `POST /v1/ledger-entries`

H writes a ledger entry. It is final only when a bank statement has matched it.

| | |
| --- | --- |
| Caller | 2B.08 |
| Callee | 2B.02 |
| Authorized by | H's own component identity. Per-Receptor isolation applies: an entry is scoped to its Receptor (LA-IF-07, LA-MEM-04). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-FIN-02, LA-FIN-05, LA-FIN-06, LA-IF-07, LA-MEM-04 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `receptor_id` | yes | string, `rcp_` |
| `amount_minor` | yes | integer |
| `currency` | yes | string |
| `kind` | yes | string, `revenue-reported`, `revenue-verified` or `payment-record` |
| `statement_id` | no | string, required for `revenue-verified` |
| `occurred_at` | yes | RFC 3339 UTC with milliseconds |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `entry_id` | yes | string |
| `final` | yes | boolean, true only for `revenue-verified` (LA-FIN-02) |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current state, records the attempt, and retries with the same idempotency key inside its retry limit. Nothing is reported as complete.

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### BND-09  J and I

| | |
| --- | --- |
| Style in the diagram | Blue, green |
| Meaning | Dashboard asks (read); memory answers with verified data |
| Sides | P1.07 to 2B.02 |

#### DASH-01  `GET /v1/financial-views/{view}`

The dashboard reads verified financial data. There is no write path and no action path.

| | |
| --- | --- |
| Caller | P1.07 |
| Callee | 2B.02 |
| Authorized by | J's own read-only component identity. J has no authority to execute actions and no write path into Core controls (LA-DASH-02). It never reaches the bank (LA-DASH-03). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `not_found`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-DASH-01, LA-DASH-02, LA-DASH-03, LA-DASH-04, LA-MEM-08 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `view` | no | path parameter, `revenue`, `payments`, `profitability`, `receptor-performance` or `reconciliation-status` |
| `receptor_id` | no | query, `rcp_` to scope to one Receptor |
| `period` | no | query, `YYYY-MM-DD` to `YYYY-MM-DD` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `rows` | yes | array of objects, the view's data |
| `verified_only` | yes | boolean, always true |
| `as_of` | yes | RFC 3339 UTC with milliseconds |
| `unverified_excluded` | yes | integer, how many rows were left out for want of verification |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller shows the view as unavailable and says so plainly; it never shows stale data as current (LA-EVD-04, LA-MON-06).

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### BND-10  D and I

| | |
| --- | --- |
| Style in the diagram | Blue, two-way |
| Meaning | State and evidence |
| Sides | 2A.09 to 2B.02 |

#### STATE-01  `PUT /v1/task-state`

D records a task's state and the evidence it rests on, durably.

| | |
| --- | --- |
| Caller | 2A.09 |
| Callee | 2B.02 |
| Authorized by | D's own component identity. Only D writes a task's state; no other component may (task-state contract, section 6). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `not_verified`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-ORC-07, LA-ORC-06, LA-MEM-08, LA-REL-01 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `task_id` | yes | string, `tsk_` |
| `state` | yes | string, one of the eight task states |
| `stop_reason` | no | string, required when the state is `stopped` |
| `evidence_ids` | yes | array of strings, `evd_`. Required and non-empty for `completed-verified` |
| `updated_at` | yes | RFC 3339 UTC with milliseconds |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `recorded_at` | yes | RFC 3339 UTC with milliseconds |
| `state` | yes | string, echoed |

**When the callee is down.** D keeps the state in its own durable queue and retries. Work continues when the voice session closes (LA-ORC-02, LA-REL-01).

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

#### STATE-02  `GET /v1/tasks/{task_id}/evidence`

D reads back the evidence for a task before it may mark it completed-verified.

| | |
| --- | --- |
| Caller | 2A.09 |
| Callee | 2B.02 |
| Authorized by | D's own component identity. A read only. |
| Errors | `unauthenticated`, `forbidden`, `not_found`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-ORC-06, LA-IF-04, LA-EVD-01 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `task_id` | no | path parameter, `tsk_` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `evidence` | yes | array of objects, each with `evidence_id`, `stage`, `outcome` and `observed_at` |
| `verified_by` | yes | string, `2B.06` or null. D may not mark a task verified on a null |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller shows the view as unavailable and says so plainly; it never shows stale data as current (LA-EVD-04, LA-MON-06).

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### BND-11  A to G, Hermes and all Receptors

| | |
| --- | --- |
| Style in the diagram | Red |
| Meaning | STOP / PAUSE / RESUME bus |
| Sides | 2A.06 to 2A.07; 2A.06 to 2B.05; 2A.07 to 2A.06 |

#### BUS-01  `POST /v1/stop-state`

The bus pushes the current stop state to the Tool Hub and to Hermes.

| | |
| --- | --- |
| Caller | 2A.06 |
| Callee | 2A.07 or 2B.05 |
| Authorized by | A, the Governance Core, through the bus. Deterministic control code, no LLM in the path, and it keeps working when B, C and Hermes are down (LA-DEP-02). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-GOV-03, LA-SAF-01, LA-HER-05, LA-DEP-02, LA-IF-03 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `command` | yes | string, `stop`, `pause` or `resume` |
| `scope` | yes | string, `all` or `receptor` |
| `receptor_id` | no | string, `rcp_` when scope is `receptor` |
| `incident_id` | no | string, `inc_` |
| `authorization_id` | no | string, required on `resume` |
| `issued_at` | yes | RFC 3339 UTC with milliseconds |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `applied_at` | yes | RFC 3339 UTC with milliseconds |
| `in_flight` | yes | array of strings, what was running when it arrived |
| `self_resume_possible` | yes | boolean, always false for Hermes (LA-HER-05) |

**When the callee is down.** The bus retries and raises an incident. A component that cannot be told is treated as not stopped and reported as such; G refuses its calls instead, so nothing new runs.

**When STOP or PAUSE is active.** Always allowed and idempotent, as in STOP-01.

#### BUS-02  `GET /v1/stop-state`

G reads the current stop state. It does this on every single tool call.

| | |
| --- | --- |
| Caller | 2A.07 |
| Callee | 2A.06 |
| Authorized by | G's own component identity. A read only. |
| Errors | `unauthenticated`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-SAF-02, LA-TOOL-01, LA-GOV-03 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `receptor_id` | no | query, `rcp_` to ask about one Receptor |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `stopped` | yes | boolean |
| `scope` | yes | string, `all`, `receptor` or `none` |
| `stop_reason` | no | string, `pause`, `stop` or `breach` when stopped |
| `as_of` | yes | RFC 3339 UTC with milliseconds |

**When the callee is down.** G treats an unreachable bus as stopped and refuses the call with `stopped`. A STOP that cannot be read is never read as a go-ahead.

**When STOP or PAUSE is active.** Always allowed, and it is the call that matters most while stopped: this is how G learns that a stop is in force. It is a read, starts no work and carries no authority.

### BND-12  E to A and J; Receptors to E

| | |
| --- | --- |
| Style in the diagram | Orange, dashed |
| Meaning | Escalation; monitoring and health status |
| Sides | P1.06 to 2A.05; P1.07 to P1.06 |

#### ESC-01  `POST /v1/escalations`

E escalates a repeated-failure or pause condition. A decides what happens; E does not.

| | |
| --- | --- |
| Caller | P1.06 |
| Callee | 2A.05 |
| Authorized by | E's own component identity. E has no authority to act on a Receptor; it observes and escalates. |
| Errors | `invalid_request`, `unauthenticated`, `idempotency_conflict`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-MON-03, LA-MON-05, LA-MON-06 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `receptor_id` | yes | string, `rcp_` |
| `condition` | yes | string, `repeated-failure`, `pause-condition` or `offline` |
| `evidence_ref` | yes | string, where the observations can be read |
| `observed_at` | yes | RFC 3339 UTC with milliseconds |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `escalation_id` | yes | string |
| `decision_owner` | yes | string, always `2A.05` |
| `action_taken` | yes | string, always `none` at this point: Governance decides (LA-MON-05) |

**When the callee is down.** E keeps the escalation in its own queue, retries, and shows the condition as unescalated so that it is visible rather than silently dropped (LA-MON-06).

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

#### ESC-02  `GET /v1/health-views/{view}`

The dashboard reads E's health and KPI views, read-only.

| | |
| --- | --- |
| Caller | P1.07 |
| Callee | P1.06 |
| Authorized by | J's own read-only component identity. Visibility confers no authority (LA-DASH-02, AMD-10). |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `not_found`, `rate_limited`, `internal`, `dependency_down` |
| Requirements | LA-MON-04, LA-DASH-02 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `view` | no | path parameter, `receptor-health` or `kpis` |
| `receptor_id` | no | query, `rcp_` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `rows` | yes | array of objects |
| `as_of` | yes | RFC 3339 UTC with milliseconds |
| `stale` | yes | boolean, true when the data is older than its freshness bound |

**When the callee is down.** Answer the caller `dependency_down` (503, retriable). The caller shows the view as unavailable and says so plainly; it never shows stale data as current (LA-EVD-04, LA-MON-06).

**When STOP or PAUSE is active.** Allowed while stopped: this call carries no authority to act and starts no new work. It is recorded like any other call.

### BND-13  Receptors to H

| | |
| --- | --- |
| Style in the diagram | Purple, dashed |
| Meaning | Financial reporting |
| Sides | Receptor to 2B.08 |

This path is the Receptor edge of LANE-FIN. Its operations are defined there and are not repeated here.

### BND-14  Bank Vault to H

| | |
| --- | --- |
| Style in the diagram | Blue |
| Meaning | Bank statement upload only (read-only input) |
| Sides | Founder to 2B.08 |

#### VLT-01  `POST /v1/bank-statements`

The Founder uploads a statement. This is the only path from the bank into Dyson.

| | |
| --- | --- |
| Caller | Founder |
| Callee | 2B.08 |
| Authorized by | The Founder alone, authenticated at the Entry Gateway. Dyson holds no bank credential and has no bank API: upload only (LA-VLT-01, LA-VLT-02). No component may call this on the Founder's behalf. |
| Errors | `invalid_request`, `unauthenticated`, `forbidden`, `idempotency_conflict`, `internal`, `dependency_down` |
| Requirements | LA-VLT-01, LA-VLT-02, LA-VLT-03, LA-VLT-04, LA-IF-05, LA-FIN-04 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `Idempotency-Key` | yes | header, `idem_` + 26 base32. Required on every state-changing call |
| `statement_ref` | yes | string, where the uploaded file was stored |
| `period` | yes | string, `YYYY-MM-DD` to `YYYY-MM-DD` |
| `uploaded_by` | yes | string, always `founder` |
| `uploaded_at` | yes | RFC 3339 UTC with milliseconds |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `statement_id` | yes | string |
| `lines_parsed` | yes | integer |
| `matched_reports` | yes | array of strings, the revenue reports this statement makes final |
| `classified_as` | yes | string, always `personal-financial-data` under the gate 6 policy (LA-VLT-04) |

**When the callee is down.** The upload fails and is reported as failed. Revenue stays `reported-not-final`; nothing is marked final on an unparsed statement.

**When STOP or PAUSE is active.** Allowed while stopped: it moves no money and starts no task. It is recorded in the audit log.

### BND-15  F and Receptors; G and Receptors

| | |
| --- | --- |
| Style in the diagram | Green and blue |
| Meaning | QA/QC verification lane; tasks lane via the Tool Hub |
| Sides | 2B.06 to Receptor; 2A.07 to Receptor |

This path is the Receptor edge of LANE-QA and LANE-TASK. Its operations are defined there and are not repeated here.

## 3. One contract that is not a drawn path (Derived)

### INT-01  G and the Supply Chain / Integration Gate (inside card A)

| | |
| --- | --- |
| Style in the diagram | Not drawn separately |
| Why it exists | Derived. The Gate is drawn as a box inside the Governance Core (PRD section 7.2.1), not as its own path. G needs it because nothing is callable until it has passed the Gate (LA-TOOL-03). |
| Sides | 2A.07 to 2A.08 |

#### SCG-01  `GET /v1/admissions/{tool_id}`

G checks that a tool, API, plugin or MCP connector has been admitted before it is callable.

| | |
| --- | --- |
| Caller | 2A.07 |
| Callee | 2A.08 |
| Authorized by | G's own component identity. A read only. Admission itself is the Gate's decision and a high-risk item needs the Founder's approval (LA-GOV-06, LA-SEC-04). |
| Errors | `unauthenticated`, `not_found`, `rate_limited`, `internal`, `dependency_down`, `timeout` |
| Requirements | LA-TOOL-03, LA-GOV-06, LA-SEC-04, LA-SEC-05 |

**Request**

| Field | Required | Specification |
| --- | --- | --- |
| `tool_id` | no | path parameter, `tool_` |

**Response (success)**

| Field | Required | Specification |
| --- | --- | --- |
| `tool_id` | yes | string, echoed |
| `admitted` | yes | boolean |
| `risk` | yes | string, `low`, `medium` or `high` |
| `founder_approval_id` | yes | string, `apr_`, required and present when risk is `high` |
| `change_record_ref` | yes | string, the auditable change record for this admission |
| `blocked` | yes | boolean, true when the item is suspect and isolated under AMD-5 |

**When the callee is down.** G treats an unreachable Gate as not admitted and refuses the tool call with `not_admitted`. An unknown admission state is never read as admitted.

**When STOP or PAUSE is active.** Always allowed: it is a read and starts no work.

## 4. Paths with no contract in v1

| Path in the figure | Why there is no contract |
| --- | --- |
| R11 to R14 | Optional governed receptor-to-receptor support. It needs more than one Receptor, and the baseline has only Test T0 (LA-IF-08, rule 8). No contract in v1. |
| Customers and R11; customer payment to bank | A Layer B concern. Layer A never sits in the customer payment flow, so there is nothing for it to implement (LA-IF-06). |
