# P1.08 Core R&D function

**Build:** a charter and an intake that sends every proposal into the Governed Amendment Workflow; external
reviews marked advisory.

**Done when:** A sample proposal reaches the workflow and cannot change a rule.

**Requirements:** LA-RD-01 to LA-RD-05.

| Piece | Where |
| --- | --- |
| The charter | `CHARTER.md` |
| The intake, the only door into the workflow | `src/intake.py` |
| The proof | `tests/test_intake.py` |

```
python3 -m unittest discover -s part1/p108_core_rd/tests -t part1/p108_core_rd/tests
```

## Why there is no apply function

Core R&D's output is a researched proposal, never a change (LA-RD-02). So `intake.py` has no path to the
register at all: `approve`, `apply_to_register` and `deploy` exist only to refuse, and one test reads the
source to confirm no writing function is hiding there. A proposal can reach step 3 of the Governed Amendment
Workflow and stops. Step 5, the Founder's authenticated approval of the exact diff, is the wall.

An outside review by Claude, Gemini or a consultant is attached as `advisory` and moves nothing. Three
approving reviews change as little as none (LA-RD-05).
