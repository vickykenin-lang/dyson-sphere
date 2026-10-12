"""Structural checks on the contract registry itself. Standard library only, no server needed.

These catch the mistakes a reader would not see: an operation with no stub, a contract with no requirement
behind it, an error code nobody defined, a port used twice.

Run:  python3 -m unittest discover -s contracts/tests -v
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "stubs")))

import behaviors  # noqa: E402
import server  # noqa: E402

REGISTRY = json.load(open(os.path.join(HERE, "..", "registry.json"), encoding="utf-8"))
CONVENTIONS = open(os.path.join(HERE, "..", "CONVENTIONS.md"), encoding="utf-8").read()


def every_operation():
    for group in ("lanes", "boundaries", "internal"):
        for contract in REGISTRY[group]:
            for op in contract["operations"]:
                yield contract, op


class RegistryShape(unittest.TestCase):

    def test_every_operation_has_a_stub_behavior(self):
        missing = [op["operation_id"] for _c, op in every_operation()
                   if op["operation_id"] not in behaviors.OPS]
        self.assertEqual(missing, [], "these operations have no stub: %s" % missing)

    def test_every_stub_behavior_belongs_to_an_operation(self):
        known = {op["operation_id"] for _c, op in every_operation()}
        extra = sorted(set(behaviors.OPS) - known)
        self.assertEqual(extra, [], "these stubs answer no documented operation: %s" % extra)

    def test_every_operation_is_routed_to_a_component(self):
        routed = {op["operation_id"] for routes in server.ROUTES.values() for *_x, op, _c in routes}
        missing = sorted({op["operation_id"] for _c, op in every_operation()} - routed)
        self.assertEqual(missing, [], "these operations reach no component: %s" % missing)

    def test_every_operation_names_a_requirement(self):
        bare = [op["operation_id"] for _c, op in every_operation() if not op["requirements"]]
        self.assertEqual(bare, [], "these operations rest on no requirement: %s" % bare)

    def test_every_operation_says_what_happens_when_the_other_side_is_down_or_stopped(self):
        bad = [op["operation_id"] for _c, op in every_operation()
               if len(op["when_callee_is_down"]) < 20 or len(op["when_stopped"]) < 20]
        self.assertEqual(bad, [], "these operations do not say enough: %s" % bad)

    def test_every_state_changing_operation_requires_an_idempotency_key(self):
        bad = []
        for _c, op in every_operation():
            if op["method"] in ("POST", "PUT", "PATCH"):
                if not any(f["name"] == "Idempotency-Key" and f["required"] for f in op["request"]):
                    bad.append(op["operation_id"])
        self.assertEqual(bad, [], "these change state with no idempotency key: %s" % bad)

    def test_a_read_only_operation_asks_for_no_key(self):
        bad = [op["operation_id"] for _c, op in every_operation()
               if op["method"] == "GET" and any(f["name"] == "Idempotency-Key" for f in op["request"])]
        self.assertEqual(bad, [], "a GET needs no idempotency key: %s" % bad)

    def test_every_error_code_is_one_the_conventions_note_defines(self):
        defined = set(re.findall(r"^\| `([a-z_]+)` \| \d{3} \|", CONVENTIONS, re.M))
        self.assertTrue(defined, "the conventions note lists no error codes")
        used = {code for _c, op in every_operation() for code in op["errors"]}
        unknown = sorted(used - defined)
        self.assertEqual(unknown, [], "these codes are used but not defined: %s" % unknown)

    def test_every_component_has_its_own_stub_port(self):
        ports = [c["stub_port"] for c in REGISTRY["components"].values()]
        self.assertEqual(len(ports), len(set(ports)), "two components share a port")

    def test_every_contract_either_has_operations_or_points_at_another(self):
        bad = [c["id"] for group in ("lanes", "boundaries", "internal") for c in REGISTRY[group]
               if not c["operations"] and not c.get("same_as")]
        self.assertEqual(bad, [], "these contracts are empty and point nowhere: %s" % bad)

    def test_every_caller_and_callee_is_a_known_component_or_actor(self):
        known = set(REGISTRY["components"]) | set(REGISTRY["actors"])
        unknown = set()
        for _c, op in every_operation():
            for side in (op["caller"], op["callee"]):
                for part in side.split(" or "):
                    if part.strip() not in known:
                        unknown.add(part.strip())
        self.assertEqual(sorted(unknown), [], "unknown sides: %s" % sorted(unknown))

    def test_every_component_of_the_map_appears_in_a_contract(self):
        """A component nobody talks to would be unreachable by design."""
        sides = set()
        for _c, op in every_operation():
            for side in (op["caller"], op["callee"]):
                sides |= {p.strip() for p in side.split(" or ")}
        missing = []
        for pid, comp in REGISTRY["components"].items():
            if pid not in sides and not comp.get("plays_role"):
                missing.append(pid)
        self.assertEqual(missing, [], "these components appear in no contract: %s" % missing)

    def test_the_excluded_paths_say_why(self):
        for e in REGISTRY["excluded_paths"]:
            self.assertGreater(len(e["reason"]), 40, "an exclusion needs a reason: %s" % e["path"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
