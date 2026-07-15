# Jul 14 — Four policies, 40 pilot tasks, matched responses

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal
Implement the actual decision rules being compared, and the benchmark's core
methodological trick: the *same* base task gets matched benign/noisy/
adversarial clarification responses, so any measured difference is
attributable to the response, not to task difficulty.

## Deliverables produced
| Artifact | What it is |
|---|---|
| `secure_clarify/estimators.py` | `estimate_info_gain`, `estimate_pre_risk`, `response_risk` |
| `secure_clarify/policies.py` | `NeverAsk`, `ConventionalVoI`, `TrustedOnly`, `SecureVoI` |
| `secure_clarify/agent.py` | `ScriptedAgent` — deterministic stand-in so the whole pipeline runs on CPU with zero model dependency |
| `secure_clarify/resolver.py` | Turns an accepted/rejected response into a resolved intent (where an injected directive actually gets merged in) |
| `secure_clarify/task_factory.py` + `secure_clarify/runner.py` | Matched task generator + episode loop / utility function |
| 40 pilot tasks (20 file + 20 calendar) | All validated |

## Key decision
`ScriptedAgent`'s numbers were labeled **"a pipeline check, not the paper's
result" from day one** — this framing is why every later script that uses it
also stamps an honest `agent_backend` label rather than letting a results
file imply more than it shows (see Jul 17-18/19).

## Definition of done
- [x] All 4 policies implemented (`NeverAsk`/`ConventionalVoI`/`TrustedOnly`/`SecureVoI`)
- [x] `estimators.py` implemented
- [x] `ScriptedAgent` implemented
- [x] ≥40 tasks with matched benign/noisy/adversarial responses

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-14--four-policies-40-pilot-tasks-matched-responses).
