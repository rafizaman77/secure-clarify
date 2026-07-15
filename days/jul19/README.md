# Jul 19 — Freeze development choices; primary test runs

**Status: 🟡 Partial** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal (from the plan)
With λ/priors frozen from the dev split (Jul 17-18), run the primary
evaluation on the **held-out 96 test-split tasks only**, with no further
tuning based on what's observed there.

## What's fully done

| Item | Evidence |
|---|---|
| Frozen inputs, never re-derived from test | `scripts/run_primary.py` loads `results/dev_calibration.json` and calls `estimators.set_priors()` — it never calls `fit_priors()` or sweeps λ itself |
| Evaluates only the 96 test tasks | `[t for t in all_tasks if t.split == "test"]` — dev tasks are excluded by construction, not by convention |
| All 4 go/no-go checks re-verified on held-out data | `results/primary_summary.json` → `verdict: "GO"` |
| Full policy × condition table | benign goal rate 1.00 for `SecureVoI`/`ConventionalVoI` vs 0.00 for `NeverAsk`; adversarial unsafe rate `ConventionalVoI` 0.417 → `SecureVoI` 0.042; `SecureVoI` benign utility 0.921 vs `TrustedOnly` 0.637 |

## The one blocker (same as Jul 17-18)
`results/primary_summary.json`'s `agent_backend` field:
```json
"agent_backend": "ScriptedAgent (placeholder -- no open-weight model wired in yet)"
```
This is mechanically identical infrastructure to what a real run will use —
`scripts/run_primary.py --backend hf_local --model <name>` is the only
difference — but the numbers are not the paper's result until that flag is
actually a real model.

## What "fully done" requires here, specifically
This day's deliverable is entirely downstream of Jul 17-18's model-backend
gap — there is nothing test-split-specific left to build. Once *any* real
model has been run through `tune_dev.py` (dev) and `run_primary.py` (test),
Jul 19 is done for that model. The plan's "development choices frozen" bar is
already met procedurally (the pipeline literally cannot leak test information
into λ/priors, by construction, not by discipline) — what's missing is
purely the real model call.

## Definition of done (once a real backend exists)
- [ ] `results/primary_summary.json`'s `agent_backend` is not `ScriptedAgent`
- [ ] All 4 go/no-go checks re-verified on the real-model test-split run
- [ ] `scripts/update_progress.py` shows Jul 19 as ✅ Done (it will, automatically — this is not something to hand-edit)

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-19--freeze-development-choices-primary-test-runs).
