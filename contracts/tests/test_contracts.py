"""Contract tests for P1.10.

Each test asserts a rule the PRD states, against a component's HTTP surface. The same tests run against the
stubs now and against the real components at Sync (S.01), by pointing DYSON_BASE_<component> at the real one.
The requirement each test proves is named in its docstring.

Run:  python3 -m unittest discover -s contracts/tests -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import ContractTest  # noqa: E402


class Conventions(ContractTest):
    """The formats of contracts/CONVENTIONS.md, which every operation shares."""

    def test_state_changing_call_needs_an_idempotency_key(self):
        """Conventions section 7. Without a key a retry could duplicate the action."""
        r = self.api.post("2A.09", "/v1/tasks", {"instruction": {"do": "x"}, "thread_id": "t1"}, idem=None)
        self.failed(r, "invalid_request")

    def test_the_same_key_and_body_does_the_work_once(self):
        """LA-ORC-03, LA-REL-02. A retry after a network failure must not duplicate the task."""
        key = self.api.idem()
        body = {"instruction": {"do": "x"}, "thread_id": "t1"}
        first = self.ok(self.api.post("2A.09", "/v1/tasks", body, idem=key))
        again = self.ok(self.api.post("2A.09", "/v1/tasks", body, idem=key))
        self.assertEqual(first["task_id"], again["task_id"], "a replay created a second task")

    def test_the_same_key_with_a_different_body_is_refused(self):
        """Conventions section 7. A reused key with new content is a caller bug, never silent work."""
        key = self.api.idem()
        self.ok(self.api.post("2A.09", "/v1/tasks", {"instruction": {"do": "x"}, "thread_id": "t1"}, idem=key))
        r = self.api.post("2A.09", "/v1/tasks", {"instruction": {"do": "DIFFERENT"}, "thread_id": "t1"}, idem=key)
        self.failed(r, "idempotency_conflict")

    def test_an_unknown_field_is_refused(self):
        """Conventions section 8. A typo must never pass silently."""
        r = self.api.post("2A.09", "/v1/tasks",
                          {"instruction": {"do": "x"}, "thread_id": "t1", "instrucion": "typo"})
        self.failed(r, "invalid_request")

    def test_a_missing_required_field_is_refused(self):
        r = self.api.post("2A.09", "/v1/tasks", {"thread_id": "t1"})
        self.failed(r, "invalid_request")

    def test_an_unserved_contract_version_is_refused(self):
        """Conventions section 8. A major-version mismatch is caught on the first call."""
        r = self.api.post("2A.09", "/v1/tasks", {"instruction": {"do": "x"}, "thread_id": "t1"},
                          headers={"X-Dyson-Contract": "v9.0"})
        self.failed(r, "invalid_request")

    def test_every_error_carries_the_documented_shape(self):
        """Conventions section 6. A caller can always read code, message, retriable and request_id."""
        err = self.failed(self.api.post("2A.09", "/v1/tasks", {"thread_id": "t1"}), "invalid_request")
        self.assertTrue(err["message"].endswith("."), "the message is one sentence for a person")
        self.assertFalse(err["retriable"], "a malformed request is not retriable")


class TaskStates(ContractTest):
    """contracts/TASK_STATES.md, which carries the Founder's decisions on open items 1, 2 and 3."""

    def test_a_new_task_uses_the_closure_state_names(self):
        """Open item 1. The wire value is the closure name, never the card D label."""
        t = self.a_task()
        self.assertEqual(t["state"], "accepted", "card D says Pending; the wire says accepted")

    def test_a_move_outside_the_table_is_refused(self):
        """TASK_STATES.md section 4. Only the listed transitions exist."""
        t = self.a_task()
        r = self.api.put("2B.02", "/v1/task-state",
                         {"task_id": t["task_id"], "state": "completed-verified", "evidence_ids": [],
                          "updated_at": "2026-10-12T10:00:00.000Z"})
        self.assertGreaterEqual(r.status, 400, "accepted must not jump straight to completed-verified")

    def test_pause_puts_a_task_in_stopped_and_never_in_held(self):
        """Open item 2. PAUSE maps to stopped; held stays for QA/QC holds only."""
        t = self.a_task()
        self.ok(self.api.put("2B.02", "/v1/task-state",
                             {"task_id": t["task_id"], "state": "running", "evidence_ids": [],
                              "updated_at": "2026-10-12T10:00:00.000Z"}))
        self.ok(self.api.put("2B.02", "/v1/task-state",
                             {"task_id": t["task_id"], "state": "stopped", "stop_reason": "pause",
                              "evidence_ids": [], "updated_at": "2026-10-12T10:01:00.000Z"}))
        after = self.ok(self.api.put("2B.02", "/v1/task-state",
                                     {"task_id": t["task_id"], "state": "stopped", "stop_reason": "pause",
                                      "evidence_ids": [], "updated_at": "2026-10-12T10:02:00.000Z"}))
        self.assertEqual(after["state"], "stopped", "a PAUSE never produces held")

    def test_a_stopped_task_needs_a_reason(self):
        """TASK_STATES.md section 3. Without a reason nothing can decide whether a resume is allowed."""
        t = self.a_task()
        self.ok(self.api.put("2B.02", "/v1/task-state",
                             {"task_id": t["task_id"], "state": "running", "evidence_ids": [],
                              "updated_at": "2026-10-12T10:00:00.000Z"}))
        r = self.api.put("2B.02", "/v1/task-state",
                         {"task_id": t["task_id"], "state": "stopped", "evidence_ids": [],
                          "updated_at": "2026-10-12T10:01:00.000Z"})
        self.failed(r, "invalid_request")

    def test_a_founder_reject_ends_the_task_as_stopped_then_closed(self):
        """Open item 3. A Reject is not a failure: nothing failed, the Founder declined."""
        check = self.ok(self.api.post("2A.05", "/v1/policy/checks",
                                      {"proposed_action": {"tools": [self.tool_ok]}, "thread_id": "t1",
                                       "estimated_spend_minor": 500}))
        self.assertEqual(check["verdict"], "approval-needed")
        task = self.ok(self.api.post("2A.09", "/v1/tasks",
                                     {"instruction": {"do": "spend"}, "thread_id": "t1",
                                      "approval_id": check["approval_id"]}))
        self.assertEqual(task["state"], "approval-needed")
        decided = self.ok(self.api.post("2A.05", "/v1/controls/decision",
                                        {"approval_id": check["approval_id"], "decision": "reject",
                                         "bound_action_digest": check["bound_action_digest"],
                                         "authenticator_assertion": self.step_up()}))
        self.assertEqual(decided["task_state"], "stopped")
        closed = self.ok(self.api.put("2B.02", "/v1/task-state",
                                      {"task_id": task["task_id"], "state": "closed", "evidence_ids": [],
                                       "updated_at": "2026-10-12T10:05:00.000Z"}))
        self.assertEqual(closed["state"], "closed")

    def test_a_task_is_not_completed_verified_without_evidence_of_a_real_output(self):
        """LA-IF-04, LA-ORC-06, LA-EVD-01. A report, or a 200 OK, is not proof."""
        t = self.a_task()
        self.ok(self.api.put("2B.02", "/v1/task-state",
                             {"task_id": t["task_id"], "state": "running", "evidence_ids": [],
                              "updated_at": "2026-10-12T10:00:00.000Z"}))
        r = self.api.put("2B.02", "/v1/task-state",
                         {"task_id": t["task_id"], "state": "completed-verified", "evidence_ids": [],
                          "updated_at": "2026-10-12T10:01:00.000Z"})
        self.failed(r, "not_verified")

    def test_a_task_is_completed_verified_once_verified_evidence_exists(self):
        """LA-EVD-03. The evidence must sit at an AMD-3 stage that proves the real output."""
        t = self.a_task()
        self.ok(self.api.put("2B.02", "/v1/task-state",
                             {"task_id": t["task_id"], "state": "running", "evidence_ids": [],
                              "updated_at": "2026-10-12T10:00:00.000Z"}))
        ev = self.ok(self.api.post("2B.02", "/v1/evidence",
                                   {"capability": "test-t0-repair", "provider": "2B.06", "stage": 7,
                                    "environment": "test", "observed_at": "2026-10-12T10:00:30.000Z",
                                    "outcome": "pass", "detail": {"ran": "the real check"}}))
        done = self.ok(self.api.put("2B.02", "/v1/task-state",
                                    {"task_id": t["task_id"], "state": "completed-verified",
                                     "evidence_ids": [ev["evidence_id"]],
                                     "updated_at": "2026-10-12T10:02:00.000Z"}))
        self.assertEqual(done["state"], "completed-verified")

    def test_evidence_at_a_lower_stage_does_not_verify_a_task(self):
        """AMD-3. A passing test (stage 4) is not a verified real output (stage 7)."""
        t = self.a_task()
        self.ok(self.api.put("2B.02", "/v1/task-state",
                             {"task_id": t["task_id"], "state": "running", "evidence_ids": [],
                              "updated_at": "2026-10-12T10:00:00.000Z"}))
        ev = self.ok(self.api.post("2B.02", "/v1/evidence",
                                   {"capability": "unit-test", "provider": "2B.06", "stage": 4,
                                    "environment": "test", "observed_at": "2026-10-12T10:00:30.000Z",
                                    "outcome": "pass", "detail": {"ran": "a unit test"}}))
        r = self.api.put("2B.02", "/v1/task-state",
                         {"task_id": t["task_id"], "state": "completed-verified",
                          "evidence_ids": [ev["evidence_id"]], "updated_at": "2026-10-12T10:02:00.000Z"})
        self.failed(r, "not_verified")


