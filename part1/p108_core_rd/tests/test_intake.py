"""P1.08 done when: a sample proposal reaches the workflow and cannot change a rule.

Run:  python3 -m unittest discover -s part1/p108_core_rd/tests -t part1/p108_core_rd/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")))
import intake  # noqa: E402


def a_sample_proposal():
    """A researched proposal: Core R&D suggests the Model Router prefer a cheaper qualified model."""
    return {
        "rule_id": "LA-RTR-02",
        "rule_version": "register-1.0",
        "current_text": "C shall pick, per task, the least expensive approved model that reliably meets the "
                        "Founder-defined acceptance bar.",
        "proposed_text": "C shall pick, per task, the least expensive approved model that reliably meets the "
                         "Founder-defined acceptance bar, and shall record the cheaper models it rejected "
                         "and why.",
        "evidence": "Over 400 synthetic Test T0 tasks, the router chose the dearer model 31 percent of the "
                    "time with no recorded reason. Measured on the prototype host, 2026-10-12.",
        "dependencies": "2B.03 Model Router, 2B.02 evidence registry, the gate 6 redaction rules",
        "risk": "A wrong rejection reason could hide a real quality failure behind a cost argument.",
        "cost": "About two days of work in 2B.03, no new paid service.",
    }


class ProposalReachesTheWorkflow(unittest.TestCase):

    def test_a_sample_proposal_enters_at_step_one(self):
        """LA-RD-04. Proposals enter the Governed Amendment Workflow like any other."""
        p = intake.submit(a_sample_proposal())
        self.assertEqual(p.step + 1, 1)
        self.assertEqual(p.step_name, "founder-request-or-dyson-proposal")

    def test_core_rd_can_draft_the_alternative(self):
        """LA-RD-01. Researching and drafting is exactly what Core R&D is for."""
        p = intake.submit(a_sample_proposal())
        p.advance()
        self.assertEqual(p.step_name, "fetch-current-authoritative-rule")
        p.advance()
        self.assertEqual(p.step_name, "draft-alternative-with-analysis")
        self.assertEqual(p.step + 1, 3)

    def test_the_proposal_carries_a_digest_of_the_exact_change(self):
        """Step 5 approves the exact diff, so the diff must be nameable."""
        p = intake.submit(a_sample_proposal())
        self.assertEqual(len(p.diff_digest), 16)
        q = intake.submit(dict(a_sample_proposal(), proposed_text="something else"))
        self.assertNotEqual(p.diff_digest, q.diff_digest, "two different changes share a digest")

    def test_an_unresearched_proposal_is_refused(self):
        """LA-RD-02. The output is researched proposals, not opinions."""
        fields = a_sample_proposal()
        del fields["evidence"]
        with self.assertRaises(intake.Refused) as e:
            intake.submit(fields)
        self.assertIn("evidence", str(e.exception))

    def test_it_stays_separate_from_the_receptor_genesis_engine(self):
        """LA-RD-03."""
        with self.assertRaises(intake.Refused):
            intake.submit(a_sample_proposal(), origin="receptor-genesis-engine")


class ItCannotChangeARule(unittest.TestCase):

    def test_core_rd_cannot_reach_the_founder_approval_step(self):
        """LA-RD-02. Step 5 is the wall."""
        p = intake.submit(a_sample_proposal())
        p.advance()
        p.advance()
        with self.assertRaises(intake.Refused) as e:
            p.advance()
        self.assertIn("Founder", str(e.exception))
        self.assertEqual(p.step + 1, 3, "the proposal stayed at the draft step")

    def test_core_rd_cannot_approve(self):
        """Closure §7. No model, agent, consultant or Receptor self-approves a rule change."""
        p = intake.submit(a_sample_proposal())
        with self.assertRaises(intake.Refused):
            p.approve()
        self.assertIsNone(p.approved_by)

    def test_core_rd_cannot_write_to_the_register(self):
        p = intake.submit(a_sample_proposal())
        with self.assertRaises(intake.Refused):
            p.apply_to_register()

    def test_core_rd_cannot_deploy(self):
        p = intake.submit(a_sample_proposal())
        with self.assertRaises(intake.Refused):
            p.deploy()

    def test_the_rule_is_unchanged_whatever_happens(self):
        """The whole point: a proposal that went as far as it can has still changed nothing."""
        p = intake.submit(a_sample_proposal())
        p.advance()
        p.advance()
        p.attach_advisory_review("claude", "looks sound")
        p.attach_advisory_review("gemini", "looks sound")
        for attempt in (p.approve, p.apply_to_register, p.deploy):
            with self.assertRaises(intake.Refused):
                attempt()
        state = p.to_dict()
        self.assertFalse(state["rule_changed"])
        self.assertIsNone(state["approved_by"])
        self.assertEqual(state["step_number"], 3)

    def test_the_intake_has_no_way_to_write_a_rule_at_all(self):
        """Not a policy, a fact about the code: no callable here writes the register."""
        with open(os.path.join(os.path.dirname(intake.__file__), "intake.py"), encoding="utf-8") as f:
            source = f.read()
        for forbidden in ("def apply(", "register.write", "register.update", "commit_rule"):
            self.assertNotIn(forbidden, source, "intake.py contains %r" % forbidden)


class ExternalReviewsAreAdvisory(unittest.TestCase):

    def test_an_outside_review_is_recorded_as_advisory(self):
        """LA-RD-05. External reviews are advisory and change nothing."""
        p = intake.submit(a_sample_proposal())
        before = p.step
        review = p.attach_advisory_review("claude", "I would accept this", notes="no credentials were shown")
        self.assertEqual(review["weight"], "advisory")
        self.assertFalse(review["changes_state"])
        self.assertEqual(p.step, before, "an advisory review moved the proposal")

    def test_many_approving_reviews_still_change_nothing(self):
        """Agreement is not authority."""
        p = intake.submit(a_sample_proposal())
        for reviewer in ("claude", "gemini", "a human consultant"):
            p.attach_advisory_review(reviewer, "approve")
        self.assertEqual(len(p.advisory_reviews), 3)
        self.assertTrue(all(r["weight"] == "advisory" for r in p.advisory_reviews))
        with self.assertRaises(intake.Refused):
            p.approve()
        self.assertFalse(p.to_dict()["rule_changed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
