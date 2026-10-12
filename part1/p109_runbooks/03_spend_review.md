# Runbook 3: Spend review

**Draft.** Steps marked `TO CONFIRM AT SYNC` need a real component that does not exist yet. Package P1.09.

**What this covers:** the monthly check that nothing is spending money without the Founder's approval, and
that the cap on record is still the Founder's cap (rule 4, LA-COST-01, LA-COST-02, LA-COST-04).

**Who runs it:** anyone. The Founder decides anything it finds.

**When:** once a month, and immediately after any alarm fires.

**How long:** about 15 minutes.

**Before you start, know this:** a budget alert that reaches nobody is not a control. The first check below is
the one that fails most often.

---

## 1. Is the alarm able to reach you?

| Check | Where | Expected |
| --- | --- | --- |
| The budget exists | AWS Budgets | yes, with an amount |
| The alert recipient is **verified** | AWS Budgets, email verification | verified, not `0/1` |
| The amount matches the Founder's cap | compare with the Status sheet | the same number |

**If the recipient is unverified, fix that first and stop treating the cap as a control until it is done.** An
unverified recipient means the alarm fires into nothing.

## 2. What was actually spent

| Write down | Value |
| --- | --- |
| Month | |
| AWS spend this month | |
| Credits remaining, and when they expire | |
| Model API spend this month | |
| Voice API spend this month | |
| **Total** | |
| The Founder's approved cap | |
| Over or under | |

The model and voice spend is not on the AWS bill. It comes from separate vendors, and rule W6 says there is
one cap for all three parts, so it counts against the same number.

## 3. Is anything running that nobody approved?

| Check | How | Expected |
| --- | --- | --- |
| Every cloud resource carries a part tag | list resources, group by `dyson-part` | nothing untagged |
| Scaffolding is still marked | filter `dyson-scaffold=yes` | each one is still needed, or it is removed |
| No paid resource appeared without approval | compare with last month's list | every new one has an approval |
| Test keys are not in the repository | search the repository | none (rule 5) |

Write down anything untagged or unexplained. An untagged resource has no owner, and at Sync nobody will know
whether to remove it.

## 4. Did the Model Router stay inside its limits

```
TO CONFIRM AT SYNC: the command, once 2B.03 exists.
```

| Check | Expected |
| --- | --- |
| Calls refused with `spend_limit` | a number, and it is fine if it is not zero |
| The cheapest qualified model was preferred | LA-RTR-02 |
| Any model used that is not approved | none |

A non-zero `spend_limit` count is good news: it means the ceiling is real.

## 5. Decide

Take one of these to the Founder, with the numbers:

| What you found | What to ask |
| --- | --- |
| Under cap, nothing unexplained | nothing. Record the review and stop |
| Approaching the cap | whether to raise the cap or cut something, before the alarm fires |
| Over cap | which resource to stop, now |
| Something untagged | whose it is, and whether to remove it |
| Credits running out | when to move to a paid plan, with the date |

Only the Founder changes a cap or approves spend (rule 4). This runbook never changes one.

## 6. Write it down

Record the review and its numbers. Keep the sheet: S.06 builds the latency and cost report from these, and
gate 9 needs a spending history before production.

---

## If something is spending without approval

1. Do not delete it yet. Write down what it is, its tag, and what it costs per day.
2. Tell the Founder with those three facts.
3. The Founder decides whether to stop it. You do not.
4. If it is costing enough to matter today, say so plainly rather than waiting for the monthly review.
