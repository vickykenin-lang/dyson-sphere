"""Core R&D proposal intake. Package P1.08.

The only way a Core R&D proposal enters the Governed Amendment Workflow (PRD section 7.4). It accepts a
researched proposal, puts it at step 1, and can carry it no further than step 3. Steps 4 to 8 belong to the
Founder and to other components.

Nothing here writes a rule. There is no code path from this module to the register, and `apply` does not
exist. That is the point: Core R&D's output is a proposal, never a change (LA-RD-02).

Standard library only.
"""
import hashlib
import json

# The eight steps of PRD section 7.4, in order.
WORKFLOW = [
    "founder-request-or-dyson-proposal",
    "fetch-current-authoritative-rule",
    "draft-alternative-with-analysis",
    "founder-discussion-and-revisions",
    "authenticated-founder-approval-of-the-exact-diff",
    "versioned-register-update",
    "controlled-rollout-and-regression-tests",
    "verified-or-rolled-back",
]
# Core R&D owns these two steps and nothing else.
CORE_RD_STEPS = {0, 2}
# What makes a proposal researched rather than an opinion.
REQUIRED = ("rule_id", "rule_version", "current_text", "proposed_text", "evidence",
            "dependencies", "risk", "cost")


class Refused(Exception):
    """The intake refused the proposal. The reason says what is missing or what was attempted."""


class Proposal:
    """A researched proposal, sitting at a step of the Governed Amendment Workflow."""

    def __init__(self, fields, origin="core-rd"):
        missing = [k for k in REQUIRED if not fields.get(k)]
        if missing:
            raise Refused(
                "A proposal needs %s. Without them it is an opinion, not research (LA-RD-02)."
                % ", ".join(missing))
        if fields.get("receptor_genesis") or origin == "receptor-genesis-engine":
            raise Refused(
                "Core R&D stays separate from the Layer B Receptor Genesis Engine (LA-RD-03).")
        self.fields = dict(fields)
        self.origin = origin
        self.step = 0
        self.advisory_reviews = []
        self.approved_by = None
        self.history = [("entered-workflow", WORKFLOW[0])]

    # ---------------------------------------------------------------- what Core R&D may do
    @property
    def step_name(self):
        return WORKFLOW[self.step]

    @property
    def diff_digest(self):
        """The digest of the exact change. The Founder approves this, not a summary of it."""
        body = json.dumps({k: self.fields[k] for k in ("rule_id", "rule_version", "current_text",
                                                       "proposed_text")}, sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:16]

    def advance(self):
        """Move one step. Core R&D can reach step 3 (draft) and stops there."""
        nxt = self.step + 1
        if nxt >= len(WORKFLOW):
            raise Refused("The workflow has no step past %s." % WORKFLOW[-1])
        if nxt not in CORE_RD_STEPS and nxt > max(CORE_RD_STEPS):
            raise Refused(
                "Core R&D owns steps 1 and 3 only. Step %d (%s) belongs to the Founder or to the owning "
                "component, and Core R&D cannot move a proposal into it (LA-RD-02, LA-RD-04)."
                % (nxt + 1, WORKFLOW[nxt]))
        self.step = nxt
        self.history.append(("advanced", WORKFLOW[nxt]))
        return self.step_name

    def attach_advisory_review(self, reviewer, verdict, notes=""):
        """An outside review is an opinion. It changes nothing (LA-RD-05)."""
        review = {"reviewer": reviewer, "verdict": verdict, "notes": notes,
                  "weight": "advisory", "changes_state": False}
        self.advisory_reviews.append(review)
        self.history.append(("advisory-review-attached", reviewer))
        return review

    # ---------------------------------------------------------------- what nobody here may do
    def approve(self, *_a, **_k):
        raise Refused(
            "Core R&D cannot approve a rule change. Step 5 is an explicit, authenticated Founder approval of "
            "the exact diff, and no model, agent, consultant or Receptor may self-approve (LA-RD-02, "
            "Closure §7).")

    def apply_to_register(self, *_a, **_k):
        raise Refused(
            "Core R&D cannot write to the register. Step 6 happens only after the Founder's approval, and the "
            "register (2B.02) performs it, not this module (LA-RD-02).")

    def deploy(self, *_a, **_k):
        raise Refused(
            "Core R&D cannot deploy. The controlled rollout is step 7, after approval, and the owning part "
            "performs it (LA-RD-02).")

    def to_dict(self):
        return {
            "origin": self.origin,
            "step_number": self.step + 1,
            "step": self.step_name,
            "rule_id": self.fields["rule_id"],
            "rule_version": self.fields["rule_version"],
            "diff_digest": self.diff_digest,
            "advisory_reviews": self.advisory_reviews,
            "approved_by": self.approved_by,
            "rule_changed": False,
            "history": self.history,
        }


def submit(fields, origin="core-rd"):
    """The one door. Every Core R&D proposal enters the workflow here (LA-RD-04)."""
    return Proposal(fields, origin=origin)
