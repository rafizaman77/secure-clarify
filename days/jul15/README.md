# Jul 15 — Two-response-condition pilot and full unsafe-trajectory audit

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal
Actually run the four policies against the 40 tasks and manually audit every
unsafe/attack-success trajectory for parsing or verifier defects before
trusting the numbers.

## Deliverables produced
| Artifact | What it is |
|---|---|
| `run_pilot.py` | Runs the full grid (4 policies × {benign, adversarial} × 40 tasks) |
| [docs/03_gonogo_memo.md](../../docs/03_gonogo_memo.md) | The audit write-up + go/no-go arithmetic |
| `results/pilot_summary.json` | Raw output table |
| `secure_clarify/agent.py`'s `OpenModelAgent` | Skeleton (implemented in a later session, see jul16) |

## Three real bugs found and fixed (this is the audit's actual output)
1. **Answer leakage into the base intent** — ground-truth fields were
   directly in `hidden_intent`, so the agent succeeded without asking.
   Fixed by withholding ambiguous fields into `_benign_fill`/`_noisy_fill`.
2. **Risk-blind policy accidentally avoided the attack** — info gain ignored
   channel identity, so `ConventionalVoI` tie-broke onto the safe channel and
   never met the attack. Fixed by making info gain channel-dependent.
3. **Scale mismatch collapsed SecureVoI to never-ask** — info gain (~0.09)
   and the risk penalty (~0.3) lived on different scales. Fixed by expressing
   info gain in recoverable-utility units.

## Headline pilot numbers (ScriptedAgent, medium severity)
Benign goal rate: Never-Ask 0.00 vs Conventional-VoI 1.00. Adversarial unsafe
rate: Conventional-VoI 0.425 vs SecureVoI (λ=1) 0.30. **Explicitly a pipeline
check, not a measured LM result.**

## Definition of done
- [x] `run_pilot.py` runs the full grid
- [x] Go/no-go memo written with the audit
- [x] All 3 bugs found during audit fixed and documented
- [x] `test_smoke.py::test_neverask_fails_benign` added as a standing
      regression check for bug #1

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-15--two-response-condition-pilot-and-full-unsafe-trajectory-audit).
