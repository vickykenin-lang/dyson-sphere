"""P1.07 done when: it runs on test data, and no action path exists.

N13 first passes here: try to start an action from the dashboard, and find there is no path.

Many of these tests exist because two independent checks defeated earlier versions of this file. Where that
is so, the test says which hole it covers, so nobody reopens it by simplifying the test later.

Run:  python3 -m unittest discover -s part1/p107_founder_dashboard/tests \\
          -t part1/p107_founder_dashboard/tests
"""
import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")))
import dashboard  # noqa: E402

T0 = "rcp_T0RCPA00000000000000000"
OLD = "2019-01-01T00:00:00.000Z"
NOW = "2026-10-14T16:00:00.000Z"
LATER = "2026-10-14T16:30:00.000Z"
SOURCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "dashboard.py")

#: Every key a panel carries, available or not.
PANEL_KEYS = {"view", "available", "reason", "rows", "as_of", "verified_only", "unverified_excluded",
              "complete", "stale", "note", "authority"}

#: So that a test can put a literal None into a body without the helper substituting a default for it.
UNSET = object()


class Source:
    """A stand-in for a source on the other side of a contract call. Synthetic Test T0 data only."""

    def __init__(self, body=None, fail=False, raises=None):
        self.body = body
        self.fail = fail
        self.raises = raises
        self.seen = []

    def __call__(self, method, path, params):
        self.seen.append({"method": method, "path": path, "params": dict(params)})
        if self.raises is not None:
            raise self.raises
        if self.fail:
            raise ConnectionError("dependency_down")
        return self.body


class Cancelled(BaseException):
    """Stands in for asyncio.CancelledError and the green thread timeouts, which are not Exceptions."""


class Hostile(dict):
    """A body that raises something that is not an Exception when a field is read out of it."""

    def __getitem__(self, key):
        if key == "as_of":
            raise Cancelled("cancelled while reading the field")
        return super().__getitem__(key)


class HostileRows(list):
    """A list, so it passes the type check, but it fights being walked."""

    def __iter__(self):
        raise Cancelled("these rows will not be walked")


class HostileStamp(str):
    """A string, so it passes the type check, but it fights being read character by character."""

    def __getitem__(self, index):
        raise Cancelled("this timestamp will not be read")


class UncopyableRow(dict):
    """A row that is a dict, so it passes validation, but fights being copied."""

    def items(self):
        raise Cancelled("this row will not be copied")


class TwoFaced(dict):
    """Answers `get` and `__getitem__` differently. A source could be one of these by accident or design."""

    def __init__(self, body, key, shown):
        super().__init__(body)
        self._key = key
        self._shown = shown

    def __getitem__(self, key):
        if key == self._key:
            return self._shown
        return super().__getitem__(key)


def money(rows=UNSET, excluded=0, verified=True, as_of=NOW, **extra):
    body = {"rows": [{"amount_usd": 120.00, "receptor_id": T0}] if rows is UNSET else rows,
            "verified_only": verified, "as_of": as_of, "unverified_excluded": excluded}
    body.update(extra)
    return body


def health(rows=UNSET, stale=False, as_of=NOW, **extra):
    body = {"rows": [{"receptor_id": T0, "status": "healthy"}] if rows is UNSET else rows,
            "as_of": as_of, "stale": stale}
    body.update(extra)
    return body


def board(financial=None, health_source=None):
    return dashboard.Dashboard(financial_source=financial, health_source=health_source)


class FinancialViews(unittest.TestCase):
    """DASH-01: verified financial data, read only."""

    def test_each_of_the_five_views_asks_for_itself_and_comes_back_with_its_rows(self):
        for name in dashboard.FINANCIAL_VIEWS:
            source = Source(money())
            panel = board(financial=source).view(name)
            self.assertIs(panel["available"], True, name)
            self.assertEqual(panel["rows"], [{"amount_usd": 120.00, "receptor_id": T0}], name)
            self.assertEqual(source.seen[0]["path"], "/v1/financial-views/%s" % name)

    def test_a_view_that_does_not_exist_is_refused(self):
        with self.assertRaises(dashboard.InvalidView):
            board(financial=Source(money())).view("everything")

    def test_the_view_states_that_it_carries_no_authority(self):
        self.assertEqual(board(financial=Source(money())).view("revenue")["authority"], "read-only")

    def test_the_timestamp_from_the_source_is_carried_through(self):
        self.assertEqual(board(financial=Source(money(as_of=LATER))).view("revenue")["as_of"], LATER)

    def test_the_panel_says_the_data_is_verified(self):
        self.assertIs(board(financial=Source(money())).view("revenue")["verified_only"], True)

    def test_a_receptor_id_that_is_not_one_is_refused(self):
        with self.assertRaises(dashboard.InvalidView):
            board(financial=Source(money())).view("revenue", receptor_id="T0")

    def test_the_scope_reaches_the_source_as_the_contract_says(self):
        source = Source(money())
        board(financial=source).view("payments", receptor_id=T0, period="2026-10-01 to 2026-10-14")
        self.assertEqual(source.seen[0]["params"],
                         {"receptor_id": T0, "period": "2026-10-01 to 2026-10-14"})

    def test_arguments_that_were_not_given_are_not_invented(self):
        source = Source(money())
        board(financial=source).view("revenue")
        self.assertEqual(source.seen[0]["params"], {})


