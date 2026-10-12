"""Builds contracts/registry.json and contracts/CONTRACTS.md for package P1.10.

registry.json is the machine-readable source the stubs and the contract tests both read.
CONTRACTS.md is the same content for a person to review.

Run:  python3 contracts/build_registry.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "v1.0"
DATE = "11 Oct 2026"

# ----------------------------------------------------------------------------------------------
# components: the component map of the work orders (section 7.1), plus the stub port of each
# ----------------------------------------------------------------------------------------------
COMPONENTS = [
    ("P1.05", "-", "Dyson app, Web first with Android as the target", "Part 1", 8105),
    ("P1.06", "E", "Monitoring and Health Controller (E)", "Part 1", 8106),
    ("P1.07", "J", "Founder Financial Dashboard (J)", "Part 1", 8107),
    ("2A.03", "-", "Entry Gateway", "Part 2A", 8203),
    ("2A.04", "-", "Direct Founder Controls", "Part 2A", 8204),
    ("2A.05", "A", "Governance Core", "Part 2A", 8205),
    ("2A.06", "-", "STOP / PAUSE / RESUME bus", "Part 2A", 8206),
    ("2A.07", "G", "Governed Tool Hub (G)", "Part 2A", 8207),
    ("2A.08", "-", "Supply Chain / Integration Gate", "Part 2A", 8208),
    ("2A.09", "D", "Task engine (Orchestrator D)", "Part 2A", 8209),
    ("2B.02", "I", "Memory & Evidence Layer (I)", "Part 2B", 8302),
    ("2B.03", "C", "Model Router & Fallback (C)", "Part 2B", 8303),
    ("2B.04", "B", "Conversation Engine (B)", "Part 2B", 8304),
    ("2B.05", "4 (Hermes)", "Hermes runtime", "Part 2B", 8305),
    ("2B.06", "F", "QA/QC Controller (F)", "Part 2B", 8306),
    ("2B.07", "-", "Test T0 and its independent verifier, built as a minimal fixture", "Part 2B", 8307),
    ("2B.08", "H", "Financial Control (H)", "Part 2B", 8308),
]
# Actors that are not Layer A components.
ACTORS = {
    "Founder": "The Founder, a person. Authenticated at the Entry Gateway; the only source of authorization",
    "Receptor": "A Layer B Receptor. In the baseline the only one is Test T0 (2B.07), synthetic and no-money",
}

DOWN_RETRY = ("Answer the caller `dependency_down` (503, retriable). The caller keeps its task in its current "
              "state, records the attempt, and retries with the same idempotency key inside its retry limit. "
              "Nothing is reported as complete.")
DOWN_READ = ("Answer the caller `dependency_down` (503, retriable). The caller shows the view as unavailable "
             "and says so plainly; it never shows stale data as current (LA-EVD-04, LA-MON-06).")
STOP_REFUSE = ("Refuse with `stopped` (409). No new work starts, and the refusal is written to the audit log. "
               "STOP is checked on every call, whatever the AI model does (LA-SAF-01, LA-SAF-02).")
STOP_ALLOW = ("Allowed while stopped: this call carries no authority to act and starts no new work. It is "
              "recorded like any other call.")


def op(oid, method, path, caller, callee, purpose, req, resp, auth, down, stopped, errors, reqs):
    """One operation of a contract. A key in req/resp beginning with '!' is a required field."""
    def fields(d):
        return [{"name": k.lstrip("!"), "required": k.startswith("!"), "spec": v} for k, v in d.items()]
    return {
        "operation_id": oid, "method": method, "path": path, "caller": caller, "callee": callee,
        "purpose": purpose, "request": fields(req), "response": fields(resp), "authorized_by": auth,
        "when_callee_is_down": down, "when_stopped": stopped, "errors": errors, "requirements": reqs,
    }


IDEM = {"!Idempotency-Key": "header, `idem_` + 26 base32. Required on every state-changing call"}

# ----------------------------------------------------------------------------------------------
# the five Layer A to Layer B lanes (PRD section 8)
# ----------------------------------------------------------------------------------------------
LANES = [
    {
        "id": "LANE-QA", "chip": "QA/QC & Verification", "style": "Green, solid",
        "layer_a_owner": "F Independent QA/QC Controller", "owner_package": "2B.06",
        "direction": "Request down to the Receptor, evidence and results back",
        "carries": "Quality standards, verification requests, evidence, results, escalations",
        "basis": "Diagram; AMD-3",
        "operations": [
            op("QA-01", "POST", "/v1/verifications", "2B.06", "Receptor",
               "F asks the Receptor to produce the real-output evidence for a task.",
               {**IDEM, "!verification_id": "string, `evd_`-style id minted by F", "!task_id": "string, `tsk_`",
                "!quality_standard": "string, the standard F will judge against",
                "!requested_evidence": "array of strings, what the Receptor must produce",
                "deadline_ms": "integer, how long F will wait"},
               {"!verification_id": "string, echoed", "!status": "string, `accepted`",
                "!accepted_at": "RFC 3339 UTC with milliseconds"},
               "F's own component identity, issued by 2A.02. A Receptor accepts a verification request only from F.",
               DOWN_RETRY, STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "stopped", "rate_limited", "internal",
                "dependency_down", "timeout"],
               ["LA-IF-01", "LA-IF-04", "LA-QA-01"]),
            op("QA-02", "POST", "/v1/evidence", "Receptor", "2B.06",
               "The Receptor returns its evidence. The claim is not proof: F verifies the real output itself.",
               {**IDEM, "!verification_id": "string", "!task_id": "string, `tsk_`",
                "!evidence": "array of objects, each with `kind`, `ref` and `produced_at`",
                "claimed_outcome": "string, the Receptor's own claim. Recorded, never trusted"},
               {"!evidence_ids": "array of strings, `evd_` ids written to the registry",
                "!verdict": "string, always `pending` on arrival. F decides in its own time",
                "!self_certification_accepted": "boolean, always false (LA-QA-05)"},
               "The Receptor's own identity. It authorizes nothing: it may report, never conclude.",
               DOWN_RETRY, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "not_found", "idempotency_conflict",
                "rate_limited", "internal"],
               ["LA-IF-04", "LA-QA-05", "LA-EVD-01", "LA-EVD-02"]),
            op("QA-03", "POST", "/v1/escalations", "Receptor", "2B.06",
               "The Receptor escalates a problem it cannot solve inside its own bounds.",
               {**IDEM, "!receptor_id": "string, `rcp_`", "!severity": "string, `low`, `medium` or `high`",
                "!summary": "string, one sentence", "task_id": "string, `tsk_` if it concerns one task"},
               {"!escalation_id": "string", "!routed_to": "string, `2B.06`, and `2A.05` when severity is high"},
               "The Receptor's own identity.", DOWN_RETRY, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "rate_limited", "internal"],
               ["LA-QA-04", "LA-MON-06"]),
        ],
    },
    {
        "id": "LANE-TASK", "chip": "Tasks from Orchestrator (via Tool Hub)", "style": "Blue, solid",
        "layer_a_owner": "D Orchestrator through G Governed Tool Hub", "owner_package": "2A.09",
        "direction": "Tasks down, results back",
        "carries": "Task instructions with task ID and idempotency key",
        "basis": "Diagram; Closure §9",
        "operations": [
            op("TASK-01", "POST", "/v1/receptor/tasks", "2A.07", "Receptor",
               "G hands a Receptor one task on D's behalf. G is the only path to a Receptor's task interface.",
               {**IDEM, "!task_id": "string, `tsk_`, minted by D", "!receptor_id": "string, `rcp_`",
                "!instruction": "object, what to do, inside the Receptor's declared scope",
                "!scope": "object, the permitted tools and spend for this task",
                "approval_id": "string, `apr_` when the action needed a Founder approval",
                "deadline_ms": "integer"},
               {"!task_id": "string, echoed", "!state": "string, `accepted`",
                "!accepted_at": "RFC 3339 UTC with milliseconds"},
               "G, after it has checked identity and permission, Receptor scope, risk and spend limits, approval "
               "status and the current STOP state. A Receptor refuses a task from anyone but G.",
               DOWN_RETRY, STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "approval_needed",
                "stopped", "not_admitted", "spend_limit", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-IF-01", "LA-IF-02", "LA-TOOL-01", "LA-TOOL-02", "LA-ORC-03", "LA-ORC-05"]),
            op("TASK-02", "POST", "/v1/task-results", "Receptor", "2A.07",
               "The Receptor reports a result. The task does not become completed-verified on this report.",
               {**IDEM, "!task_id": "string, `tsk_`", "!output_ref": "string, where the real output can be checked",
                "!claimed_outcome": "string, the Receptor's own claim",
                "evidence": "array of objects, what it can show"},
               {"!task_id": "string, echoed", "!state": "string, `running` until F verifies (LA-IF-04)",
                "!verification_required": "boolean, always true"},
               "The Receptor's own identity. It cannot set a task's state.",
               DOWN_RETRY, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "not_found", "idempotency_conflict",
                "rate_limited", "internal"],
               ["LA-IF-04", "LA-ORC-06", "LA-EVD-01", "LA-EVD-02"]),
        ],
    },
    {
        "id": "LANE-FIN", "chip": "Financial Reporting", "style": "Purple, dashed",
        "layer_a_owner": "H Financial Control & Reconciliation", "owner_package": "2B.08",
        "direction": "Receptor to Core", "carries": "Revenue reports and payment records",
        "basis": "Diagram; AMD-2",
        "operations": [
            op("FIN-01", "POST", "/v1/revenue-reports", "Receptor", "2B.08",
               "The Receptor reports revenue. It stays not final until H matches a Founder-uploaded statement.",
               {**IDEM, "!receptor_id": "string, `rcp_`", "!period": "string, `YYYY-MM-DD` to `YYYY-MM-DD`",
                "!amount_minor": "integer, in the currency's minor unit. No floating point for money",
                "!currency": "string, ISO 4217", "payment_records": "array of objects, each with `ref` and `amount_minor`"},
               {"!report_id": "string", "!status": "string, always `reported-not-final` on arrival (LA-IF-05)",
                "!reconciled": "boolean, always false on arrival",
                "!bank_statement_required": "boolean, always true"},
               "The Receptor's own identity. A report authorizes no payment and moves no money: Layer A never "
               "sits in the customer payment flow (LA-IF-06).",
               DOWN_RETRY, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "rate_limited", "internal"],
               ["LA-IF-01", "LA-IF-05", "LA-IF-06", "LA-FIN-01", "LA-FIN-02"]),
        ],
    },
    {
        "id": "LANE-MON", "chip": "Monitoring / Health", "style": "Orange, dashed",
        "layer_a_owner": "E Monitoring & Health Controller", "owner_package": "P1.06",
        "direction": "Receptor to Core", "carries": "Task status, KPIs, health, failures",
        "basis": "Diagram; AMD-10",
        "operations": [
            op("MON-01", "POST", "/v1/health-reports", "Receptor", "P1.06",
               "The Receptor reports its status, KPIs and failures on the monitoring lane.",
               {**IDEM, "!receptor_id": "string, `rcp_`",
                "!status": "string, `healthy`, `degraded`, `failing` or `offline`",
                "!reported_at": "RFC 3339 UTC with milliseconds",
                "kpis": "object, name to number", "failures": "array of objects, each with `task_id` and `reason`"},
               {"!accepted": "boolean", "!escalated": "boolean, true when a repeated-failure condition is met"},
               "The Receptor's own identity. A report gives E no authority to act on the Receptor (LA-MON-05).",
               DOWN_RETRY, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "idempotency_conflict", "rate_limited", "internal"],
               ["LA-IF-01", "LA-MON-01", "LA-MON-02"]),
            op("MON-02", "GET", "/v1/health", "P1.06", "Receptor",
               "E polls the Receptor's health endpoint, so an offline Receptor is reported as offline.",
               {}, {"!receptor_id": "string", "!status": "string, as in MON-01",
                    "!checks": "array of objects, each with `name` and `ok`"},
               "E's own component identity. A read only.",
               ("E records the Receptor as `offline` and reports it as offline rather than silent "
                "(LA-MON-06). It raises a repeated-failure condition if the poll keeps failing."),
               STOP_ALLOW,
               ["unauthenticated", "not_found", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-MON-01", "LA-MON-06"]),
        ],
    },
    {
        "id": "LANE-STOP", "chip": "STOP / PAUSE / RESUME (to all receptors)", "style": "Red, solid",
        "layer_a_owner": "A Governance Core", "owner_package": "2A.05",
        "direction": "Core to Receptor", "carries": "Control commands, independent of AI reasoning",
        "basis": "Diagram; AMD-5",
        "operations": [
            op("STOP-01", "POST", "/v1/control", "2A.06", "Receptor",
               "The red path carries STOP, PAUSE and RESUME to every Receptor, with no LLM in its way.",
               {**IDEM, "!command": "string, `stop`, `pause` or `resume`", "!receptor_id": "string, `rcp_` or `all`",
                "!issued_at": "RFC 3339 UTC with milliseconds",
                "incident_id": "string, `inc_`, required when the command follows a breach",
                "authorization_id": "string, required on `resume` (LA-SAF-04)"},
               {"!command": "string, echoed", "!applied": "boolean",
                "!applied_at": "RFC 3339 UTC with milliseconds",
                "!in_flight": "array of strings, task ids that were already running when the command arrived"},
               "A, the Governance Core, on the Founder's command. Deterministic control code; no model decides "
               "it, and it works when every model and the app are down (LA-GOV-03, LA-DFC-04).",
               ("The bus retries on the red path and raises an incident. A Receptor that cannot be reached is "
                "treated as not stopped, reported as such, and isolated at the Tool Hub instead, so no new "
                "task reaches it."),
               ("A STOP or PAUSE always applies, even while already stopped: the command is idempotent. A "
                "`resume` is refused with `forbidden` when it carries no authorization, and after a breach it "
                "needs an authorization naming the incident (LA-GOV-08, LA-SAF-04)."),
               ["invalid_request", "unauthenticated", "forbidden", "rate_limited", "internal", "dependency_down",
                "timeout"],
               ["LA-IF-03", "LA-SAF-01", "LA-SAF-03", "LA-SAF-04", "LA-GOV-03", "LA-GOV-08", "LA-DFC-04"]),
        ],
    },
]

# ----------------------------------------------------------------------------------------------
# component boundaries: one per row of the PRD's "Paths drawn in the figure" table
# ----------------------------------------------------------------------------------------------
BOUNDARIES = [
    {
        "id": "BND-01", "path": "Founder, Dyson App, Entry Gateway", "style": "Blue out, green back",
        "meaning": "Voice or text instruction in; answer, report or response out",
        "pairs": [["Founder", "P1.05"], ["P1.05", "2A.03"]],
        "operations": [
            op("GW-01", "POST", "/v1/sessions", "P1.05", "2A.03",
               "The Gateway authenticates the Founder for the session and issues a session token.",
               {**IDEM,
                "!authenticator_assertion": "object, the result of the Founder's own authentication. The app "
                                            "never holds or forwards a credential (LA-SEC-01)"},
               {"!session_token": "string, opaque, short-lived", "!expires_at": "RFC 3339 UTC with milliseconds",
                "!subject": "string, always `founder`"},
               "The Founder, authenticated at the Gateway for every session. The app holds no authority of its "
               "own (LA-APP-06, LA-SEC-03).",
               DOWN_READ,
               ("Sessions still open while the Core is stopped, so the Founder can see state and use the Direct "
                "Founder Controls. No new task is accepted (BND-03 is the path that is never blocked)."),
               ["invalid_request", "unauthenticated", "rate_limited", "internal", "dependency_down"],
               ["LA-GW-01", "LA-GW-02", "LA-SEC-03", "LA-APP-06"]),
            op("GW-02", "POST", "/v1/messages", "P1.05", "2A.03",
               "One Founder instruction in Hindi, English or Hinglish. The answer is an honest acknowledgment.",
               {**IDEM, "!locale": "string, `hi`, `en` or `hi-Latn` for Hinglish",
                "!content": "object, `text` or `audio_ref`",
                "transcription_uncertain": "boolean, true when speech recognition was not confident (LA-APP-07)"},
               {"!acknowledgment": "string, `accepted` or `approval-needed`. Never a completion (LA-APP-04)",
                "task_id": "string, `tsk_` when the instruction became a task",
                "!thread_id": "string, one history for voice and text (LA-APP-03)"},
               "The session token from GW-01.", DOWN_RETRY, STOP_REFUSE,
               ["invalid_request", "unauthenticated", "idempotency_conflict", "approval_needed", "stopped",
                "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-APP-02", "LA-APP-03", "LA-APP-04", "LA-APP-07", "LA-PERF-01", "LA-GW-03"]),
        ],
    },
    {
        "id": "BND-02", "path": "Entry Gateway and B", "style": "Blue down, green up",
        "meaning": "Gateway routes to the Conversation Engine; B's response returns to the Founder",
        "pairs": [["2A.03", "2B.04"]],
        "operations": [
            op("CONV-01", "POST", "/v1/conversation/turns", "2A.03", "2B.04",
               "The Gateway routes an authenticated instruction to B, which interprets it in thread context.",
               {**IDEM, "!thread_id": "string", "!locale": "string, as in GW-02",
                "!content": "object, `text` or a transcript of the audio",
                "transcription_uncertain": "boolean, carried through from the app"},
               {"!reply": "string, what the Founder is told",
                "!intent": "string, `answer`, `clarify` or `proposed_action`",
                "proposed_action": "object, present only for `proposed_action`, to be checked at BND-04",
                "!completion_claimed": "boolean, always false here (LA-CONV-07)"},
               "The Gateway, which has already authenticated the Founder. B holds no authority to execute.",
               DOWN_READ, STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "stopped",
                "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-GW-03", "LA-CONV-01", "LA-CONV-03", "LA-CONV-07"]),
        ],
    },
    {
        "id": "BND-03", "path": "Direct Founder Controls to A", "style": "Red",
        "meaning": ("Approve / Reject and Emergency STOP / PAUSE go straight to the Governance Core, not "
                    "through the app or the normal flow"),
        "pairs": [["2A.04", "2A.05"]],
        "operations": [
            op("DFC-01", "POST", "/v1/controls/decision", "2A.04", "2A.05",
               "The Founder approves or rejects one exact action. A Reject ends the task (open item 3).",
               {**IDEM, "!approval_id": "string, `apr_`", "!decision": "string, `approve` or `reject`",
                "!bound_action_digest": "string, the digest of the exact action shown to the Founder (LA-DFC-05)",
                "!authenticator_assertion": "object, the step-up authentication chosen at gate 3"},
               {"!approval_id": "string, echoed", "!recorded_at": "RFC 3339 UTC with milliseconds",
                "!task_state": "string, `running` on approve, `stopped` with `stop_reason` `reject` on reject",
                "!approver": "string, always `founder`"},
               "The Founder alone, on an independently authenticated path that touches no app and no LLM. No "
               "model, agent or Receptor can produce this call (LA-DFC-01, LA-GOV-02, LA-AMD-01).",
               ("The control path is the last thing allowed to fail. If A does not answer, the Controls raise "
                "an incident, keep the decision unsent, and show the Founder that it was not recorded. A "
                "decision is never assumed to have landed."),
               ("Always allowed. An approval decision reaches A even while the Core is stopped: that is how a "
                "stop is lifted and how a rejected task is closed."),
               ["invalid_request", "unauthenticated", "forbidden", "not_found", "idempotency_conflict",
                "internal", "dependency_down", "timeout"],
               ["LA-DFC-01", "LA-DFC-02", "LA-DFC-03", "LA-DFC-05", "LA-GOV-02", "LA-AMD-01"]),
            op("DFC-02", "POST", "/v1/controls/emergency", "2A.04", "2A.05",
               "Emergency STOP or PAUSE, working whatever the models and the app are doing.",
               {**IDEM, "!command": "string, `stop`, `pause` or `resume`",
                "!scope": "string, `all` or `receptor`", "receptor_id": "string, required when scope is `receptor`",
                "!authenticator_assertion": "object, the step-up authentication chosen at gate 3",
                "incident_id": "string, `inc_`, required to resume after a breach"},
               {"!incident_id": "string, `inc_`", "!applied_at": "RFC 3339 UTC with milliseconds",
                "!reached": "array of strings, the components and Receptors the command reached",
                "!not_reached": "array of strings, reported plainly rather than assumed stopped"},
               "The Founder alone, independently authenticated. Deterministic: no LLM in the path (LA-GOV-03).",
               ("A STOP that cannot be recorded is still carried out: the bus applies it and the failure to "
                "record raises an incident. A resume is never applied when A cannot be reached."),
               "Always allowed, and idempotent: a STOP on an already stopped system is accepted.",
               ["invalid_request", "unauthenticated", "forbidden", "internal", "dependency_down", "timeout"],
               ["LA-DFC-01", "LA-DFC-04", "LA-GOV-03", "LA-SAF-01", "LA-SAF-04"]),
        ],
    },
    {
        "id": "BND-04", "path": "A and B", "style": "Blue, two-way", "meaning": "Policy / approval checks",
        "pairs": [["2B.04", "2A.05"]],
        "operations": [
            op("POL-01", "POST", "/v1/policy/checks", "2B.04", "2A.05",
               "B asks A whether a prepared action is allowed, before it is prepared for execution.",
               {**IDEM, "!proposed_action": "object, what would be done, with its tools and scope",
                "estimated_spend_minor": "integer, in the currency's minor unit",
                "receptor_id": "string, `rcp_` when the action touches a Receptor",
                "!thread_id": "string"},
               {"!verdict": "string, `allow`, `approval-needed` or `deny`",
                "!policy_version": "string, the version of the rule that decided it (LA-GOV-01)",
                "approval_id": "string, `apr_` created when the verdict is `approval-needed`",
                "bound_action_digest": "string, present with an approval_id: the digest of the exact action "
                                       "the approval is bound to, which the Founder's controls must send back "
                                       "(LA-DFC-05)",
                "!reasons": "array of strings, which rule decided, for the audit log"},
               "B's own component identity. The verdict is A's alone, and A refuses a verdict from any model, "
               "agent or Receptor (LA-GOV-02). Every financial action stays blocked until an approval exists "
               "(LA-GOV-05).",
               ("B must not proceed. It answers the Founder that the check could not be made, and the task "
                "stays where it is. A missing policy check is never read as an allow."),
               STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "stopped",
                "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-GOV-01", "LA-GOV-02", "LA-GOV-04", "LA-GOV-05", "LA-CONV-06", "LA-AMD-01", "LA-AMD-02"]),
        ],
    },
    {
        "id": "BND-05", "path": "B, C, D, E (neighbors)", "style": "Blue right, green left",
        "meaning": "Neighboring cards exchange requests and responses",
        "pairs": [["2B.04", "2B.03"], ["2B.04", "2A.09"], ["2A.09", "P1.06"]],
        "operations": [
            op("RTR-01", "POST", "/v1/model/completions", "2B.04", "2B.03",
               "B reaches an external model only through C, inside cost and token limits.",
               {**IDEM, "!purpose": "string, what the call is for, used to pick a model",
                "!input": "object, the prompt material. C applies the gate 6 redaction rules before it leaves",
                "max_cost_minor": "integer, the ceiling for this call",
                "task_id": "string, `tsk_` when the call belongs to a task"},
               {"!model_id": "string, the approved model that answered",
                "!output": "object, the model's answer", "!cost_minor": "integer, what it cost",
                "!redaction_applied": "boolean, true when redaction rules changed the input (LA-RTR-07)",
                "!fallback_used": "boolean, true when the first choice failed (LA-RTR-04)"},
               "B's own component identity. C is the only approved path to an external model, and no model "
               "access exists outside governance (LA-RTR-01).",
               ("C answers `dependency_down` only after its tested fallback has also failed. Task state and "
                "memory survive either way (LA-RTR-04, LA-REL-06)."),
               STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "stopped",
                "spend_limit", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-RTR-01", "LA-RTR-02", "LA-RTR-04", "LA-RTR-05", "LA-RTR-07", "LA-SEC-07"]),
            op("ORC-01", "POST", "/v1/tasks", "2B.04", "2A.09",
               "B hands a prepared instruction to D, which mints the task and owns its state from then on.",
               {**IDEM, "!instruction": "object, the prepared action", "!thread_id": "string",
                "approval_id": "string, `apr_` when BND-04 answered `approval-needed`",
                "receptor_id": "string, `rcp_` when the task touches a Receptor"},
               {"!task_id": "string, `tsk_`, minted by D and by nobody else",
                "!state": "string, `accepted` or `approval-needed`",
                "!created_at": "RFC 3339 UTC with milliseconds"},
               "B's own component identity. B prepares and never executes (LA-CONV-02); D routes all tool use "
               "through G (LA-ORC-05).",
               DOWN_RETRY, STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "approval_needed",
                "stopped", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-CONV-02", "LA-ORC-01", "LA-ORC-02", "LA-ORC-03", "LA-REL-01", "LA-REL-02"]),
            op("MON-03", "POST", "/v1/task-status", "2A.09", "P1.06",
               "D tells E a task's state, so monitoring and the dashboard can show the truth.",
               {**IDEM, "!task_id": "string, `tsk_`", "!state": "string, one of the eight task states",
                "stop_reason": "string, present when the state is `stopped`",
                "receptor_id": "string, `rcp_`", "!updated_at": "RFC 3339 UTC with milliseconds"},
               {"!accepted": "boolean"},
               "D's own component identity. E observes and escalates; it never acts (LA-MON-05).",
               ("D keeps the state in its own durable store and retries. A monitoring outage never changes a "
                "task's state or stops the work."),
               STOP_ALLOW,
               ["invalid_request", "unauthenticated", "idempotency_conflict", "rate_limited", "internal",
                "dependency_down"],
               ["LA-MON-02", "LA-MON-04", "LA-ORC-01"]),
        ],
    },
    {
        "id": "BND-06", "path": "Hermes and C", "style": "Blue, two-way",
        "meaning": "Approved model access, governed",
        "pairs": [["2B.05", "2B.03"]],
        "operations": [
            op("HER-01", "POST", "/v1/model/completions", "2B.05", "2B.03",
               "Hermes reaches a model only through C, with its own identity and its own limits.",
               {**IDEM, "!purpose": "string", "!input": "object, redaction applies as in RTR-01",
                "max_cost_minor": "integer", "task_id": "string, `tsk_`"},
               {"!model_id": "string", "!output": "object", "!cost_minor": "integer",
                "!redaction_applied": "boolean", "!fallback_used": "boolean"},
               "Hermes's own component identity, which is separate from B's and carries no governance rights. "
               "C refuses a call from Hermes that is outside Hermes's approved scope (LA-HER-02, LA-RTR-01).",
               "As in RTR-01. Hermes has no other path to a model and does not fall back on its own.",
               STOP_REFUSE,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "stopped",
                "spend_limit", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-HER-01", "LA-HER-02", "LA-RTR-01", "LA-DEP-01"]),
        ],
    },
    {
        "id": "BND-07", "path": "D and G; Hermes and G", "style": "Blue, two-way",
        "meaning": "All tool use passes through the hub",
        "pairs": [["2A.09", "2A.07"], ["2B.05", "2A.07"]],
        "operations": [
            op("TOOL-01", "POST", "/v1/tool-calls", "2A.09 or 2B.05", "2A.07",
               "Every tool call, from D or from Hermes, is authorized one call at a time by G.",
               {**IDEM, "!tool_id": "string, `tool_`, an entry in G's governed registry",
                "!arguments": "object, the call's own arguments", "!task_id": "string, `tsk_`",
                "receptor_id": "string, `rcp_` when the call acts on a Receptor",
                "estimated_spend_minor": "integer"},
               {"!tool_call_id": "string", "!result": "object, present on success",
                "!checks": "object, the five checks and their outcome: identity, scope, risk and spend, "
                           "approval, STOP state (LA-TOOL-01)",
                "!audited": "boolean, always true, on success and on refusal (LA-TOOL-04)"},
               "G alone, and deterministically: no LLM sits in its decision path (LA-TOOL-07). G is the only "
               "path to any tool, API, plugin or MCP connector, for D and for Hermes alike (LA-TOOL-02, "
               "LA-HER-03).",
               ("The caller gets `dependency_down`. It does not reach the tool another way: there is no other "
                "way. The task stays in its state and the attempt is recorded."),
               ("Refuse with `stopped` (409) and audit the refusal. G checks the STOP state on every single "
                "call, so a stop takes effect on the next call with no restart (LA-SAF-02)."),
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "approval_needed",
                "stopped", "not_admitted", "spend_limit", "rate_limited", "internal", "dependency_down",
                "timeout"],
               ["LA-TOOL-01", "LA-TOOL-02", "LA-TOOL-04", "LA-TOOL-06", "LA-TOOL-07", "LA-SAF-02", "LA-HER-03"]),
        ],
    },
    {
        "id": "BND-08", "path": "F, G, H, I (neighbors)", "style": "Blue right, green left",
        "meaning": "Neighboring cards exchange requests and responses",
        "pairs": [["2B.06", "2B.02"], ["2B.08", "2B.02"], ["2B.06", "2A.07"]],
        "operations": [
            op("EVD-01", "POST", "/v1/evidence", "2B.06", "2B.02",
               "F writes an evidence record at its exact AMD-3 stage, with the failed evidence kept.",
               {**IDEM, "!capability": "string, what was tested", "!provider": "string, by whom",
                "!stage": "integer, 1 to 8, the AMD-3 stage reached",
                "!environment": "string, where it ran", "!observed_at": "RFC 3339 UTC with milliseconds",
                "expires_at": "RFC 3339 UTC with milliseconds",
                "!outcome": "string, `pass` or `fail`. A failure is kept, never dropped",
                "task_id": "string, `tsk_`", "!detail": "object, what was actually run and seen"},
               {"!evidence_id": "string, `evd_`", "!stage": "integer, echoed",
                "!immutable": "boolean, always true: a record is appended, never edited"},
               "F's own component identity. I is a controlled store, not an authority: writing evidence grants "
               "no permission (LA-MEM-08).",
               ("F holds the evidence in its own queue and retries. It never reports a verification as done "
                "while the record is unwritten."),
               STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "rate_limited",
                "internal", "dependency_down"],
               ["LA-EVD-03", "LA-QA-06", "LA-MEM-08", "LA-MEM-07"]),
            op("FIN-02", "POST", "/v1/ledger-entries", "2B.08", "2B.02",
               "H writes a ledger entry. It is final only when a bank statement has matched it.",
               {**IDEM, "!receptor_id": "string, `rcp_`", "!amount_minor": "integer", "!currency": "string",
                "!kind": "string, `revenue-reported`, `revenue-verified` or `payment-record`",
                "statement_id": "string, required for `revenue-verified`",
                "!occurred_at": "RFC 3339 UTC with milliseconds"},
               {"!entry_id": "string", "!final": "boolean, true only for `revenue-verified` (LA-FIN-02)"},
               "H's own component identity. Per-Receptor isolation applies: an entry is scoped to its Receptor "
               "(LA-IF-07, LA-MEM-04).",
               DOWN_RETRY, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "rate_limited",
                "internal", "dependency_down"],
               ["LA-FIN-02", "LA-FIN-05", "LA-FIN-06", "LA-IF-07", "LA-MEM-04"]),
        ],
    },
    {
        "id": "BND-09", "path": "J and I", "style": "Blue, green",
        "meaning": "Dashboard asks (read); memory answers with verified data",
        "pairs": [["P1.07", "2B.02"]],
        "operations": [
            op("DASH-01", "GET", "/v1/financial-views/{view}", "P1.07", "2B.02",
               "The dashboard reads verified financial data. There is no write path and no action path.",
               {"view": "path parameter, `revenue`, `payments`, `profitability`, `receptor-performance` or "
                        "`reconciliation-status`",
                "receptor_id": "query, `rcp_` to scope to one Receptor",
                "period": "query, `YYYY-MM-DD` to `YYYY-MM-DD`"},
               {"!rows": "array of objects, the view's data", "!verified_only": "boolean, always true",
                "!as_of": "RFC 3339 UTC with milliseconds",
                "!unverified_excluded": "integer, how many rows were left out for want of verification"},
               "J's own read-only component identity. J has no authority to execute actions and no write path "
               "into Core controls (LA-DASH-02). It never reaches the bank (LA-DASH-03).",
               DOWN_READ, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "not_found", "rate_limited", "internal",
                "dependency_down", "timeout"],
               ["LA-DASH-01", "LA-DASH-02", "LA-DASH-03", "LA-DASH-04", "LA-MEM-08"]),
        ],
    },
    {
        "id": "BND-10", "path": "D and I", "style": "Blue, two-way", "meaning": "State and evidence",
        "pairs": [["2A.09", "2B.02"]],
        "operations": [
            op("STATE-01", "PUT", "/v1/task-state", "2A.09", "2B.02",
               "D records a task's state and the evidence it rests on, durably.",
               {**IDEM, "!task_id": "string, `tsk_`", "!state": "string, one of the eight task states",
                "stop_reason": "string, required when the state is `stopped`",
                "!evidence_ids": "array of strings, `evd_`. Required and non-empty for `completed-verified`",
                "!updated_at": "RFC 3339 UTC with milliseconds"},
               {"!recorded_at": "RFC 3339 UTC with milliseconds", "!state": "string, echoed"},
               "D's own component identity. Only D writes a task's state; no other component may (task-state "
               "contract, section 6).",
               ("D keeps the state in its own durable queue and retries. Work continues when the voice session "
                "closes (LA-ORC-02, LA-REL-01)."),
               STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "not_verified",
                "rate_limited", "internal", "dependency_down"],
               ["LA-ORC-07", "LA-ORC-06", "LA-MEM-08", "LA-REL-01"]),
            op("STATE-02", "GET", "/v1/tasks/{task_id}/evidence", "2A.09", "2B.02",
               "D reads back the evidence for a task before it may mark it completed-verified.",
               {"task_id": "path parameter, `tsk_`"},
               {"!evidence": "array of objects, each with `evidence_id`, `stage`, `outcome` and `observed_at`",
                "!verified_by": "string, `2B.06` or null. D may not mark a task verified on a null"},
               "D's own component identity. A read only.", DOWN_READ, STOP_ALLOW,
               ["unauthenticated", "forbidden", "not_found", "rate_limited", "internal", "dependency_down"],
               ["LA-ORC-06", "LA-IF-04", "LA-EVD-01"]),
        ],
    },
    {
        "id": "BND-11", "path": "A to G, Hermes and all Receptors", "style": "Red",
        "meaning": "STOP / PAUSE / RESUME bus",
        "pairs": [["2A.06", "2A.07"], ["2A.06", "2B.05"], ["2A.07", "2A.06"]],
        "operations": [
            op("BUS-01", "POST", "/v1/stop-state", "2A.06", "2A.07 or 2B.05",
               "The bus pushes the current stop state to the Tool Hub and to Hermes.",
               {**IDEM, "!command": "string, `stop`, `pause` or `resume`", "!scope": "string, `all` or `receptor`",
                "receptor_id": "string, `rcp_` when scope is `receptor`",
                "incident_id": "string, `inc_`", "authorization_id": "string, required on `resume`",
                "!issued_at": "RFC 3339 UTC with milliseconds"},
               {"!applied_at": "RFC 3339 UTC with milliseconds",
                "!in_flight": "array of strings, what was running when it arrived",
                "!self_resume_possible": "boolean, always false for Hermes (LA-HER-05)"},
               "A, the Governance Core, through the bus. Deterministic control code, no LLM in the path, and it "
               "keeps working when B, C and Hermes are down (LA-DEP-02).",
               ("The bus retries and raises an incident. A component that cannot be told is treated as not "
                "stopped and reported as such; G refuses its calls instead, so nothing new runs."),
               "Always allowed and idempotent, as in STOP-01.",
               ["invalid_request", "unauthenticated", "forbidden", "internal", "dependency_down", "timeout"],
               ["LA-GOV-03", "LA-SAF-01", "LA-HER-05", "LA-DEP-02", "LA-IF-03"]),
            op("BUS-02", "GET", "/v1/stop-state", "2A.07", "2A.06",
               "G reads the current stop state. It does this on every single tool call.",
               {"receptor_id": "query, `rcp_` to ask about one Receptor"},
               {"!stopped": "boolean", "!scope": "string, `all`, `receptor` or `none`",
                "stop_reason": "string, `pause`, `stop` or `breach` when stopped",
                "!as_of": "RFC 3339 UTC with milliseconds"},
               "G's own component identity. A read only.",
               ("G treats an unreachable bus as stopped and refuses the call with `stopped`. A STOP that cannot "
                "be read is never read as a go-ahead."),
               ("Always allowed, and it is the call that matters most while stopped: this is how G learns that "
                "a stop is in force. It is a read, starts no work and carries no authority."),
               ["unauthenticated", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-SAF-02", "LA-TOOL-01", "LA-GOV-03"]),
        ],
    },
    {
        "id": "BND-12", "path": "E to A and J; Receptors to E", "style": "Orange, dashed",
        "meaning": "Escalation; monitoring and health status",
        "pairs": [["P1.06", "2A.05"], ["P1.07", "P1.06"]],
        "operations": [
            op("ESC-01", "POST", "/v1/escalations", "P1.06", "2A.05",
               "E escalates a repeated-failure or pause condition. A decides what happens; E does not.",
               {**IDEM, "!receptor_id": "string, `rcp_`",
                "!condition": "string, `repeated-failure`, `pause-condition` or `offline`",
                "!evidence_ref": "string, where the observations can be read",
                "!observed_at": "RFC 3339 UTC with milliseconds"},
               {"!escalation_id": "string", "!decision_owner": "string, always `2A.05`",
                "!action_taken": "string, always `none` at this point: Governance decides (LA-MON-05)"},
               "E's own component identity. E has no authority to act on a Receptor; it observes and escalates.",
               ("E keeps the escalation in its own queue, retries, and shows the condition as unescalated so "
                "that it is visible rather than silently dropped (LA-MON-06)."),
               STOP_ALLOW,
               ["invalid_request", "unauthenticated", "idempotency_conflict", "rate_limited", "internal",
                "dependency_down"],
               ["LA-MON-03", "LA-MON-05", "LA-MON-06"]),
            op("ESC-02", "GET", "/v1/health-views/{view}", "P1.07", "P1.06",
               "The dashboard reads E's health and KPI views, read-only.",
               {"view": "path parameter, `receptor-health` or `kpis`",
                "receptor_id": "query, `rcp_`"},
               {"!rows": "array of objects", "!as_of": "RFC 3339 UTC with milliseconds",
                "!stale": "boolean, true when the data is older than its freshness bound"},
               "J's own read-only component identity. Visibility confers no authority (LA-DASH-02, AMD-10).",
               DOWN_READ, STOP_ALLOW,
               ["invalid_request", "unauthenticated", "forbidden", "not_found", "rate_limited", "internal",
                "dependency_down"],
               ["LA-MON-04", "LA-DASH-02"]),
        ],
    },
    {
        "id": "BND-13", "path": "Receptors to H", "style": "Purple, dashed", "meaning": "Financial reporting",
        "pairs": [["Receptor", "2B.08"]],
        "same_as": "LANE-FIN",
        "operations": [],
    },
    {
        "id": "BND-14", "path": "Bank Vault to H", "style": "Blue",
        "meaning": "Bank statement upload only (read-only input)",
        "pairs": [["Founder", "2B.08"]],
        "operations": [
            op("VLT-01", "POST", "/v1/bank-statements", "Founder", "2B.08",
               "The Founder uploads a statement. This is the only path from the bank into Dyson.",
               {**IDEM, "!statement_ref": "string, where the uploaded file was stored",
                "!period": "string, `YYYY-MM-DD` to `YYYY-MM-DD`",
                "!uploaded_by": "string, always `founder`",
                "!uploaded_at": "RFC 3339 UTC with milliseconds"},
               {"!statement_id": "string", "!lines_parsed": "integer",
                "!matched_reports": "array of strings, the revenue reports this statement makes final",
                "!classified_as": "string, always `personal-financial-data` under the gate 6 policy (LA-VLT-04)"},
               "The Founder alone, authenticated at the Entry Gateway. Dyson holds no bank credential and has "
               "no bank API: upload only (LA-VLT-01, LA-VLT-02). No component may call this on the Founder's "
               "behalf.",
               ("The upload fails and is reported as failed. Revenue stays `reported-not-final`; nothing is "
                "marked final on an unparsed statement."),
               "Allowed while stopped: it moves no money and starts no task. It is recorded in the audit log.",
               ["invalid_request", "unauthenticated", "forbidden", "idempotency_conflict", "internal",
                "dependency_down"],
               ["LA-VLT-01", "LA-VLT-02", "LA-VLT-03", "LA-VLT-04", "LA-IF-05", "LA-FIN-04"]),
        ],
    },
    {
        "id": "BND-15", "path": "F and Receptors; G and Receptors", "style": "Green and blue",
        "meaning": "QA/QC verification lane; tasks lane via the Tool Hub",
        "pairs": [["2B.06", "Receptor"], ["2A.07", "Receptor"]],
        "same_as": "LANE-QA and LANE-TASK",
        "operations": [],
    },
]

# Paths in the PRD table that are deliberately outside the baseline and get no contract.
EXCLUDED = [
    {"path": "R11 to R14",
     "reason": "Optional governed receptor-to-receptor support. It needs more than one Receptor, and the "
               "baseline has only Test T0 (LA-IF-08, rule 8). No contract in v1."},
    {"path": "Customers and R11; customer payment to bank",
     "reason": "A Layer B concern. Layer A never sits in the customer payment flow, so there is nothing for it "
               "to implement (LA-IF-06)."},
]

# A contract that is needed but is not a separate path in the figure: the Supply Chain / Integration Gate
# (2A.08) is drawn inside card A, and G cannot satisfy LA-TOOL-03 without asking it. Derived.
INTERNAL = [
    {
        "id": "INT-01", "path": "G and the Supply Chain / Integration Gate (inside card A)",
        "style": "Not drawn separately",
        "meaning": ("Derived. The Gate is drawn as a box inside the Governance Core (PRD section 7.2.1), not as "
                    "its own path. G needs it because nothing is callable until it has passed the Gate "
                    "(LA-TOOL-03)."),
        "pairs": [["2A.07", "2A.08"]],
        "operations": [
            op("SCG-01", "GET", "/v1/admissions/{tool_id}", "2A.07", "2A.08",
               "G checks that a tool, API, plugin or MCP connector has been admitted before it is callable.",
               {"tool_id": "path parameter, `tool_`"},
               {"!tool_id": "string, echoed", "!admitted": "boolean",
                "!risk": "string, `low`, `medium` or `high`",
                "!founder_approval_id": "string, `apr_`, required and present when risk is `high`",
                "!change_record_ref": "string, the auditable change record for this admission",
                "!blocked": "boolean, true when the item is suspect and isolated under AMD-5"},
               "G's own component identity. A read only. Admission itself is the Gate's decision and a high-risk "
               "item needs the Founder's approval (LA-GOV-06, LA-SEC-04).",
               ("G treats an unreachable Gate as not admitted and refuses the tool call with `not_admitted`. "
                "An unknown admission state is never read as admitted."),
               "Always allowed: it is a read and starts no work.",
               ["unauthenticated", "not_found", "rate_limited", "internal", "dependency_down", "timeout"],
               ["LA-TOOL-03", "LA-GOV-06", "LA-SEC-04", "LA-SEC-05"]),
        ],
    },
]


# A component that appears in a contract under an actor's name rather than its own package ID.
PLAYS_ROLE = {
    "2B.07": "Receptor. Test T0 is a Receptor, so it meets Layer A on the five lanes like any other "
             "(open item 4). It has no contract of its own, and it must satisfy every Receptor obligation.",
}


def registry():
    comps = {}
    for pid, card, name, part, port in COMPONENTS:
        comps[pid] = {"card": card, "name": name, "part": part, "stub_port": port}
        if pid in PLAYS_ROLE:
            comps[pid]["plays_role"] = PLAYS_ROLE[pid]
    return {
        "contract_version": VERSION, "date": DATE, "owner_package": "P1.10",
        "built_from": {"plan": "Layer A Execution Plan, Docs rev 62", "prd": "Layer A PRD v1.0, Docs rev 31"},
        "conventions": "contracts/CONVENTIONS.md", "task_states": "contracts/TASK_STATES.md",
        "components": comps, "actors": ACTORS,
        "lanes": LANES, "boundaries": BOUNDARIES, "internal": INTERNAL, "excluded_paths": EXCLUDED,
    }


# ----------------------------------------------------------------------------------------------
# markdown rendering
# ----------------------------------------------------------------------------------------------
def md_fields(fields):
    if not fields:
        return "_None._\n"
    out = ["| Field | Required | Specification |", "| --- | --- | --- |"]
    for f in fields:
        out.append("| `%s` | %s | %s |" % (f["name"], "yes" if f["required"] else "no", f["spec"]))
    return "\n".join(out) + "\n"


def md_op(o):
    out = ["#### %s  `%s %s`" % (o["operation_id"], o["method"], o["path"]), ""]
    out.append("%s" % o["purpose"])
    out.append("")
    out.append("| | |")
    out.append("| --- | --- |")
    out.append("| Caller | %s |" % o["caller"])
    out.append("| Callee | %s |" % o["callee"])
    out.append("| Authorized by | %s |" % o["authorized_by"])
    out.append("| Errors | %s |" % ", ".join("`%s`" % e for e in o["errors"]))
    out.append("| Requirements | %s |" % ", ".join(o["requirements"]))
    out.append("")
    out.append("**Request**")
    out.append("")
    out.append(md_fields(o["request"]))
    out.append("**Response (success)**")
    out.append("")
    out.append(md_fields(o["response"]))
    out.append("**When the callee is down.** %s" % o["when_callee_is_down"])
    out.append("")
    out.append("**When STOP or PAUSE is active.** %s" % o["when_stopped"])
    out.append("")
    return "\n".join(out)


def render(reg):
    out = ["# Contracts (P1.10)", "",
           "Version %s, %s. Owner: Part 1, package P1.10. Built from %s and %s." %
           (reg["contract_version"], reg["date"], reg["built_from"]["plan"], reg["built_from"]["prd"]), "",
           "This file is generated from `registry.json` by `build_registry.py`. Read `CONVENTIONS.md` for the "
           "formats every contract uses and `TASK_STATES.md` for the one task-state set.", "",
           "A contract changes only by a change note that every affected part accepts (rule 6). Review the "
           "contracts that have one of your own components at either end.", "",
           "## Components and their stub ports", "",
           "| Card | Component | Package | Part | Stub port |", "| --- | --- | --- | --- | --- |"]
    for pid, c in reg["components"].items():
        out.append("| %s | %s | %s | %s | %d |" % (c["card"], c["name"], pid, c["part"], c["stub_port"]))
    out += ["", "| Actor | Who it is |", "| --- | --- |"]
    for a, d in reg["actors"].items():
        out.append("| %s | %s |" % (a, d))
    roles = [(pid, c["plays_role"]) for pid, c in reg["components"].items() if c.get("plays_role")]
    if roles:
        out += ["", "| Component | Appears in the contracts as |", "| --- | --- |"]
        for pid, r in roles:
            out.append("| %s | %s |" % (pid, r))

    out += ["", "## 1. The five Layer A to Layer B lanes (PRD section 8)", ""]
    for ln in reg["lanes"]:
        out += ["### %s  %s" % (ln["id"], ln["chip"]), "",
                "| | |", "| --- | --- |",
                "| Style in the diagram | %s |" % ln["style"],
                "| Layer A owner | %s (%s) |" % (ln["layer_a_owner"], ln["owner_package"]),
                "| Direction | %s |" % ln["direction"],
                "| Carries | %s |" % ln["carries"],
                "| Basis | %s |" % ln["basis"], ""]
        for o in ln["operations"]:
            out.append(md_op(o))

    out += ["## 2. Component boundaries (PRD, paths drawn in the figure)", ""]
    for b in reg["boundaries"]:
        out += ["### %s  %s" % (b["id"], b["path"]), "",
                "| | |", "| --- | --- |",
                "| Style in the diagram | %s |" % b["style"],
                "| Meaning | %s |" % b["meaning"],
                "| Sides | %s |" % "; ".join("%s to %s" % (p[0], p[1]) for p in b["pairs"]), ""]
        if b.get("same_as"):
            out += ["This path is the Receptor edge of %s. Its operations are defined there and are not "
                    "repeated here." % b["same_as"], ""]
        for o in b["operations"]:
            out.append(md_op(o))

    out += ["## 3. One contract that is not a drawn path (Derived)", ""]
    for b in reg["internal"]:
        out += ["### %s  %s" % (b["id"], b["path"]), "",
                "| | |", "| --- | --- |",
                "| Style in the diagram | %s |" % b["style"],
                "| Why it exists | %s |" % b["meaning"],
                "| Sides | %s |" % "; ".join("%s to %s" % (p[0], p[1]) for p in b["pairs"]), ""]
        for o in b["operations"]:
            out.append(md_op(o))

    out += ["## 4. Paths with no contract in v1", "",
            "| Path in the figure | Why there is no contract |", "| --- | --- |"]
    for e in reg["excluded_paths"]:
        out.append("| %s | %s |" % (e["path"], e["reason"]))
    out.append("")
    return "\n".join(out)


def main():
    reg = registry()
    with open(os.path.join(HERE, "registry.json"), "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(HERE, "CONTRACTS.md"), "w", encoding="utf-8") as f:
        f.write(render(reg))
    ops = sum(len(x["operations"]) for x in reg["lanes"] + reg["boundaries"] + reg["internal"])
    print("registry.json and CONTRACTS.md written: %d lanes, %d boundaries, %d internal, %d excluded, %d operations"
          % (len(reg["lanes"]), len(reg["boundaries"]), len(reg["internal"]), len(reg["excluded_paths"]), ops))


if __name__ == "__main__":
    main()
