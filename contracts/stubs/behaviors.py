"""What each stubbed operation does. One function per operation id of registry.json.

Every function is deterministic and returns (http_status, body). It raises state.Err to produce one of the
documented errors. No function reaches the network, a model or real data.
"""
from state import (STATE, Err, RCP_T0, TOOL_HIGH, TOOL_NONE, TOOL_OK, APR_OPEN, mint, move_task, now,
                   require_not_stopped, set_stop, stop_state)

OPS = {}


def handles(op_id):
    def deco(fn):
        OPS[op_id] = fn
        return fn
    return deco


def need(body, *names):
    for n in names:
        if body.get(n) in (None, ""):
            raise Err("invalid_request", "The field %s is required." % n, {"field": n})
    return [body.get(n) for n in names]


def one_of(value, allowed, field):
    if value not in allowed:
        raise Err("invalid_request", "%s must be one of: %s." % (field, ", ".join(allowed)), {"field": field})
    return value


# ---------------------------------------------------------------------------------- BND-01 app to gateway
@handles("GW-01")
def gw_01(c):
    assertion = c["body"].get("authenticator_assertion")
    if not isinstance(assertion, dict) or not assertion.get("verified"):
        raise Err("unauthenticated", "The Founder was not authenticated for this session.")
    tok = mint("ses")
    STATE.setdefault("sessions", {})[tok] = {"subject": "founder", "created_at": now()}
    return 200, {"session_token": tok, "expires_at": now(), "subject": "founder"}


@handles("GW-02")
def gw_02(c):
    locale, content = need(c["body"], "locale", "content")
    one_of(locale, ["hi", "en", "hi-Latn"], "locale")
    if not isinstance(content, dict) or not (content.get("text") or content.get("audio_ref")):
        raise Err("invalid_request", "content needs either text or audio_ref.", {"field": "content"})
    require_not_stopped()
    thread = STATE.setdefault("threads", {}).setdefault("thread-1", {"turns": []})
    thread["turns"].append({"locale": locale, "at": now()})
    task_id = mint("tsk")
    STATE["tasks"][task_id] = {
        "task_id": task_id, "state": "accepted", "idempotency_key": c["idem"], "created_at": now(),
        "updated_at": now(), "qa_failure_count": 0, "approval_id": None, "evidence_ids": [],
        "display_label": "Pending",
    }
    # An acknowledgment, never a completion (LA-APP-04).
    return 200, {"acknowledgment": "accepted", "task_id": task_id, "thread_id": "thread-1"}


# ---------------------------------------------------------------------------------- BND-02 gateway to B
@handles("CONV-01")
def conv_01(c):
    thread_id, locale, content = need(c["body"], "thread_id", "locale", "content")
    one_of(locale, ["hi", "en", "hi-Latn"], "locale")
    require_not_stopped()
    text = (content or {}).get("text", "")
    if c["body"].get("transcription_uncertain") or "?" in str(text):
        return 200, {"reply": "I am not certain I heard that correctly. Please say it again.",
                     "intent": "clarify", "completion_claimed": False}
    return 200, {"reply": "Understood. I will check whether this is permitted before anything runs.",
                 "intent": "proposed_action",
                 "proposed_action": {"summary": str(text)[:80], "tools": [TOOL_OK]},
                 "completion_claimed": False}


# ---------------------------------------------------------------------------------- BND-03 controls to A
@handles("DFC-01")
def dfc_01(c):
    approval_id, decision, digest, assertion = need(
        c["body"], "approval_id", "decision", "bound_action_digest", "authenticator_assertion")
    one_of(decision, ["approve", "reject"], "decision")
    if not isinstance(assertion, dict) or not assertion.get("step_up_verified"):
        raise Err("unauthenticated", "A consequential approval needs an independently authenticated Founder.")
    apr = STATE["approvals"].get(approval_id)
    if apr is None:
        raise Err("not_found", "No approval request with that id exists.", {"approval_id": approval_id})
    if apr.get("bound_action_digest") and apr["bound_action_digest"] != digest:
        raise Err("invalid_request",
                  "The digest does not match the action shown to the Founder; the approval is not reusable.",
                  {"approval_id": approval_id})
    apr["decision"] = decision
    apr["decided_at"] = now()
    task_state = None
    if apr.get("task_id"):
        if decision == "approve":
            task_state = move_task(apr["task_id"], "running")["state"]
        else:  # the Founder's decision on open item 3: stopped with reason reject, then closed
            task_state = move_task(apr["task_id"], "stopped", stop_reason="reject")["state"]
    return 200, {"approval_id": approval_id, "recorded_at": now(),
                 "task_state": task_state or ("running" if decision == "approve" else "stopped"),
                 "approver": "founder"}


