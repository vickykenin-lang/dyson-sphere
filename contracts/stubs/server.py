"""The P1.10 contract stubs: one deterministic stand-in for every component in registry.json.

Start every stub, each on the port registry.json gives it:

    python3 contracts/stubs/server.py

Start one:

    python3 contracts/stubs/server.py --component 2A.07 --port 8207

List what is served:

    python3 contracts/stubs/server.py --list

A stub makes no model call, no call to the outside network and holds no real data. State is in memory and is
cleared by `POST /v1/_stub/reset`. `X-Dyson-Stub-Force: <error code>` makes any operation answer with that
documented error, so a caller can test its own error handling. The stubs share one process and one store; see
the note at the top of state.py.
"""
import argparse
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import behaviors  # noqa: E402
import state  # noqa: E402

REGISTRY = json.load(open(os.path.join(HERE, "..", "registry.json"), encoding="utf-8"))
CONTRACT_MAJOR = REGISTRY["contract_version"].split(".")[0]
HEADER_SPECS = ("header",)
NON_BODY_SPECS = ("header", "path parameter", "query")


def all_contracts():
    for group in ("lanes", "boundaries", "internal"):
        for c in REGISTRY[group]:
            yield c


def callee_components(callee):
    """The components that serve an operation. The Receptor role is served by Test T0 (2B.07)."""
    out = []
    for part in callee.split(" or "):
        part = part.strip()
        out.append("2B.07" if part == "Receptor" else part)
    return out


def build_routes():
    """component -> list of (method, compiled path, param names, operation)."""
    routes = {}
    for c in all_contracts():
        for op in c["operations"]:
            pattern = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", op["path"]) + "$"
            names = re.findall(r"\{(\w+)\}", op["path"])
            for comp in callee_components(op["callee"]):
                routes.setdefault(comp, []).append(
                    (op["method"], re.compile(pattern), names, op, c["id"]))
    return routes


ROUTES = build_routes()


def body_fields(op):
    return [f for f in op["request"] if not f["spec"].startswith(NON_BODY_SPECS)]


def needs_idempotency(op):
    return any(f["name"] == "Idempotency-Key" for f in op["request"])