class Approvals(ContractTest):
    """The Founder's own path: BND-03 and BND-04."""

    def test_an_approval_cannot_be_reused_for_another_action(self):
        """LA-DFC-05. An approval binds to the exact action shown to the Founder."""
        check = self.ok(self.api.post("2A.05", "/v1/policy/checks",
                                      {"proposed_action": {"tools": [self.tool_ok]}, "thread_id": "t1",
                                       "estimated_spend_minor": 500}))
        r = self.api.post("2A.05", "/v1/controls/decision",
                          {"approval_id": check["approval_id"], "decision": "approve",
                           "bound_action_digest": "a-digest-for-some-other-action",
                           "authenticator_assertion": self.step_up()})
        self.failed(r, "invalid_request")

    def test_a_decision_without_step_up_authentication_is_refused(self):
        """LA-DFC-03. A consequential approval needs an independently authenticated Founder."""
        check = self.ok(self.api.post("2A.05", "/v1/policy/checks",
                                      {"proposed_action": {"tools": [self.tool_ok]}, "thread_id": "t1",
                                       "estimated_spend_minor": 500}))
        r = self.api.post("2A.05", "/v1/controls/decision",
                          {"approval_id": check["approval_id"], "decision": "approve",
                           "bound_action_digest": check["bound_action_digest"],
                           "authenticator_assertion": {"step_up_verified": False}})
        self.failed(r, "unauthenticated")

    def test_a_money_action_needs_an_approval_before_anything_runs(self):
        """LA-GOV-05. Every financial action stays blocked until a Founder approval exists."""
        check = self.ok(self.api.post("2A.05", "/v1/policy/checks",
                                      {"proposed_action": {"tools": [self.tool_ok]}, "thread_id": "t1",
                                       "estimated_spend_minor": 1}))
        self.assertEqual(check["verdict"], "approval-needed")
        self.assertIn("approval_id", check)


