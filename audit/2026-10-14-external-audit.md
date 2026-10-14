# External audit, 14 October 2026

Commissioned by the Founder. Two independent auditors, neither of which saw the builder's reasoning, each
given the locked rule book (the PRD and the three work orders) and the artifacts, and asked to find what is
wrong rather than to confirm that things are fine.

**Both declined to sign off.**

This file records the findings so a human third party can audit them in turn. It is kept whole, including
the parts that are unflattering, because `CHECKING.md` says a third party can only audit what was recorded
rather than claimed, and because negative evidence is kept (AMD-3, plan rule 3).

---

## Auditor 1: the built code against the requirements

Scope: does the built code meet the requirements it claims, and are the claims made about it true?

Verified first: all 47 files byte-identical before and after, 262 tests pass as handed over.

### Verdict

> "I would not sign off on this work in its current state."

### The findings, as reported

**1. LA-SEC-06 is not met: the repository is public, not private.**
LA-SEC-06 says GitHub shall be used for *private* source control. LA-DEP-05 says a deployment shall be
reproducible from *private* source control. The repository was made public on 12 Oct 2026 to get rulesets at
no cost. Four files in the tree still assert the repository is private, including P1.02's own README,
`FOUNDER_SETTINGS.md`, and the ownership guard's refusal message. A locked requirement was overridden by a
settings preference, with no change note and no amendment record. This needs the Governed Amendment Workflow
of PRD section 7.4, or the repository goes private.

**2. P1.02 claims a review gate that is not enforced.**
`FOUNDER_SETTINGS.md` specifies 1 required approval, "Rule 2: the builder never approves its own work". The
setting is now 0. P1.02's README still claims "A change reaches main only through a reviewed pull request".
P1.02's done-when is "A reviewed change becomes a rebuilt artifact that can be rolled back": the rollback
half is met and was independently reproduced; the reviewed half is not.

**3. P1.06 violates the P1.10 task-state contract, and no test can see it.**
`monitor.py` declares a state `completed-unverified` that exists nowhere else in the tree, in neither the PRD
nor `contracts/TASK_STATES.md`, and omits `closed`, which the contract requires and which the Founder's own
decision on open item 1 keeps. The comment above it says "as in the contracts note", which is false. So when
the Orchestrator reports a task closed, Monitoring will refuse it. This breaks at Sync.

The reason P1.10 did not catch it: `registry.json` carries the task states only as the *string*
`"contracts/TASK_STATES.md"`. The state set is prose, not data, so no contract test can enforce it.

**4. A gap recorded as closed is in fact still open.**
`CHECKING.md` and P1.06's README both record, as a real gap found and fixed, that "a restarted monitor would
escalate the same condition under a new key". The key includes the observation time, so a restarted monitor
that re-observes the same persistent condition later still produces a different key. The test that is meant
to carry this passes both monitors the identical timestamp, so it only re-tests that the hashing is
deterministic, which the test above it already covered. It passes without testing what its name says.

**5. Three packages claim a source-inspection guarantee that a one-line change defeats.**

| Package | The claim | Result |
| --- | --- | --- |
| P1.06 | "a test reads its own source to prove it cannot reach out at all" | **Defeated.** A live `urllib.request` was added; all 47 tests passed |
| P1.01 | "no network call of any kind, and a test reads the module's own source to keep it that way" | **Defeated.** Same injection; all 55 tests passed |
| P1.08 | "one test reads the source to confirm no writing function is hiding there" | **Defeated.** A working `commit_amendment()` that writes the register was added; all 13 tests passed |
| P1.07 | "pins every member of the class and every name in the module" | **Holds.** The same injection was caught |

The auditor's note on this: P1.07 discovered this exact weakness twice during its own rounds, fixed it
properly, and recorded the lesson. It was never carried back to P1.01, P1.06 or P1.08, which kept claiming
the strong guarantee while keeping the weak check.

**6. P1.08 can report `rule_changed: False` after a rule was changed.** The field is hardcoded, and
`approved_by` is an ordinary writable attribute reported verbatim. The one record a Founder would read to
confirm nothing changed cannot detect that something did (LA-EVD-04).