@handles("DFC-02")
def dfc_02(c):
    command, scope, assertion = need(c["body"], "command", "scope", "authenticator_assertion")
    one_of(command, ["stop", "pause", "resume"], "command")
    one_of(scope, ["all", "receptor"], "scope")
    if not isinstance(assertion, dict) or not assertion.get("step_up_verified"):
        raise Err("unauthenticated", "An emergency control needs an independently authenticated Founder.")
    receptor_id = c["body"].get("receptor_id")
    if scope == "receptor" and not receptor_id:
        raise Err("invalid_request", "receptor_id is required when scope is receptor.", {"field": "receptor_id"})
    incident_id = c["body"].get("incident_id") or mint("inc")
    reason = "pause" if command == "pause" else "stop"
    set_stop(command, scope, receptor_id, reason, c["body"].get("authorization_id") or "founder-step-up",
             c["body"].get("incident_id"))
    reached = ["2A.06", "2A.07", "2B.05", RCP_T0]
    return 200, {"incident_id": incident_id, "applied_at": now(), "reached": reached, "not_reached": []}


# ---------------------------------------------------------------------------------- BND-04 B to A
@handles("POL-01")
def pol_01(c):
    action, thread_id = need(c["body"], "proposed_action", "thread_id")
    require_not_stopped()
    spend = c["body"].get("estimated_spend_minor") or 0
    tools = (action or {}).get("tools") or []
    if spend > 0 or TOOL_HIGH in tools:
        apr = mint("apr")
        # The approval binds here, to the exact action shown to the Founder (LA-DFC-05).
        STATE["approvals"][apr] = {"approval_id": apr, "decision": None, "task_id": None,
                                   "bound_action_digest": c["digest"]}
        return 200, {"verdict": "approval-needed", "policy_version": "register-1.0", "approval_id": apr,
                     "bound_action_digest": c["digest"],
                     "reasons": ["Every money-out action stays blocked until a Founder approval exists."]}
    if TOOL_NONE in tools:
        return 200, {"verdict": "deny", "policy_version": "register-1.0",
                     "reasons": ["The tool has not passed the Supply Chain Gate."]}
    return 200, {"verdict": "allow", "policy_version": "register-1.0",
                 "reasons": ["No rule requires an approval for this action."]}


# ---------------------------------------------------------------------------------- BND-05 neighbors
def _model(c, caller):
    purpose, data = need(c["body"], "purpose", "input")
    require_not_stopped()
    cap = c["body"].get("max_cost_minor")
    cost = 12
    if cap is not None and cost > cap:
        raise Err("spend_limit", "The call would cost more than the ceiling the caller set.",
                  {"cost_minor": cost, "max_cost_minor": cap})
    redacted = bool((data or {}).get("contains_personal_data"))
    fallback = bool((data or {}).get("force_primary_failure"))
    return 200, {"model_id": "stub-model-b" if fallback else "stub-model-a",
                 "output": {"text": "A deterministic stub answer for: %s" % purpose},
                 "cost_minor": cost, "redaction_applied": redacted, "fallback_used": fallback}


@handles("RTR-01")
def rtr_01(c):
    return _model(c, "2B.04")


@handles("HER-01")
def her_01(c):
    return _model(c, "2B.05")