class StopPath(ContractTest):
    """AMD-5: the red path. N3 and N14 live here."""

    def test_stop_blocks_every_new_tool_call_and_the_refusal_is_audited(self):
        """N3, LA-SAF-02, LA-TOOL-04. STOP is checked on every single call."""
        before = self.ok(self.api.post("2A.07", "/v1/tool-calls",
                                       {"tool_id": self.tool_ok, "arguments": {}, "task_id": "tsk_x"}))
        self.assertTrue(before["audited"])
        self.ok(self.api.post("2A.05", "/v1/controls/emergency",
                              {"command": "stop", "scope": "all",
                               "authenticator_assertion": self.step_up()}))
        err = self.failed(self.api.post("2A.07", "/v1/tool-calls",
                                        {"tool_id": self.tool_ok, "arguments": {}, "task_id": "tsk_x"}),
                          "stopped")
        self.assertEqual(err["details"]["checks"]["stop_state"], "fail", "the refusal records which check failed")

    def test_the_bus_reports_the_stop_state_to_whoever_asks(self):
        """BND-11 BUS-02. The Tool Hub reads this on every call."""
        self.assertFalse(self.ok(self.api.get("2A.06", "/v1/stop-state"))["stopped"])
        self.ok(self.api.post("2A.05", "/v1/controls/emergency",
                              {"command": "pause", "scope": "all",
                               "authenticator_assertion": self.step_up()}))
        now = self.ok(self.api.get("2A.06", "/v1/stop-state"))
        self.assertTrue(now["stopped"])
        self.assertEqual(now["stop_reason"], "pause")

    def test_a_resume_without_authorization_is_refused(self):
        """N14, LA-SAF-04, LA-GOV-08. There is no automatic resume."""
        self.ok(self.api.post("2A.05", "/v1/controls/emergency",
                              {"command": "stop", "scope": "all",
                               "authenticator_assertion": self.step_up()}))
        r = self.api.post("2B.07", "/v1/control",
                          {"command": "resume", "receptor_id": "all",
                           "issued_at": "2026-10-12T10:00:00.000Z"})
        self.failed(r, "forbidden")

    def test_a_stop_is_idempotent(self):
        """LANE-STOP. A STOP on an already stopped system is accepted, never an error."""
        for _ in range(2):
            self.ok(self.api.post("2A.05", "/v1/controls/emergency",
                                  {"command": "stop", "scope": "all",
                                   "authenticator_assertion": self.step_up()}))

    def test_stop_reaches_the_tool_hub_and_hermes(self):
        """LA-GOV-03. STOP acts on the Tool Hub, Hermes and all Receptors."""
        out = self.ok(self.api.post("2A.05", "/v1/controls/emergency",
                                    {"command": "stop", "scope": "all",
                                     "authenticator_assertion": self.step_up()}))
        for who in ("2A.07", "2B.05"):
            self.assertIn(who, out["reached"], "%s was not reached by STOP" % who)
        self.assertEqual(out["not_reached"], [], "anything unreached is reported, never assumed stopped")