**7. P1.06: a second outage after a recovery is never escalated, and no test notices.** The charter claims
clearing a Receptor's conditions means "the same condition can be raised again if the trouble returns".
Removing that clearing leaves all 47 tests green, and the second outage goes unescalated.

**8. The contract tests do not cover revenue finality where it is actually reported.** Changing FIN-02's
`final` to always true, so a ledger entry is final with no bank statement match, leaves all 58 contract tests
passing. Two tests look like they cover it and do not; one asserts only that a report id appears in a list
and never that the revenue became final.

**9. Four of P1.10's assigned requirements are absent from the entire repository.** LA-IF-09 to LA-IF-12
appear in no file. LA-IF-12 matters most: it defines the synthetic Test T0 with a planted fault and an
independent verifier, and P1.06's own done-when depends on a Test T0 stub.

**10. P1.10's done-when cannot be met as written.** It requires that "the owners of Part 2A and Part 2B
accept the contracts". With one builder there are no such owners. The auditor notes no document overstates
this, but the Founder should see plainly that P1.10 is not closed and cannot close under the present
arrangement.

**11. The build is deterministic only when the output directory is named `dist`.** `EXCLUDE_DIRS` excludes
`dist` and nothing else, so a second build into a differently named directory includes the first build's
output and produces a different digest. The CI step survives by using `dist` then `dist2` once, in that
order. The claim in the README is unconditional; the behaviour is not. Also: there is no unit test anywhere
for `build_artifact.py` or `rollback.py`, the two pieces that carry LA-DEP-05.

**12. P1.01's two documents contradict each other and the code.** The README says 55 tests and twenty-two
mutations and then shows a table of fifteen rows; `COST_REGISTER.md` says 47 tests and fourteen mutations;
the actual count is 55. No mutation log is committed anywhere, so no mutation count in any package is
verifiable by a third party. For a repository whose stated principle is that a third party can only audit
what was recorded, the check-2 evidence is the one thing recorded only as a claim.

**13. P1.01 is partly met, and one Build item is missing entirely.** LA-COST-01 is not met, which the package
discloses honestly. But the plan's Build line includes "plus a usage review routine", which is absent from
the package. And `COST_REGISTER.md` says "What is still open: Nothing in this package", which its own earlier
line contradicts. Latent: `VERIFICATION_STALE_AFTER_DAYS` is defined and never read, so a verification of any
age is accepted.

**14. P1.06: LA-MON-01 and LA-MON-03 are partly met.** There is no enrolment list, so a Receptor that never
reports is absent from the view rather than reported offline, which is the opposite of what the done-when
intends. LA-MON-03 requires escalation to the Governance Core *and* to the Dashboard; only the first exists.

**15. A P1.02 test writes a probe file into P1.06's source directory** and removes it afterwards. If the
process dies it is left behind.

### What the auditor found sound

P1.07 ("the best work here", 8 of 10 mutations caught, the two survivors genuinely equivalent); runbook 4's
reproducible-rollback claim, independently reproduced to the same digest on a different tree; P1.01's alarm
and refusal logic; the ownership guard's refusal to report Allowed when it cannot see a diff; the registry's
structural meta-tests; the contract harness's design for Sync; P1.08's refusal surface; and `CHECKING.md`
itself, whose stated ceiling on check 3 the auditor called correct, noting that findings 4, 5, 7 and 8 are
"exactly the class of error it predicts a same-family checker would miss".

---

## Auditor 2: the gate 2 proposal, and the builder's own audit of it

Scope: judge both the proposal and the self-audit, and say what both missed.

### Verdict

> "Do not accept this proposal as the basis for gate 2."

### What the proposal got wrong that the self-audit also missed

**The repository is public, and gate 2 owns the secrets architecture.** The same finding as auditor 1,
reached independently, with the added point that 2A.01 must publish infrastructure-as-code into that
repository, exposing network topology, firewall rules, bucket names and parameter paths. 2A.02's done-when
is that the canary never appears in a prompt, log, *repository* or memory.

**The paper the plan asked for was not written.** The Part 2A work order says to prepare "a one-page
comparison from prices verified on the actual account" and to give the Founder "each option with its cost and
its trade-off". The PRD says "EC2 or Lightsail is pending a sizing and cost review". **EC2 was never priced
and never mentioned.** There is no bill of materials. Half the option set the plan named was never put in
front of the Founder.