class HealthViews(unittest.TestCase):
    """ESC-02. Under-tested once; these cover the same ground as the financial views."""

    def test_both_health_views_ask_for_themselves_on_the_contract_path(self):
        for name in dashboard.HEALTH_VIEWS:
            source = Source(health())
            panel = board(health_source=source).health_view(name)
            self.assertIs(panel["available"], True, name)
            self.assertEqual(source.seen[0]["path"], "/v1/health-views/%s" % name)

    def test_the_health_rows_actually_carry_the_source_data(self):
        """Covers a hole: nothing asserted health rows at all, so returning [] every time passed."""
        rows = [{"receptor_id": T0, "status": "degraded", "consecutive_bad": 2}]
        panel = board(health_source=Source(health(rows=rows))).health_view("receptor-health")
        self.assertEqual(panel["rows"], rows)

    def test_the_health_panel_carries_its_timestamp_and_its_authority(self):
        panel = board(health_source=Source(health(as_of=LATER))).health_view("kpis")
        self.assertEqual(panel["as_of"], LATER)
        self.assertEqual(panel["authority"], "read-only")

    def test_the_health_view_scope_reaches_the_source(self):
        source = Source(health())
        board(health_source=source).health_view("kpis", receptor_id=T0)
        self.assertEqual(source.seen[0]["params"], {"receptor_id": T0})

    def test_a_half_answer_from_monitoring_is_refused_too(self):
        """Covers a hole: only the financial path validated rows and as_of."""
        for missing in ("rows", "as_of", "stale"):
            body = health()
            del body[missing]
            panel = board(health_source=Source(body)).health_view("kpis")
            self.assertIs(panel["available"], False, missing)
            self.assertEqual(panel["reason"], dashboard.REASON_MALFORMED, missing)

    def test_health_rows_that_are_not_a_list_of_objects_are_refused(self):
        for bad in ("abc", 42, {"a": 1}, [1, 2], None):
            panel = board(health_source=Source(health(rows=bad))).health_view("kpis")
            self.assertIs(panel["available"], False, bad)

    def test_a_health_timestamp_that_is_not_one_is_refused(self):
        for bad in ("2026-10-14", "yesterday", None, 1760000000):
            panel = board(health_source=Source(health(as_of=bad))).health_view("kpis")
            self.assertIs(panel["available"], False, bad)

    def test_stale_data_is_marked_stale_and_says_not_to_read_it_as_current(self):
        panel = board(health_source=Source(health(stale=True))).health_view("receptor-health")
        self.assertIs(panel["stale"], True)
        self.assertIn("not", panel["note"])

    def test_fresh_data_carries_no_warning(self):
        panel = board(health_source=Source(health(stale=False))).health_view("kpis")
        self.assertIs(panel["stale"], False)
        self.assertIsNone(panel["note"])

    def test_an_unknown_health_view_is_refused(self):
        with self.assertRaises(dashboard.InvalidView):
            board(health_source=Source(health())).health_view("everything")


