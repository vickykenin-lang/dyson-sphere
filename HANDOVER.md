# Handover

Everything a new session needs to pick up Dyson Sphere Layer A without asking the Founder to repeat himself.
Written 13 Oct 2026. Read this file first, then `README.md`, then `contracts/CONVENTIONS.md`.

---

## 1. The project

Dyson Sphere is a governed multi-AI business operating ecosystem.

**Layer A** is the shared spine: governance, security, control, intelligence routing, state, execution,
monitoring and evidence. That is what is being built.

**Layer B** is the business Receptors. Out of scope, except the synthetic Test T0 used for testing. Layer B
has its own PRD and plan. Do not start on them unless the Founder asks.

The Founder is Vicky Gautam. He is the only person who decides, approves spend, approves rule changes and
merges.

### Source documents

Two Claude Docs. Both were re-confirmed unchanged at the time of writing. Read them before building anything,
and never contradict them from memory.

| Document | Id | Revision when last read |
| --- | --- | --- |
| Layer A Execution Plan | `306e74f3-6ae1-41f3-9917-794544e49243` | 62 |
| Layer A PRD | `237b05c9-4922-418b-8f15-c5176b53de75` | 31, 174 requirement ids |

The plan has 34 packages (P1.01 to P1.10, 2A.01 to 2A.09, 2B.01 to 2B.08, S.01 to S.07), nine gates, eight
open items, 14 negative tests N1 to N14, and six milestone streams A to F.

---

## 2. How the Founder wants to be worked with

These are not suggestions. The Founder said them directly, and the last one came after three long answers to a
simple yes or no question.

> "ab tum hi banao, pahle P1 ko execute karo ... kaam shuru se karna hai, zyada complex mat karna, ek ek
> activity execute karo, mujhe update karo, uske baad aage bade, continusaly karte mat rahna, me har activty
> ko cross check karte huye chaunga, rule breck mat karna."

> "mujhe sirf streight forward answer zyada pasand hai."

> "mujhe koi bhi complex answer nahi doge aage se pls."

So: **short answers. One activity at a time. Report, then stop and wait.** He checks each activity himself. He
reads Hindi written in Latin script and replies that way; match him.

### His standing preferences

1. Never state a specific value (id, number, key, filename, timestamp, path) from memory. Re-read it from the
   actual source immediately before using it, even if it appeared earlier in the conversation.
2. After any UI action, verify the result actually matches intent before moving on. Do not assume success.
3. Before typing into any code or JSON editor prone to autocomplete, verify the typed content immediately
   after, not after several steps have been built on top of it.
4. Be direct. No multiple-choice suggestion cards, no "would you like me to also" offers, no optional
   next-step menus unless asked. Do the task, report the result, stop.
5. If something is genuinely ambiguous, ask one short question. Do not pad it with options.
6. Prefer fewer correct actions over fast unverified ones. One extra verification costs less than a repeated
   round from a bad assumption.
7. Never open, reveal or click "Show" on any credential or secret. If the next step would expose one, stop
   right before it and hand it back to the Founder.

### Writing style for generated files

No em dashes, no en dashes, no double hyphens used as dashes. US spelling. No leaked placeholders or braces.
Tables with a consistent number of columns.

### Two things that must never appear in a generated file

The Founder's email address and the AWS account id. Both are for identification only. Do not write either
into any file in this repository, and do not send either to any service that does not already need it.

---

## 3. The rules

### The plan's eight rules

1. No gate, no build.
2. An independent check for critical packages.
3. AMD-3 stages, with negative evidence kept.
4. No spend, credential, integration or rule change without the Founder's authenticated approval.
5. The Founder enters credentials. The AI never opens one.
6. Contracts change only by an accepted change note.
7. Three failed checks put the thing on HOLD.
8. Test T0 only, synthetic data.

### The eight side-by-side rules, W1 to W8

1. **W1** One file, one builder.
2. **W2** Each part works in its own folder and its own branch. The first repository commit by P1.02 is the
   only exception on `main`.
3. **W3** Each part gets its own cloud prefix, its own tag and a limited per-part sign-in. Never root.
4. **W4** Parts interact through contracts, never through each other's code.
5. **W5** Wait for a link to be CLOSED or BRIDGE before depending on it.
6. **W6** The Founder decides. One author per paper. One spend cap across all parts.
7. **W7** Scaffolding lives under `scaffold/`, tagged `dyson-scaffold=yes`. Test keys never go in the
   repository.
8. **W8** If anything clashes, stop and ask the Founder.

### Decisions the Founder has already made

| Decision | What he chose | When |
| --- | --- | --- |
| Open item 1, closure names | Adopt the closure state names. `Closed` is housekeeping only | 11 to 12 Oct 2026 |
| Open item 2, PAUSE | PAUSE maps to `stopped`. `held` stays for QA and QC only | 11 to 12 Oct 2026 |
| Open item 3, Reject | Reject goes to `stopped` with reason `reject`, then `closed` | 11 to 12 Oct 2026 |
| Open item 6 and gate 8 | Closed | 12 Oct 2026 |
| Voice | Deferred. Text first. Cost treated as X. Not a blocker for Dyson becoming operational | 12 Oct 2026 |
| Cloud | Core on AWS. Hermes may stay on Oracle, where he already runs it | 12 Oct 2026 |
| Repository visibility | Public, so GitHub rulesets are enforced at no cost | 12 Oct 2026 |
| Required approvals on `main` | 0, because a one-person repository cannot supply a second reviewer | 12 Oct 2026 |

