# Runbook 1: STOP drill

**Draft.** Steps marked `TO CONFIRM AT SYNC` need a real component that does not exist yet. Package P1.09.

**What this drill proves:** N3, that pressing STOP with the LLM and voice provider down still reaches the Tool
Hub, Hermes and every Receptor lane, and that no new tool call passes. And N14, that recovery after a serious
breach does not resume on its own.

**Who runs it:** someone who did not write this runbook (P1.09 done-when). The Founder presses STOP; the
runner watches and records.

**How long:** about 20 minutes.

**Before you start, know this:** STOP is meant to work when everything else is broken. If any step here needs
the app, the Conversation Engine or a model to be alive, that step is wrong and the drill has found a defect.

---

## 1. Record where you are starting from

| Write down | Value |
| --- | --- |
| Date and time (UTC) | |
| Who is running it | |
| Commit the system is built from | |
| Tasks running right now | |
| Stop state before the drill | |

```
curl -s $BUS/v1/stop-state            # expect {"stopped": false, "scope": "none"}
```

`TO CONFIRM AT SYNC`: the real bus address, once 2A.06 exists.

## 2. Start a task and leave it running

Give Dyson a synthetic Test T0 task that takes a minute or two. Confirm it is `running`.

```
curl -s $MEMORY/v1/tasks/$TASK_ID/evidence
```

Write the task id down. You will check it again in step 6.

## 3. Take the LLM and the voice provider down

This is the point of the drill. STOP must not need them.

- Block the Model Router's outbound path, or stop the Router.
- Block the voice provider, or stop the voice session.

`TO CONFIRM AT SYNC`: the exact way to do this, once 2B.03 exists. Until then, use the contract stub's
`X-Dyson-Stub-Force: dependency_down`.

Confirm they are really down before going on. A drill against a healthy system proves nothing.

## 4. Press STOP

The Founder presses Emergency STOP on the Direct Founder Controls. Not through the app. Not through a chat.

```
POST $CONTROLS/v1/controls/emergency
{"command": "stop", "scope": "all", "authenticator_assertion": {...}}
```

Start a timer when the Founder presses it.

## 5. Check that it landed everywhere

| Check | How | Expected |
| --- | --- | --- |
| The bus knows | `GET $BUS/v1/stop-state` | `stopped: true`, `scope: all` |
| The Tool Hub refuses | call any tool through G | `409 stopped`, and `checks.stop_state` is `fail` |
| Hermes is stopped | `GET $HERMES/health` | reports stopped, and cannot resume itself |
| Every Receptor lane | `POST $RECEPTOR/v1/control` was reached | the response lists it under `reached` |
| Nothing was missed | the STOP response | `not_reached` is empty |

**If `not_reached` is not empty:** that component is not stopped. It is reported as not stopped, which is
correct behavior, and the Tool Hub refuses its calls instead. Record which component and why. This is a finding,
not a drill failure.

Write down how long step 4 to step 5 took.

## 6. Check the task that was running

The task from step 2 must now be `stopped`, with `stop_reason` `stop`. Not `held`. Not `failed`.

```
curl -s $MEMORY/v1/tasks/$TASK_ID/evidence
```

## 7. Try to resume without authorization

```
POST $RECEPTOR/v1/control
{"command": "resume", "receptor_id": "all", "issued_at": "..."}
```

**Expected: `403 forbidden`.** A resume with no authorization must be refused. If anything resumes on its own,
stop the drill and report it to the Founder as an incident. That is N14 failing, and it is serious.

## 8. Resume properly

The Founder authorizes the resume on the Direct Founder Controls, with the incident id.

Confirm: the bus reports `stopped: false`, and a tool call passes again.

## 9. Write it down

Record in the evidence registry at its AMD-3 stage, with the time each step took, anything that was not
reached, and anything that surprised you. Keep the failed attempt from step 7: negative evidence is kept, not
dropped (AMD-3).

---

## If the drill fails

| What happened | What it means | Do this |
| --- | --- | --- |
| STOP did not reach a component | That component can still act | Treat it as an incident. The Tool Hub refuses its calls meanwhile |
| A tool call passed after STOP | LA-SAF-02 is broken | Stop all work. Report to the Founder |
| Something resumed by itself | N14 is broken | Stop all work. Report to the Founder |
| STOP needed the LLM or the app | The red path is not independent | Report as a design defect, not an operations problem |

Three consecutive failed drills put this on HOLD for the Founder (rule 7).