class RefusingToMislead(unittest.TestCase):
    """A dashboard that misleads is worse than one that is blank."""

    def test_a_source_that_is_down_makes_the_view_unavailable_not_stale(self):
        panel = board(financial=Source(fail=True)).view("revenue")
        self.assertIs(panel["available"], False)
        self.assertEqual(panel["reason"], dashboard.REASON_DEPENDENCY_DOWN)
        self.assertEqual(panel["rows"], [])
        self.assertIsNone(panel["as_of"])

    def test_a_source_that_is_down_never_shows_what_it_said_last_time(self):
        source = Source(money())
        screen = board(financial=source)
        self.assertEqual(screen.view("revenue")["rows"], [{"amount_usd": 120.00, "receptor_id": T0}])
        source.fail = True
        self.assertEqual(screen.view("revenue")["rows"], [])

    def test_unverified_data_is_refused_rather_than_shown_as_verified(self):
        for bad in (False, None, "yes", 1):
            panel = board(financial=Source(money(verified=bad))).view("revenue")
            self.assertIs(panel["available"], False, bad)
            self.assertEqual(panel["reason"], dashboard.REASON_UNVERIFIED, bad)

    def test_a_half_answer_is_not_rendered_as_a_whole_one(self):
        for missing in ("rows", "as_of", "unverified_excluded", "verified_only"):
            body = money()
            del body[missing]
            panel = board(financial=Source(body)).view("revenue")
            self.assertIs(panel["available"], False, missing)

    def test_rows_that_are_not_a_list_of_objects_are_refused(self):
        for bad in ("abc", 42, {"amount": 1}, [1, 2, 3], [{"ok": True}, "nope"], None):
            self.assertIs(board(financial=Source(money(rows=bad))).view("revenue")["available"], False, bad)

    def test_a_count_that_is_not_a_whole_number_is_refused_and_does_not_crash_the_screen(self):
        for bad in ("3", 1.5, -1, True, None):
            panel = board(financial=Source(money(excluded=bad))).view("revenue")
            self.assertIs(panel["available"], False, bad)
            self.assertEqual(panel["reason"], dashboard.REASON_MALFORMED, bad)

    def test_a_single_view_survives_a_source_raising_something_that_is_not_an_exception(self):
        """Covers a hole: the containment was only exercised through everything(), so making the read
        catch Exception rather than BaseException passed the whole suite while a direct view() call would
        have raised straight out at the caller."""
        panel = board(financial=Source(raises=Cancelled("cancelled"))).view("revenue")
        self.assertIs(panel["available"], False)
        self.assertEqual(panel["reason"], dashboard.REASON_DEPENDENCY_DOWN)

        panel = board(health_source=Source(raises=Cancelled("cancelled"))).health_view("kpis")
        self.assertIs(panel["available"], False)

    def test_a_body_that_raises_while_being_read_does_not_escape_either(self):
        """The read itself succeeded, so this is caught where the field is read, not at the source."""
        panel = board(financial=Source(Hostile(money()))).view("revenue")
        self.assertIs(panel["available"], False)

        screen = board(financial=Source(Hostile(money())), health_source=Source(health())).everything()
        self.assertIs(screen["views"]["revenue"]["available"], False)
        self.assertIs(screen["views"]["kpis"]["available"], True)

    def test_rows_that_fight_being_walked_do_not_escape_a_direct_view_call(self):
        """Covers a hole: validation sat outside every guard, so a list subclass whose __iter__ raises
        propagated straight out of view(), which is called directly and not only from behind the screen."""
        for body, read in ((money(rows=HostileRows([{"a": 1}])), "view"),
                           (health(rows=HostileRows([{"a": 1}])), "health_view")):
            source = Source(body)
            screen = board(financial=source, health_source=source)
            panel = getattr(screen, read)("revenue" if read == "view" else "kpis")
            self.assertIs(panel["available"], False)
            self.assertEqual(panel["reason"], dashboard.REASON_MALFORMED)

    def test_a_timestamp_that_fights_being_read_does_not_escape_either(self):
        panel = board(financial=Source(money(as_of=HostileStamp("x" * 24)))).view("revenue")
        self.assertIs(panel["available"], False)

    def test_a_timestamp_with_the_right_prefix_but_extra_on_the_end_is_refused(self):
        """Covers a hole: no test used a too-long stamp, so a length check of < 24 instead of != 24
        rendered "2026-10-14T16:00:00.000Z EXTRA" as the panel's timestamp."""
        for bad in (NOW + " EXTRA", NOW + "Z", NOW + "\n"):
            self.assertIs(board(financial=Source(money(as_of=bad))).view("revenue")["available"],
                          False, bad)

    def test_a_financial_panel_does_not_claim_a_freshness_it_cannot_know(self):
        """DASH-01 carries no stale field and J has no clock, so stale is not stated for money. Saying
        False would be an assertion with nothing behind it; as_of is the only freshness signal there is."""
        panel = board(financial=Source(money(as_of=OLD))).view("revenue")
        self.assertIs(panel["available"], True)
        self.assertIsNone(panel["stale"])
        self.assertEqual(panel["as_of"], OLD)

    def test_a_row_that_cannot_be_copied_makes_the_panel_unavailable(self):
        """Covers a hole: a row can pass the is-a-dict check and still fight being copied, and nothing
        exercised that, so dropping the copy guard passed the whole suite."""
        body = money(rows=[UncopyableRow({"receptor_id": T0})])
        panel = board(financial=Source(body)).view("revenue")
        self.assertIs(panel["available"], False)
        self.assertEqual(panel["reason"], dashboard.REASON_MALFORMED)

        panel = board(health_source=Source(health(rows=[UncopyableRow({"receptor_id": T0})]))) \
            .health_view("kpis")
        self.assertIs(panel["available"], False)

        screen = board(financial=Source(body), health_source=Source(health())).everything()
        self.assertIs(screen["views"]["revenue"]["available"], False)
        self.assertIs(screen["views"]["kpis"]["available"], True)

    def test_a_source_that_answers_one_way_and_renders_another_is_caught(self):
        """Covers a real defect: a field was validated through `get` and then read again through
        `__getitem__`, so an object answering the two differently rendered an unvalidated value."""
        body = TwoFaced(money(), "as_of", "THERE IS NO TIMESTAMP")
        panel = board(financial=Source(body)).view("revenue")
        self.assertNotEqual(panel["as_of"], "THERE IS NO TIMESTAMP")
        self.assertIs(panel["available"], False)

        body = TwoFaced(health(), "as_of", None)
        panel = board(health_source=Source(body)).health_view("kpis")
        self.assertIs(panel["available"], False)

    def test_a_timestamp_the_calendar_does_not_have_is_refused(self):
        """Covers a real defect: the check was shape only, so 9999-99-99 passed and then became the
        headline timestamp for the whole screen."""
        for bad in ("9999-99-99T99:99:99.999Z", "0000-00-00T00:00:00.000Z", "2026-13-01T00:00:00.000Z",
                    "2026-02-30T00:00:00.000Z", "2026-00-10T00:00:00.000Z", "2026-10-32T00:00:00.000Z",
                    "2026-10-14T24:00:00.000Z", "2026-10-14T00:60:00.000Z", "2026-10-14T00:00:60.000Z",
                    "2025-02-29T00:00:00.000Z"):
            self.assertIs(board(financial=Source(money(as_of=bad))).view("revenue")["available"],
                          False, bad)

    def test_real_timestamps_including_leap_days_are_accepted(self):
        for good in (NOW, OLD, "2024-02-29T23:59:59.999Z", "2000-02-29T00:00:00.000Z",
                     "2026-12-31T23:59:59.000Z"):
            self.assertIs(board(financial=Source(money(as_of=good))).view("revenue")["available"],
                          True, good)

    def test_a_timestamp_of_the_wrong_shape_is_refused(self):
        for bad in ("2026-10-14", "2026-10-14T16:00:00Z", "2026/10/14T16:00:00.000Z",
                    "2026-10-14 16:00:00.000Z", "2026-10-14T16:00:00.000+", "", None, 1760000000,
                    "2026-10-14T16:00:00.0O0Z", "٢٠٢٦-١٠-١٤T١٦:٠٠:٠٠.٠٠٠Z"):
            self.assertIs(board(financial=Source(money(as_of=bad))).view("revenue")["available"],
                          False, bad)

    def test_rows_held_back_for_want_of_verification_are_counted_and_said_out_loud(self):
        panel = board(financial=Source(money(excluded=3))).view("reconciliation-status")
        self.assertEqual(panel["unverified_excluded"], 3)
        self.assertIs(panel["complete"], False)
        self.assertIn("partial", panel["note"])

    def test_a_complete_view_says_so_without_a_warning(self):
        panel = board(financial=Source(money(excluded=0))).view("revenue")
        self.assertIs(panel["complete"], True)
        self.assertIsNone(panel["note"])

    def test_an_empty_view_is_not_the_same_as_an_unavailable_one(self):
        panel = board(financial=Source(money(rows=[]))).view("payments")
        self.assertIs(panel["available"], True)
        self.assertEqual(panel["rows"], [])

    def test_a_source_that_answers_with_nonsense_is_treated_as_malformed(self):
        for rubbish in ("ok", 42, None, [1, 2]):
            panel = board(financial=Source(rubbish)).view("revenue")
            self.assertIs(panel["available"], False, rubbish)
            self.assertEqual(panel["reason"], dashboard.REASON_MALFORMED, rubbish)

    def test_a_dashboard_that_was_never_wired_blames_itself_not_the_source(self):
        panel = board().view("revenue")
        self.assertEqual(panel["reason"], dashboard.REASON_NOT_WIRED)
        self.assertIn("wiring problem here", panel["note"])

    def test_every_panel_has_every_key_available_or_not(self):
        """Covers a real defect: unavailable panels dropped verified_only, complete and stale, so a caller
        reading panel["stale"] got None on a down feed, which reads as 'not stale'."""
        panels = [
            board(financial=Source(money())).view("revenue"),
            board(financial=Source(fail=True)).view("revenue"),
            board(financial=Source(money(verified=False))).view("revenue"),
            board(financial=Source(money(rows="abc"))).view("revenue"),
            board().view("revenue"),
            board(health_source=Source(health())).health_view("kpis"),
            board(health_source=Source(fail=True)).health_view("kpis"),
            board().health_view("kpis"),
        ]
        for panel in panels:
            self.assertEqual(set(panel), PANEL_KEYS, panel.get("view"))

    def test_an_unavailable_panel_reports_itself_as_stale_not_as_fresh(self):
        for panel in (board(financial=Source(fail=True)).view("revenue"),
                      board(health_source=Source(fail=True)).health_view("kpis"),
                      board().view("payments")):
            self.assertIs(panel["stale"], True, panel["view"])
            self.assertIs(panel["complete"], False, panel["view"])

    def test_the_copy_reaches_through_tuples_as_well_as_lists_and_objects(self):
        body = money(rows=[{"receptor_id": T0, "pair": ({"inner": "original"},)}])
        panel = board(financial=Source(body)).view("revenue")
        panel["rows"][0]["pair"][0]["inner"] = "TAMPERED"
        self.assertEqual(body["rows"][0]["pair"][0]["inner"], "original")

    def test_the_rows_handed_out_cannot_be_used_to_reach_back_into_the_source(self):
        """Covers a real defect: the copy was one level deep, so writing into a nested value changed the
        source's own response body."""
        body = money(rows=[{"receptor_id": T0, "detail": {"note": "original"}}])
        panel = board(financial=Source(body)).view("revenue")
        panel["rows"][0]["detail"]["note"] = "TAMPERED"
        panel["rows"][0]["receptor_id"] = "TAMPERED"
        self.assertEqual(body["rows"][0]["detail"]["note"], "original")
        self.assertEqual(body["rows"][0]["receptor_id"], T0)


