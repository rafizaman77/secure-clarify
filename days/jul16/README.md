# Jul 16 — Go/no-go decision, freeze method, split tasks

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal
Decide GO/NO-GO on the method before spending Jul 17+ scaling it up, then
close the two gaps the decision depends on: a real `OpenModelAgent` and a
frozen dev/test split.

## Deliverables produced
| Artifact | What it is |
|---|---|
| [docs/03_gonogo_memo.md](../../docs/03_gonogo_memo.md) | Verdict: **GO** — all 4 checks pass |
| `secure_clarify/agent.py`'s `OpenModelAgent` | All 3 methods implemented for real (`sample_intents`/`classify_malice`/`act`), fail-safe/closed on malformed output |
| `secure_clarify/task_factory.py`'s `assign_split()` | Deterministic `idx % 5 == 0 → dev` rule |
| `scripts/freeze_tasks.py` | Regenerates a frozen task JSON + sha256 checksum manifest |
| `tasks/pilot_40.json` (frozen) | 8 dev / 32 test |
| `test_smoke.py` | Coverage for splits + `OpenModelAgent`'s parsing/fallback behavior |

## Go/no-go verdict: GO
1. Benign clarification materially improves task success (+1.00 goal rate)
2. Adversarial clarification materially increases unsafe actions (+0.425)
3. SecureVoI reduces the harm (0.30 < 0.425, reaching 0.125 at λ=2)
4. Not degenerate — SecureVoI's benign utility (0.95) beats Trusted-Only (0.64)

## Key decision
`OpenModelAgent`'s `sample_intents` never reads `task.hidden_intent` — that's
the ground-truth answer a real agent wouldn't have. Malformed model output
fails **safe** for `sample_intents` (zero measured disagreement) but **closed**
for `classify_malice` (maximally suspicious) since the latter feeds a security
gate — asymmetric on purpose.

## Definition of done
- [x] Go/no-go verdict: GO, documented with all 4 checks passing
- [x] `schema.py`/`simulators.py`/`verifiers.py`/threat model/novelty matrix frozen
- [x] `OpenModelAgent`'s 3 methods implemented (no `NotImplementedError`)
- [x] Dev/test split assigned and frozen with a checksum manifest

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-16--go-no-go-decision-freeze-split-tasks)
and the "Jul 15-16 gap closure" entry immediately below it.