class ToolHub(ContractTest):
    """LA-TOOL: G authorizes one call at a time. N1 lives here."""

    def test_a_tool_outside_the_registry_is_denied_and_audited(self):
        """N1, LA-TOOL-03, LA-TOOL-04. Nothing is callable until it passes the Supply Chain Gate."""
        err = self.failed(self.api.post("2A.07", "/v1/tool-calls",
                                        {"tool_id": self.tool_none, "arguments": {}, "task_id": "tsk_x"}),
                          "not_admitted")
        self.assertEqual(err["details"]["checks"]["admission"], "fail")

    def test_a_high_risk_tool_waits_for_a_founder_approval(self):
        """LA-GOV-06, AMD-13. High-risk integrations need the Founder."""
        self.failed(self.api.post("2A.07", "/v1/tool-calls",
                                  {"tool_id": self.tool_high, "arguments": {}, "task_id": "tsk_x"}),
                    "approval_needed")

    def test_a_call_outside_the_receptor_scope_is_denied(self):
        """LA-TOOL-01. Receptor scope is one of the five checks."""
        self.failed(self.api.post("2A.07", "/v1/tool-calls",
                                  {"tool_id": self.tool_ok, "arguments": {}, "task_id": "tsk_x",
                                   "receptor_id": "rcp_0000000000000000000NOTMINE"[:31]}),
                    "forbidden")

    def test_every_tool_call_reports_all_five_checks(self):
        """LA-TOOL-01. Identity, scope, risk and spend, approval, STOP state."""
        out = self.ok(self.api.post("2A.07", "/v1/tool-calls",
                                    {"tool_id": self.tool_ok, "arguments": {"a": 1}, "task_id": "tsk_x"}))
        for check in ("identity", "scope", "admission", "approval", "spend", "stop_state"):
            self.assertIn(check, out["checks"], "the call did not report the %s check" % check)
        self.assertTrue(out["audited"])

    def test_the_supply_chain_gate_answers_whether_a_tool_is_admitted(self):
        """LA-TOOL-03, LA-SEC-04. G reads admission from the Gate."""
        self.assertTrue(self.ok(self.api.get("2A.08", "/v1/admissions/" + self.tool_ok))["admitted"])
        blocked = self.ok(self.api.get("2A.08", "/v1/admissions/" + self.tool_none))
        self.assertFalse(blocked["admitted"])
        self.assertTrue(blocked["blocked"])


