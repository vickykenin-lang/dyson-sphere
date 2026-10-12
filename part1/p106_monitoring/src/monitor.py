"""Monitoring and Health Controller (E). Package P1.06.

E watches every Receptor on the Monitoring / Health lane, keeps the status, KPIs and failures it is told
about, notices repeated-failure and pause conditions, and escalates them to the Governance Core (2A.05) and
to the Founder Dashboard (P1.07) through read-only views.

What it cannot do is act. There is no method here that pauses, stops, resumes or reassigns anything on a
Receptor, and the four that look like one exist only to refuse (LA-MON-05). The Governance Core decides.

The other half of the job is telling the truth. A Receptor that does not answer is reported as `offline`,
not left showing its last happy status. A view older than its freshness bound is returned with `stale` set.
An escalation the Governance Core did not accept is kept and shown as unescalated rather than dropped
(LA-MON-06).

Standard library only.
"""
import hashlib

# Crockford base32, as in the contracts note. No I, L, O or U.
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# The four statuses a Receptor may report (MON-01, MON-02).
STATUSES = ("healthy", "degraded", "failing", "offline")
# The three conditions E may escalate (ESC-01).
CONDITIONS = ("repeated-failure", "pause-condition", "offline")
# The eight task states, as in the contracts note.
TASK_STATES = ("accepted", "approval-needed", "running", "held", "stopped", "failed",
               "completed-unverified", "completed-verified")
# How many consecutive bad observations make a repeated-failure condition. Three, to match plan rule 7.
REPEATED_FAILURE_AT = 3
# A view older than this is stale. Milliseconds.
FRESHNESS_MS = 60000
# What a dependency may be, including the honest answers.
DEPENDENCY_STATES = ("online", "offline", "unverified")


class NoAuthority(Exception):
    """E was asked to act on a Receptor. It observes and escalates; it never acts (LA-MON-05)."""


class InvalidReport(Exception):
    """The report does not match the contract, so it is refused rather than half-recorded."""


def idempotency_key(*parts):
    """A deterministic `idem_` key. A retry of the same escalation reuses it, which is what ESC-01 wants."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    body = "".join(B32[b % 32] for b in digest[:26])
    return "idem_" + body


def _ms(timestamp):
    """Milliseconds since the epoch from an RFC 3339 UTC timestamp with milliseconds.

    Parsed by hand so this module stays free of anything that guesses at a time zone.
    """
    try:
        date, clock = timestamp.split("T")
        year, month, day = (int(x) for x in date.split("-"))
        clock = clock.rstrip("Z")
        hour, minute, rest = clock.split(":")
        second, _, milli = rest.partition(".")
        days = _days_from_civil(year, month, day)
        return (((days * 24 + int(hour)) * 60 + int(minute)) * 60 + int(second)) * 1000 + int(milli or 0)
    except (ValueError, AttributeError):
        raise InvalidReport("%r is not an RFC 3339 UTC timestamp with milliseconds." % (timestamp,))


def _days_from_civil(year, month, day):
    """Days since 1970-01-01. Howard Hinnant's algorithm, so no calendar library is needed."""
    year -= month <= 2
    era = (year if year >= 0 else year - 399) // 400
    year_of_era = year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468


