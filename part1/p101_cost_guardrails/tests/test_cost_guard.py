"""P1.01 done when: an alarm fires on a test threshold, and the cap is on record.

Run:  python3 -m unittest discover -s part1/p101_cost_guardrails/tests \\
          -t part1/p101_cost_guardrails/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")))
import cost_guard  # noqa: E402


def a_register(**over):
    """The register as it stands today, verified against the Founder's actual account on 14 Oct 2026."""
    fields = {
        "approved_cap_usd": 7.00,
        "period": "month",
        "approved_by": "founder",
        "approved_at": "2026-10-14T15:29:52.000Z",
        "plan": "free",
        "region": "ap-southeast-2",
        "credits_remaining_usd": 100.00,
        "days_remaining": 181,
        "verified_at": "2026-10-14T14:58:00.000Z",
        "verified_how": "Read in the AWS console, in the Founder's own account",
    }
    fields.update(over)
    return cost_guard.CostRegister(**fields)


class Money(unittest.TestCase):
    """Money is integer cents. Floating point never decides whether a cap was crossed."""

    def test_dollars_convert_to_whole_cents(self):
        self.assertEqual(cost_guard.cents(10), 1000)
        self.assertEqual(cost_guard.cents(0.1), 10)
        self.assertEqual(cost_guard.cents(24.99), 2499)

    def test_the_result_is_an_integer_and_not_a_float_that_looks_like_one(self):
        self.assertIsInstance(cost_guard.cents(0.1), int)
        self.assertNotIsInstance(cost_guard.cents(0.1), float)

    def test_the_amounts_where_multiplying_by_a_hundred_goes_wrong(self):
        """These are the ones that bite. 0.29 times 100 is 28.999999999999996 in floating point, so a
        cent-short result would quietly put spend one cent under a threshold it had actually reached."""
        for usd, expected in ((0.29, 29), (1.15, 115), (0.07, 7), (19.99, 1999), (8.20, 820),
                              (0.57, 57), (4.35, 435)):
            self.assertEqual(cost_guard.cents(usd), expected, usd)

    def test_the_classic_floating_point_trap_does_not_bite(self):
        self.assertEqual(cost_guard.cents(0.1) + cost_guard.cents(0.2), cost_guard.cents(0.3))

    def test_a_negative_amount_is_refused(self):
        with self.assertRaises(cost_guard.InvalidRegister):
            cost_guard.cents(-1)

    def test_something_that_is_not_an_amount_is_refused(self):
        for bad in ("10", None, True, [10]):
            with self.assertRaises(cost_guard.InvalidRegister):
                cost_guard.cents(bad)


class TheCapOnRecord(unittest.TestCase):
    """LA-COST-01: the cap exists, and it is the Founder's."""

    def test_a_register_the_founder_approved_is_accepted(self):
        register = a_register()
        self.assertEqual(register.cap_usd, 7.00)
        self.assertEqual(register.period, "month")
        self.assertEqual(register.approved_by, "founder")
        self.assertEqual(register.region, "ap-southeast-2")

    def test_a_cap_nobody_approved_is_not_a_cap(self):
        for who in ("claude", "the builder", "", None):
            with self.assertRaises(cost_guard.InvalidRegister):
                a_register(approved_by=who)

    def test_a_cap_of_zero_is_refused(self):
        with self.assertRaises(cost_guard.InvalidRegister):
            a_register(approved_cap_usd=0)

    def test_the_region_must_be_recorded(self):
        with self.assertRaises(cost_guard.InvalidRegister):
            a_register(region="")

    def test_a_plan_outside_free_and_paid_is_refused(self):
        with self.assertRaises(cost_guard.InvalidRegister):
            a_register(plan="trial")

    def test_another_currency_needs_a_change_note_first(self):
        with self.assertRaises(cost_guard.InvalidRegister):
            a_register(currency="INR")

    def test_days_remaining_must_be_a_whole_number_of_days(self):
        for bad in (-1, 180.5, "181"):
            with self.assertRaises(cost_guard.InvalidRegister):
                a_register(days_remaining=bad)

    def test_the_register_reads_back_as_a_plain_record(self):
        record = a_register().to_dict()
        self.assertEqual(record["approved_cap_usd"], 7.00)
        self.assertEqual(record["plan"], "free")
        self.assertIs(record["verified"], True)

    def test_a_cap_with_no_period_is_refused_because_it_means_nothing(self):
        for bad in ("", None, "year", "forever", "week"):
            with self.assertRaises(cost_guard.InvalidRegister):
                a_register(period=bad)

    def test_the_record_spells_the_cap_out_in_words_so_it_cannot_be_read_as_a_total(self):
        record = a_register().to_dict()
        self.assertEqual(record["period"], "month")
        self.assertEqual(record["cap_reads_as"], "$7.00 per month")

    def test_the_alarm_carries_the_period_too(self):
        self.assertEqual(cost_guard.Guard(a_register()).check_spend(1.00)["period"], "month")


