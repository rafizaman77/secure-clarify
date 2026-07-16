# Jul 19 — Freeze development choices; primary test runs

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal (from the plan)
With λ/priors frozen from the dev split (Jul 17-18), run the primary
evaluation on the **held-out 96 test-split tasks only**, with no further
tuning based on what's observed there.

## What's done, on a real model

| Item | Evidence |
|---|---|
| Frozen inputs, never re-derived from test | `scripts/run_primary.py` loads `results/dev_calibration.json` and calls `estimators.set_priors()` — never calls `fit_priors()` or sweeps λ itself |
| Evaluates only the 96 test tasks | `[t for t in all_tasks if t.split == "test"]` |
| Real model backend | `results/primary_summary.json`'s `agent_backend`: **`"ollama:mistral-nemo:12b"`** |
| Frozen λ used | **0.75** (from `results/dev_calibration.json`, dev-only) |
| Verdict | **GO** — all four go/no-go checks pass on held-out data |

## Held-out result (96 test tasks, λ=0.75, verdict GO)
- Benign goal rate: Never Ask 0.00 → asking 1.00.
- Adversarial unsafe rate: Conventional VoI **0.500** vs SecureVoI **0.083**
  (paired bootstrap −0.417 [−0.521, −0.323], p<0.001).
- Benign utility: SecureVoI 0.950 vs Trusted-Only 0.675 (+0.275
  [0.183, 0.367], p<0.001).

Both central comparisons statistically significant on real, held-out,
never-tuned-on data.

## Why this is legitimately "frozen," not just procedurally so
`run_primary.py`'s architecture makes test-set leakage structurally
impossible, not just disciplined: the script literally never imports
`fit_priors` or the λ-sweep logic — only `set_priors()` (a pure reload) and
whatever λ value is already sitting in the calibration file. There is no
code path by which a test-split observation could feed back into λ/priors
within this pipeline.

## What's still open
A **second completed test-split model** (Llama-3.3-70B only reached dev
validation before Groq's free-tier daily cap stopped the run) — see
[days/jul22-23](../jul22-23/README.md).

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#gap-closed--real-open-weight-models-wired-in-held-out-numbers-obtained).