**Lightsail plus SSM Parameter Store is internally inconsistent.** A Lightsail instance cannot take an IAM
instance profile, so reading SSM requires a long-lived access key written to the host's disk, which is a
credential living outside the secret store (LA-MEM-06, LA-SEC-01, LA-SEC-02). On EC2 the instance profile
issues short-lived credentials and nothing is on disk. The auditor called this "the strongest single argument
in the whole gate-2 decision", absent from both documents because neither priced EC2.

**Both cost numbers contradict the project's own merged cost register.** `COST_REGISTER.md`, already built
and merged, says it is "the one place a number about money is allowed to live" and records that the cheapest
shape that runs Layer A is about $24 a month. It also decides and tests that **the $7 cap does not bind AWS
at all while the account is on the free plan.** So the self-audit's central claim, that the cap is smaller
than the architecture needs, rests on a premise the project had already refuted in its own code. The builder
argued two rounds about a cap that does not apply.

**"Everything bound to localhost" cannot deliver Hermes or Receptor isolation.** On one host every process on
the loopback can reach every other, including the secret store and the audit log. There is no network
boundary to block at, so N6 ("Hermes attempts a direct tool call. Expected: blocked at the network") cannot
be shown. Gate 2 has to specify three isolation domains, Core, Hermes and Test T0, and the proposal priced
one.

**"Write-only" does not deliver LA-DEP-04.** A principal with `PutObject` and no `DeleteObject` can still
overwrite an existing object at the same key, destroying the prior backup. "Cannot alter" needs versioning
plus Object Lock, and a KMS key policy excluding the runtime. The self-audit listed backups under "what was
correct" and so never tested the mechanism against the words.

**Gate 2 decides what gate 3 owns.** The proposal specified a TLS client certificate for Direct Founder
Controls. LA-DFC-03 says the method "is decided at gate 3", which is OPEN. Rule 1: no gate, no build.

**Gate 2 cannot close ahead of gate 6.** "Keep 7 daily and 4 weekly" is a retention decision, and LA-PRIV-01
puts retention and deletion controls at gate 6, whose paper another part owns. The proposal does not mention
gate 6 at all.

**Test T0 and 2B.07 appear nowhere**, though gate 2 blocks them and Test T0 must meet every Receptor
obligation including separate data and credentials.

**"Only port 443 open" collides with administration and with Let's Encrypt.** There is no stated
administrative path, and the HTTP-01 challenge needs port 80, so auto-renewal needs DNS-01, which needs
another credential. EC2 with Session Manager answers the first with no inbound port at all.

**The restore runbook called "existing" is a draft** with three `TO CONFIRM AT SYNC` markers, including the
one for checking the backup is encrypted.

### The auditor's verdicts on the four claimed errors

| Claimed error | Verdict |
| --- | --- |
| 1. The cap set the specification | **Partly right, and wrong about the cap.** Right in principle and right that 1 GB was reverse-engineered from $7. Wrong that there are fifteen components (the registry defines seventeen), wrong that the cap binds AWS, and the proposed $12 floor "commits the identical sin at smaller magnitude" |
| 2. A second public port breaks LA-GW-04 | **Right on the diagnosis, wrong on the correction.** Routing Direct Founder Controls through the Gateway runs into LA-DFC-02, "Both controls shall connect only to the Governance Core", and a path the diagram draws as direct. And the self-audit corrected one instance of its own error while leaving the STOP listener version standing |
| 3. SQLite is wrong twice, one concealed | **Right about the concealment, overstated on LA-MEM-07, correction incomplete.** The concealment finding is understated rather than overstated, because LA-MEM-05 is quoted verbatim in 2B.01's own requirements table, so choosing SQLite silently rewrites what another part must build. But LA-MEM-07 forbids *AI components* altering the log, which a separate OS user could satisfy, so "cannot hold" is too strong. And on one host, Postgres roles stop AI components and not a superuser credential |
| 4. Hermes on Oracle is not free isolation | **Right conclusion, wrong reasons, far too mild.** The citations given were the three weakest available. LA-SAF-01 is about independence from LLM and voice providers, not networks. The decisive grounds, all unmentioned: it breaches LA-GW-04, it contradicts the drawn architecture where zone 4 is inside the AWS Core, it makes LA-HER-06 and the Supply Chain Gate unenforceable, and the mutual TLS keys live outside the secret store |

