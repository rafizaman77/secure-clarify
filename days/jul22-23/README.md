# Jul 22-23 — Third model, ablations, robustness subset

**Status: ⬜ Not started** — but no longer blocked: this is now the actual
frontier, since Jul 17-21's real-model gap closed (see
[jul17-18](../jul17-18/README.md)).

## Goal (from the plan)
120 tasks × 3 conditions × 6 policies × 3 models = 6,480 deterministic
episodes, plus 3 stochastic repetitions on a stratified 30-task subset
(section 11).

## Where model coverage actually stands
| Model | Dev split | Test split | Status |
|---|---|---|---|
| `mistral-nemo:12b` (Ollama) | ✅ fit λ=0.75 | ✅ full run, verdict GO | **Complete** |
| `llama-3.3-70b-versatile` (Groq) | ✅ same clean frontier | ❌ hit free-tier daily token cap mid-run | Dev-only |
| GPT-OSS-20B | tried | — | **Resists injections** (real finding, in abstract) |
| Qwen3-32B | tried | — | **Resists injections** (real finding, in abstract) |

"Three models" in the plan means three **test-split-complete** runs with
their own dev-tuned λ/priors and bootstrap stats — only Mistral-Nemo is there
today. The two resistant models are a genuine, reportable result (model-
dependent susceptibility) but not yet a second data point for the main table.

## Concrete steps (in dependency order)
1. **Finish Llama-3.3-70B's test split** — either find a route around Groq's
   daily cap (a paid tier, spread the 96-task grid across multiple days using
   `GEN_MIN_INTERVAL`, or run it locally via Ollama like Mistral was) — this
   is the cheapest path to a second complete model, since dev calibration is
   already done.
2. **A third test-split-complete model** — GPT-OSS-20B or Qwen3-32B, if their
   injection-resistance holds up under the frozen λ/priors methodology (worth
   running to completion specifically *because* they resist — a policy
   comparison where the baseline is already safe is a different and useful
   data point, not a wasted run).
3. **Two more policies** to reach "six" (currently 4: `NeverAsk` /
   `ConventionalVoI` / `TrustedOnly` / `SecureVoI`). Plan section 9 names a
   **confidence-threshold** baseline and a **post-hoc guardrail** baseline
   (Conventional VoI + final-action screening) — neither implemented in
   `secure_clarify/policies.py` yet.
4. **Oracle-vs-learned-risk ablation** — how much of SecureVoI's benefit
   survives if `response_risk` used the ground-truth `carries_attack` label
   instead of `classify_malice`'s learned signal (an oracle upper bound).
5. **Stratified 30-task stochastic-repetition subset** — needs a controlled
   randomness source (currently fully deterministic at temperature=0 by
   design); decide the operationalization (temperature>0 sampling vs.
   re-running task_factory with a different seed) before implementing.

## How to run the next model (mechanically identical to Mistral-Nemo's)
```bash
python scripts/smoke_real_model.py --backend ollama --model <name>          # sanity check
python scripts/tune_dev.py    --tasks tasks/main_120.json --backend ollama --model <name>
python scripts/run_primary.py --tasks tasks/main_120.json --backend ollama --model <name>
python scripts/compute_stats.py
python scripts/make_main_table.py
```
No code changes needed — this is exactly the pipeline Jul 17-20 built and
validated on Mistral-Nemo.
