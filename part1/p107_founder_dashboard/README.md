# P1.07 Founder Financial Dashboard (J)

Read-only views of verified financial data, Receptor performance and reconciliation status. J reads. That is
the entire capability.

**Done when:** it runs on test data, and no action path exists. Both are tested end to end in the `DoneWhen`
class.

## Files

| File | What it is |
| --- | --- |
| `src/dashboard.py` | J. Standard library only, and no imports at all |
| `tests/test_dashboard.py` | 76 tests, including N13 and the two "done when" cases |

## Run the tests

```
python3 -m unittest discover -s part1/p107_founder_dashboard/tests -t part1/p107_founder_dashboard/tests
```

## What it will not do

J has no action path. The six methods shaped like one exist only to refuse, and the check for that pins
**every member of the class and every name in the module, private ones included**. Python has no access
control, so a private action path is an action path.

It also imports nothing, which is what actually holds LA-DASH-03. The check reads the module's syntax tree,
looks for every name an import can be reached through, and pins the module's whole namespace, because
whatever a hidden import fetches has to be stored somewhere.

## What it will not pretend

| Situation | What J shows |
| --- | --- |
| A source does not answer | unavailable, with a machine-readable reason. Never the last numbers it gave |
| A source answers a half answer | unavailable. A missing `rows`, `as_of` or count is not a view |
| A source does not confirm the data is verified | unavailable. Unverified money shown as verified is worse than a blank screen |
| A source gives a timestamp the calendar does not have | unavailable. `9999-99-99T99:99:99.999Z` has the right shape and is not a date |
| Nothing is wired to a view | unavailable, and it says the fault is here, not at the source |
| Monitoring says its data is stale | shown, marked stale, with a line saying not to read it as current |
| Financial data, where the contract has no freshness field | `stale` is **not stated**. J has no clock, so claiming freshness would be an assertion with nothing behind it. `as_of` is the only signal, and it is carried truthfully |
| One feed is down | that feed's panels go unavailable. The rest stay up |
| A panel is partial or unavailable | the whole screen says so, and the screen's headline timestamp is the **oldest** panel on it, never the newest |

## How it was checked

All three checks from `CHECKING.md`, three rounds of them. This package is the reason that file exists in
the form it does.

| Round | Check 1 | Check 2 | Check 3 |
| --- | --- | --- | --- |
| 1 | 31 tests pass | 14 of 14 mutations caught | **Failed.** Real defects found |
| 2 | 50 tests pass | 22 of 22 caught, including round 1's attacks | **Failed.** More real defects found |
| 3 | 76 tests pass | 64 of 71 caught, the rest redundant layers | **Requirement met.** Refinements found and fixed |

### What check 3 caught that checks 1 and 2 did not

This is the part worth reading, because checks 1 and 2 were green every single time.

**Round 1.** The test that carried LA-DASH-03, the promise that J cannot reach a network, searched the source
text for the strings `import socket` and friends. A live `urlopen` was added through `importlib` and all 31
tests passed. The N13 sweep used `inspect.isfunction`, which skips properties and classmethods; an acting
`@property` passed the suite. Separately, a source answering without `rows` or `as_of` rendered as a verified,
complete panel.

**Round 2.** The N13 sweep still skipped anything beginning with an underscore. A private `_execute_payment`
that wrote a `POST` into the call record passed all 50 tests and worked from outside. The syntax tree import
check looked for `__import__` as a bare name, so `__builtins__.__import__("socket")` sailed through and the
module held `socket.socket` while the suite stayed green. Three real defects came with it: a field was
validated through one lookup and rendered through another, so an object answering the two differently got an
unvalidated value onto the screen; a `BaseException` from one source took the whole screen down; and
unavailable panels silently dropped `stale`, so a caller reading it got `None`, which reads as "not stale".

**Round 3.** A scoping test asserted inside `for call in source.seen:` with `seen` empty, so it passed
vacuously and hid a regression that would have blamed Monitoring for a bug on this side. `act()` looked its
argument up in a dict before refusing it, so an unhashable action raised `TypeError` out of the component
whose whole job is to refuse. Financial panels hard-coded `stale: False`, asserting a freshness J cannot
know. And a timestamp length check had no too-long case behind it.

Every one of those is now covered by a test that says which hole it closes.

### The three mutations that still survive

Honest about these rather than quiet: removing the guard inside `_is_rows`, the guard inside `_is_timestamp`,
or the guard around a panel changes nothing the tests can see. That is not a gap. Those validators use
`type(x) is list` and `type(x) is str` rather than `isinstance`, so a hostile subclass is rejected before any
guard is reached. The guards are there in case someone later loosens those checks, which is exactly when they
would start to matter.

## Status

| Item | State |
| --- | --- |
| Needs first: gate 8, open item 6 | both closed by the Founder |
| Built against | the contract stubs. No Receptor and no Memory Layer exist yet, so both sources are injected |
| Waiting for Sync (S.02) | the real feeds from Test T0 (2B.07) and the Memory and Evidence Layer (2B.02) |
| N13 | passes here for the first time |
| AMD-3 stage reached | 4, test passed. Not 5, because nothing is deployed |
