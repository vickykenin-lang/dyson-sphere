"""In-memory state shared by the stubs, plus the deterministic behavior of each operation.

Nothing here reaches the network, a model or real data. The same request in the same order gives the same
answer on every run and on every machine. State is lost on restart, and `POST /v1/_stub/reset` clears it.

The stubs run in one process and share this store. In the real system a component reaches another over HTTP
(for example G reads the stop state from the bus, BND-11 BUS-02). The shared store stands in for that call, so
a contract test asserts what each component's own HTTP surface does, which is true of the stub now and of the
real component at Sync. The calls between real components are wired and shown at S.01 and S.02.
"""
import hashlib
import json

B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32, no I, L, O or U
TASK_STATES = ["accepted", "approval-needed", "running", "held", "stopped", "failed",
               "completed-verified", "closed"]
ACTIVE_STATES = ["accepted", "approval-needed", "running", "held", "failed"]
STOP_REASONS = ["pause", "stop", "breach", "reject"]

# The allowed transitions of contracts/TASK_STATES.md section 4. (from, to) with the row number.
TRANSITIONS = {
    ("accepted", "approval-needed"): 2, ("approval-needed", "running"): 3, ("accepted", "running"): 4,
    ("running", "completed-verified"): 5, ("running", "failed"): 6, ("failed", "running"): 7,
    ("running", "held"): 8, ("failed", "held"): 8, ("stopped", "running"): 10, ("held", "running"): 11,
    ("held", "closed"): 11, ("completed-verified", "closed"): 12, ("failed", "closed"): 12,
    ("stopped", "closed"): 12, ("approval-needed", "stopped"): 13,
}
for _s in ACTIVE_STATES:
    TRANSITIONS[(_s, "stopped")] = 9  # row 9: any active state to stopped


def fid(prefix, tag=""):
    """A deterministic id of the documented shape: prefix + 26 Crockford base32 characters."""
    tag = tag.upper()
    assert all(c in B32 for c in tag), tag
    return "%s_%s" % (prefix, tag.rjust(26, "0"))


# Fixtures, so a test has something to act on without inventing data.
RCP_T0 = fid("rcp", "TST0")          # Test T0, the only Receptor in the baseline
TOOL_OK = fid("tool", "ADMT")        # admitted, low risk
TOOL_HIGH = fid("tool", "HGH")       # admitted, high risk, needs a Founder approval
TOOL_NONE = fid("tool", "NADM")      # not admitted: nothing may call it
APR_OPEN = fid("apr", "APR1")        # an open approval request


def fresh():
    return {
        "counters": {},
        "idem": {},
        "tasks": {},
        "approvals": {APR_OPEN: {"approval_id": APR_OPEN, "decision": None, "task_id": None}},
        "evidence": {},
        "revenue": {},
        "statements": {},
        "escalations": {},
        "verifications": {},
        "tool_calls": {},
        "stop": {"all": None, "receptors": {}},
        "admissions": {
            TOOL_OK: {"admitted": True, "risk": "low", "founder_approval_id": None, "blocked": False},
            TOOL_HIGH: {"admitted": True, "risk": "high", "founder_approval_id": APR_OPEN, "blocked": False},
            TOOL_NONE: {"admitted": False, "risk": "high", "founder_approval_id": None, "blocked": True},
        },
    }


STATE = fresh()
CLOCK = {"ms": 0}


def reset():
    """Clear the store in place, so every module that imported STATE keeps the same object."""
    STATE.clear()
    STATE.update(fresh())
    CLOCK["ms"] = 0


def nxt(kind):
    STATE["counters"][kind] = STATE["counters"].get(kind, 0) + 1
    return STATE["counters"][kind]