### The handed-back question was not a real conflict

The builder paraphrased LA-DEP-02 as "the STOP path keeps working when other things are down". The actual
text names three components and only three: "when **the Conversation Engine, Model Router and Hermes** are
down". Every STOP-availability requirement in the locked set is about independence from the intelligence
path, not about surviving infrastructure failure. The Gateway is named in none of them.

The auditor's note: the correction in claimed error 2 routes STOP through the Gateway and asserts it
satisfies LA-DEP-02, which is literally true for exactly the reason the builder then called an unresolved
conflict. "He argued both sides and noticed neither."

The sound answer is not reachability but **fail-closed**: LA-SAF-02 requires the Tool Hub to check the STOP
state on every call, so gate 2 should state that when it cannot read that state it denies. The contract
already carries `dependency_down` for it. An unreachable Governance Core then stops the system rather than
freeing it, and it is testable from day one.

Separately, the builder routed STOP behaviour to gate 9. LA-DFC-06 puts how STOP treats operations already
running at **gate 4**, which is open now, and 2A.06 cannot start until gate 4 is closed.

### On sizing, judged independently

The registry defines **17** services, plus PostgreSQL and a metrics agent: about nineteen long-running
processes, with Hermes needing its own isolation domain on top. Realistic memory: 1.2 to 2.2 GB with no
headroom.

- **1 GB is not defensible.** It is also below LA-COST-02's disk band, 40 GB against 50 to 80. Fixing the
  disk alone puts the host at $8, over the cap the proposal was built to respect. The $7 proposal was
  internally impossible.
- **2 GB is not defensible either, as presented.** Zero margin, nothing left for isolated Hermes or Test T0,
  and no measurement behind it. The same reverse-engineering, one step up.
- **LA-COST-03 was inverted.** "Resources scaled up only from evidence" constrains increases. It does not
  license starting below the written planning target.
- **The real constraint is the credit runway, not $7.** $100 over 181 days is about $16.50 a month. 4 GB
  exhausts the credits around day 125, roughly eight weeks before the plan period ends. That is the genuine
  trade-off, and the builder never gave it.

The auditor's recommendation: provision EC2 at the written hypothesis, 2 vCPU / 4 GB / 50 to 80 GB, for a
bounded instrumented 30-day measurement window, close P1.03 first, then step down on evidence with the
decision recorded at an AMD-3 stage.

### The question nobody has asked

The dominant driver of the memory bill is not the SKU. It is **17 separate OS processes**, a choice made in
`CONVENTIONS.md` by P1.10, not by gate 2. Collapsing several cards into one process would cut the requirement
sharply and would weaken the AMD-1 plane separation and the LA-DEP-01 isolation boundaries. Gate 2 cannot
settle compute without the Founder deciding process topology, and that trade has never been put to him.

---

## What the Founder must decide, from both auditors

1. **The repository's visibility.** LA-SEC-06 says private source control. The repository is public. Either
   the requirement is amended through the section 7.4 workflow, or the repository goes private. No secrets
   architecture can be signed off until this is settled.
2. **Process topology.** Whether Layer A cards may share an OS process. This, not the SKU, sets the memory
   bill, and the price of separation is paid in plane separation.
3. **How many isolation domains gate 2 buys.** Core, Hermes and Test T0 are three. The proposal priced one.
4. **Whether Hermes returns to AWS.** The alternative requires amending the drawn architecture and leaves
   LA-GW-04 breached.
5. **That gate 2 cannot close ahead of gate 6**, because retention, classification and redaction belong to
   another part and are still open. Gate 4 is also open and blocks 2A.06.
6. **The measurement window.** The binding constraint is $100 and 181 days, not $7 a month.

## What the builder owes, before any of the above

Findings 1 to 5 of auditor 1, in order; carrying the P1.07-grade check back to P1.01, P1.06 and P1.08;
making the task-state set machine-checkable in `registry.json` rather than prose; committing the mutation
logs so check 2 is evidence rather than a claim; and reconciling the P1.01 and P1.02 documents with what is
actually true.