class ThePeriod(unittest.TestCase):
    """The contract says 'YYYY-MM-DD to YYYY-MM-DD'. receptor_id is checked, so period is too."""

    def test_a_period_in_the_contract_format_is_accepted(self):
        source = Source(money())
        board(financial=source).view("revenue", period="2026-10-01 to 2026-10-14")
        self.assertEqual(source.seen[0]["params"]["period"], "2026-10-01 to 2026-10-14")

    def test_a_period_that_is_not_in_the_contract_format_is_refused(self):
        for bad in ("whenever", "2026-10-01", "2026-10-01..2026-10-14", "2026-10-01 to 2026-13-01",
                    "2026-10-14 to 2026-10-01", {"from": "2026-10-01"}, 20261001,
                    "2026-10-01 to 2026-10-14 to 2026-10-20", ""):
            with self.assertRaises(dashboard.InvalidView, msg=repr(bad)):
                board(financial=Source(money())).view("revenue", period=bad)


class TheWholeScreen(unittest.TestCase):
    """everything(): one failing feed does not blank the rest, and the header is true of what is under it."""

    def test_monitoring_being_down_does_not_blank_the_financial_views(self):
        screen = board(financial=Source(money()), health_source=Source(fail=True)).everything()
        self.assertEqual(sorted(screen["unavailable"]), sorted(dashboard.HEALTH_VIEWS))
        self.assertIs(screen["views"]["revenue"]["available"], True)

    def test_the_money_being_down_does_not_blank_the_health_views(self):
        screen = board(financial=Source(fail=True), health_source=Source(health())).everything()
        self.assertEqual(sorted(screen["unavailable"]), sorted(dashboard.FINANCIAL_VIEWS))
        self.assertIs(screen["views"]["kpis"]["available"], True)

    def test_a_source_raising_something_that_is_not_an_exception_does_not_blank_the_screen(self):
        """Covers a real defect: a cancelled coroutine or a green thread timeout is a BaseException, and
        it used to propagate out of everything(), losing all seven panels instead of five."""
        screen = board(financial=Source(raises=Cancelled("cancelled")),
                       health_source=Source(health())).everything()
        self.assertEqual(sorted(screen["unavailable"]), sorted(dashboard.FINANCIAL_VIEWS))
        self.assertIs(screen["views"]["kpis"]["available"], True)

    def test_a_single_panel_can_never_take_the_whole_screen_down(self):
        for raised in (Cancelled("cancelled"), SystemExit(1), MemoryError(), RecursionError(),
                       ValueError("odd")):
            screen = board(financial=Source(raises=raised), health_source=Source(health())).everything()
            self.assertIs(screen["views"]["kpis"]["available"], True, raised)
            self.assertIs(screen["views"]["revenue"]["available"], False, raised)

    def test_unverified_money_makes_that_panel_unavailable_without_raising(self):
        screen = board(financial=Source(money(verified=False)), health_source=Source(health())).everything()
        self.assertIs(screen["views"]["revenue"]["available"], False)
        self.assertIs(screen["views"]["kpis"]["available"], True)

    def test_the_headline_timestamp_is_the_oldest_panel_not_the_newest(self):
        """Covers a real defect: the header took the newest panel, so a seven year old panel sat under a
        header that said half an hour."""
        screen = board(financial=Source(money(as_of=OLD)), health_source=Source(health(as_of=LATER))) \
            .everything()
        self.assertEqual(screen["as_of"], OLD)
        self.assertEqual(screen["newest_as_of"], LATER)

    def test_a_total_blackout_has_no_timestamp_at_all(self):
        screen = board(financial=Source(fail=True), health_source=Source(fail=True)).everything()
        self.assertIsNone(screen["as_of"])
        self.assertIsNone(screen["newest_as_of"])
        self.assertIs(screen["complete"], False)
        self.assertIs(screen["stale"], True)

    def test_a_partial_panel_makes_the_whole_screen_incomplete(self):
        screen = board(financial=Source(money(excluded=2)), health_source=Source(health())).everything()
        self.assertIs(screen["complete"], False)

    def test_one_stale_panel_makes_the_screen_stale(self):
        screen = board(financial=Source(money()), health_source=Source(health(stale=True))).everything()
        self.assertIs(screen["stale"], True)

    def test_the_whole_screen_can_be_scoped_to_one_receptor_and_a_period(self):
        financial, health_source = Source(money()), Source(health())
        board(financial=financial, health_source=health_source) \
            .everything(receptor_id=T0, period="2026-10-01 to 2026-10-14")
        self.assertEqual(len(financial.seen), len(dashboard.FINANCIAL_VIEWS))
        self.assertEqual(len(health_source.seen), len(dashboard.HEALTH_VIEWS))
        for call in financial.seen:
            self.assertEqual(call["params"], {"receptor_id": T0, "period": "2026-10-01 to 2026-10-14"})
        for call in health_source.seen:
            self.assertEqual(call["params"], {"receptor_id": T0})

    def test_bad_caller_input_is_reported_as_bad_input_not_as_the_sources_being_down(self):
        """Covers a hole: nothing pinned the re-raise, so dropping it turned a caller's own mistake into
        seven panels blaming the sources."""
        screen = board(financial=Source(money()), health_source=Source(health()))
        with self.assertRaises(dashboard.InvalidView):
            screen.everything(receptor_id="T0")
        with self.assertRaises(dashboard.InvalidView):
            screen.everything(period="whenever")

    def test_a_screen_with_everything_working_says_it_is_complete_and_fresh(self):
        screen = board(financial=Source(money()), health_source=Source(health())).everything()
        self.assertIs(screen["complete"], True)
        self.assertIs(screen["stale"], False)
        self.assertEqual(screen["unavailable"], [])


