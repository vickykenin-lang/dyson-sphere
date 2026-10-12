"""P1.02: the ownership guard must refuse a rule W2 or LA-SEC-06 breach, and must refuse to answer at all
when it cannot see what changed.

Run:  python3 -m unittest discover -s part1/p102_source_control_cicd/tests \\
          -t part1/p102_source_control_cicd/tests
"""
import os
import subprocess
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import ownership_guard as guard  # noqa: E402


def run_guard(*args):
    done = subprocess.run([sys.executable, os.path.join("tools", "ownership_guard.py")] + list(args),
                          cwd=REPO, capture_output=True, text=True)
    return done.returncode, done.stdout


class CannotSeeTheDiff(unittest.TestCase):
    """The failure that matters most: a guard that cannot compute a diff must not report Allowed.

    It did, once. `git rev-parse` failed, the helper swallowed the error and returned an empty string, the
    file list came back empty, and the guard printed "nothing changed. Allowed." on a branch that had in
    fact changed four files. Silence read as permission.
    """

    def test_a_base_this_clone_does_not_have_is_refused_not_allowed(self):
        code, out = run_guard("--base", "origin/no-such-revision", "--branch", "part1/anything")
        self.assertEqual(code, 2, out)
        self.assertIn("CANNOT CHECK", out)
        # The two verdict lines the guard prints when it did look. Neither may appear here.
        self.assertNotIn("Every file is inside", out)
        self.assertNotIn("nothing changed", out)

    def test_the_message_says_how_to_fix_it(self):
        _, out = run_guard("--base", "origin/no-such-revision", "--branch", "part1/anything")
        self.assertIn("git fetch", out)

    def test_a_failing_git_command_raises_rather_than_returning_nothing(self):
        with self.assertRaises(guard.CannotCheck):
            guard.run("git", "rev-parse", "--verify", "definitely-not-a-revision")

    def test_an_empty_file_list_given_on_purpose_is_still_allowed(self):
        """Passing --files with nothing is a real answer, not a failure to look."""
        code, out = run_guard("--files", "--branch", "part1/anything")
        self.assertEqual(code, 0, out)
        self.assertIn("Allowed", out)


class RuleW2(unittest.TestCase):
    """One file, one builder. A branch may only write inside its own part's folder."""

    def test_a_part1_branch_may_write_in_its_own_folder(self):
        self.assertEqual(guard.check(["part1/p106_monitoring/src/monitor.py"], "part1/p106-monitoring"), [])

    def test_a_part1_branch_may_write_the_shared_folders_it_owns(self):
        for path in ("contracts/CONVENTIONS.md", "tools/rollback.py", ".github/workflows/ci.yml",
                     "README.md"):
            self.assertEqual(guard.check([path], "part1/p106-monitoring"), [], path)

    def test_a_part1_branch_may_not_write_in_another_parts_folder(self):
        problems = guard.check(["part2b/p2b01_memory/src/store.py"], "part1/p106-monitoring")
        self.assertEqual(len(problems), 1)
        self.assertIn("part2b", problems[0])

    def test_a_part2a_branch_may_not_write_the_contracts(self):
        problems = guard.check(["contracts/CONVENTIONS.md"], "part2a/whatever")
        self.assertEqual(len(problems), 1)

    def test_every_file_in_a_mixed_change_is_reported_not_just_the_first(self):
        problems = guard.check(["part2a/a.py", "part2b/b.py"], "part1/p106-monitoring")
        self.assertEqual(len(problems), 2)

    def test_a_branch_that_names_no_part_is_refused(self):
        self.assertTrue(guard.check(["part1/p106_monitoring/src/monitor.py"], "my-branch"))


class RuleLASEC06(unittest.TestCase):
    """No pull request or Action may sit in the runtime response loop."""

    def setUp(self):
        self.scratch = os.path.join(REPO, "part1", "p106_monitoring", "src", "_guard_probe.py")

    def tearDown(self):
        if os.path.exists(self.scratch):
            os.remove(self.scratch)

    def _probe(self, body):
        with open(self.scratch, "w") as handle:
            handle.write(body)
        return guard.check(["part1/p106_monitoring/src/_guard_probe.py"], "part1/p106-monitoring")

    def test_runtime_code_reaching_the_github_api_is_refused(self):
        problems = self._probe('URL = "https://api.github.com/repos/x/y/issues"\n')
        self.assertEqual(len(problems), 1)
        self.assertIn("LA-SEC-06", problems[0])

    def test_runtime_code_triggering_a_workflow_is_refused(self):
        self.assertTrue(self._probe('EVENT = "workflow_dispatch"\n'))
        self.assertTrue(self._probe('EVENT = "repository_dispatch"\n'))

    def test_ordinary_runtime_code_is_allowed(self):
        self.assertEqual(self._probe('STATUSES = ("healthy", "offline")\n'), [])


if __name__ == "__main__":
    unittest.main()
