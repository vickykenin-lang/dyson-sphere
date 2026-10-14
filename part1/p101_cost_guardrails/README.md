# P1.01 Cost guardrails

The cap on record, the alarm that says when spend has crossed a threshold, and the refusal of everything only
the Founder may do.

`COST_REGISTER.md` is the record itself: what the Founder approved, and what was actually read in his AWS
account on 14 Oct 2026. Read that first.

## Files

| File | What it is |
| --- | --- |
| `COST_REGISTER.md` | The cap, the verified account facts, and what is still open |
| `src/cost_guard.py` | The register, the alarm and the refusals. Standard library only |
| `tests/test_cost_guard.py` | 50 tests, including the two "done when" cases |

## Run the tests

```
python3 -m unittest discover -s part1/p101_cost_guardrails/tests -t part1/p101_cost_guardrails/tests
```

## What it will not do

There is no credential here, no `boto3`, and no network call of any kind, and a test reads the module's own
source to keep it that way. Rule 5 says the Founder enters credentials and the AI never opens one; this
module holds to that by having nothing to open.

It also refuses, rather than performs, every action that is the Founder's: approving spend, raising the cap,
adding a payment method, upgrading the AWS plan, and activating advanced AWS features. The last two cannot be
undone, and the refusal says so.

## How it was checked

50 tests pass. Beyond that, the implementation was deliberately broken eighteen ways and the tests re-run:

| What was broken | Caught |
| --- | --- |
| The period was dropped, so $7 could read as a total rather than a rate | yes, after a fix |
| A threshold fired only above itself, never exactly at it | yes |
| `over_cap` only counted past the cap, not at it | yes |
| Headroom was allowed to go negative | yes |
| Anyone could approve the cap, not only the Founder | yes |
| A cap of zero was accepted | yes |
| Money was kept as a float instead of integer cents | yes, after a fix |
| A missing part tag was ignored | yes, after a fix |
| Only the first bad resource was reported | yes |
| Unknown actions were let through instead of refused | yes |
| The advanced-features warning lost the part about the spend limit | yes |
| The verification requirement was dropped | yes |
| The free plan claimed it was being charged | yes |
| The currency check was removed | yes |
| A negative amount was accepted | yes |

Two survived the first run, and both were real gaps rather than equivalent mutations.

**Money as a float.** The test checked `0.1`, `24.99` and `10`, and every one of those happens to come out
exact in floating point, so a float implementation passed. The values that bite are ones like `0.29`, where
`0.29 * 100` is `28.999999999999996`. A cent-short result would quietly put spend one cent under a threshold
it had actually reached. Those values are now in the test.

**A missing tag read as a wrong one.** With the missing-tag branch removed, the next branch still fired and
reported the tag as holding the value `None`. The test only counted the problems, so it passed. Missing is a
different fault from wrong, and the test now checks the message says which.

## Status

| Item | State |
| --- | --- |
| Needs first: gate 1 | closed by the Founder, 14 Oct 2026 |
| LA-COST-04, verified against the real account | done, in the console, 14 Oct 2026 |
| LA-COST-01, the cap on record | done. $7.00 a month, approved 14 Oct 2026 |
| A real AWS budget that fires | cannot be proven on the free plan. There is nothing to bill |
| AMD-3 stage reached | 4, test passed |