class N13NoActionPath(unittest.TestCase):
    """N13: try to start an action from the dashboard. Expected: no action path exists."""

    #: Every member of Dashboard, private ones included. Python has no access control, so a private action
    #: path is an action path. A member not in one of these sets fails the sweep below.
    READS = {"view", "health_view", "everything", "calls"}
    REFUSALS = {"approve", "pay", "stop", "retry_task", "adjust_figure", "act"}
    INTERNALS = {"_panel_or_unavailable", "_params", "_read"}

    #: Every name the module defines. Pinned so a module-level action, or a reached-for module object such
    #: as `socket.socket`, cannot be added without failing here.
    MODULE_NAMES = {
        "FINANCIAL_VIEWS", "HEALTH_VIEWS", "READ_ONLY_METHOD", "CALL_LOG_LIMIT", "DAYS_IN_MONTH",
        "NO_ACTION", "REASON_DEPENDENCY_DOWN", "REASON_MALFORMED", "REASON_NOT_WIRED", "REASON_UNVERIFIED",
        "NoActionPath", "InvalidView", "Dashboard",
        "_once", "_copied", "_copied_rows", "_is_rows", "_timestamp_shape", "_is_count", "_is_date", "_is_timestamp", "_is_period",
        "_panel", "_unavailable",
    }

    def setUp(self):
        self.board = board(financial=Source(money()), health_source=Source(health()))

    def test_every_action_shaped_method_only_refuses(self):
        for name in sorted(self.REFUSALS):
            with self.assertRaises(dashboard.NoActionPath):
                getattr(self.board, name)()

    def test_the_catch_all_refuses_an_action_nobody_thought_of(self):
        for action in ("transfer", "delete_everything", "", None, 7):
            with self.assertRaises(dashboard.NoActionPath):
                self.board.act(action)

    def test_the_refusal_says_visibility_is_not_control(self):
        with self.assertRaises(dashboard.NoActionPath) as caught:
            self.board.act("transfer")
        self.assertIn("Visibility is not control", str(caught.exception))

    def test_the_whole_class_surface_is_pinned_private_members_included(self):
        """The real N13.

        An earlier sweep skipped anything starting with an underscore. An independent check added
        `_execute_payment`, which wrote a POST into the call record and worked from outside, and all fifty
        tests passed. Python has no access control, so there is no such thing as a private action path.
        """
        members = {name for name in vars(dashboard.Dashboard)
                   if not (name.startswith("__") and name.endswith("__"))}
        self.assertEqual(members, self.READS | self.REFUSALS | self.INTERNALS,
                         "the surface of Dashboard changed. Classify the new member before updating this.")

    def test_the_whole_module_surface_is_pinned_too(self):
        """An earlier sweep pinned the class but not the module. A module-level `execute_payment` survived
        the suite, and so did `BANK_REACH = socket.socket` reached through `__builtins__.__import__`."""
        names = {name for name in vars(dashboard)
                 if not (name.startswith("__") and name.endswith("__"))}
        self.assertEqual(names, self.MODULE_NAMES,
                         "the module's namespace changed. Anything new must be classified first.")

    def test_nothing_outside_the_reads_can_be_touched_without_being_refused(self):
        for name in sorted(self.REFUSALS):
            with self.assertRaises(dashboard.NoActionPath, msg="%s is not a refusal" % name):
                getattr(self.board, name)()

    def test_the_module_holds_no_module_object_and_nothing_callable_it_should_not(self):
        """Whatever route an import took, the thing it fetched has to live somewhere. This looks for it."""
        for name, value in vars(dashboard).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            self.assertFalse(type(value).__name__ == "module", "%s is a module object" % name)
            self.assertIn(name, self.MODULE_NAMES, name)

    def test_j_only_ever_reads_and_never_passes_another_verb(self):
        self.board.everything()
        for name in dashboard.FINANCIAL_VIEWS:
            self.board.view(name, receptor_id=T0)
        for name in dashboard.HEALTH_VIEWS:
            self.board.health_view(name, receptor_id=T0)
        self.assertTrue(self.board.calls)
        for call in self.board.calls:
            self.assertEqual(call["method"], "GET", call)

    def test_the_sources_themselves_saw_nothing_but_reads(self):
        financial, health_source = Source(money()), Source(health())
        board(financial=financial, health_source=health_source).everything()
        self.assertEqual(len(financial.seen) + len(health_source.seen),
                         len(dashboard.FINANCIAL_VIEWS) + len(dashboard.HEALTH_VIEWS))
        for source in (financial, health_source):
            self.assertTrue(source.seen)
            for call in source.seen:
                self.assertEqual(call["method"], "GET", call)

    def test_a_view_name_cannot_be_used_to_reach_another_path(self):
        for attempt in ("../../v1/payments", "revenue/../../pay", "revenue\nPOST /v1/pay", "revenue "):
            with self.assertRaises(dashboard.InvalidView, msg=attempt):
                self.board.view(attempt)

    def test_the_record_of_calls_cannot_be_written_into_from_outside(self):
        self.board.view("revenue")
        record = self.board.calls
        record.append({"method": "POST", "path": "/v1/pay", "params": {}})
        record[0]["method"] = "DELETE"
        record[0]["params"]["injected"] = True
        self.assertTrue(all(call["method"] == "GET" for call in self.board.calls))
        self.assertEqual(len(self.board.calls), 1)

    def test_a_limit_of_zero_does_not_invert_into_keeping_everything(self):
        """Covers a latent trap: del list[:-0] is the empty slice, so a limit of zero kept every call."""
        original = dashboard.CALL_LOG_LIMIT
        try:
            dashboard.CALL_LOG_LIMIT = 0
            for _ in range(5):
                self.board.view("revenue")
            self.assertEqual(self.board.calls, [])
        finally:
            dashboard.CALL_LOG_LIMIT = original

    def test_an_unhashable_action_is_refused_like_any_other(self):
        """Covers a real defect: the catch-all looked the action up in a dict before refusing it, so an
        unhashable one raised TypeError instead of NoActionPath, and a caller catching NoActionPath got an
        uncaught error from the component that claims to refuse everything."""
        for action in ([], {}, set(), bytearray(b"pay"), {"do": "pay"}):
            with self.assertRaises(dashboard.NoActionPath, msg=repr(action)):
                self.board.act(action)

    def test_the_record_of_calls_does_not_grow_without_limit(self):
        for _ in range(dashboard.CALL_LOG_LIMIT + 50):
            self.board.view("revenue")
        self.assertEqual(len(self.board.calls), dashboard.CALL_LOG_LIMIT)

    def test_the_module_imports_nothing_by_any_route(self):
        """LA-DASH-03.

        A string search for "import socket" was defeated by `importlib`. A syntax tree search for
        `__import__` as a bare name was defeated by `__builtins__.__import__`, which is an attribute call.
        This looks for the import statements, for any mention of the names an import can be reached
        through, and the namespace pin above catches whatever such a call would have to store.
        """
        with open(SOURCE_PATH) as handle:
            tree = ast.parse(handle.read())
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertEqual(imports, [], "the dashboard must import nothing")

        reached = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                reached.add(node.id)
            elif isinstance(node, ast.Attribute):
                reached.add(node.attr)
        for forbidden in ("__import__", "__builtins__", "__loader__", "importlib", "eval", "exec",
                          "compile", "open", "globals", "vars", "load_module", "import_module"):
            self.assertNotIn(forbidden, reached, "the dashboard must not reach %s" % forbidden)

    def test_the_module_names_nothing_that_belongs_to_a_bank(self):
        with open(SOURCE_PATH) as handle:
            source = handle.read().lower()
        for banking in ("iban", "swift_", "account_number", "routing_number", "sort_code"):
            self.assertNotIn(banking, source, "J never connects to the bank: %s" % banking)