class ReceptorLanes(ContractTest):
    """LA-IF: the five lanes, and what a Receptor may never do."""

    def test_a_receptor_result_does_not_complete_a_task(self):
        """LA-IF-04. A Receptor's report is not proof."""
        self.ok(self.api.post("2B.07", "/v1/receptor/tasks",
                              {"task_id": "tsk_0000000000000000000000001", "receptor_id": self.receptor,
                               "instruction": {"do": "x"}, "scope": {"tools": []}}))
        out = self.ok(self.api.post("2A.07", "/v1/task-results",
                                    {"task_id": "tsk_0000000000000000000000001", "output_ref": "s3://x",
                                     "claimed_outcome": "I did it"}))
        self.assertEqual(out["state"], "running", "a result must not move the task to completed-verified")
        self.assertTrue(out["verification_required"])

    def test_a_receptor_cannot_self_certify(self):
        """LA-QA-05. Completion needs an independent verification step."""
        out = self.ok(self.api.post("2B.06", "/v1/evidence",
                                    {"verification_id": "evd_0000000000000000000000001",
                                     "task_id": "tsk_0000000000000000000000001",
                                     "evidence": [{"kind": "screenshot", "ref": "s3://x"}],
                                     "claimed_outcome": "all good"}))
        self.assertFalse(out["self_certification_accepted"])
        self.assertEqual(out["verdict"], "pending", "F decides in its own time; arrival is not a verdict")

    def test_revenue_is_not_final_until_a_statement_matches_it(self):
        """LA-IF-05, LA-FIN-02. Reported revenue stays reported, not final."""
        out = self.ok(self.api.post("2B.08", "/v1/revenue-reports",
                                    {"receptor_id": self.receptor, "period": "2026-10-01 to 2026-10-31",
                                     "amount_minor": 12345, "currency": "INR"}))
        self.assertEqual(out["status"], "reported-not-final")
        self.assertFalse(out["reconciled"])
        self.assertTrue(out["bank_statement_required"])

    def test_a_bank_statement_is_accepted_only_from_the_founder(self):
        """LA-VLT-01, LA-VLT-02. Dyson holds no bank credential and has no bank API."""
        self.failed(self.api.post("2B.08", "/v1/bank-statements",
                                  {"statement_ref": "s3://stmt", "period": "2026-10-01 to 2026-10-31",
                                   "uploaded_by": "2B.03", "uploaded_at": "2026-10-12T10:00:00.000Z"}),
                    "forbidden")
        ok = self.ok(self.api.post("2B.08", "/v1/bank-statements",
                                   {"statement_ref": "s3://stmt", "period": "2026-10-01 to 2026-10-31",
                                    "uploaded_by": "founder", "uploaded_at": "2026-10-12T10:00:00.000Z"}))
        self.assertEqual(ok["classified_as"], "personal-financial-data")

    def test_a_statement_upload_makes_the_matching_revenue_final(self):
        """LA-FIN-02. Revenue is final only after a match."""
        rep = self.ok(self.api.post("2B.08", "/v1/revenue-reports",
                                    {"receptor_id": self.receptor, "period": "2026-10-01 to 2026-10-31",
                                     "amount_minor": 500, "currency": "INR"}))
        out = self.ok(self.api.post("2B.08", "/v1/bank-statements",
                                    {"statement_ref": "s3://stmt", "period": "2026-10-01 to 2026-10-31",
                                     "uploaded_by": "founder", "uploaded_at": "2026-10-12T10:00:00.000Z"}))
        self.assertIn(rep["report_id"], out["matched_reports"])

    def test_an_offline_receptor_is_reported_as_offline(self):
        """LA-MON-06. Monitoring reports the truth rather than staying silent."""
        out = self.ok(self.api.post("P1.06", "/v1/health-reports",
                                    {"receptor_id": self.receptor, "status": "offline",
                                     "reported_at": "2026-10-12T10:00:00.000Z"}))
        self.assertTrue(out["escalated"])

    def test_monitoring_escalates_without_acting(self):
        """LA-MON-05. E observes and escalates; the Governance Core decides."""
        out = self.ok(self.api.post("2A.05", "/v1/escalations",
                                    {"receptor_id": self.receptor, "condition": "repeated-failure",
                                     "evidence_ref": "s3://obs", "observed_at": "2026-10-12T10:00:00.000Z"}))
        self.assertEqual(out["decision_owner"], "2A.05")
        self.assertEqual(out["action_taken"], "none")


