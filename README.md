# Security-Aware Clarification for Agents — Jul 12–16 scaffold

Runnable scaffolding for the AAAI-27 project. Everything here executes on CPU with a
**scripted agent** so the pipeline is validated before open-weight models are wired in.
The scripted-agent numbers are a **pipeline check, not the paper's result** — real-model
numbers are the contribution.

## Status vs. the plan's schedule

| Date | Deliverable | Here |
|---|---|---|
| Jul 12 | Novelty matrix, threat model, schemas, seed tasks | `docs/01_novelty_matrix.md`, `docs/02_threat_model.md`, `secure_clarify/schema.py`, `task_factory.py` |
| Jul 13 | File/calendar simulators, verifiers, tasks | `simulators.py`, `verifiers.py` |
| Jul 14 | Four policies, 40 pilot tasks, matched responses | `policies.py`, `estimators.py`, `agent.py`, `resolver.py`, `tasks/pilot_40.json` |
| Jul 15 | Two-"model" pilot + unsafe-trajectory audit | `run_pilot.py`, `docs/03_gonogo_memo.md` |
| Jul 16 | Go/no-go, freeze, split | `docs/03_gonogo_memo.md` (verdict: GO) |

## Run

```bash
python3 test_smoke.py     # invariants + trade-off + lambda monotonicity
python3 run_pilot.py      # full pilot table, go/no-go, writes results/
```

## Layout

```
secure_clarify/
  schema.py        # Task/Question/Response dataclasses + validation (Jul 12)
  simulators.py    # FileEnv/CalendarEnv, immutable action log (Jul 13)
  verifiers.py     # goal_verifier + safety_verifier, both non-LLM (Jul 13)
  estimators.py    # info-gain + pre/post risk estimators (Jul 14)
  policies.py      # NeverAsk, ConventionalVoI, TrustedOnly, SecureVoI (Jul 14)
  agent.py         # ScriptedAgent + OpenModelAgent skeleton (Jul 14)
  resolver.py      # answer -> resolved intent, injection effect (Jul 14)
  runner.py        # episode loop, utility, summaries (Jul 14-15)
task_factory.py    # matched benign/noisy/adversarial task generator
tasks/pilot_40.json
docs/              # novelty matrix, threat model, go/no-go memo, references
results/           # pilot_summary.json, frontier.json
```

## Pilot result (scripted agent — pipeline check only)

- Benign: Conventional VoI goal 1.00 vs Never Ask 0.00 → asking helps.
- Adversarial: Conventional VoI unsafe **0.425**; SecureVoI drops it to **0.30** (λ=1),
  **0.125** (λ=2), **0.00** (λ≥4), while holding benign utility ≈0.95 until λ≈4.
- SecureVoI beats Trusted-Only on benign utility (0.95 vs 0.64) → not degenerate.

Three real bugs were found and fixed during the audit (answer leakage, risk-blind
policy dodging the attack, info/risk scale mismatch). See `docs/03_gonogo_memo.md`.

## Wiring in the real models (Jul 16→17)

Implement three methods in `agent.OpenModelAgent`:

```python
sample_intents(task, k) -> list[dict]   # k JSON intent hypotheses
classify_malice(text)   -> float        # lightweight injection prob in [0,1]
act(task, resolved)     -> list[(tool, args)]  # JSON tool-call plan
```

Nothing else changes: policies, estimators, verifiers, and the runner are model-agnostic.
Keep decoding deterministic for the main runs; fit channel priors and λ on the dev split only.

## Honest limitations (carry into the paper)

- Scripted-agent trade-off is *constructed to be possible*, not measured on an LM.
- `classify_malice` and channel priors are seeded heuristics; fit on dev, and report the
  oracle-vs-learned-risk ablation.
- Simulator evidence shows the trade-off's existence and policy ordering, not real-world safety.
