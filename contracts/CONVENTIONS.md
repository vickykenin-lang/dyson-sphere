# Conventions note (P1.10)

Version 1.0, 11 Oct 2026. Owner: Part 1, package P1.10. Basis: the Execution Plan's P1.10 and PRD section 8.

Every part follows this note. It makes its own choices and waits for no other part. It is Derived: it adds no
requirement to any package. A change to it needs a change note that every affected part accepts (rule 6).

## 1. What this note settles

| # | Topic | Settled in |
| --- | --- | --- |
| 1 | Language and framework | section 2 |
| 2 | Repository layout | section 3 |
| 3 | Identifier format | section 4 |
| 4 | Timestamp format | section 5 |
| 5 | Error format | section 6 |
| 6 | Idempotency key | section 7 |
| 7 | Interface versioning | section 8 |
| 8 | How to start a stub | section 9 |

## 2. Language and framework

| Thing | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12 or newer | One language across the three parts, present on the prototype host, and the data and AWS libraries are first class |
| Transport between components | JSON over HTTP/1.1, UTF-8, one request per call | Readable in a log, testable with one command, and no message broker to run before Sync |
| Stub framework | The Python standard library only (`http.server`, `json`) | A stub must start with one command on a clean checkout, with nothing to install |
| Real component framework | Each part chooses its own (FastAPI, Flask, or standard library) | The contract is the HTTP surface, not the framework. A real component passes the same contract tests |
| Test runner | `python3 -m unittest`, standard library only | A contract test must run on a clean checkout with nothing installed, on any part's machine |
| Formatting | 4-space indent, 120-column limit, `snake_case` for fields | One style, so a diff shows real changes |

A component never reads another part's Python code. It calls the HTTP surface in `registry.json` (rule W4).

## 3. Repository layout

The top level is fixed by section 2.2 of every work order. This note settles what sits inside.

```
contracts/          Part 1 owns it. This note, registry.json, CONTRACTS.md, TASK_STATES.md, stubs/, tests/
part1/              Part 1 packages P1.01 to P1.09
part2a/             Part 2A packages 2A.01 to 2A.09
part2b/             Part 2B packages 2B.01 to 2B.08
```

Inside a part's own folder:

```
part2a/
  2a03_entry_gateway/       One folder per package, <id without the dot>_<short name>
    src/                    The component
    tests/                  The part's own tests, not the contract tests
    scaffold/               Stubs, development databases and shortcuts for a bridge (rule W7)
    README.md               How to run it from a clean checkout
```

A package folder is named from its package ID, so a reader finds it from any table in the work orders. No part
writes outside its own folder; `contracts/` and the root files belong to Part 1 (rule W2).

## 4. Identifier format

An identifier is a type prefix, an underscore, and 26 characters of Crockford base32 (a ULID: 48 bits of
millisecond time, then 80 bits of randomness). It sorts by creation time as a plain string, carries no meaning
of its own, and is safe in a URL, a log line and a database key.

| Prefix | For | Created by |
| --- | --- | --- |
| `tsk_` | A task | D, the task engine (2A.09) |
| `idem_` | An idempotency key | The caller, before the first attempt (section 7) |
| `apr_` | An approval request | A, the Governance Core (2A.05) |
| `evd_` | An evidence record | I, the Memory and Evidence Layer (2B.02) |
| `rcp_` | A Receptor | A, the Governance Core (2A.05) |
| `tool_` | A registry entry for a tool, API, plugin or MCP connector | G, the Governed Tool Hub (2A.07) |
| `req_` | One HTTP request, for the log and the error body | The callee, on arrival |
| `inc_` | An incident or a STOP event | A, the Governance Core (2A.05) |

Rules. An ID is opaque: never parse it for meaning other than sorting. Never reuse one. Never invent an ID for
a record another component owns: ask that component and use what it returns. A Receptor never mints a `tsk_`.

Example: `tsk_01K77H3QZJ4R8V2M9X6Y0B5N7C`.

## 5. Timestamp format

RFC 3339, always UTC, always a `Z`, always milliseconds: `2026-10-11T16:21:04.512Z`.

Local time appears only in something a person reads. Durations are integer milliseconds in a field ending
`_ms`. A date with no time is `YYYY-MM-DD`. No other format is accepted, and a timestamp without a zone is an
error (`invalid_request`).

## 6. Error format

Every failing call answers with a JSON body of exactly this shape, and an HTTP status from the table below.

