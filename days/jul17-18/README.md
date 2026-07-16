# Jul 17-18 — 120 tasks, development runs, tune lambda and priors

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md).
This file is a detailed, human-written companion to that auto-generated
status, not a replacement for it — the checkmark is only ever set by
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
| Dev-only channel-prior fit, on a real model | `scripts/tune_dev.py` counts `carries_attack` over the 24 dev tasks' adversarial responses, Laplace-smoothed — **`agent_backend: "ollama:mistral-nemo:12b"`**, not ScriptedAgent |
| Lambda sweep + selection, on a real model | Frontier swept on `ollama:mistral-nemo:12b`; **chosen λ = 0.75** (the plan's dev-only-tuning rule, applied to real-model dev-set behavior rather than the earlier ScriptedAgent placeholder) |
| Caching layer | `secure_clarify.agent.CachingAgent` — memoizes `sample_intents`/`classify_malice`/`act`; without it a real model backend at 120-task scale would ask the same question 8-12 redundant times per task |
| Result artifact | `results/dev_calibration.json` |

## The blocker from the last update is closed

A real open-weight model — **`ollama:mistral-nemo:12b`**, run locally via
Ollama (no rate limits, deterministic at temperature 0) — is what
`results/dev_calibration.json`'s `agent_backend` field now says. A hosted
route (Groq `llama-3.3-70b-versatile`) was also validated on the **dev
split only** — `results/models/llama-3.3-70b/dev_calibration.json` — and
reproduces the same clean monotone frontier, but Groq's free-tier daily
token cap couldn't finish the full 96-task test grid, so the completed
held-out numbers are the local Mistral run.

## Eight real bugs, invisible under ScriptedAgent, found the moment a real
## model touched the pipeline

ScriptedAgent hard-codes correct tool calls and reads a structured attack
channel (`_inject_*` keys) that doesn't exist for a real model. Once one
actually ran:
1. Hosted-API 403s from Cloudflare (missing `User-Agent`) — fixed in
   `model_backends.py`.
2. Groq's real binding limit is a 130-300s burst/daily cap, not the
   per-minute bucket — `Retry-After` is now honored up to 310s.
3. A real model invents plausible-but-wrong tool arg keys unless the prompt
   spells out the exact schema — `agent.py`'s `act()` prompt now lists every
   tool's required keys explicitly.
4. **The injection channel itself was wrong for a real model.** ScriptedAgent
   reads structured `_inject_*` keys; a real model only gets fooled by the
   accepted answer's actual *text*. `runner.py` now passes that text into
   `act()`; acceptance (SecureVoI's stage-2 gate) is what admits or blocks it
   — the real security mechanism, finally exercised through its realistic
   channel.
5. A latent `private_person` field leaked into the model's view of the
   intent and caused a spurious unsafe action on *every benign* calendar
   task — now filtered (`_LATENT_INTENT_KEYS`).
6. Added `_repair_json` for the common one-brace slip that otherwise drops
   an entire, otherwise-correct plan.
7. Prompt now explicitly tells the model to treat an accepted clarification
   as authoritative (so it actually can be fooled) while not inventing
   unstated details (so it doesn't hallucinate unsafe actions).
8. **`estimators.estimate_info_gain`**: the channel-info multiplier now
   applies *outside* the disagreement-saturation clip — a real model's
   higher disagreement saturated the clip and erased channel differences,
   letting the risk-blind policy dodge the attack again (the exact Jul 15
   bug, re-emerging at real-model disagreement levels). Algebraically
   identical for ScriptedAgent (never saturates), so the pilot/smoke tests
   are unchanged.

Full detail: [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#gap-closed--real-open-weight-models-wired-in-held-out-numbers-obtained).

## A real finding, not a gap
Injection-susceptibility is **model-dependent**: Mistral-Nemo-12B and
Llama-3.3-70B follow injected riders (exhibit the trade-off); GPT-OSS-20B and
Qwen3-32B resist them and show little Conventional-VoI harm. This is now
noted in `abstract.md` rather than treated as noise.

## What's still open (moved to Jul 22-23, not re-litigated here)
- A second/third **completed test-split** model (only Mistral's test split
  finished; Llama-3.3-70B is dev-only so far).
- Confidence-threshold and post-hoc-guardrail baselines are not implemented —
  the abstract was written to claim only the two baselines actually run.
- Oracle-vs-learned-risk ablation, robustness subset — see
  [days/jul22-23](../jul22-23/README.md).

## Known, deliberately-not-hidden limitation
`task_factory.py` still has only 2 base task templates (one per domain).
120 tasks' diversity comes from parameter combinations (stakes × channel ×
attack type) layered on those 2 templates, not from genuinely distinct task
*families* — the plan's "stratified by ... family" is only partially met.
This belongs in the paper's Limitations section, not quietly patched over.

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md).