class DoneWhen(unittest.TestCase):
    """The two things P1.07 is done when."""

    def test_it_runs_on_test_data(self):
        """Synthetic Test T0 figures through every panel on the screen."""
        screen = board(
            financial=Source(money(rows=[{"receptor_id": T0, "amount_usd": 120.00, "reconciled": True}],
                                   excluded=1)),
            health_source=Source(health())).everything()

        self.assertEqual(screen["unavailable"], [])
        self.assertEqual(len(screen["views"]), len(dashboard.FINANCIAL_VIEWS) + len(dashboard.HEALTH_VIEWS))
        self.assertEqual(screen["views"]["revenue"]["rows"][0]["amount_usd"], 120.00)
        self.assertEqual(screen["views"]["revenue"]["unverified_excluded"], 1)
        self.assertIs(screen["views"]["revenue"]["complete"], False)
        self.assertIs(screen["views"]["revenue"]["verified_only"], True)
        self.assertEqual(screen["views"]["revenue"]["as_of"], NOW)
        self.assertIs(screen["views"]["receptor-health"]["available"], True)
        self.assertEqual(screen["as_of"], NOW)
        self.assertIs(screen["complete"], False)
        self.assertEqual(screen["authority"], "read-only")

    def test_no_action_path_exists(self):
        screen = board(financial=Source(money()), health_source=Source(health()))
        for attempt in ("approve", "pay", "stop", "retry_task", "adjust_figure", "transfer", "anything"):
            with self.assertRaises(dashboard.NoActionPath):
                screen.act(attempt)
        screen.everything()
        self.assertTrue(all(call["method"] == "GET" for call in screen.calls))


if __name__ == "__main__":
    unittest.main()