class FounderFacing(ContractTest):
    """What the Founder sees: the app and the dashboard."""

    def test_the_app_answers_with_an_acknowledgment_never_a_completion(self):
        """LA-APP-04. An acknowledgment shall never be presented as completion."""
        out = self.ok(self.api.post("2A.03", "/v1/messages",
                                    {"locale": "hi-Latn", "content": {"text": "ek kaam karo"}}))
        self.assertIn(out["acknowledgment"], ("accepted", "approval-needed"))

    def test_voice_and_text_share_one_thread(self):
        """LA-APP-03. Voice and text share one conversation history."""
        a = self.ok(self.api.post("2A.03", "/v1/messages",
                                  {"locale": "hi", "content": {"text": "pehla"}}))
        b = self.ok(self.api.post("2A.03", "/v1/messages",
                                  {"locale": "en", "content": {"audio_ref": "s3://clip"}}))
        self.assertEqual(a["thread_id"], b["thread_id"])

    def test_the_conversation_engine_claims_no_completion(self):
        """LA-CONV-07. B shall not report an action complete because a tool answered 200 OK."""
        out = self.ok(self.api.post("2B.04", "/v1/conversation/turns",
                                    {"thread_id": "t1", "locale": "en", "content": {"text": "do it"}}))
        self.assertFalse(out["completion_claimed"])

    def test_the_dashboard_shows_only_verified_data_and_has_no_write_path(self):
        """LA-DASH-01, LA-DASH-02. Visibility confers no authority."""
        self.ok(self.api.post("2B.02", "/v1/ledger-entries",
                              {"receptor_id": self.receptor, "amount_minor": 100, "currency": "INR",
                               "kind": "revenue-reported", "occurred_at": "2026-10-12T10:00:00.000Z"}))
        view = self.ok(self.api.get("2B.02", "/v1/financial-views/revenue"))
        self.assertTrue(view["verified_only"])
        self.assertEqual(view["rows"], [], "unverified revenue must not appear")
        self.assertEqual(view["unverified_excluded"], 1)
        self.assertGreaterEqual(self.api.post("2B.02", "/v1/financial-views/revenue", {}).status, 400,
                                "the dashboard view must have no write path")


class ModelAccess(ContractTest):
    """LA-RTR and LA-HER: the only governed path to a model."""

    def test_a_model_call_reports_its_cost_and_whether_redaction_applied(self):
        """LA-RTR-05, LA-RTR-07. Cost control and the gate 6 redaction rules."""
        out = self.ok(self.api.post("2B.03", "/v1/model/completions",
                                    {"purpose": "summarize", "input": {"contains_personal_data": True}}))
        self.assertTrue(out["redaction_applied"])
        self.assertIsInstance(out["cost_minor"], int)

    def test_a_model_call_over_the_ceiling_is_refused(self):
        """LA-RTR-05. Cost control and token limits inside approved budgets."""
        self.failed(self.api.post("2B.03", "/v1/model/completions",
                                  {"purpose": "summarize", "input": {}, "max_cost_minor": 1}),
                    "spend_limit")

    def test_the_router_falls_back_without_losing_the_task(self):
        """LA-RTR-04, LA-REL-06. A failure falls back to a tested alternative."""
        out = self.ok(self.api.post("2B.03", "/v1/model/completions",
                                    {"purpose": "summarize", "input": {"force_primary_failure": True}}))
        self.assertTrue(out["fallback_used"])

    def test_hermes_reaches_a_model_only_through_the_router(self):
        """LA-HER-02. Hermes has no other path, and its calls stop when the Core stops."""
        self.ok(self.api.post("2B.03", "/v1/model/completions",
                              {"purpose": "think", "input": {}},
                              headers={"X-Dyson-Caller": "2B.05"}))
        self.ok(self.api.post("2A.05", "/v1/controls/emergency",
                              {"command": "stop", "scope": "all",
                               "authenticator_assertion": self.step_up()}))
        self.failed(self.api.post("2B.03", "/v1/model/completions",
                                  {"purpose": "think", "input": {}},
                                  headers={"X-Dyson-Caller": "2B.05"}),
                    "stopped")


class StubDiscipline(ContractTest):
    """The stub must be able to produce the errors its contract documents, and only those."""

    def test_a_documented_error_can_be_forced_for_a_caller_to_test_against(self):
        self.failed(self.api.post("2A.07", "/v1/tool-calls",
                                  {"tool_id": self.tool_ok, "arguments": {}, "task_id": "tsk_x"},
                                  headers={"X-Dyson-Stub-Force": "dependency_down"}),
                    "dependency_down")

    def test_an_undocumented_error_cannot_be_forced(self):
        self.failed(self.api.get("2A.08", "/v1/admissions/" + self.tool_ok,
                                 headers={"X-Dyson-Stub-Force": "spend_limit"}),
                    "invalid_request")


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
