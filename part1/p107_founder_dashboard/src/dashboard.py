"""Founder Financial Dashboard (J). Package P1.07. Requirements LA-DASH-01 to LA-DASH-05.

J shows the Founder verified financial data, Receptor performance and reconciliation status. It reads. That
is the entire capability.

The thing that makes a dashboard dangerous is a button. Somebody adds one convenient action, and a component
built to be looked at becomes a component that can act, usually without anyone revisiting who may press it.
So J has no action path, and the check for that pins every name in this module and every member of this
class, private ones included. Python has no access control, so a private action path is an action path.

The second danger is quieter. A dashboard that shows something is believed, so a half-answer from a source
must never render as a whole one:

- Every required field of a contract response is read **once**, validated, and the validated value is what
  gets rendered. Never validated through one lookup and emitted through another, because an object can
  answer two lookups differently.
- A timestamp is checked against the calendar, not only against its shape. `9999-99-99T99:99:99.999Z` has
  the right shape and is not a date.
- Every panel has the same keys whether it is available or not, so a caller reading one uniformly cannot
  raise on exactly the failure path. An unavailable panel reports `stale` as true, because unknown freshness
  is not freshness.
- The screen's headline timestamp is the **oldest** panel on it, not the newest. A header has to be true of
  everything under it, and a fresh header over a seven year old panel is the exact lie this component exists
  to avoid.
- Rows are copied all the way down before they are handed out, so a reader cannot reach back into a source's
  own response body.

**The honest limit.** The names below are module globals, so code already running in this process can
reassign `READ_ONLY_METHOD` or extend `FINANCIAL_VIEWS`. That is tampering from inside the process, not a
surface J exposes, and it is written down rather than papered over with a claim that it cannot happen.

Standard library only, and no imports at all. The check for that reads this module's syntax tree and also
pins its entire namespace, because a string search for `import` is defeated by `__builtins__.__import__` and
a syntax tree search for `__import__` as a bare name is defeated by reaching it as an attribute.
"""

# The views J offers, and which source answers each.
FINANCIAL_VIEWS = ("revenue", "payments", "profitability", "receptor-performance", "reconciliation-status")
HEALTH_VIEWS = ("receptor-health", "kpis")

# J reads. This is the only method it ever passes to a source.
READ_ONLY_METHOD = "GET"

# Why a view is not being shown. Machine readable, so a caller is not left parsing prose.
REASON_DEPENDENCY_DOWN = "dependency_down"
REASON_MALFORMED = "malformed_response"
REASON_NOT_WIRED = "not_wired"
REASON_UNVERIFIED = "unverified"

# How many calls J keeps in its own record before dropping the oldest.
CALL_LOG_LIMIT = 500

# Days per month, with February's leap length. Used to check a timestamp against the calendar.
DAYS_IN_MONTH = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

# What J is asked for sometimes, and will not do (LA-DASH-02, LA-DASH-03, N13).
NO_ACTION = {
    "approve": "An approval is the Founder's, made on the Direct Founder Controls, not on a screen that "
               "only shows numbers.",
    "pay": "J has no payment path, and never reaches a bank.",
    "stop": "Emergency STOP is the Founder's red path through the Control Bus. A dashboard button would be "
            "a second, weaker one.",
    "retry_task": "Task state belongs to the Orchestrator. J observes it.",
    "adjust_figure": "The figures come from the Memory and Evidence Layer and are verified there. "
                     "Correcting them on the screen would make the screen disagree with the evidence.",
}


class NoActionPath(Exception):
    """Something tried to act through the dashboard. J has no authority to execute actions (LA-DASH-02)."""


class InvalidView(Exception):
    """A view that does not exist, or arguments that do not match the contract."""


