# The cost register

Package P1.01. Requirements LA-COST-01 and LA-COST-04.

This is the record of what the Founder approved and what was actually checked in his account. It is the one
place a number about money is allowed to live. Nothing else quotes a cap from memory.

---

## 1. The cap

| Field | Value |
| --- | --- |
| Approved cap | **Not yet approved.** See "What is still open" below |
| Currency | USD |
| Approved by | the Founder, and nobody else (rule 4) |
| Scope | one cap across all three parts (rule W6) |

Until the Founder records a number here, `cost_guard.CostRegister` refuses to build a register, and the
guard has nothing to measure against. That refusal is deliberate. A cap nobody approved is not a cap.

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
| The cap is on record | **Waiting** on the Founder's number |
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

One thing, and it is the Founder's:

**What cap do you approve?** On the free plan nothing can be spent past the $100 of credits, so a cap below
that is an early warning line rather than a hard ceiling. Record the number in section 1 and the guard has
something to measure against.

---

## How to use this from code

```python
from cost_guard import CostRegister, Guard

register = CostRegister(
    approved_cap_usd=<the Founder's number>,
    approved_by="founder",
    approved_at="<when he approved it>",
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