class Verification(unittest.TestCase):
    """LA-COST-04: verified against the Founder's actual account, with a date and how."""

    def test_a_register_with_a_date_and_a_method_counts_as_verified(self):
        self.assertTrue(a_register().is_verified)

    def test_a_claim_with_no_date_is_not_a_verification(self):
        self.assertFalse(a_register(verified_at=None).is_verified)

    def test_a_date_with_no_method_is_not_a_verification_either(self):
        self.assertFalse(a_register(verified_how=None).is_verified)


class TheAlarm(unittest.TestCase):
    """The done-when: an alarm fires on a test threshold."""

    def setUp(self):
        self.guard = cost_guard.Guard(a_register(approved_cap_usd=10.00))

    def test_nothing_fires_below_the_first_threshold(self):
        answer = self.guard.check_spend(4.99)
        self.assertEqual(answer["fired"], [])
        self.assertIs(answer["alarm"], False)
        self.assertIs(answer["over_cap"], False)

    def test_the_first_threshold_fires_exactly_at_it_not_a_cent_later(self):
        self.assertEqual(self.guard.check_spend(5.00)["fired"], [0.50])

    def test_crossing_further_thresholds_fires_the_ones_below_too(self):
        self.assertEqual(self.guard.check_spend(8.00)["fired"], [0.50, 0.80])
        self.assertEqual(self.guard.check_spend(8.00)["highest_fired"], 0.80)

    def test_reaching_the_cap_fires_the_cap_and_counts_as_over(self):
        answer = self.guard.check_spend(10.00)
        self.assertEqual(answer["fired"], [0.50, 0.80, 1.00])
        self.assertIs(answer["over_cap"], True)
        self.assertEqual(answer["headroom_usd"], 0.0)

    def test_past_the_cap_does_not_report_negative_headroom(self):
        self.assertEqual(self.guard.check_spend(15.00)["headroom_usd"], 0.0)

    def test_headroom_is_what_is_actually_left(self):
        self.assertEqual(self.guard.check_spend(3.00)["headroom_usd"], 7.0)

    def test_a_custom_test_threshold_fires_on_its_own_terms(self):
        guard = cost_guard.Guard(a_register(approved_cap_usd=10.00), thresholds=(0.01,))
        self.assertEqual(guard.check_spend(0.10)["fired"], [0.01])
        self.assertEqual(guard.check_spend(0.09)["fired"], [])

    def test_a_threshold_outside_zero_to_one_is_refused(self):
        for bad in ((0,), (1.5,), (-0.5,)):
            with self.assertRaises(cost_guard.InvalidRegister):
                cost_guard.Guard(a_register(), thresholds=bad)

    def test_the_guard_needs_a_real_register(self):
        with self.assertRaises(cost_guard.InvalidRegister):
            cost_guard.Guard({"approved_cap_usd": 100})