class Dashboard:
    """J. Two sources, both injected, both read only.

    `financial_source` answers DASH-01 and `health_source` answers ESC-02. Each is a callable taking
    `(method, path, params)` and returning the response body. J always passes `GET`.
    """

    def __init__(self, financial_source=None, health_source=None):
        self._financial_source = financial_source
        self._health_source = health_source
        self._calls = []

    @property
    def calls(self):
        """A copy of J's own record of what it asked for, copied all the way down, so nothing can write
        into the record that the no-action check audits."""
        return _copied(self._calls)

    # ------------------------------------------------------------------ DASH-01, the financial views
    def view(self, name, receptor_id=None, period=None):
        """A verified financial view. Never stale, never unverified, never a half answer dressed as whole."""
        if name not in FINANCIAL_VIEWS:
            raise InvalidView("%r is not a financial view. The views are %s."
                              % (name, ", ".join(FINANCIAL_VIEWS)))
        params = self._params(receptor_id=receptor_id, period=period)
        answer, failed = self._read(self._financial_source, "/v1/financial-views/%s" % name, params)
        if failed:
            return _unavailable(name, failed)

        # Read each field once. What is validated is what is rendered.
        rows = _once(answer, "rows")
        as_of = _once(answer, "as_of")
        verified_only = _once(answer, "verified_only")
        held_back = _once(answer, "unverified_excluded")

        if not _is_rows(rows) or not _is_timestamp(as_of):
            return _unavailable(name, REASON_MALFORMED)
        if not _is_count(held_back):
            return _unavailable(name, REASON_MALFORMED)
        if verified_only is not True:
            return _unavailable(name, REASON_UNVERIFIED)
        copied, copyable = _copied_rows(rows)
        if not copyable:
            return _unavailable(name, REASON_MALFORMED)

        return _panel(
            name, rows=copied, as_of=as_of, verified_only=True, unverified_excluded=held_back,
            complete=held_back == 0, stale=None,
            note=None if held_back == 0 else
            "%d row(s) are not shown because they are not verified. This screen is partial." % held_back)

    # ------------------------------------------------------------------ ESC-02, the health views
    def health_view(self, name, receptor_id=None):
        """A health or KPI view from Monitoring. A source that does not say whether its data is stale has
        not answered the question, so J does not guess that it is fresh."""
        if name not in HEALTH_VIEWS:
            raise InvalidView("%r is not a health view. The views are %s." % (name, ", ".join(HEALTH_VIEWS)))
        params = self._params(receptor_id=receptor_id)
        answer, failed = self._read(self._health_source, "/v1/health-views/%s" % name, params)
        if failed:
            return _unavailable(name, failed)

        rows = _once(answer, "rows")
        as_of = _once(answer, "as_of")
        stale = _once(answer, "stale")

        if not _is_rows(rows) or not _is_timestamp(as_of) or not isinstance(stale, bool):
            return _unavailable(name, REASON_MALFORMED)
        copied, copyable = _copied_rows(rows)
        if not copyable:
            return _unavailable(name, REASON_MALFORMED)

        return _panel(
            name, rows=copied, as_of=as_of, verified_only=None, unverified_excluded=None,
            complete=True, stale=stale,
            note="This data is older than its freshness bound. Do not read it as current." if stale
            else None)

    def everything(self, receptor_id=None, period=None):
        """Every view at once, for the screen.

        A source that fails makes its own views unavailable and leaves the others alone, because a dashboard
        that goes blank when one feed drops is less useful than one that says which part is missing. No
        single panel can take the screen down, whatever its source raises.

        `as_of` is the **oldest** available panel, because a headline has to be true of everything beneath
        it. `newest_as_of` is there for anyone who wants the other end.
        """
        screen = {"views": {}, "unavailable": [], "as_of": None, "newest_as_of": None,
                  "complete": True, "stale": False, "authority": "read-only"}
        for name in FINANCIAL_VIEWS:
            screen["views"][name] = self._panel_or_unavailable(self.view, name, receptor_id, period)
        for name in HEALTH_VIEWS:
            screen["views"][name] = self._panel_or_unavailable(self.health_view, name, receptor_id, None)

        stamps = []
        for name in sorted(screen["views"]):
            panel = screen["views"][name]
            if panel["available"]:
                stamps.append(panel["as_of"])
                if panel["stale"]:
                    screen["stale"] = True
            else:
                screen["unavailable"].append(name)
                screen["complete"] = False
                screen["stale"] = True
            if panel["complete"] is False:
                screen["complete"] = False
        if stamps:
            screen["as_of"] = min(stamps)
            screen["newest_as_of"] = max(stamps)
        return screen

    # ------------------------------------------------------------------ what J will not do (N13)
    def approve(self, *_a, **_k):
        raise NoActionPath("J cannot approve. " + NO_ACTION["approve"])

    def pay(self, *_a, **_k):
        raise NoActionPath("J cannot pay. " + NO_ACTION["pay"])

    def stop(self, *_a, **_k):
        raise NoActionPath("J cannot stop anything. " + NO_ACTION["stop"])

    def retry_task(self, *_a, **_k):
        raise NoActionPath("J cannot retry a task. " + NO_ACTION["retry_task"])

    def adjust_figure(self, *_a, **_k):
        raise NoActionPath("J cannot change a figure. " + NO_ACTION["adjust_figure"])

    def act(self, action=None, *_a, **_k):
        """The catch-all. Anything that reaches here is refused, named or not."""
        try:
            known = NO_ACTION.get(action)
        except TypeError:          # an unhashable action is still an action, and still refused
            known = None
        raise NoActionPath(
            "J has no action path at all. %s"
            % (known or "%r is not something a dashboard does. Visibility is not control." % (action,)))

    # ------------------------------------------------------------------ internals
    def _panel_or_unavailable(self, read, name, receptor_id, period):
        """One panel, and no way for it to take the screen down with it."""
        try:
            if period is None:
                return read(name, receptor_id=receptor_id)
            return read(name, receptor_id=receptor_id, period=period)
        except InvalidView:
            raise
        except KeyboardInterrupt:
            raise
        except BaseException:
            return _unavailable(name, REASON_DEPENDENCY_DOWN)

    def _params(self, **kwargs):
        params = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if key == "receptor_id" and not (isinstance(value, str) and value.startswith("rcp_")):
                raise InvalidView("receptor_id must be a string starting with rcp_, not %r." % (value,))
            if key == "period" and not _is_period(value):
                raise InvalidView(
                    "period must read 'YYYY-MM-DD to YYYY-MM-DD', with real dates, not %r." % (value,))
            params[key] = value
        return params

    def _read(self, source, path, params):
        """One read. Always GET.

        Returns `(answer, failure_reason)`. Exactly one of the two is meaningful. Nothing is remembered
        between calls, so a source that stops answering cannot have its last reply served again.

        Everything a source raises is a failure of that source, including the ones that are not `Exception`.
        A cancelled coroutine or a timeout from a green thread is still a source that did not answer, and it
        must not take the screen with it. The one thing re-raised is the person pressing Ctrl-C.
        """
        self._calls.append({"method": READ_ONLY_METHOD, "path": path, "params": _copied(params)})
        del self._calls[:max(len(self._calls) - max(CALL_LOG_LIMIT, 0), 0)]
        if source is None:
            return None, REASON_NOT_WIRED
        try:
            answer = source(READ_ONLY_METHOD, path, params)
        except KeyboardInterrupt:
            raise
        except BaseException:
            return None, REASON_DEPENDENCY_DOWN
        if not isinstance(answer, dict):
            return None, REASON_MALFORMED
        return answer, None