class Monitor:
    """E's state and the five contract operations it takes part in.

    `escalate_to` is how ESC-01 is sent to the Governance Core: a callable taking the request body and the
    idempotency key, returning the response. Pass `None` to model the Governance Core being unreachable;
    escalations are then queued and shown as unescalated, which is the honest answer.
    """

    def __init__(self, escalate_to=None, freshness_ms=FRESHNESS_MS):
        self.escalate_to = escalate_to
        self.freshness_ms = freshness_ms
        self.receptors = {}
        self.tasks = {}
        self.sent_escalations = []
        self.unescalated = []
        self.dependencies = {}
        self.observations = []
        self._raised = set()

    # ------------------------------------------------------------------ MON-01, the Receptor reports in
    def report_health(self, receptor_id, status, reported_at, kpis=None, failures=None):
        """A Receptor reports its status, KPIs and failures (LA-MON-01, LA-MON-02)."""
        self._require_receptor_id(receptor_id)
        if status not in STATUSES:
            raise InvalidReport("status must be one of %s, not %r." % (", ".join(STATUSES), status))
        at = _ms(reported_at)
        failures = list(failures or [])
        for failure in failures:
            if not isinstance(failure, dict) or "task_id" not in failure or "reason" not in failure:
                raise InvalidReport("every failure needs a task_id and a reason.")

        record = self._receptor(receptor_id)
        record["status"] = status
        record["reported_at"] = reported_at
        record["reported_at_ms"] = at
        record["source"] = "report"
        record["kpis"] = dict(kpis or {})
        record["failures"] = record["failures"] + failures
        self._count(record, status, bool(failures))
        self._observe("health-report", receptor_id, reported_at,
                      {"status": status, "failure_count": len(failures)})

        escalated = False
        if record["consecutive_bad"] >= REPEATED_FAILURE_AT:
            escalated = self._raise(receptor_id, "repeated-failure", reported_at)
        if status == "offline":
            escalated = self._raise(receptor_id, "offline", reported_at) or escalated
        return {"accepted": True, "escalated": escalated}

    # ------------------------------------------------------------------ MON-02, E polls the Receptor
    def poll(self, receptor_id, fetch, observed_at):
        """E polls a Receptor's health endpoint.

        `fetch` is a callable returning the MON-02 response. If it raises, or answers something that does
        not match the contract, the Receptor is recorded and reported as `offline`. It is never left showing
        the status it had before (LA-MON-06).
        """
        self._require_receptor_id(receptor_id)
        at = _ms(observed_at)
        record = self._receptor(receptor_id)
        try:
            answer = fetch()
            status = answer["status"]
            checks = answer["checks"]
            if status not in STATUSES:
                raise ValueError(status)
            reachable = True
            detail = {"status": status, "checks": checks}
        except Exception as problem:               # any failure to answer means offline, not unknown
            status = "offline"
            checks = []
            reachable = False
            detail = {"status": status, "unreachable_because": type(problem).__name__}

        record["status"] = status
        record["reported_at"] = observed_at
        record["reported_at_ms"] = at
        record["source"] = "poll"
        record["checks"] = list(checks)
        record["reachable"] = reachable
        self._count(record, status, any(c.get("ok") is False for c in checks))
        self._observe("poll", receptor_id, observed_at, detail)

        escalated = False
        if status == "offline":
            escalated = self._raise(receptor_id, "offline", observed_at)
        if record["consecutive_bad"] >= REPEATED_FAILURE_AT:
            escalated = self._raise(receptor_id, "repeated-failure", observed_at) or escalated
        return {"receptor_id": receptor_id, "status": status, "checks": list(checks),
                "escalated": escalated}

    # ------------------------------------------------------------------ MON-03, D reports a task's state
    def report_task_status(self, task_id, state, updated_at, stop_reason=None, receptor_id=None):
        """The Orchestrator tells E a task's state, so the views and the dashboard show the truth."""
        if not isinstance(task_id, str) or not task_id.startswith("tsk_"):
            raise InvalidReport("task_id must be a string starting with tsk_, not %r." % (task_id,))
        if state not in TASK_STATES:
            raise InvalidReport("state must be one of the eight task states, not %r." % (state,))
        if state == "stopped" and not stop_reason:
            raise InvalidReport("a stopped task needs a stop_reason.")
        if receptor_id is not None:
            self._require_receptor_id(receptor_id)
        _ms(updated_at)

        self.tasks[task_id] = {"task_id": task_id, "state": state, "stop_reason": stop_reason,
                              "receptor_id": receptor_id, "updated_at": updated_at}
        self._observe("task-status", receptor_id, updated_at, {"task_id": task_id, "state": state,
                                                               "stop_reason": stop_reason})

        # A pause condition, under the Founder's closure decisions: a pause arrives as `stopped` with
        # stop_reason `pause`, and `held` is the QA and QC hold. Either is escalated, neither is acted on.
        paused = state == "held" or (state == "stopped" and stop_reason == "pause")
        if paused and receptor_id:
            self._raise(receptor_id, "pause-condition", updated_at)
        return {"accepted": True}

    # ------------------------------------------------------------------ ESC-02, the dashboard reads a view
    def view(self, name, as_of, receptor_id=None):
        """A read-only view for the Founder Dashboard (LA-MON-04, LA-DASH-02).

        `stale` is true when the newest observation behind the view is older than the freshness bound. The
        dashboard is told that rather than being handed old numbers as if they were current.
        """
        if name not in ("receptor-health", "kpis"):
            raise InvalidReport("view must be receptor-health or kpis, not %r." % (name,))
        now = _ms(as_of)
        chosen = [r for r in self.receptors.values()
                  if receptor_id is None or r["receptor_id"] == receptor_id]
        chosen.sort(key=lambda r: r["receptor_id"])

        if name == "receptor-health":
            rows = [{"receptor_id": r["receptor_id"],
                     "status": r["status"],
                     "reported_at": r["reported_at"],
                     "consecutive_bad": r["consecutive_bad"],
                     "open_conditions": sorted(c for (rid, c) in self._raised
                                               if rid == r["receptor_id"]),
                     "unescalated": sum(1 for e in self.unescalated
                                        if e["body"]["receptor_id"] == r["receptor_id"])}
                    for r in chosen]
        else:
            rows = [{"receptor_id": r["receptor_id"], "kpis": dict(r["kpis"]),
                     "reported_at": r["reported_at"]} for r in chosen]

        newest = max((r["reported_at_ms"] for r in chosen), default=None)
        stale = True if newest is None else (now - newest) > self.freshness_ms
        return {"rows": rows, "as_of": as_of, "stale": stale,
                "dependencies": {n: d["state"] for n, d in sorted(self.dependencies.items())},
                "authority": "read-only"}

    # ------------------------------------------------------------------ truthful reporting of dependencies
    def set_dependency(self, name, state, observed_at):
        """Record a model, tool, Receptor or the Core itself as online, offline or unverified (LA-MON-06)."""
        if state not in DEPENDENCY_STATES:
            raise InvalidReport("a dependency is %s, not %r." % (", ".join(DEPENDENCY_STATES), state))
        _ms(observed_at)
        self.dependencies[name] = {"state": state, "observed_at": observed_at}
        self._observe("dependency", None, observed_at, {"name": name, "state": state})
        return dict(self.dependencies[name])

    def retry_escalations(self):
        """Try the queue again. Same bodies, same idempotency keys, so a duplicate is safe."""
        queued, self.unescalated = self.unescalated, []
        sent = 0
        for item in queued:
            if self._send(item["body"], item["idempotency_key"]):
                sent += 1
            else:
                self.unescalated.append(item)
        return {"sent": sent, "still_unescalated": len(self.unescalated)}

    # ------------------------------------------------------------------ what E is not allowed to do
    def pause_receptor(self, *_a, **_k):
        raise NoAuthority(
            "E cannot pause a Receptor. It records the condition and escalates it to the Governance Core "
            "(2A.05), which decides (LA-MON-05).")

    def stop_receptor(self, *_a, **_k):
        raise NoAuthority(
            "E cannot stop a Receptor. Emergency STOP is the Founder's red path through the Control Bus, "
            "not a monitoring action (LA-MON-05, LA-SAF-02).")

    def resume_receptor(self, *_a, **_k):
        raise NoAuthority(
            "E cannot resume a Receptor. A resume after a stop needs the Founder's authorization "
            "(LA-MON-05, N14).")

    def reassign_task(self, *_a, **_k):
        raise NoAuthority(
            "E cannot move a task. It observes task state; the Orchestrator (2A.09) owns it (LA-MON-05).")

    # ------------------------------------------------------------------ internals
    def _require_receptor_id(self, receptor_id):
        if not isinstance(receptor_id, str) or not receptor_id.startswith("rcp_"):
            raise InvalidReport("receptor_id must be a string starting with rcp_, not %r." % (receptor_id,))

    def _receptor(self, receptor_id):
        return self.receptors.setdefault(receptor_id, {
            "receptor_id": receptor_id, "status": "offline", "reported_at": None,
            "reported_at_ms": None, "source": None, "kpis": {}, "failures": [],
            "checks": [], "reachable": None, "consecutive_bad": 0})

    def _count(self, record, status, had_failures):
        """Only a healthy observation with nothing failing clears the count."""
        if status == "healthy" and not had_failures:
            record["consecutive_bad"] = 0
            self._raised = {(rid, c) for (rid, c) in self._raised if rid != record["receptor_id"]}
        elif status in ("failing", "offline") or had_failures:
            record["consecutive_bad"] += 1

    def _observe(self, kind, receptor_id, at, detail):
        self.observations.append({"kind": kind, "receptor_id": receptor_id, "at": at, "detail": detail})

    def _raise(self, receptor_id, condition, observed_at):
        """Escalate a condition once, until the Receptor reports healthy again."""
        if condition not in CONDITIONS:
            raise InvalidReport("condition must be one of %s." % ", ".join(CONDITIONS))
        if (receptor_id, condition) in self._raised:
            return False
        self._raised.add((receptor_id, condition))
        body = {"receptor_id": receptor_id, "condition": condition,
                "evidence_ref": "monitor://receptors/%s/observations" % receptor_id,
                "observed_at": observed_at}
        key = idempotency_key(receptor_id, condition, observed_at)
        if not self._send(body, key):
            self.unescalated.append({"body": body, "idempotency_key": key})
        return True

    def _send(self, body, key):
        """Try ESC-01. A failure is kept, not swallowed, so the condition stays visible (LA-MON-06)."""
        if self.escalate_to is None:
            return False
        try:
            answer = self.escalate_to(body, key)
        except Exception:
            return False
        if not isinstance(answer, dict) or not answer.get("escalation_id"):
            return False
        self.sent_escalations.append({"body": body, "idempotency_key": key,
                                      "escalation_id": answer["escalation_id"],
                                      "decision_owner": answer.get("decision_owner"),
                                      "action_taken": answer.get("action_taken")})
        return True