def mint(prefix):
    """A deterministic stand-in for a ULID: the same call order gives the same ids on every run."""
    n = nxt(prefix)
    return fid(prefix, B32[n // 32] + B32[n % 32] + "000")


def now():
    """A fixed clock that advances one second per call, so timestamps are ordered and reproducible."""
    CLOCK["ms"] += 1000
    s, ms = divmod(CLOCK["ms"], 1000)
    mi, s = divmod(s, 60)
    h, mi = divmod(mi, 60)
    return "2026-10-11T%02d:%02d:%02d.%03dZ" % (h % 24, mi % 60, s, ms)


def body_digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


class Err(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def stop_state(receptor_id=None):
    """(stopped, scope, reason) as the bus would answer (BND-11 BUS-02)."""
    if STATE["stop"]["all"]:
        return True, "all", STATE["stop"]["all"]
    if receptor_id and STATE["stop"]["receptors"].get(receptor_id):
        return True, "receptor", STATE["stop"]["receptors"][receptor_id]
    return False, "none", None


def set_stop(command, scope, receptor_id, reason, authorization_id, incident_id):
    if command == "resume":
        if not authorization_id:
            raise Err("forbidden", "A resume needs an authenticated Founder authorization; none was given.")
        stopped, _, current = stop_state(receptor_id)
        if current == "breach" and not incident_id:
            raise Err("forbidden",
                      "A resume after a breach needs an authorization naming the incident.")
        if current == "reject":
            raise Err("forbidden", "A rejected task is final and cannot be resumed; raise a new task.")
        if scope == "all":
            STATE["stop"]["all"] = None
        else:
            STATE["stop"]["receptors"].pop(receptor_id, None)
        return
    if scope == "all":
        STATE["stop"]["all"] = reason
    else:
        STATE["stop"]["receptors"][receptor_id] = reason


def require_not_stopped(receptor_id=None):
    stopped, scope, reason = stop_state(receptor_id)
    if stopped:
        raise Err("stopped",
                  "STOP or PAUSE is active; no new work is accepted and the refusal is audited.",
                  {"scope": scope, "stop_reason": reason})


def verified_evidence(evidence_ids):
    """Evidence that proves a real output: a passing record at AMD-3 stage 7 or 8 (LA-ORC-06, LA-IF-04)."""
    out = []
    for e in evidence_ids or []:
        rec = STATE["evidence"].get(e)
        if rec and rec["outcome"] == "pass" and rec["stage"] >= 7:
            out.append(e)
    return out


def move_task(task_id, to, stop_reason=None, evidence_ids=None):
    t = STATE["tasks"].get(task_id)
    if t is None:
        raise Err("not_found", "No task with that id exists for this caller.", {"task_id": task_id})
    frm = t["state"]
    if to not in TASK_STATES:
        raise Err("invalid_request", "That is not one of the eight task states.", {"state": to})
    if frm == to and to == "stopped":
        pass  # a STOP on an already stopped task is accepted and idempotent
    elif (frm, to) not in TRANSITIONS:
        raise Err("invalid_request",
                  "That move is not in the allowed transitions of the task-state contract.",
                  {"from": frm, "to": to})
    if to == "stopped":
        if stop_reason not in STOP_REASONS:
            raise Err("invalid_request", "A stopped task needs a stop_reason.", {"stop_reason": stop_reason})
        t["stop_reason"] = stop_reason
    else:
        t.pop("stop_reason", None)
    if to == "running" and frm == "stopped":
        if t.get("stop_reason_history") and t["stop_reason_history"][-1] == "reject":
            raise Err("forbidden", "A rejected task is final and cannot be resumed.")
    if to == "completed-verified":
        if not verified_evidence(evidence_ids):
            raise Err("not_verified",
                      "A task becomes completed-verified only on evidence that an independent verification "
                      "proved the real output. A report or a 200 OK is not proof.")
    if stop_reason:
        t.setdefault("stop_reason_history", []).append(stop_reason)
    t["state"] = to
    if evidence_ids:
        t["evidence_ids"] = sorted(set(t.get("evidence_ids", [])) | set(evidence_ids))
    t["updated_at"] = now()
    return t