```json
{
  "error": {
    "code": "stopped",
    "message": "STOP is active for this Receptor; no new tool call is accepted.",
    "retriable": false,
    "request_id": "req_01K77H3QZJ4R8V2M9X6Y0B5N7C",
    "details": {"receptor_id": "rcp_01K77H3R0A1B2C3D4E5F6G7H8J"}
  }
}
```

`code` is from this closed list. `message` is one sentence for a person. `retriable` says whether the same call
with the same idempotency key may be sent again. `request_id` is the callee's `req_` ID, and it appears in the
callee's log. `details` is optional and carries no credential, no secret and no personal data.

| code | HTTP | Meaning | retriable |
| --- | --- | --- | --- |
| `invalid_request` | 400 | A field is missing, malformed or of the wrong type | no |
| `unauthenticated` | 401 | No valid session or caller identity | no |
| `forbidden` | 403 | The caller is known but not permitted for this call | no |
| `not_found` | 404 | The named record does not exist for this caller | no |
| `idempotency_conflict` | 409 | The same idempotency key arrived with a different body | no |
| `approval_needed` | 409 | The action needs a Founder approval that does not exist yet | no |
| `stopped` | 409 | STOP or PAUSE is active for this Receptor or for the whole Core | no |
| `not_admitted` | 409 | The tool or connector has not passed the Supply Chain Gate | no |
| `not_verified` | 409 | The result exists but no independent verification proves it | no |
| `spend_limit` | 409 | The call would exceed an approved budget or token limit | no |
| `rate_limited` | 429 | Too many calls from this caller | yes |
| `internal` | 500 | The callee failed for a reason the caller cannot fix | yes |
| `dependency_down` | 503 | A component the callee needs did not answer | yes |
| `timeout` | 504 | The callee gave up waiting for a dependency | yes |

A success never carries an `error` key. A failure never carries a result. `200 OK` alone proves nothing: a
completion claim needs the evidence fields the contract names (LA-EVD-02).

## 7. Idempotency key

Every call that changes state carries the header `Idempotency-Key: idem_<26>`, minted by the caller before its
first attempt and reused for every retry of that same intent.

| Situation | What the callee does |
| --- | --- |
| Key not seen before | Do the work, store the key with the result, answer |
| Key seen, same request body | Answer with the stored result. Do not do the work again |
| Key seen, different request body | Refuse with `idempotency_conflict`. Do no work |
| Key missing on a state-changing call | Refuse with `invalid_request` |

A stored key and result live at least 24 hours. A read-only call (`GET`) needs no key. A retry after a network
failure uses the same key, which is how a duplicate action is prevented (LA-REL-02, LA-ORC-03).

## 8. Interface versioning

A contract version is in the path and repeated in a header, so a mismatch is caught in the first call.

```
POST /v1/tasks            Idempotency-Key: idem_...    X-Dyson-Contract: v1.0
```

| Change | Allowed inside v1 | Needs |
| --- | --- | --- |
| Add an optional field to a request | yes | A note in `registry.json` |
| Add a field to a response | yes | A note in `registry.json` |
| Add a new endpoint or a new error code | yes | A note in `registry.json` |
| Rename or remove a field, make an optional field required, change a type, change the meaning of a code | no | A new version `v2` and an accepted change note (rule 6) |

A caller ignores a response field it does not know. A callee refuses an unknown field in a request with
`invalid_request`, so a typo never passes silently. `X-Dyson-Contract` names the major and minor version the
caller was built against; a callee answers `invalid_request` to a major version it does not serve.

## 9. How to start a stub

From a clean checkout, with nothing installed:

```
python3 contracts/stubs/server.py --component 2A.07 --port 8107
```

Every stub together, each on the port in `registry.json`:

```
bash contracts/run_stubs.sh
```

A stub is deterministic: no model call, no network call of its own, no real data, and no clock-dependent
answer other than the timestamps it writes. The same request with the same idempotency key gives the same
answer on every run and on every machine. State lives in memory and is lost on restart, which is deliberate: a
stub is not a database. `POST /v1/_stub/reset` clears it between tests.

A stub answers both the documented success and the documented errors. Where a contract names an error, the
stub can be made to produce it (`X-Dyson-Stub-Force: stopped`), so a caller can test its own error handling
without waiting for the real component.

Every stub carries the prefix `scaffold` in its own part's folder and the tag `dyson-scaffold=yes` if it runs
in the cloud (rule W7). Sync removes all of it (S.03).
