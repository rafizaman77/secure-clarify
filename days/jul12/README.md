# Jul 12 — Novelty matrix, threat model, schemas, seed tasks

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal
Establish the paper's actual contribution before writing code that assumes
it, and lay down the data model everything else builds on.

## Deliverables produced
| Artifact | What it is |
|---|---|
| [docs/01_novelty_matrix.md](../../docs/01_novelty_matrix.md) | 7-axis matrix (Ask/What/Where/Adv/Util/Loss/Exec) vs. every closely related paper — finds the gap only this project fills |
| [docs/02_threat_model.md](../../docs/02_threat_model.md) | Principal/channel/attacker model, frozen Jul 16 |
| `secure_clarify/schema.py` | `Task`/`Question`/`Response` dataclasses + `.validate()` enforcing the threat model in code |
| 10 seed tasks | Validated end-to-end through the schema |

## Key decision
The novelty matrix's whole point is finding "the column of `n`s that only our
row fills in." Result: prior VoI/clarification work is strong on Ask/What/Util
and has nothing on Where/Loss (assumes one trusted answerer); prior security
work (InjecAgent, AgentDojo, CaMeL) is strong on Where/Adv/Exec and has
nothing on Ask/What (treats injection as ambient contamination, not a
consequence of choosing to ask). **CaMeL flagged as the sharpest foil** —
must be addressed explicitly in related work or a reviewer files this as "a
weaker CaMeL."

## Definition of done
- [x] Novelty matrix scored against every closely related paper, working
      novelty statement frozen
- [x] Threat model's principal/channel/attacker sections written
- [x] `schema.py` implemented with validation
- [x] ≥10 seed tasks validate

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-12--novelty-matrix-threat-model-schemas-seed-tasks).
