"""Cost guardrails. Package P1.01. Requirements LA-COST-01 and LA-COST-04.

Three jobs, and only three.

**Hold the cap on record.** The Founder approves one cap across all parts (rule W6). It is recorded here with
the account facts it was approved against, and the module refuses to work from a cap nobody approved.

**Say when spend has crossed a threshold.** Not "roughly", and not in floating point. Money is held in
integer cents, thresholds are fractions of the cap, and crossing one is a fact the tests can check rather
than a message somebody hopes was sent.

**Refuse what only the Founder may do.** Approving spend, raising the cap, upgrading the AWS plan and
activating advanced AWS features all live behind a refusal. The last two are irreversible, and activating
advanced features removes the ability to set a spend limit at all, so they are refused with that said plainly.

This module does not talk to AWS. There is no credential here and no network call, which is why rule 5 holds
by construction rather than by promise. The real budget in the Founder's account is created by the Founder;
this is the record of what it must say and the check that the alarm logic is right.

Standard library only.
"""

# The two AWS actions that cannot be undone. Neither may happen without the Founder's approval (rule 4).
IRREVERSIBLE = {
    "upgrade-plan": (
        "Upgrading the AWS plan cannot be reversed. The free plan account is not charged at all: credits "
        "cover it and access ends when they run out. Upgrading replaces that with a bill."),
    "activate-advanced-features": (
        "Activating advanced AWS features cannot be reversed, and it removes the ability to set a spend "
        "limit at all, which makes the Founder responsible for every cost incurred. Nothing Layer A needs "
        "requires it: one region, one account, no external identity provider, no multi-account structure."),
}

# Everything else that only the Founder decides (rule 4, rule W6).
FOUNDER_ONLY = {
    "approve-spend": "Only the Founder approves spend.",
    "raise-cap": "Only the Founder raises the cap, and there is one cap across all parts (rule W6).",
    "add-payment-method": "Only the Founder enters payment details. The AI never does (rule 5).",
}

# The parts that may own a cloud resource, and the tags every resource carries (rules W3 and W7).
PARTS = ("part1", "part2a", "part2b")
PART_TAG = "dyson-part"
SCAFFOLD_TAG = "dyson-scaffold"

# Fractions of the cap at which an alarm fires. 1.0 is the cap itself.
DEFAULT_THRESHOLDS = (0.50, 0.80, 1.00)

# A verification of free tier eligibility and prices goes stale (LA-COST-04).
VERIFICATION_STALE_AFTER_DAYS = 30


class NeedsFounderApproval(Exception):
    """Something only the Founder may do was attempted. The reason says what and why."""


class InvalidRegister(Exception):
    """The register does not describe a real, approved state, so it is refused rather than half trusted."""


def cents(amount_usd):
    """Dollars to integer cents. Money is never held as a float here."""
    if isinstance(amount_usd, bool) or not isinstance(amount_usd, (int, float)):
        raise InvalidRegister("%r is not an amount." % (amount_usd,))
    if amount_usd < 0:
        raise InvalidRegister("An amount cannot be negative: %r." % (amount_usd,))
    return int(round(amount_usd * 100))


def dollars(amount_cents):
    """Integer cents back to dollars, for display only."""
    return amount_cents / 100.0


class CostRegister:
    """The Founder's approved cap, and the account facts it was approved against (LA-COST-01, LA-COST-04).

    `verified_at` and `verified_how` are not decoration. LA-COST-04 asks that free tier eligibility and
    prices be verified against the Founder's actual account, and a verification with no date is not a
    verification.
    """

    def __init__(self, approved_cap_usd, approved_by, approved_at, plan, region,
                 credits_remaining_usd=None, days_remaining=None,
                 verified_at=None, verified_how=None, currency="USD"):
        if approved_by != "founder":
            raise InvalidRegister(
                "A cap is only on record when the Founder approved it, not %r (rule 4)." % (approved_by,))
        if plan not in ("free", "paid"):
            raise InvalidRegister("plan must be free or paid, not %r." % (plan,))
        if not region or not isinstance(region, str):
            raise InvalidRegister("The region the cap applies to must be recorded.")
        if currency != "USD":
            raise InvalidRegister("The cap is recorded in USD. %r needs a change note first." % (currency,))
        if days_remaining is not None and (not isinstance(days_remaining, int) or days_remaining < 0):
            raise InvalidRegister("days_remaining must be a whole number of days, not %r."
                                  % (days_remaining,))

        self.cap_cents = cents(approved_cap_usd)
        if self.cap_cents <= 0:
            raise InvalidRegister("A cap of zero is not a cap. Record what the Founder actually approved.")
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.plan = plan
        self.region = region
        self.credits_cents = None if credits_remaining_usd is None else cents(credits_remaining_usd)
        self.days_remaining = days_remaining
        self.verified_at = verified_at
        self.verified_how = verified_how
        self.currency = currency

    @property
    def cap_usd(self):
        return dollars(self.cap_cents)

    @property
    def is_verified(self):
        """LA-COST-04 is met only when the facts were checked against the Founder's own account."""
        return bool(self.verified_at and self.verified_how)

    def to_dict(self):
        return {
            "approved_cap_usd": self.cap_usd,
            "currency": self.currency,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "plan": self.plan,
            "region": self.region,
            "credits_remaining_usd": None if self.credits_cents is None else dollars(self.credits_cents),
            "days_remaining": self.days_remaining,
            "verified_at": self.verified_at,
            "verified_how": self.verified_how,
            "verified": self.is_verified,
        }


