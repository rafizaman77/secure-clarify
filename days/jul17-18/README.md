# Jul 17-18 — 120 tasks, development runs, tune lambda and priors

**Status: 🟡 Partial** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md);
this file is a detailed, human-written companion to that auto-generated
status, not a replacement for it — the checkmark above is only ever set by
`scripts/update_progress.py`, never hand-edited here.)

## Goal (from the plan, section 11)
Scale from the 40-task pilot to **120 base tasks (24 dev / 96 test,
stratified by domain, family, attack type, ambiguity, stakes, and channel
availability, frozen + checksummed)**, and make development-only choices
(risk weight λ, channel priors, response-risk feature weights, prompt
wording) **using the dev split only**.

## What's fully done

| Item | Evidence |
|---|---|
| 120-task main set, exact 24/96 split ratio | `tasks/main_120.json`, generated via `python scripts/freeze_tasks.py --n-per-domain 60 --tasks-out tasks/main_120.json --manifest-out results/main120_manifest.json` |
| Frozen + checksummed | `results/main120_manifest.json` (sha256 over dev task IDs, sha256 over test task IDs, separately) |
| Dev-only channel-prior fit | `scripts/tune_dev.py` counts `carries_attack` **only over the 24 dev tasks'** adversarial responses, Laplace-smoothed — never touches test-split labels |
| Lambda sweep + selection | Swept `λ ∈ {0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8}` on dev only; picked **smallest λ hitting the dev-set safety target**, not max-utility (see "Key decision" below) |
| Result artifact | `results/dev_calibration.json` |
| Caching layer (added this session, needed to make a real model backend feasible) | `secure_clarify.agent.CachingAgent` — memoizes `sample_intents`/`classify_malice`/`act` since `policies.decide()` otherwise asks the same question of the model 8-12 redundant times per task |

## The one blocker: no real model yet

Every number above ran on **ScriptedAgent**, the deterministic heuristic
stand-in from Jul 14 — `results/dev_calibration.json`'s `agent_backend` field
says so explicitly:
```json
"agent_backend": "ScriptedAgent (placeholder -- no open-weight model wired in yet)"
```
`scripts/update_progress.py` is deliberately hardened to check this field —
file existence alone does **not** flip this row to ✅ Done, on purpose (see
`_uses_real_model_backend()` in that script). This is not a formatting nit;
it's the actual scientific gap. "Development runs" in the plan means real
open-weight models disagreeing with each other and getting fooled by
injected text in their own idiosyncratic ways — a hand-written heuristic
cannot produce that data no matter how much infrastructure surrounds it.

## Key decision: how λ=0.25 was actually chosen

The lambda frontier on the 24-task dev split (ScriptedAgent) is **not**
monotonic in utility (only unsafe-rate is guaranteed monotonic — see
`test_smoke.py::test_lambda_monotone`):

| λ | benign util | adv unsafe |
|---|---|---|
| 0.00 | 0.950 | 0.417 |
| 0.25 | 0.921 | 0.042 |
| 0.50 | 0.908 | 0.000 |
| 0.75-1.5 | ~0.904 | 0.000 |
| 2.00-8.00 | rises back to 0.929 | 0.000 |

A first version of `tune_dev.py` picked λ=6.0 by "max utility among λ
hitting the safety target" — almost certainly 24-task sampling noise, not
signal (utility dipping mid-grid then rebounding at the far end has no
principled explanation). **Corrected rule: smallest λ clearing the target**
→ λ=0.25. This is exactly the kind of dev-set overfitting a real research
process is supposed to catch, and it's flagged here so a collaborator
reviewing this doesn't have to re-derive why the obvious-looking rule was
wrong.

## What's needed to fully finish (in order)

1. **Pick an inference route** — see `scripts/model_backends.py` and
   `docs/DAILY_LOG.md`'s walkthrough. Being executed *right now* in this
   session: a local small open-weight model (`Qwen/Qwen2.5-0.5B-Instruct`)
   via `hf_local_generate_fn`, in an isolated `.venv_model/` (the system
   Python's numpy/scikit-learn ABI is broken, so `transformers` can't import
   there — see `days/jul17-18/environment-notes.md`).
2. Smoke-test one task: `scripts/smoke_real_model.py --backend hf_local
   --model Qwen/Qwen2.5-0.5B-Instruct`.
3. Re-run `scripts/tune_dev.py --tasks tasks/main_120.json --backend hf_local
   --model Qwen/Qwen2.5-0.5B-Instruct` for real.
4. Repeat with a **second** model family (plan requires 2 for the pilot
   re-run) — e.g. `HuggingFaceTB/SmolLM2-360M-Instruct`.
5. Only then does this row's evidence stop saying "still ScriptedAgent."

## Known, deliberately-not-hidden limitation
`task_factory.py` still has only 2 base task templates (one per domain).
120 tasks' diversity comes from parameter combinations (stakes × channel ×
attack type) layered on those 2 templates, not from genuinely distinct task
*families* — the plan's "stratified by ... family" is only partially met.
This belongs in the paper's Limitations section, not quietly patched over.

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-17-18--scale-to-120-tasks-development-runs-tune-lambda-and-priors).
