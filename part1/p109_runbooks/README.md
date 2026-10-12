# P1.09 Runbooks

**Build:** STOP drill, restore drill, spend review, release and rollback. Drafted now, finalized at Sync.

**Done when:** Each runbook is followed once on the integrated system by someone who did not write it.

**Supports:** LA-SAF-03, LA-REL-03.

| Runbook | State | Proves |
| --- | --- | --- |
| `01_stop_drill.md` | Draft. Needs 2A.06 | N3, N14 |
| `02_restore_drill.md` | Draft. Needs 2B.01 | N12, LA-REL-03 |
| `03_spend_review.md` | Draft. Needs 2B.03 for one section | LA-COST-01, LA-COST-04, rule 4 |
| `04_release_and_rollback.md` | **Run and proven**, except the deploy steps | LA-DEP-05 |

## Why three of these are drafts

P1.09 waits for 2A.06 (the STOP bus) and 2B.01 (the data foundation). Neither exists. Every step that needs a
real component is marked `TO CONFIRM AT SYNC`, so a reader can see exactly what is written from the contracts
and what is written from a real run.

Runbook 4 is different: P1.02 exists, so it was run end to end on 12 Oct 2026 and the output is in its
section 6. Only its deploy steps wait for 2A.01.

## When these are finished

When 2A.06 and 2B.01 are CLOSED, the `TO CONFIRM AT SYNC` marks are replaced with real commands. The drills are
then followed once on the integrated system after S.03, by someone who did not write them. That run is the
check for P1.09, and S.07 waits for it.

**P1.09 is not in the Part 1 review.** The plan checks it after S.03.

## How to tell a good runbook from a bad one

Every drill here ends by comparing something real against something written down beforehand: a sentence
character for character, a digest against a digest, a refusal that must happen. None of them accept a command
returning zero as proof. That is the habit these are meant to teach, because under pressure it is the first
thing people drop.