@handles("ORC-01")
def orc_01(c):
    instruction, thread_id = need(c["body"], "instruction", "thread_id")
    require_not_stopped()
    task_id = mint("tsk")
    approval_id = c["body"].get("approval_id")
    state = "accepted"
    if approval_id:
        apr = STATE["approvals"].get(approval_id)
        if apr is None:
            raise Err("not_found", "No approval request with that id exists.", {"approval_id": approval_id})
        apr["task_id"] = task_id
        state = "approval-needed" if apr.get("decision") is None else "accepted"
    STATE["tasks"][task_id] = {
        "task_id": task_id, "state": state, "idempotency_key": c["idem"], "created_at": now(),
        "updated_at": now(), "qa_failure_count": 0, "approval_id": approval_id, "evidence_ids": [],
        "receptor_id": c["body"].get("receptor_id"),
        "display_label": "Approval Needed" if state == "approval-needed" else "Pending",
    }
    return 200, {"task_id": task_id, "state": state, "created_at": now()}


@handles("MON-03")
def mon_03(c):
    task_id, state, updated_at = need(c["body"], "task_id", "state", "updated_at")
    STATE.setdefault("status_feed", []).append({"task_id": task_id, "state": state, "at": updated_at})
    return 200, {"accepted": True}


# ---------------------------------------------------------------------------------- BND-07 tool hub
@handles("TOOL-01")
def tool_01(c):
    tool_id, args, task_id = need(c["body"], "tool_id", "arguments", "task_id")
    receptor_id = c["body"].get("receptor_id")
    checks = {}
    # 1. identity
    checks["identity"] = "pass"
    # 2. Receptor scope
    if receptor_id and receptor_id != RCP_T0:
        checks["scope"] = "fail"
        raise Err("forbidden", "That Receptor is outside the caller's approved scope.", {"checks": checks})
    checks["scope"] = "pass"
    # 3. admission, which G reads from the Supply Chain Gate (INT-01)
    adm = STATE["admissions"].get(tool_id)
    if adm is None or not adm["admitted"] or adm["blocked"]:
        checks["admission"] = "fail"
        raise Err("not_admitted", "The tool has not passed the Supply Chain Gate, so it is not callable.",
                  {"tool_id": tool_id, "checks": checks})
    checks["admission"] = "pass"
    # 4. risk, spend and approval
    spend = c["body"].get("estimated_spend_minor") or 0
    if adm["risk"] == "high" or spend > 0:
        apr_id = adm.get("founder_approval_id")
        apr = STATE["approvals"].get(apr_id) if apr_id else None
        if not apr or apr.get("decision") != "approve":
            checks["approval"] = "fail"
            raise Err("approval_needed", "The call needs a Founder approval that does not exist yet.",
                      {"tool_id": tool_id, "checks": checks})
    checks["approval"] = "pass"
    checks["spend"] = "pass"
    # 5. STOP state, read on every single call (LA-SAF-02)
    stopped, scope, reason = stop_state(receptor_id)
    if stopped:
        checks["stop_state"] = "fail"
        raise Err("stopped", "STOP or PAUSE is active; the refusal is audited.",
                  {"scope": scope, "stop_reason": reason, "checks": checks})
    checks["stop_state"] = "pass"
    call_id = mint("tlc")
    STATE["tool_calls"][call_id] = {"tool_id": tool_id, "task_id": task_id, "at": now()}
    return 200, {"tool_call_id": call_id, "result": {"ok": True, "echo": args}, "checks": checks,
                 "audited": True}


# ---------------------------------------------------------------------------------- INT-01 supply chain
@handles("SCG-01")
def scg_01(c):
    tool_id = c["path_params"].get("tool_id")
    adm = STATE["admissions"].get(tool_id)
    if adm is None:
        raise Err("not_found", "No admission record exists for that tool.", {"tool_id": tool_id})
    return 200, {"tool_id": tool_id, "admitted": adm["admitted"], "risk": adm["risk"],
                 "founder_approval_id": adm["founder_approval_id"],
                 "change_record_ref": "scg/changes/%s" % tool_id, "blocked": adm["blocked"]}