On that last one: the control that matters is still in place. The builder does not merge his own work
unreviewed, the green `check` must pass, and the Founder decides when to merge.

---

## 4. The repository

`https://github.com/vickykenin-lang/dyson-sphere`, public, default branch `main`.

Ruleset "main protection", active, four rules: `deletion`, `non_fast_forward`, `pull_request` with 0 required
approvals, and `required_status_checks` with one required check named `check`.

`strict_required_status_checks_policy` is on, so a branch must be up to date with `main` before it can merge.
In practice: merge one pull request, then update the next branch, wait for its check, then merge it.

### A trap worth knowing

A fresh clone in this environment came with an empty `remote.origin.fetch`, so `git fetch origin` silently did
not update `origin/main`. If `git rev-parse origin/main` fails or looks stale, run:

```
git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git fetch origin
```

---

## 5. What is built and merged

`main` was at `fd98f7e9d84b388459c8e61690f10fbdb5263c91` when this was written. Pull requests 1, 2 and 3
are merged and closed.

| Package | What it is | State |
| --- | --- | --- |
| P1.10 | The interface contracts: conventions, task states, registry, stubs, tests | merged |
| P1.02 | Source control and CI/CD: the pipeline, the ownership guard, the artifact builder, rollback | merged |
| P1.08 | Core R&D charter and proposal intake | merged |
| P1.09 | The four runbooks | merged |
| P1.06 | Monitoring and Health Controller (E) | merged |

### Test counts, as run on `main`

| Suite | Tests |
| --- | --- |
| `contracts/run_tests.sh` | 58 |
| `part1/p102_source_control_cicd/tests` | 13 |
| `part1/p106_monitoring/tests` | 47 |
| `part1/p108_core_rd/tests` | 13 |

All pass. There is nothing to install: every test uses the standard library and `python3 -m unittest`.
**pytest is not available in this environment.** Do not write tests that need it.

### What each piece actually guarantees

- `contracts/` is the single source of truth for how components talk. `build_registry.py` generates
  `registry.json` and `CONTRACTS.md`; edit the generator, never the generated files.
- `tools/ownership_guard.py` turns rule W2 and LA-SEC-06 into a CI check rather than a written promise. It
  now refuses with exit code 2 when it cannot compute a diff, instead of reporting Allowed.
- `tools/build_artifact.py` builds a deterministic tar.gz. `tools/rollback.py` rebuilds from source control at
  an earlier commit and compares digests, so a rollback is proven rather than hoped for.
- `part1/p108_core_rd/src/intake.py` has no code path to the register. `approve`, `apply_to_register` and
  `deploy` exist only to refuse.
- `part1/p106_monitoring/src/monitor.py` has no way to act on a Receptor, and a test reads its own source to
  prove it cannot reach out at all.

### How the work has been checked

Beyond the tests: each critical module was deliberately broken several ways and the tests re-run, to show they
would notice. For P1.06 that was twelve mutations. Eleven were caught on the first pass; the twelfth found a
real gap, which was then closed with a new test. Keep doing this. It is the only thing that tells you whether
a passing suite means anything.

---

## 6. What is blocked, and on what

Nothing in Part 1 can move without the Founder.

| Package | Blocked on |
| --- | --- |
| P1.01 Cost guardrails | Gate 1, which is incomplete |
| P1.03, P1.04, P1.05 | Other parts that do not exist yet |
| P1.07 Founder Dashboard | Needs the Founder's decisions and AWS |

### Gate 1 is not finished

Three things are open, and all three are the Founder's to do:

1. The region is not decided. Sydney or Mumbai.
2. The EC2 vCPU quota has not been checked or raised.
3. The budget alert email is unverified. It showed `0/1`.

That third one matters most. An unverified recipient means the budget alarm fires into nothing, so the cap is
not a control yet. `part1/p109_runbooks/03_spend_review.md` opens with exactly this check.

### A cost fact the Founder should keep in view

The $10 budget on record cannot host Layer A. The cheapest shape that runs it is about $24 a month, or $20
if IPv6 only. This was raised and has not been resolved.

---

## 7. This environment

| Thing | State |
| --- | --- |
| AWS from this session | **Unreachable.** `sts.amazonaws.com` returns 403 through the proxy tunnel |
| GitHub API | Reachable |
| `gh` CLI with `GH_TOKEN` | Token is not valid for `gh`, but `git push` works through the session proxy |
| Outbound network | Allowlisted. Package registries and GitHub only. Other sites are refused before they are reached |
| pytest | Not installed. Use `python3 -m unittest` |
| Chrome browser control | Available when the Founder's computer is online with the desktop app running |

Because AWS is unreachable from here, anything that needs the AWS console is the Founder's to do, or has to go
through his browser.

---

## 8. What to do next

In order:

1. Ask the Founder to finish gate 1: pick the region, check the EC2 vCPU quota, and verify the budget alert
   email. One short message, not a menu.
2. When gate 1 closes, build P1.01, the cost guardrails.
3. P1.07, the Founder Dashboard, after that.

Do not start Part 2A or 2B. The work order for them exists, but Part 1 is not finished and rule 1 says no
gate, no build.

### How to start the session

```
git clone https://github.com/vickykenin-lang/dyson-sphere
cd dyson-sphere
git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
bash contracts/run_tests.sh
for d in part1/*/tests; do python3 -m unittest discover -s "$d" -t "$d"; done
```

If all four suites pass, the handover is intact and you are where this session left off.