class Guard:
    """The checks that run against a register. It reports and refuses. It never spends and never approves."""

    def __init__(self, register, thresholds=DEFAULT_THRESHOLDS):
        if not isinstance(register, CostRegister):
            raise InvalidRegister("The guard needs a CostRegister, not %r." % (type(register).__name__,))
        bad = [t for t in thresholds if not 0 < t <= 1]
        if bad:
            raise InvalidRegister("A threshold is a fraction of the cap above 0 and at most 1. Got %r."
                                  % (bad,))
        self.register = register
        self.thresholds = tuple(sorted(thresholds))

    # ------------------------------------------------------------------ the alarm
    def check_spend(self, spend_usd):
        """Which thresholds this spend has crossed, and how much room is left.

        A threshold fires when spend reaches it, not after it is passed. At exactly the cap the 1.00
        threshold fires and `over_cap` is true, because a cap that only notices at one cent over is not a cap.
        """
        spent = cents(spend_usd)
        cap = self.register.cap_cents
        fired = [t for t in self.thresholds if spent * 100 >= int(round(t * 100)) * cap]
        return {
            "spend_usd": dollars(spent),
            "cap_usd": self.register.cap_usd,
            "fired": fired,
            "highest_fired": fired[-1] if fired else None,
            "over_cap": spent >= cap,
            "headroom_usd": dollars(max(cap - spent, 0)),
            "alarm": bool(fired),
        }

    def credits_warning(self):
        """On the free plan the thing that runs out is credits and days, not a budget.

        Returns what is left and whether the Founder has to decide before it runs out, rather than after.
        """
        reg = self.register
        if reg.plan != "free":
            return {"applies": False, "reason": "The account is on the paid plan. The cap is the control."}
        return {
            "applies": True,
            "credits_remaining_usd": None if reg.credits_cents is None else dollars(reg.credits_cents),
            "days_remaining": reg.days_remaining,
            "charged_today": False,
            "note": ("A free plan account is not charged. Credits cover it, and access to AWS services ends "
                     "when the credits or the plan period run out. The decision to move to a paid plan has "
                     "to be made before that, not after."),
        }

    # ------------------------------------------------------------------ the tags
    def check_tags(self, resources):
        """Every cloud resource carries its part. Scaffolding says so (rules W3 and W7)."""
        problems = []
        for resource in resources:
            name = resource.get("name", "an unnamed resource")
            tags = resource.get("tags") or {}
            part = tags.get(PART_TAG)
            if not part:
                problems.append(
                    "%s carries no %s tag. An untagged resource has no owner, and at Sync nobody will know "
                    "whether to remove it (rule W3)." % (name, PART_TAG))
            elif part not in PARTS:
                problems.append("%s is tagged %s=%r, which is not one of %s."
                                % (name, PART_TAG, part, ", ".join(PARTS)))
            scaffold = tags.get(SCAFFOLD_TAG)
            if scaffold is not None and scaffold != "yes":
                problems.append("%s has %s=%r. Scaffolding is marked %s=yes or not marked at all (rule W7)."
                                % (name, SCAFFOLD_TAG, scaffold, SCAFFOLD_TAG))
        return problems

    # ------------------------------------------------------------------ what the guard refuses
    def request(self, action, **_k):
        """Anything only the Founder may do is refused here, with the reason."""
        if action in IRREVERSIBLE:
            raise NeedsFounderApproval(
                "%s needs the Founder's authenticated approval (rule 4). %s" % (action, IRREVERSIBLE[action]))
        if action in FOUNDER_ONLY:
            raise NeedsFounderApproval(
                "%s needs the Founder's authenticated approval (rule 4). %s" % (action, FOUNDER_ONLY[action]))
        raise NeedsFounderApproval(
            "%r is not an action this guard knows. It refuses what it does not recognize rather than "
            "letting it through (rule W8)." % (action,))

    def approve_spend(self, *_a, **_k):
        raise NeedsFounderApproval(FOUNDER_ONLY["approve-spend"] + " This module never does (rule 4).")

    def raise_cap(self, *_a, **_k):
        raise NeedsFounderApproval(FOUNDER_ONLY["raise-cap"] + " This module never does (rule 4).")

    # ------------------------------------------------------------------ the gate before paid deployment
    def ready_for_paid_deployment(self):
        """LA-COST-01: budgets, alarms and explicit spend limits exist before any paid deployment.

        Returns the list of what is still missing. An empty list is the only thing that counts as ready.
        """
        reg = self.register
        missing = []
        if reg.approved_by != "founder":
            missing.append("A cap approved by the Founder.")
        if not reg.is_verified:
            missing.append(
                "Free tier eligibility and prices verified against the Founder's actual account, with a date "
                "and how it was checked (LA-COST-04).")
        if 1.00 not in self.thresholds:
            missing.append("An alarm at the cap itself, not only below it.")
        if reg.plan == "free":
            missing.append(
                "A budget and alarm in the account. On the free plan there is nothing to bill yet, so this "
                "cannot be proven until the plan changes, and the plan only changes by the Founder's "
                "approval (rule 4).")
        return missing
