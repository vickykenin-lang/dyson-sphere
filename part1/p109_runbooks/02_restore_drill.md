# Runbook 2: Restore drill

**Draft.** Steps marked `TO CONFIRM AT SYNC` need a real component that does not exist yet. Package P1.09.

**What this drill proves:** N12, that after restarting the host and restoring a backup, an old transcript is
still retrievable. And LA-REL-03, that backups are encrypted and a restore is tested.

**Who runs it:** someone who did not write this runbook.

**How long:** about 45 minutes, most of it waiting.

**Before you start, know this:** an untested backup is not a backup. The only thing that counts here is that
you read back real content that was written before the restore, not that a command said OK.

---

## 1. Write down what must survive

Pick a transcript, a task and an evidence record that already exist, and write down enough to recognise them
afterwards.

| Write down | Value |
| --- | --- |
| Date and time (UTC) | |
| Who is running it | |
| A transcript id and one exact sentence in it | |
| A task id and its state | |
| An evidence id and its AMD-3 stage | |
| Backup the restore will use (name, time) | |

Copy that exact sentence somewhere outside the system. You will compare it character by character later.

## 2. Confirm the backup is encrypted and recent

```
TO CONFIRM AT SYNC: the command, once 2B.01 exists.
```

| Check | Expected |
| --- | --- |
| The backup exists | yes, with a time |
| It is encrypted | yes |
| The runtime cannot delete or alter it | the key and permissions do not allow it (LA-DEP-04) |
| How old it is | write it down |

**If the runtime can delete the backup, stop.** That is LA-DEP-04 failing, and the drill cannot prove anything
until it is fixed.

## 3. Restart the host

Restart the prototype host. Not a graceful shutdown of the application: a restart, the way it would happen if
it failed.

Start a timer.

## 4. Watch what comes back on its own

| Check | Expected |
| --- | --- |
| The host is up | |
| The STOP path answers | it must come back first, or at least independently (LA-DEP-02) |
| Durable tasks resumed | a task that was running does not vanish (LA-REL-01) |
| The app can reconnect | task states and context come back (LA-APP-05) |

Write down how long until each one answered.

## 5. Restore from the backup

```
TO CONFIRM AT SYNC: the restore command, once 2B.01 exists.
```

Record the start and end time. Record anything the restore reported as skipped or changed.

## 6. Read back what you wrote down in step 1

This is the whole drill. Everything before it was setup.

| Check | How | Expected |
| --- | --- | --- |
| The transcript | retrieve it and read the sentence | character for character the same |
| The task | read its state | the same state and `stop_reason` as before |
| The evidence record | read it | the same AMD-3 stage, the same outcome |
| Nothing silently changed | compare counts before and after | the same |

**If the sentence differs by even a word, the restore did not work.** Do not accept "close enough".

## 7. Check what the restore cost

| Write down | Value |
| --- | --- |
| Time from restart to the host being up | |
| Time from restart to a usable system | |
| How much data was lost, if any | |
| Anything that needed a hand | |

The last two matter most. A restore that needs someone who knows a trick is not a restore.

## 8. Write it down

Record in the evidence registry at its AMD-3 stage. Keep the timings: S.06 needs them for the latency and cost
report, and gate 9 needs them for the disaster recovery objectives.

---

## If the drill fails

| What happened | What it means | Do this |
| --- | --- | --- |
| The transcript came back changed or missing | The backup does not hold what you thought | Stop. Nothing else about memory can be trusted until this is understood |
| The restore needed an undocumented step | The runbook is wrong, not the system | Fix this runbook and run it again from step 1 |
| The runtime could delete the backup | LA-DEP-04 is broken | Report to the Founder before continuing |
| Tasks did not come back | LA-REL-01 is broken | Report as a design defect |

Three consecutive failed drills put this on HOLD for the Founder (rule 7).
