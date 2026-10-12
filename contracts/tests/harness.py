"""Test plumbing shared by the contract tests. Standard library only.

By default the tests run against the stubs in this repository, started in this process. To run the same test
against a real component, set an environment variable for it before running the tests:

    DYSON_BASE_2A07=https://tool-hub.internal.example  python3 -m unittest discover contracts/tests

Anything not overridden still points at its stub, so a part can test its own real component while the others
are still stand-ins. At Sync (S.01) every base URL is a real component and the same tests run unchanged.

A test here asserts what a component's HTTP surface does, never how the stub does it. A test that passes only
against the stub is a defect in the test.
"""
import json
import os
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "stubs")))

import server as stub_server  # noqa: E402
import state as stub_state  # noqa: E402

REGISTRY = json.load(open(os.path.join(HERE, "..", "registry.json"), encoding="utf-8"))
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_started = []


def env_base(component):
    return os.environ.get("DYSON_BASE_" + component.replace(".", ""))


def start_stubs():
    """Start a stub for every component that has no real base URL in the environment. Idempotent."""
    if _started:
        return
    for comp in sorted(stub_server.ROUTES):
        if env_base(comp):
            continue
        port = REGISTRY["components"][comp]["stub_port"]
        httpd = stub_server.serve(comp, port)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        _started.append(httpd)
    for httpd in _started:
        socket.create_connection(httpd.server_address, timeout=5).close()


class Response:
    def __init__(self, status, body, headers):
        self.status = status
        self.body = body
        self.headers = headers

    @property
    def code(self):
        return (self.body.get("error") or {}).get("code")


class Client:
    """Calls a component's HTTP surface. It knows nothing about the stub's internals."""

    def __init__(self):
        self.n = 0

    def base(self, component):
        return env_base(component) or "http://127.0.0.1:%d" % REGISTRY["components"][component]["stub_port"]

    def idem(self):
        self.n += 1
        return "idem_" + ("T" + B32[self.n % 32] + B32[(self.n // 32) % 32]).rjust(26, "0")

    def call(self, method, component, path, body=None, idem="auto", headers=None):
        req = urllib.request.Request(self.base(component) + path,
                                     data=None if body is None else json.dumps(body).encode(), method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Dyson-Contract", REGISTRY["contract_version"])
        if idem == "auto":
            if method in ("POST", "PUT", "PATCH"):
                req.add_header("Idempotency-Key", self.idem())
        elif idem is not None:
            req.add_header("Idempotency-Key", idem)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return Response(r.status, json.loads(r.read() or b"{}"), dict(r.headers))
        except urllib.error.HTTPError as e:
            return Response(e.code, json.loads(e.read() or b"{}"), dict(e.headers))

    def post(self, component, path, body=None, **kw):
        return self.call("POST", component, path, body if body is not None else {}, **kw)

    def put(self, component, path, body=None, **kw):
        return self.call("PUT", component, path, body if body is not None else {}, **kw)

    def get(self, component, path, **kw):
        return self.call("GET", component, path, None, **kw)


class ContractTest(unittest.TestCase):
    """Base class: starts the stubs once and clears their state before each test."""

    @classmethod
    def setUpClass(cls):
        start_stubs()

    def setUp(self):
        self.api = Client()
        for comp in sorted(stub_server.ROUTES):
            if not env_base(comp):
                self.api.post(comp, "/v1/_stub/reset")
                break  # one process, one shared store: resetting once is enough
        self.receptor = os.environ.get("DYSON_RECEPTOR_ID", stub_state.RCP_T0)
        self.tool_ok = os.environ.get("DYSON_TOOL_OK", stub_state.TOOL_OK)
        self.tool_high = os.environ.get("DYSON_TOOL_HIGH", stub_state.TOOL_HIGH)
        self.tool_none = os.environ.get("DYSON_TOOL_NONE", stub_state.TOOL_NONE)

    # ---- assertions written in the language of the contract, not of the stub ----
    def ok(self, r):
        self.assertLess(r.status, 300, "expected success, got %s %s" % (r.status, r.body))
        self.assertNotIn("error", r.body, "a success carries no error key: %s" % r.body)
        return r.body

    def failed(self, r, code):
        self.assertGreaterEqual(r.status, 400, "expected a failure, got %s %s" % (r.status, r.body))
        err = r.body.get("error")
        self.assertTrue(err, "a failure carries an error object: %s" % r.body)
        self.assertEqual(err["code"], code, "expected %s, got %s (%s)" % (code, err["code"], err.get("message")))
        for field in ("code", "message", "retriable", "request_id"):
            self.assertIn(field, err, "the error body is missing %s" % field)
        self.assertIsInstance(err["retriable"], bool)
        return err

    def verified(self):
        return {"verified": True, "method": "test"}

    def step_up(self):
        return {"step_up_verified": True, "method": "test"}

    def a_task(self, approval=None):
        """Create one task through the documented path and return its id."""
        body = {"instruction": {"do": "a synthetic thing"}, "thread_id": "t1"}
        if approval:
            body["approval_id"] = approval
        return self.ok(self.api.post("2A.09", "/v1/tasks", body))
