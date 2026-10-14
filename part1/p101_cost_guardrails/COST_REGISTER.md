# The cost register

Package P1.01. Requirements LA-COST-01 and LA-COST-04.

This is the record of what the Founder approved and what was actually checked in his account. It is the one
place a number about money is allowed to live. Nothing else quotes a cap from memory.

---

## 1. The cap

| Field | Value |
| --- | --- |
| Approved cap | **$7.00 per month** |
| Currency | USD |
| Period | month. A cap with no period is not a cap, and the register refuses one without it |
| Approved by | the Founder |
| Approved at | 2026-10-14T15:29:52.000Z |
| Scope | one cap across all three parts (rule W6) |

### What $7.00 a month buys, and what it does not

$7.00 is exactly the price of the Lightsail bundle this prototype is sized for: 1 GB RAM, 2 vCPU, 40 GB SSD.
So the host alone consumes the entire cap, and the alarm at 1.00 would fire in the first month the host runs.

That is worth saying plainly rather than discovering later:

| Cost | Covered by this cap? |
| --- | --- |
| The prototype host, $7.00 a month | Yes, and it uses all of it |
| Extra block storage, $0.10 per GB a month | No headroom left for it |
| Model API calls to an external vendor | **No.** These are a different vendor and are not on the AWS bill at all |
| Voice API | **No**, and voice is deferred anyway |

Rule W6 says there is one cap across all three parts. Model and voice API spend falls under that same cap,
and at $7.00 a month there is nothing left for it. Two honest readings follow, and only the Founder picks:

1. The cap covers AWS only, and model API spend gets its own approved number when 2B.03 needs one.
2. The cap covers everything, and it has to rise before any model API call is made.

Until he says which, nothing is blocked: no host exists, no model call is made, and no money moves.

## 2. What was verified in the Founder's own account

LA-COST-04 asks that free tier eligibility and prices be verified against the Founder's actual AWS account,
not against documentation. This was read in the console on **14 Oct 2026**.

| Fact | Value | Where it was read |
| --- | --- | --- |
| Account | the new one. The earlier account is no longer in use | Console home |
| Experience | AWS's simplified, project-based experience | Console home |
| Project | Dyson Sphere | Console home |
| Plan | Free plan | Free Tier page |
| Region | Asia Pacific (Sydney), **ap-southeast-2**, already assigned | EC2 console |
| Credits remaining | **$100.00** | Free Tier page |
| Days remaining | **181** | Console home |
| Free tier offers in use | 0 | Free Tier page |
| Budgets that exist | **none** | Budgets page |
| EC2 vCPU quota | `Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances` = **5**, **0** in use | Service Quotas |
| Quota increase | the "Request increase at account level" button is disabled in this experience | Service Quotas |

## 3. The fact that changes the shape of this package

The Free Tier page states it plainly: **a free plan account does not get charged.** Credits cover the costs,
and access to AWS services ends when the free plan period expires or the credits run out. Billing does not
start.

So on this plan there is no bill to cap, and a budget alarm has nothing to fire on. The guardrail that
actually protects the Founder is not an alarm. It is this:

| Guardrail | Why |
| --- | --- |
| **Do not upgrade the plan** | Cannot be reversed. It replaces "not charged" with a bill |
| **Do not activate advanced features** | Cannot be reversed, and it removes the ability to set a spend limit at all, which makes the Founder responsible for every cost incurred |
| Every resource carries `dyson-part` | An untagged resource has no owner, and at Sync nobody will know whether to remove it (rule W3) |
| Scaffolding carries `dyson-scaffold=yes` | So it can be found and removed later (rule W7) |
| Watch credits and days, not the bill | What runs out here is $100 and 181 days |

Both of the first two are refused by `cost_guard.Guard.request`, with the reason, and neither may happen
without the Founder's authenticated approval (rule 4).

Nothing AWS lists as a reason to activate advanced features applies to Layer A: one region, one account, no
external identity provider, no multi-account structure.

## 4. What this package can and cannot prove today

| Claim | State |
| --- | --- |
| The alarm logic is right | **Proven.** 47 tests, and the implementation was broken fourteen ways to check the tests notice |
| The cap is on record | **Done.** $7.00 a month, approved 14 Oct 2026 |
| The account facts are verified | **Done**, 14 Oct 2026, in the console |
| A real budget exists in AWS and fires | **Cannot be proven on the free plan.** There is nothing to bill |

AMD-3 stage reached: **4, test passed.** Not 5, because nothing is deployed and no real budget exists yet.

## 5. The cost fact worth keeping in view

The cheapest shape that actually runs Layer A is about **$24 a month**, or **$20** if IPv6 only. While
credits last that comes out of the $100 rather than out of pocket. At that rate the $100 covers roughly four
months, and the plan period is 181 days, so the credits are likely to run out before the days do.

The decision about what happens next has to be made **before** the credits run out, not after. When they do
run out on the free plan, access ends rather than a bill arriving.

## 6. What is still open

One thing, and it is the Founder's: **does the $7.00 cap cover AWS only, or everything including model API
spend?** Section 1 sets out both readings. Nothing is blocked until a model call is actually made.

---

## How to use this from code

```python
from cost_guard import CostRegister, Guard

register = CostRegister(
    approved_cap_usd=7.00,
    period="month",
    approved_by="founder",
    approved_at="2026-10-14T15:29:52.000Z",
    plan="free",
    region="ap-southeast-2",
    credits_remaining_usd=100.00,
    days_remaining=181,
    verified_at="2026-10-14T14:58:00.000Z",
    verified_how="Read in the AWS console, in the Founder's own account",
)
guard = Guard(register)
guard.check_spend(42.00)          # which thresholds have fired, and the headroom left
guard.credits_warning()           # what is left on the free plan, and that nothing is charged
guard.check_tags(resources)       # anything without an owner
guard.ready_for_paid_deployment() # what LA-COST-01 still needs before any paid deployment
```

`guard.request("upgrade-plan")` and `guard.request("activate-advanced-features")` both refuse, and say why.
