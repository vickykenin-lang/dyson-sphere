# How work is checked

Set by the Founder on 14 Oct 2026: every action is checked three times, explained to him, and open to a
third party audit he may commission. He processes and approves. This session leads the building.

This file is the rule. It is not a promise made in conversation, because a promise made in conversation is
not something anyone can hold you to later.

---

## Three checks, not one check three times

Running the same check three times finds exactly what it found the first time. The three below are different
in kind, and each one catches what the other two cannot.

### Check 1: does it do what it claims?

The package's own "done when", proven by tests that actually run. Not a description of what would happen.
The command, and its output.

**What this catches:** the thing does not work.

**What it misses:** everything, if the tests are weak. A suite of 50 tests that all pass can still be worth
nothing, which is what check 2 exists to find out.

### Check 2: would the tests notice if it broke?

The implementation is deliberately broken, one way at a time, and the tests are run against each break. A
break the tests do not catch is a gap in the tests, not a curiosity.

**What this catches:** tests that pass for the wrong reason.

This is not theory. In this repository it has already found four real gaps that check 1 said nothing about:

| Package | What the tests were missing |
| --- | --- |
| P1.06 | A restarted monitor would escalate the same condition under a new key, and the Governance Core would see it twice |
| P1.01 | Money held as a float. The test values happened to be exact ones, so a broken implementation passed |
| P1.01 | A missing tag was reported as a tag holding the value `None`, so missing and wrong read the same |
| P1.01 | The period was dropped from the record, so "$7" could be read as a total rather than a rate |

Every one of those would have shipped on check 1 alone.

**What it misses:** a correct implementation of the wrong requirement. Both the code and its tests can agree
with each other and disagree with the plan.

### Check 3: a different pair of eyes

The work is checked by **a separate agent that did not see it being built**. It is given the requirement and
the finished artifact. It is not given the reasoning, the commit messages, or the explanation of why a
choice was made, because those are exactly what would carry a misreading across.

**What this catches:** the builder and his tests misreading the requirement together.

**Mandatory** for every critical package, which is all of Part 2A and Part 2B. Plan rule 2 asks for this,
and with one builder it is the only form of independence available inside the session.

## The honest limit of check 3

A separate agent is a genuine improvement on checking your own work. It is **not** the same thing as an
outside auditor, and it should never be described as one.

It shares the same training, the same habits of thought, and the same blind spots as the builder. It can
catch a misread requirement, a missing case, an unstated assumption. It is less likely to catch something
that an entire class of model gets wrong in the same way.

That is the ceiling, and it is why the Founder's third party audit is worth commissioning for anything that
touches authority, money or the ability to stop the system. Nothing here replaces it.

## What the Founder gets to read

For every package, in plain language, without needing to read the code:

| What | Where |
| --- | --- |
| What it does, and what it refuses to do | the package's `README.md` and charter |
| What was run, and what came back | the pull request body |
| Which breaks were tried, and which were caught | the `README.md`, as a table |
| What could not be proven, and why | stated plainly, never left out |

That last row matters most. A package that cannot prove something says so. P1.01 cannot prove a real AWS
budget fires, because on the free plan there is nothing to bill, and it says that rather than implying the
alarm has been seen working.

## What makes an audit possible

A third party can only audit what was recorded rather than claimed:

- Every number is read from its source at the moment it is used, never from memory.
- Every build is reproducible: the same commit builds to the same bytes, and `tools/rollback.py` proves a
  rollback target by rebuilding it rather than trusting a stored copy.
- Negative evidence is kept. A refused attempt, a failed drill and a check that did not pass stay on record
  (AMD-3). They are the most useful thing an auditor reads.
- Where a fact came from is written down next to the fact.

## When a check fails

| Situation | What happens |
| --- | --- |
| Check 1 fails | Fix it. It is not finished |
| Check 2 finds an uncaught break | The **test** is fixed, never weakened to pass. Then the break is run again to prove the fix |
| Check 3 disagrees | Stop. Take it to the Founder. Do not argue the agent into agreement |
| Three failed checks in a row | HOLD for the Founder (plan rule 7) |

The second row is the one that goes wrong most easily. When a deliberate break slips past the tests, the
tempting move is to decide the break did not matter. Four times in this repository it did.

## What this does not change

The Founder still decides, approves spend, approves rule changes and merges. Checking harder is not a
substitute for his approval, and no amount of checking lets a builder approve his own work.