# ---------------------------------------------------------------------------------- BND-08 F, G, H, I
@handles("EVD-01")
def evd_01(c):
    cap, provider, stage, env, observed, outcome, detail = need(
        c["body"], "capability", "provider", "stage", "environment", "observed_at", "outcome", "detail")
    if not isinstance(stage, int) or not 1 <= stage <= 8:
        raise Err("invalid_request", "stage is an integer from 1 to 8, the AMD-3 stages.", {"field": "stage"})
    one_of(outcome, ["pass", "fail"], "outcome")
    eid = mint("evd")
    STATE["evidence"][eid] = {"evidence_id": eid, "capability": cap, "provider": provider, "stage": stage,
                              "environment": env, "observed_at": observed, "outcome": outcome,
                              "task_id": c["body"].get("task_id"), "detail": detail, "written_at": now()}
    return 200, {"evidence_id": eid, "stage": stage, "immutable": True}


@handles("FIN-02")
def fin_02(c):
    rcp, amount, currency, kind, occurred = need(
        c["body"], "receptor_id", "amount_minor", "currency", "kind", "occurred_at")
    one_of(kind, ["revenue-reported", "revenue-verified", "payment-record"], "kind")
    if not isinstance(amount, int):
        raise Err("invalid_request", "amount_minor is an integer in the currency's minor unit.",
                  {"field": "amount_minor"})
    if kind == "revenue-verified" and not c["body"].get("statement_id"):
        raise Err("invalid_request", "revenue-verified needs the statement_id that matched it.",
                  {"field": "statement_id"})
    eid = mint("led")
    STATE.setdefault("ledger", {})[eid] = {"entry_id": eid, "receptor_id": rcp, "kind": kind,
                                           "amount_minor": amount, "currency": currency}
    return 200, {"entry_id": eid, "final": kind == "revenue-verified"}


# ---------------------------------------------------------------------------------- BND-09 dashboard reads
@handles("DASH-01")
def dash_01(c):
    view = c["path_params"].get("view")
    one_of(view, ["revenue", "payments", "profitability", "receptor-performance", "reconciliation-status"],
           "view")
    rows, excluded = [], 0
    for e in STATE.get("ledger", {}).values():
        if e["kind"] == "revenue-verified":
            rows.append({"receptor_id": e["receptor_id"], "amount_minor": e["amount_minor"],
                         "currency": e["currency"]})
        else:
            excluded += 1
    return 200, {"rows": rows, "verified_only": True, "as_of": now(), "unverified_excluded": excluded}


# ---------------------------------------------------------------------------------- BND-10 D and I
@handles("STATE-01")
def state_01(c):
    task_id, state, evidence_ids, updated_at = need(
        c["body"], "task_id", "state", "evidence_ids", "updated_at")
    if task_id not in STATE["tasks"]:
        raise Err("not_found", "No task with that id exists for this caller.", {"task_id": task_id})
    t = move_task(task_id, state, stop_reason=c["body"].get("stop_reason"), evidence_ids=evidence_ids)
    return 200, {"recorded_at": now(), "state": t["state"]}


@handles("STATE-02")
def state_02(c):
    task_id = c["path_params"].get("task_id")
    t = STATE["tasks"].get(task_id)
    if t is None:
        raise Err("not_found", "No task with that id exists for this caller.", {"task_id": task_id})
    ev = [{"evidence_id": e, "stage": STATE["evidence"][e]["stage"],
           "outcome": STATE["evidence"][e]["outcome"],
           "observed_at": STATE["evidence"][e]["observed_at"]}
          for e in t.get("evidence_ids", []) if e in STATE["evidence"]]
    verified = "2B.06" if any(x["outcome"] == "pass" and x["stage"] >= 7 for x in ev) else None
    return 200, {"evidence": ev, "verified_by": verified}


