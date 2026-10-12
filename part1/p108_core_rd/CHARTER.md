# Core R&D charter

Package P1.08. Requirements LA-RD-01 to LA-RD-05.

## What Core R&D is

An independent function that evaluates and improves the Dyson Core: model routing, safety, runtime,
performance, capabilities and future possibilities (LA-RD-01).

Its output is **researched proposals**. Nothing else. It writes no rule, changes no rule, and deploys nothing
(LA-RD-02).

## What it may not do

| It may not | Because |
| --- | --- |
| Change a rule, a policy or the register, even a small one | LA-RD-02: it shall never make automatic constitutional changes |
| Approve its own proposal | Closure §7: no model, agent, consultant or Receptor self-approves a rule change |
| Deploy anything, or ask a component to deploy | It researches; the rollout is step 7 of the workflow, after the Founder's approval |
| Touch the Layer B Receptor Genesis Engine, or take work from it | LA-RD-03: the two stay separate |
| Treat an outside review as a decision | LA-RD-05: an external review is advisory |

A proposal that would change a rule does not become a change by being good. It becomes a change only by
passing through the Governed Amendment Workflow and receiving the Founder's authenticated approval.

## What it may look at

Model routing and fallback, safety and STOP behavior, runtime performance and cost, memory and evidence,
Receptor governance, and capabilities Dyson does not yet have. It may read anything the governed interfaces
expose. It holds no credential and reaches no tool except through the Governed Tool Hub.

## Where a proposal goes

Every proposal enters the Governed Amendment Workflow (PRD section 7.4) at step 1, like any proposal from
anyone else (LA-RD-04). Core R&D owns step 1 and step 3 and nothing beyond them.

| Step | What happens | Who owns it |
| --- | --- | --- |
| 1 | Founder request, or a Dyson-initiated improvement proposal | Core R&D, or the Founder |
| 2 | Fetch the exact current authoritative rule and version | The register (2B.02) |
| 3 | Draft the alternative with rationale and dependency, risk and cost analysis | Core R&D |
| 4 | Founder discussion and revisions | The Founder |
| 5 | Explicit, authenticated Founder approval of the exact diff | **The Founder alone** |
| 6 | Versioned register update with immutable history | The register (2B.02) |
| 7 | Controlled rollout, technical regression tests and audit | The owning part |
| 8 | Verified status, or rollback and escalation | QA/QC (2B.06) |

Step 5 is the wall. Nothing crosses it without the Founder.

## External reviews

Core R&D may ask an outside model, for example Claude or Gemini, to review a proposal. Every such review is
recorded as **advisory** and carries no weight of its own (LA-RD-05). It is attached to the proposal as an
opinion, never as a verdict, and the data and permission rules apply to whatever is shown to it: no
credentials, no personal data, and nothing beyond the gate 6 redaction rules.

An advisory review never changes a proposal's state and never satisfies step 4 or step 5.

## What a proposal must carry

A proposal that is missing any of these is not researched, and the intake refuses it:

- The exact rule it would change, with its version
- What it would become, written out
- Why: the evidence, not the argument
- What else depends on that rule
- The risk if it is wrong
- The cost in money and in work

## How this is checked

`src/intake.py` is the only way a proposal enters the workflow, and `tests/test_intake.py` shows that a sample
proposal reaches the workflow and cannot change a rule. Run the tests from the repository root:

```
python3 -m unittest discover -s part1/p108_core_rd/tests -t part1/p108_core_rd/tests
```