class FreePlanReality(unittest.TestCase):
    """On the free plan the thing that runs out is credits and days, not a bill."""

    def test_the_free_plan_reports_what_is_left_and_that_nothing_is_charged(self):
        answer = cost_guard.Guard(a_register()).credits_warning()
        self.assertIs(answer["applies"], True)
        self.assertIs(answer["charged_today"], False)
        self.assertEqual(answer["credits_remaining_usd"], 100.00)
        self.assertEqual(answer["days_remaining"], 181)

    def test_on_a_paid_plan_the_cap_is_the_control_instead(self):
        answer = cost_guard.Guard(a_register(plan="paid")).credits_warning()
        self.assertIs(answer["applies"], False)


class Tags(unittest.TestCase):
    """Rules W3 and W7: every resource says whose it is, and scaffolding says it is scaffolding."""

    def test_a_properly_tagged_resource_passes(self):
        guard = cost_guard.Guard(a_register())
        self.assertEqual(guard.check_tags([
            {"name": "prototype-host", "tags": {"dyson-part": "part1"}},
            {"name": "throwaway-bucket", "tags": {"dyson-part": "part1", "dyson-scaffold": "yes"}},
        ]), [])

    def test_an_untagged_resource_is_reported_as_missing_the_tag(self):
        """Missing is a different fault from wrong, and the message has to say which. Reporting a missing
        tag as if it held a wrong value hides that nobody set it at all."""
        guard = cost_guard.Guard(a_register())
        problems = guard.check_tags([{"name": "mystery-box", "tags": {}}])
        self.assertEqual(len(problems), 1)
        self.assertIn("mystery-box", problems[0])
        self.assertIn("carries no", problems[0])
        self.assertNotIn("None", problems[0])

    def test_a_resource_with_no_tags_key_at_all_is_reported_the_same_way(self):
        guard = cost_guard.Guard(a_register())
        problems = guard.check_tags([{"name": "bare"}])
        self.assertEqual(len(problems), 1)
        self.assertIn("carries no", problems[0])

    def test_a_wrong_part_reads_differently_from_a_missing_one(self):
        guard = cost_guard.Guard(a_register())
        missing = guard.check_tags([{"name": "x", "tags": {}}])[0]
        wrong = guard.check_tags([{"name": "x", "tags": {"dyson-part": "part3"}}])[0]
        self.assertNotEqual(missing, wrong)
        self.assertIn("carries no", missing)
        self.assertIn("part3", wrong)

    def test_a_part_that_does_not_exist_is_reported(self):
        guard = cost_guard.Guard(a_register())
        problems = guard.check_tags([{"name": "odd", "tags": {"dyson-part": "part3"}}])
        self.assertEqual(len(problems), 1)
        self.assertIn("part3", problems[0])

    def test_a_scaffold_tag_with_the_wrong_value_is_reported(self):
        guard = cost_guard.Guard(a_register())
        problems = guard.check_tags([
            {"name": "temp", "tags": {"dyson-part": "part1", "dyson-scaffold": "true"}}])
        self.assertEqual(len(problems), 1)

    def test_every_bad_resource_is_reported_not_just_the_first(self):
        guard = cost_guard.Guard(a_register())
        self.assertEqual(len(guard.check_tags([{"name": "a"}, {"name": "b"}])), 2)