# ---------------------------------------------------------------------------------- BND-11 the STOP bus
@handles("BUS-01")
def bus_01(c):
    command, scope, issued = need(c["body"], "command", "scope", "issued_at")
    one_of(command, ["stop", "pause", "resume"], "command")
    one_of(scope, ["all", "receptor"], "scope")
    receptor_id = c["body"].get("receptor_id")
    if scope == "receptor" and not receptor_id:
        raise Err("invalid_request", "receptor_id is required when scope is receptor.", {"field": "receptor_id"})
    reason = c["body"].get("stop_reason") or ("pause" if command == "pause" else "stop")
    if c["body"].get("incident_id") and command != "resume":
        reason = "breach"
    set_stop(command, scope, receptor_id, reason, c["body"].get("authorization_id"),
             c["body"].get("incident_id"))
    in_flight = [t for t, v in STATE["tasks"].items() if v["state"] == "running"]
    return 200, {"applied_at": now(), "in_flight": in_flight, "self_resume_possible": False}


@handles("BUS-02")
def bus_02(c):
    stopped, scope, reason = stop_state(c["query"].get("receptor_id"))
    out = {"stopped": stopped, "scope": scope, "as_of": now()}
    if stopped:
        out["stop_reason"] = reason
    return 200, out


@handles("STOP-01")
def stop_01(c):
    command, receptor_id, issued = need(c["body"], "command", "receptor_id", "issued_at")
    one_of(command, ["stop", "pause", "resume"], "command")
    if command == "resume" and not c["body"].get("authorization_id"):
        raise Err("forbidden", "A resume needs an authorization; it is never automatic.")
    scope = "all" if receptor_id == "all" else "receptor"
    reason = "breach" if c["body"].get("incident_id") else ("pause" if command == "pause" else "stop")
    set_stop(command, scope, None if scope == "all" else receptor_id, reason,
             c["body"].get("authorization_id"), c["body"].get("incident_id"))
    in_flight = [t for t, v in STATE["tasks"].items() if v["state"] == "running"]
    return 200, {"command": command, "applied": True, "applied_at": now(), "in_flight": in_flight}


# ---------------------------------------------------------------------------------- BND-12 escalation
@handles("ESC-01")
def esc_01(c):
    rcp, condition, ref, observed = need(c["body"], "receptor_id", "condition", "evidence_ref", "observed_at")
    one_of(condition, ["repeated-failure", "pause-condition", "offline"], "condition")
    eid = mint("esc")
    STATE["escalations"][eid] = {"escalation_id": eid, "receptor_id": rcp, "condition": condition}
    return 200, {"escalation_id": eid, "decision_owner": "2A.05", "action_taken": "none"}


@handles("ESC-02")
def esc_02(c):
    view = c["path_params"].get("view")
    one_of(view, ["receptor-health", "kpis"], "view")
    rows = [{"receptor_id": r, "status": v["status"]} for r, v in STATE.get("health", {}).items()]
    return 200, {"rows": rows, "as_of": now(), "stale": not rows}


# ---------------------------------------------------------------------------------- BND-14 bank statements
@handles("VLT-01")
def vlt_01(c):
    ref, period, by, at = need(c["body"], "statement_ref", "period", "uploaded_by", "uploaded_at")
    if by != "founder":
        raise Err("forbidden",
                  "Only a Founder-initiated upload is accepted; Dyson holds no bank credential.",
                  {"field": "uploaded_by"})
    sid = mint("stm")
    matched = []
    for rid, rep in STATE["revenue"].items():
        if rep["status"] == "reported-not-final":
            rep["status"] = "reconciled"
            rep["statement_id"] = sid
            matched.append(rid)
    STATE["statements"][sid] = {"statement_id": sid, "period": period, "lines": len(matched) or 1}
    return 200, {"statement_id": sid, "lines_parsed": len(matched) or 1, "matched_reports": matched,
                 "classified_as": "personal-financial-data"}


# ---------------------------------------------------------------------------------- lanes: QA/QC
@handles("QA-01")
def qa_01(c):
    vid, task_id, std, requested = need(
        c["body"], "verification_id", "task_id", "quality_standard", "requested_evidence")
    require_not_stopped(c["body"].get("receptor_id"))
    STATE["verifications"][vid] = {"verification_id": vid, "task_id": task_id, "standard": std}
    return 200, {"verification_id": vid, "status": "accepted", "accepted_at": now()}