# ---------------------------------------------------------------------- helpers, kept out of the class
# so that the no-action sweep can pin the class's members without having to tell readers from refusals.

def _once(answer, key):
    """One lookup, so a value cannot be validated through `get` and rendered through `__getitem__`.

    A body that fights being read is not data. Whatever it raises, including the things that are not
    `Exception`, the field is simply missing. The one thing re-raised is the person pressing Ctrl-C.
    """
    try:
        return answer[key]
    except KeyboardInterrupt:
        raise
    except BaseException:
        return None


def _copied_rows(rows):
    """Copy the rows, or say it could not be done, for the same reason as `_once`."""
    try:
        return _copied(rows), True
    except KeyboardInterrupt:
        raise
    except BaseException:
        return [], False


def _copied(value):
    """A copy all the way down. A reader cannot reach back into a source's own response body."""
    if isinstance(value, dict):
        return {key: _copied(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copied(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copied(item) for item in value)
    return value


def _is_rows(rows):
    """A list of objects. A list that fights being walked is not one, and must not escape as an exception,
    because `view()` is called directly as well as from behind the screen's guard."""
    if type(rows) is not list:
        return False
    try:
        return all(isinstance(row, dict) for row in rows)
    except KeyboardInterrupt:
        raise
    except BaseException:
        return False


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_date(year, month, day):
    """A real calendar date. Shape is not enough: 9999-99-99 has the right shape."""
    if not 1 <= month <= 12 or day < 1:
        return False
    length = DAYS_IN_MONTH[month - 1]
    if month == 2 and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        length = 28
    return day <= length


def _is_timestamp(value):
    """RFC 3339, UTC, with milliseconds, and a date the calendar actually has: 2026-10-11T16:21:04.512Z.

    Hostile string subclasses are refused rather than allowed to raise, for the same reason as `_is_rows`.
    """
    try:
        return _timestamp_shape(value)
    except KeyboardInterrupt:
        raise
    except BaseException:
        return False


def _timestamp_shape(value):
    if type(value) is not str or len(value) != 24:
        return False
    if (value[4], value[7], value[10], value[13], value[16], value[19], value[23]) != \
            ("-", "-", "T", ":", ":", ".", "Z"):
        return False
    parts = (value[0:4], value[5:7], value[8:10], value[11:13], value[14:16], value[17:19], value[20:23])
    if not all(part.isdigit() and part.isascii() for part in parts):
        return False
    year, month, day, hour, minute, second, _milli = (int(part) for part in parts)
    if not _is_date(year, month, day):
        return False
    return hour <= 23 and minute <= 59 and second <= 59


def _is_period(value):
    """The contract's period: 'YYYY-MM-DD to YYYY-MM-DD', with real dates, the first not after the last."""
    if not isinstance(value, str):
        return False
    halves = value.split(" to ")
    if len(halves) != 2:
        return False
    for half in halves:
        if len(half) != 10 or half[4] != "-" or half[7] != "-":
            return False
        parts = (half[0:4], half[5:7], half[8:10])
        if not all(part.isdigit() and part.isascii() for part in parts):
            return False
        if not _is_date(*(int(part) for part in parts)):
            return False
    return halves[0] <= halves[1]


def _panel(name, rows, as_of, verified_only, unverified_excluded, complete, stale, note):
    """Every panel has these keys, available or not, so a caller reading one uniformly cannot raise on
    exactly the failure path."""
    return {
        "view": name,
        "available": True,
        "reason": None,
        "rows": rows,
        "as_of": as_of,
        "verified_only": verified_only,
        "unverified_excluded": unverified_excluded,
        "complete": complete,
        "stale": stale,
        "note": note,
        "authority": "read-only",
    }


def _unavailable(name, reason):
    """An unavailable panel reports `stale` as true. Unknown freshness is not freshness, and a caller
    reading `panel["stale"]` must not be told that missing data is current."""
    why = {
        REASON_DEPENDENCY_DOWN: "The source did not answer.",
        REASON_MALFORMED: "The source answered with something that does not match the contract, so it "
                          "cannot be trusted as data.",
        REASON_NOT_WIRED: "This dashboard has no source connected for that view. This is a wiring problem "
                          "here, not a fault at the source.",
        REASON_UNVERIFIED: "The source did not confirm the figures are verified. Only verified financial "
                           "data is shown.",
    }[reason]
    panel = _panel(name, rows=[], as_of=None, verified_only=False, unverified_excluded=None,
                   complete=False, stale=True,
                   note="%s The view is unavailable. Nothing older is shown in its place, because old "
                        "figures read as current ones." % why)
    panel["available"] = False
    panel["reason"] = reason
    return panel