class Handler(BaseHTTPRequestHandler):
    component = None
    server_version = "dyson-stub/1.0"

    def log_message(self, fmt, *args):  # keep the test output readable
        pass

    # ---------------------------------------------------------------- helpers
    def send(self, status, payload):
        raw = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Dyson-Contract", REGISTRY["contract_version"])
        self.send_header("X-Dyson-Component", self.component)
        self.end_headers()
        self.wfile.write(raw)

    def fail(self, err):
        status = {
            "invalid_request": 400, "unauthenticated": 401, "forbidden": 403, "not_found": 404,
            "idempotency_conflict": 409, "approval_needed": 409, "stopped": 409, "not_admitted": 409,
            "not_verified": 409, "spend_limit": 409, "rate_limited": 429, "internal": 500,
            "dependency_down": 503, "timeout": 504,
        }[err.code]
        retriable = err.code in ("rate_limited", "internal", "dependency_down", "timeout")
        self.send(status, {"error": {"code": err.code, "message": err.message, "retriable": retriable,
                                     "request_id": state.mint("req"), "details": err.details}})

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except ValueError:
            raise state.Err("invalid_request", "The body is not valid JSON.")
        if not isinstance(data, dict):
            raise state.Err("invalid_request", "The body must be a JSON object.")
        return data

    # ---------------------------------------------------------------- dispatch
    def handle_any(self, method):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if path == "/v1/_stub/reset" and method == "POST":
                state.reset()
                state.CLOCK["ms"] = 0
                return self.send(200, {"reset": True, "component": self.component})
            if path == "/v1/_stub/routes" and method == "GET":
                return self.send(200, {"component": self.component, "routes": [
                    {"method": m, "path": op["path"], "operation_id": op["operation_id"], "contract": cid}
                    for m, _p, _n, op, cid in ROUTES.get(self.component, [])]})

            matches = []
            for m, pattern, names, op, cid in ROUTES.get(self.component, []):
                hit = pattern.match(path)
                if hit and m == method:
                    matches.append((op, cid, hit.groupdict()))
            if not matches:
                raise state.Err("not_found", "This component serves no such operation at that path.",
                                {"path": path, "method": method})
            op, contract_id, path_params = matches[0]
            if len(matches) > 1:
                caller = self.headers.get("X-Dyson-Caller")
                for cand, cid, pp in matches:
                    if caller and caller in cand["caller"]:
                        op, contract_id, path_params = cand, cid, pp
                        break

            ver = self.headers.get("X-Dyson-Contract")
            if ver and ver.split(".")[0] != CONTRACT_MAJOR:
                raise state.Err("invalid_request",
                                "This component does not serve that contract major version.",
                                {"served": REGISTRY["contract_version"], "asked": ver})

            body = self.read_body() if method in ("POST", "PUT", "PATCH") else {}

            known = {f["name"] for f in body_fields(op)}
            unknown = sorted(set(body) - known)
            if unknown:
                raise state.Err("invalid_request",
                                "The request carries a field this operation does not accept.",
                                {"unknown_fields": unknown})
            missing = sorted(f["name"] for f in body_fields(op)
                             if f["required"] and body.get(f["name"]) in (None, ""))
            if missing:
                raise state.Err("invalid_request", "A required field is missing.", {"missing": missing})

            idem = self.headers.get("Idempotency-Key")
            if needs_idempotency(op):
                if not idem:
                    raise state.Err("invalid_request",
                                    "A state-changing call needs an Idempotency-Key header.")
                if not re.match(r"^idem_[0-9A-HJKMNP-TV-Z]{26}$", idem):
                    raise state.Err("invalid_request",
                                    "An Idempotency-Key is `idem_` and 26 Crockford base32 characters.")

            forced = self.headers.get("X-Dyson-Stub-Force")
            if forced:
                if forced not in op["errors"]:
                    raise state.Err("invalid_request",
                                    "This operation does not document that error code.",
                                    {"documented": op["errors"]})
                raise state.Err(forced, "Forced by X-Dyson-Stub-Force for a caller's error-handling test.")

            digest = state.body_digest(body)
            if idem and needs_idempotency(op):
                key = (self.component, op["operation_id"], idem)
                seen = state.STATE["idem"].get(key)
                if seen:
                    if seen["digest"] != digest:
                        raise state.Err("idempotency_conflict",
                                        "That idempotency key arrived with a different body; no work was done.",
                                        {"operation_id": op["operation_id"]})
                    return self.send(seen["status"], seen["body"])

            fn = behaviors.OPS.get(op["operation_id"])
            ctx = {"component": self.component, "body": body, "query": query, "path_params": path_params,
                   "headers": self.headers, "op": op, "idem": idem, "digest": digest}
            if fn is None:
                raise state.Err("internal", "This operation has no stub behavior yet.",
                                {"operation_id": op["operation_id"]})
            status, payload = fn(ctx)

            missing_resp = sorted(f["name"] for f in op["response"]
                                  if f["required"] and f["name"] not in payload)
            if missing_resp:
                raise state.Err("internal",
                                "The stub left out a response field its own contract requires.",
                                {"missing": missing_resp, "operation_id": op["operation_id"]})

            if idem and needs_idempotency(op):
                state.STATE["idem"][(self.component, op["operation_id"], idem)] = {
                    "digest": digest, "status": status, "body": payload}
            self.send(status, payload)
        except state.Err as e:
            self.fail(e)
        except Exception as e:  # a stub never hangs: it says what went wrong
            self.fail(state.Err("internal", "The stub failed: %s" % e))

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")

    def do_PUT(self):
        self.handle_any("PUT")

    def do_DELETE(self):
        self.handle_any("DELETE")


def serve(component, port):
    cls = type("Handler_%s" % component.replace(".", "_"), (Handler,), {"component": component})
    httpd = ThreadingHTTPServer(("127.0.0.1", port), cls)
    httpd.daemon_threads = True
    return httpd


def main():
    ap = argparse.ArgumentParser(description="P1.10 contract stubs")
    ap.add_argument("--component", help="serve one component, for example 2A.07")
    ap.add_argument("--port", type=int, help="the port for --component")
    ap.add_argument("--list", action="store_true", help="list the components and their operations")
    args = ap.parse_args()

    if args.list:
        for comp, routes in sorted(ROUTES.items()):
            c = REGISTRY["components"].get(comp, {})
            print("%s  %s  port %s" % (comp, c.get("name", "?"), c.get("stub_port", "?")))
            for m, _p, _n, op, cid in sorted(routes, key=lambda r: r[3]["operation_id"]):
                print("    %-6s %-40s %-10s %s" % (m, op["path"], op["operation_id"], cid))
        return

    if args.component:
        port = args.port or REGISTRY["components"][args.component]["stub_port"]
        print("stub %s on http://127.0.0.1:%d" % (args.component, port))
        serve(args.component, port).serve_forever()
        return

    servers = []
    for comp in sorted(ROUTES):
        port = REGISTRY["components"][comp]["stub_port"]
        httpd = serve(comp, port)
        servers.append((comp, port, httpd))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
    for comp, port, _h in servers:
        print("stub %-6s http://127.0.0.1:%d  %s" % (comp, port, REGISTRY["components"][comp]["name"]))
    print("%d stubs running. Ctrl-C to stop." % len(servers))
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