@handles("QA-02")
def qa_02(c):
    vid, task_id, evidence = need(c["body"], "verification_id", "task_id", "evidence")
    if not isinstance(evidence, list) or not evidence:
        raise Err("invalid_request", "evidence is a non-empty array.", {"field": "evidence"})
    ids = []
    for item in evidence:
        eid = mint("evd")
        STATE["evidence"][eid] = {"evidence_id": eid, "capability": "receptor-output",
                                  "provider": "receptor", "stage": 7, "environment": "stub",
                                  "observed_at": now(), "outcome": "pass", "task_id": task_id,
                                  "detail": item, "written_at": now()}
        ids.append(eid)
    # The Receptor's claim is recorded and never concluded from (LA-IF-04, LA-QA-05).
    return 200, {"evidence_ids": ids, "verdict": "pending", "self_certification_accepted": False}


@handles("QA-03")
def qa_03(c):
    rcp, severity, summary = need(c["body"], "receptor_id", "severity", "summary")
    one_of(severity, ["low", "medium", "high"], "severity")
    eid = mint("esc")
    STATE["escalations"][eid] = {"escalation_id": eid, "receptor_id": rcp, "severity": severity}
    return 200, {"escalation_id": eid, "routed_to": "2B.06, 2A.05" if severity == "high" else "2B.06"}


# ---------------------------------------------------------------------------------- lanes: tasks
@handles("TASK-01")
def task_01(c):
    task_id, rcp, instruction, scope = need(
        c["body"], "task_id", "receptor_id", "instruction", "scope")
    require_not_stopped(rcp)
    if not task_id.startswith("tsk_"):
        raise Err("invalid_request", "task_id must be a tsk_ id minted by the task engine.",
                  {"field": "task_id"})
    STATE.setdefault("receptor_tasks", {})[task_id] = {"receptor_id": rcp, "at": now()}
    return 200, {"task_id": task_id, "state": "accepted", "accepted_at": now()}


@handles("TASK-02")
def task_02(c):
    task_id, output_ref, claimed = need(c["body"], "task_id", "output_ref", "claimed_outcome")
    if task_id not in STATE.get("receptor_tasks", {}):
        raise Err("not_found", "That task was never handed to this Receptor.", {"task_id": task_id})
    # A result is not a completion: the state stays running until F verifies (LA-IF-04).
    return 200, {"task_id": task_id, "state": "running", "verification_required": True}


# ---------------------------------------------------------------------------------- lanes: financial
@handles("FIN-01")
def fin_01(c):
    rcp, period, amount, currency = need(
        c["body"], "receptor_id", "period", "amount_minor", "currency")
    if not isinstance(amount, int):
        raise Err("invalid_request", "amount_minor is an integer in the currency's minor unit.",
                  {"field": "amount_minor"})
    rid = mint("rev")
    STATE["revenue"][rid] = {"report_id": rid, "receptor_id": rcp, "amount_minor": amount,
                             "currency": currency, "status": "reported-not-final"}
    return 200, {"report_id": rid, "status": "reported-not-final", "reconciled": False,
                 "bank_statement_required": True}


# ---------------------------------------------------------------------------------- lanes: monitoring
@handles("MON-01")
def mon_01(c):
    rcp, status, reported = need(c["body"], "receptor_id", "status", "reported_at")
    one_of(status, ["healthy", "degraded", "failing", "offline"], "status")
    h = STATE.setdefault("health", {}).setdefault(rcp, {"status": status, "fails": 0})
    h["status"] = status
    failures = c["body"].get("failures") or []
    h["fails"] = h["fails"] + len(failures) if failures else 0
    return 200, {"accepted": True, "escalated": h["fails"] >= 3 or status == "offline"}


@handles("MON-02")
def mon_02(c):
    return 200, {"receptor_id": RCP_T0, "status": "healthy",
                 "checks": [{"name": "task-interface", "ok": True}, {"name": "evidence", "ok": True}]}