class WhatOnlyTheFounderMayDo(unittest.TestCase):
    """Rule 4, and the two AWS actions that cannot be undone."""

    def setUp(self):
        self.guard = cost_guard.Guard(a_register())

    def test_upgrading_the_plan_is_refused_and_says_it_cannot_be_reversed(self):
        with self.assertRaises(cost_guard.NeedsFounderApproval) as caught:
            self.guard.request("upgrade-plan")
        self.assertIn("cannot be reversed", str(caught.exception))

    def test_activating_advanced_features_is_refused_and_says_what_it_costs(self):
        with self.assertRaises(cost_guard.NeedsFounderApproval) as caught:
            self.guard.request("activate-advanced-features")
        message = str(caught.exception)
        self.assertIn("cannot be reversed", message)
        self.assertIn("spend limit", message)

    def test_every_founder_only_action_is_refused(self):
        for action in ("approve-spend", "raise-cap", "add-payment-method"):
            with self.assertRaises(cost_guard.NeedsFounderApproval):
                self.guard.request(action)

    def test_an_action_the_guard_does_not_know_is_refused_rather_than_let_through(self):
        with self.assertRaises(cost_guard.NeedsFounderApproval):
            self.guard.request("just-this-once")

    def test_the_methods_that_look_like_approval_only_refuse(self):
        for name in ("approve_spend", "raise_cap"):
            with self.assertRaises(cost_guard.NeedsFounderApproval):
                getattr(self.guard, name)(100.00)

    def test_the_module_cannot_reach_aws_or_hold_a_credential(self):
        """Rule 5 holds by construction: there is nothing here to call AWS with."""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "cost_guard.py")
        with open(path) as handle:
            source = handle.read()
        for forbidden in ("import boto3", "import subprocess", "import socket", "import urllib",
                          "import http.client", "os.environ", "AWS_SECRET", "AWS_ACCESS_KEY"):
            self.assertNotIn(forbidden, source, "cost guardrails must not reach AWS: %s" % forbidden)


class BeforePaidDeployment(unittest.TestCase):
    """LA-COST-01: budgets, alarms and explicit spend limits exist before any paid deployment."""

    def test_on_the_free_plan_the_budget_cannot_be_proven_yet_and_it_says_so(self):
        missing = cost_guard.Guard(a_register()).ready_for_paid_deployment()
        self.assertEqual(len(missing), 1)
        self.assertIn("free plan", missing[0])

    def test_an_unverified_register_is_reported_as_missing_the_verification(self):
        missing = cost_guard.Guard(a_register(plan="paid", verified_at=None)).ready_for_paid_deployment()
        self.assertTrue(any("LA-COST-04" in m for m in missing))

    def test_alarms_that_stop_below_the_cap_are_reported(self):
        missing = cost_guard.Guard(a_register(plan="paid"),
                                   thresholds=(0.50, 0.80)).ready_for_paid_deployment()
        self.assertTrue(any("at the cap itself" in m for m in missing))

    def test_a_fully_prepared_paid_account_reports_nothing_missing(self):
        self.assertEqual(cost_guard.Guard(a_register(plan="paid")).ready_for_paid_deployment(), [])


class DoneWhen(unittest.TestCase):
    """The two things P1.01 is done when, end to end."""

    def test_the_cap_is_on_record_with_the_account_it_was_approved_against(self):
        record = a_register().to_dict()
        self.assertEqual(record["approved_by"], "founder")
        self.assertEqual(record["approved_cap_usd"], 7.00)
        self.assertEqual(record["cap_reads_as"], "$7.00 per month")
        self.assertEqual(record["region"], "ap-southeast-2")
        self.assertIs(record["verified"], True)
        self.assertEqual(record["credits_remaining_usd"], 100.00)

    def test_an_alarm_fires_on_a_test_threshold(self):
        """A one percent test threshold on the recorded cap, driven past it and back under it.

        One percent of the $7.00 monthly cap is 7 cents, which is exactly the kind of figure that goes
        wrong when money is held as a float."""
        guard = cost_guard.Guard(a_register(), thresholds=(0.01, 0.50, 1.00))

        quiet = guard.check_spend(0.03)
        self.assertEqual(quiet["fired"], [])
        self.assertIs(quiet["alarm"], False)

        fired = guard.check_spend(0.07)
        self.assertIs(fired["alarm"], True)
        self.assertEqual(fired["fired"], [0.01])
        self.assertEqual(fired["headroom_usd"], 6.93)
        self.assertIs(fired["over_cap"], False)

        at_cap = guard.check_spend(7.00)
        self.assertEqual(at_cap["fired"], [0.01, 0.50, 1.00])
        self.assertIs(at_cap["over_cap"], True)
        self.assertEqual(at_cap["headroom_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
