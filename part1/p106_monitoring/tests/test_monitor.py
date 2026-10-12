"""P1.06 done when: failures of a Test T0 stub are detected and escalated, and an offline Receptor is
reported as offline.

Run:  python3 -m unittest discover -s part1/p106_monitoring/tests -t part1/p106_monitoring/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")))
import monitor  # noqa: E402

def _id(prefix, tag):
    """An id in the shape the contracts note defines: prefix plus 26 Crockford base32 characters."""
    assert all(c in monitor.B32 for c in tag), tag
    return prefix + (tag + "0" * 26)[:26]


T0 = _id("rcp_", "T0RCPA")
OTHER = _id("rcp_", "T0RCPB")
# Test T0 task ids. Numbered rather than named, because Crockford base32 has no I, L, O or U.
TASK = {n: _id("tsk_", "T0TASK%d" % n) for n in range(1, 10)}
FAULT = TASK[9]


def at(second, milli=0):
    return "2026-10-12T09:%02d:%02d.%03dZ" % (second // 60, second % 60, milli)


class Governance:
    """A stand-in for the Governance Core (2A.05) on the other side of ESC-01."""

    def __init__(self, fail=False):
        self.fail = fail
        self.received = []
        self.keys = []

    def __call__(self, body, key):
        self.keys.append(key)
        if self.fail:
            raise RuntimeError("dependency_down")
        self.received.append(body)
        return {"escalation_id": "esc_%d" % len(self.received), "decision_owner": "2A.05",
                "action_taken": "none"}


class Reporting(unittest.TestCase):
    """MON-01: what a Receptor tells E, and what E does with it."""

    def setUp(self):
        self.core = Governance()
        self.e = monitor.Monitor(escalate_to=self.core)

    def test_a_healthy_report_is_accepted_and_escalates_nothing(self):
        answer = self.e.report_health(T0, "healthy", at(0), kpis={"tasks_done": 4})
        self.assertEqual(answer, {"accepted": True, "escalated": False})
        self.assertEqual(self.core.received, [])

    def test_three_failing_reports_raise_a_repeated_failure_and_escalate_it(self):
        self.assertFalse(self.e.report_health(T0, "failing", at(0))["escalated"])
        self.assertFalse(self.e.report_health(T0, "failing", at(10))["escalated"])
        self.assertTrue(self.e.report_health(T0, "failing", at(20))["escalated"])
        self.assertEqual([r["condition"] for r in self.core.received], ["repeated-failure"])
        self.assertEqual(self.core.received[0]["receptor_id"], T0)

    def test_a_reported_failure_counts_even_when_the_status_is_not_failing(self):
        for second in (0, 10, 20):
            self.e.report_health(T0, "degraded", at(second),
                                 failures=[{"task_id": FAULT, "reason": "timeout"}])
        self.assertEqual([r["condition"] for r in self.core.received], ["repeated-failure"])

    def test_a_healthy_report_clears_the_count_so_the_condition_can_be_raised_again(self):
        self.e.report_health(T0, "failing", at(0))
        self.e.report_health(T0, "failing", at(10))
        self.e.report_health(T0, "healthy", at(20))
        self.assertEqual(self.e.receptors[T0]["consecutive_bad"], 0)
        self.assertEqual(self.core.received, [])
        for second in (30, 40, 50):
            self.e.report_health(T0, "failing", at(second))
        self.assertEqual(len(self.core.received), 1)

    def test_a_condition_is_escalated_once_not_on_every_later_report(self):
        for second in (0, 10, 20, 30, 40):
            self.e.report_health(T0, "failing", at(second))
        self.assertEqual(len(self.core.received), 1)

    def test_a_receptor_reporting_itself_offline_is_escalated_as_offline(self):
        self.assertTrue(self.e.report_health(T0, "offline", at(0))["escalated"])
        self.assertEqual([r["condition"] for r in self.core.received], ["offline"])

    def test_one_receptors_failures_do_not_touch_another(self):
        for second in (0, 10, 20):
            self.e.report_health(T0, "failing", at(second))
        self.e.report_health(OTHER, "healthy", at(30))
        self.assertEqual(self.e.receptors[OTHER]["consecutive_bad"], 0)
        self.assertEqual([r["receptor_id"] for r in self.core.received], [T0])

    def test_a_report_that_does_not_match_the_contract_is_refused_not_half_recorded(self):
        for bad in (
            lambda: self.e.report_health("T0", "healthy", at(0)),
            lambda: self.e.report_health(T0, "fine", at(0)),
            lambda: self.e.report_health(T0, "healthy", "12 Oct 2026"),
            lambda: self.e.report_health(T0, "healthy", at(0), failures=[{"reason": "no task id"}]),
        ):
            with self.assertRaises(monitor.InvalidReport):
                bad()
        self.assertEqual(self.e.receptors, {})


class Polling(unittest.TestCase):
    """MON-02: E asks, and reports the truth about what came back."""

    def setUp(self):
        self.core = Governance()
        self.e = monitor.Monitor(escalate_to=self.core)

    def test_a_receptor_that_answers_is_recorded_with_what_it_said(self):
        answer = self.e.poll(T0, lambda: {"receptor_id": T0, "status": "degraded",
                                          "checks": [{"name": "queue", "ok": True}]}, at(0))
        self.assertEqual(answer["status"], "degraded")
        self.assertEqual(self.e.receptors[T0]["source"], "poll")
        self.assertIs(self.e.receptors[T0]["reachable"], True)

    def test_a_receptor_that_does_not_answer_is_reported_as_offline(self):
        def unreachable():
            raise OSError("connection refused")

        answer = self.e.poll(T0, unreachable, at(0))
        self.assertEqual(answer["status"], "offline")
        self.assertEqual(self.e.receptors[T0]["status"], "offline")
        self.assertIs(self.e.receptors[T0]["reachable"], False)
        self.assertTrue(answer["escalated"])
        self.assertEqual([r["condition"] for r in self.core.received], ["offline"])

    def test_a_receptor_that_goes_quiet_does_not_keep_showing_its_last_happy_status(self):
        self.e.poll(T0, lambda: {"receptor_id": T0, "status": "healthy", "checks": []}, at(0))
        self.assertEqual(self.e.receptors[T0]["status"], "healthy")
        self.e.poll(T0, lambda: (_ for _ in ()).throw(TimeoutError()), at(10))
        self.assertEqual(self.e.receptors[T0]["status"], "offline")

    def test_a_receptor_answering_with_nonsense_is_offline_rather_than_believed(self):
        answer = self.e.poll(T0, lambda: {"status": "wonderful", "checks": []}, at(0))
        self.assertEqual(answer["status"], "offline")

    def test_polls_that_keep_failing_raise_a_repeated_failure_as_well_as_offline(self):
        for second in (0, 10, 20):
            self.e.poll(T0, lambda: (_ for _ in ()).throw(OSError()), at(second))
        self.assertEqual(sorted(r["condition"] for r in self.core.received),
                         ["offline", "repeated-failure"])

    def test_a_failed_check_counts_as_a_bad_observation(self):
        for second in (0, 10, 20):
            self.e.poll(T0, lambda: {"status": "degraded", "checks": [{"name": "disk", "ok": False}]},
                        at(second))
        self.assertEqual([r["condition"] for r in self.core.received], ["repeated-failure"])


class TaskStatus(unittest.TestCase):
    """MON-03: E records task state and escalates a pause condition, but never moves a task."""

    def setUp(self):
        self.core = Governance()
        self.e = monitor.Monitor(escalate_to=self.core)

    def test_a_task_state_is_accepted_and_recorded(self):
        answer = self.e.report_task_status(TASK[1], "running", at(0),
                                           receptor_id=T0)
        self.assertEqual(answer, {"accepted": True})
        self.assertEqual(self.e.tasks[TASK[1]]["state"], "running")

    def test_a_held_task_is_a_pause_condition_and_is_escalated(self):
        self.e.report_task_status(TASK[2], "held", at(0), receptor_id=T0)
        self.assertEqual([r["condition"] for r in self.core.received], ["pause-condition"])

    def test_a_pause_arrives_as_stopped_with_reason_pause_and_is_escalated(self):
        self.e.report_task_status(TASK[3], "stopped", at(0),
                                  stop_reason="pause", receptor_id=T0)
        self.assertEqual([r["condition"] for r in self.core.received], ["pause-condition"])

    def test_a_stop_is_not_mistaken_for_a_pause(self):
        self.e.report_task_status(TASK[4], "stopped", at(0),
                                  stop_reason="stop", receptor_id=T0)
        self.assertEqual(self.core.received, [])

    def test_a_stopped_task_without_a_reason_is_refused(self):
        with self.assertRaises(monitor.InvalidReport):
            self.e.report_task_status(TASK[5], "stopped", at(0))

    def test_a_state_outside_the_eight_is_refused(self):
        with self.assertRaises(monitor.InvalidReport):
            self.e.report_task_status(TASK[6], "paused", at(0))

    def test_a_task_id_that_is_not_a_task_id_is_refused(self):
        with self.assertRaises(monitor.InvalidReport):
            self.e.report_task_status("12345", "running", at(0))


class Views(unittest.TestCase):
    """ESC-02: what the Founder Dashboard reads, and how staleness is admitted."""

    def setUp(self):
        self.core = Governance()
        self.e = monitor.Monitor(escalate_to=self.core)

    def test_the_health_view_lists_each_receptor_with_its_open_conditions(self):
        for second in (0, 10, 20):
            self.e.report_health(T0, "failing", at(second))
        self.e.report_health(OTHER, "healthy", at(20))
        view = self.e.view("receptor-health", at(25))
        self.assertEqual([r["receptor_id"] for r in view["rows"]], sorted([T0, OTHER]))
        row = [r for r in view["rows"] if r["receptor_id"] == T0][0]
        self.assertEqual(row["status"], "failing")
        self.assertEqual(row["open_conditions"], ["repeated-failure"])

    def test_the_kpi_view_returns_the_numbers_the_receptor_reported(self):
        self.e.report_health(T0, "healthy", at(0), kpis={"tasks_done": 7, "mean_ms": 420})
        view = self.e.view("kpis", at(1))
        self.assertEqual(view["rows"][0]["kpis"], {"tasks_done": 7, "mean_ms": 420})

    def test_a_view_can_be_narrowed_to_one_receptor(self):
        self.e.report_health(T0, "healthy", at(0))
        self.e.report_health(OTHER, "healthy", at(0))
        view = self.e.view("receptor-health", at(1), receptor_id=T0)
        self.assertEqual([r["receptor_id"] for r in view["rows"]], [T0])

    def test_fresh_data_is_not_marked_stale(self):
        self.e.report_health(T0, "healthy", at(0))
        self.assertFalse(self.e.view("receptor-health", at(30))["stale"])

    def test_data_older_than_the_freshness_bound_is_marked_stale(self):
        self.e.report_health(T0, "healthy", at(0))
        self.assertTrue(self.e.view("receptor-health", at(120))["stale"])

    def test_a_view_with_nothing_behind_it_is_stale_not_quietly_empty(self):
        view = self.e.view("receptor-health", at(0))
        self.assertEqual(view["rows"], [])
        self.assertTrue(view["stale"])

    def test_the_view_states_that_visibility_carries_no_authority(self):
        self.assertEqual(self.e.view("kpis", at(0))["authority"], "read-only")

    def test_an_unknown_view_is_refused(self):
        with self.assertRaises(monitor.InvalidReport):
            self.e.view("everything", at(0))


class TruthfulReporting(unittest.TestCase):
    """LA-MON-06: offline is offline, unverified is unverified, and a dropped escalation is visible."""

    def test_a_dependency_can_be_reported_unverified_and_shows_in_the_view(self):
        e = monitor.Monitor(escalate_to=Governance())
        e.set_dependency("model-router", "unverified", at(0))
        e.set_dependency("governance-core", "offline", at(0))
        e.report_health(T0, "healthy", at(0))
        self.assertEqual(e.view("receptor-health", at(1))["dependencies"],
                         {"governance-core": "offline", "model-router": "unverified"})

    def test_a_dependency_state_outside_the_three_is_refused(self):
        e = monitor.Monitor()
        with self.assertRaises(monitor.InvalidReport):
            e.set_dependency("model-router", "probably fine", at(0))

    def test_an_escalation_the_governance_core_refuses_is_kept_and_shown_as_unescalated(self):
        core = Governance(fail=True)
        e = monitor.Monitor(escalate_to=core)
        e.report_health(T0, "offline", at(0))
        self.assertEqual(core.received, [])
        self.assertEqual(len(e.unescalated), 1)
        row = e.view("receptor-health", at(1))["rows"][0]
        self.assertEqual(row["unescalated"], 1)

    def test_with_no_governance_core_at_all_the_condition_is_queued_not_lost(self):
        e = monitor.Monitor(escalate_to=None)
        e.report_health(T0, "offline", at(0))
        self.assertEqual(len(e.unescalated), 1)

    def test_a_retry_sends_the_queued_escalation_with_the_same_idempotency_key(self):
        core = Governance(fail=True)
        e = monitor.Monitor(escalate_to=core)
        e.report_health(T0, "offline", at(0))
        first_key = core.keys[0]
        core.fail = False
        self.assertEqual(e.retry_escalations(), {"sent": 1, "still_unescalated": 0})
        self.assertEqual(core.keys[-1], first_key)
        self.assertEqual(len(e.sent_escalations), 1)

    def test_a_retry_that_fails_again_leaves_the_condition_queued(self):
        core = Governance(fail=True)
        e = monitor.Monitor(escalate_to=core)
        e.report_health(T0, "offline", at(0))
        self.assertEqual(e.retry_escalations(), {"sent": 0, "still_unescalated": 1})

    def test_a_governance_core_answering_without_an_escalation_id_is_not_treated_as_success(self):
        e = monitor.Monitor(escalate_to=lambda body, key: {"decision_owner": "2A.05"})
        e.report_health(T0, "offline", at(0))
        self.assertEqual(len(e.unescalated), 1)
        self.assertEqual(e.sent_escalations, [])

    def test_the_escalation_records_who_decides_and_that_nothing_was_done(self):
        core = Governance()
        e = monitor.Monitor(escalate_to=core)
        e.report_health(T0, "offline", at(0))
        self.assertEqual(e.sent_escalations[0]["decision_owner"], "2A.05")
        self.assertEqual(e.sent_escalations[0]["action_taken"], "none")


class NoAuthority(unittest.TestCase):
    """LA-MON-05: E observes and escalates. It has no authority to act on a Receptor."""

    def setUp(self):
        self.e = monitor.Monitor(escalate_to=Governance())

    def test_every_action_shaped_method_only_refuses(self):
        for name in ("pause_receptor", "stop_receptor", "resume_receptor", "reassign_task"):
            with self.assertRaises(monitor.NoAuthority):
                getattr(self.e, name)(T0)

    def test_the_module_has_no_way_to_reach_out_and_act_at_all(self):
        """The only outbound path is the escalation callable the caller supplies. Nothing else."""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "monitor.py")
        with open(path) as handle:
            source = handle.read()
        for forbidden in ("import subprocess", "import socket", "import urllib", "os.system",
                          "import http.client", "import requests"):
            self.assertNotIn(forbidden, source, "monitoring must not be able to act: %s" % forbidden)

    def test_escalating_is_the_only_thing_that_leaves_the_monitor(self):
        calls = []
        e = monitor.Monitor(escalate_to=lambda body, key: calls.append(body) or
                            {"escalation_id": "esc_1", "decision_owner": "2A.05", "action_taken": "none"})
        e.report_health(T0, "offline", at(0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["condition"], "offline")
        self.assertEqual(calls[0]["evidence_ref"], "monitor://receptors/%s/observations" % T0)


class Identifiers(unittest.TestCase):
    """The idempotency key ESC-01 requires."""

    def test_the_key_has_the_shape_the_contract_asks_for(self):
        key = monitor.idempotency_key(T0, "offline", at(0))
        self.assertTrue(key.startswith("idem_"))
        self.assertEqual(len(key), len("idem_") + 26)
        self.assertTrue(all(c in monitor.B32 for c in key[5:]))

    def test_the_same_condition_gives_the_same_key_and_a_different_one_does_not(self):
        same = monitor.idempotency_key(T0, "offline", at(0))
        self.assertEqual(same, monitor.idempotency_key(T0, "offline", at(0)))
        self.assertNotEqual(same, monitor.idempotency_key(T0, "repeated-failure", at(0)))

    def test_the_monitor_derives_the_key_so_a_restart_does_not_escalate_twice(self):
        """E could be restarted between the observation and a successful send. The Governance Core must be
        able to recognize the retry, so the key comes from the condition, not from chance."""
        first = Governance(fail=True)
        before = monitor.Monitor(escalate_to=first)
        before.report_health(T0, "offline", at(0))

        second = Governance()
        after = monitor.Monitor(escalate_to=second)
        after.report_health(T0, "offline", at(0))

        self.assertEqual(first.keys, second.keys)
        self.assertEqual(second.keys[0], monitor.idempotency_key(T0, "offline", at(0)))

    def test_every_identifier_these_tests_use_is_a_real_one(self):
        for identifier in [T0, OTHER] + list(TASK.values()):
            prefix, body = identifier[:4], identifier[4:]
            self.assertIn(prefix, ("rcp_", "tsk_"))
            self.assertEqual(len(body), 26)
            self.assertTrue(all(c in monitor.B32 for c in body), identifier)

    def test_the_timestamp_parser_agrees_with_the_calendar(self):
        self.assertEqual(monitor._ms("1970-01-01T00:00:00.000Z"), 0)
        self.assertEqual(monitor._ms("1970-01-01T00:00:01.500Z"), 1500)
        self.assertEqual(monitor._ms("2026-10-12T00:00:00.000Z"), 1791763200000)
        self.assertEqual(monitor._ms("2026-10-12T09:00:01.250Z") -
                         monitor._ms("2026-10-12T09:00:00.000Z"), 1250)


class DoneWhen(unittest.TestCase):
    """The two things P1.06 is done when, end to end on a Test T0 stub."""

    def test_a_planted_fault_in_a_test_t0_stub_is_detected_and_escalated(self):
        core = Governance()
        e = monitor.Monitor(escalate_to=core)
        fault = {"task_id": FAULT, "reason": "tool call returned 500"}

        e.report_health(T0, "healthy", at(0), kpis={"tasks_done": 3})
        self.assertEqual(core.received, [])

        for second in (10, 20, 30):
            e.report_health(T0, "degraded", at(second), failures=[fault])
        e.report_task_status(fault["task_id"], "failed", at(31), receptor_id=T0)

        self.assertEqual([r["condition"] for r in core.received], ["repeated-failure"])
        self.assertEqual(core.received[0]["receptor_id"], T0)
        self.assertEqual(e.sent_escalations[0]["action_taken"], "none")
        row = e.view("receptor-health", at(32))["rows"][0]
        self.assertEqual(row["open_conditions"], ["repeated-failure"])
        self.assertFalse(e.view("receptor-health", at(32))["stale"])

    def test_an_offline_receptor_is_reported_as_offline(self):
        core = Governance()
        e = monitor.Monitor(escalate_to=core)

        e.poll(T0, lambda: {"receptor_id": T0, "status": "healthy", "checks": []}, at(0))
        self.assertEqual(e.view("receptor-health", at(1))["rows"][0]["status"], "healthy")

        e.poll(T0, lambda: (_ for _ in ()).throw(OSError("no route to host")), at(10))

        row = e.view("receptor-health", at(11))["rows"][0]
        self.assertEqual(row["status"], "offline")
        self.assertEqual(row["open_conditions"], ["offline"])
        self.assertEqual([r["condition"] for r in core.received], ["offline"])


if __name__ == "__main__":
    unittest.main()
