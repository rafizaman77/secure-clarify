# Jul 22-23 — Third model, ablations, robustness subset

**Status: 🟡 In progress** — four of five items below are done; the
remaining one (a second/third *test-split-complete* model) is actively
running.

## Goal (from the plan)
120 tasks × 3 conditions × 6 policies × 3 models = 6,480 deterministic
episodes, plus 3 stochastic repetitions on a stratified 30-task subset
(section 11).

## Where model coverage actually stands
| Model | Dev split | Test split | Status |
|---|---|---|---|
| `mistral-nemo:12b` (Ollama, Anagh's machine) | ✅ fit λ=0.75 | ✅ full run, verdict GO | **Complete** |
| `llama-3.3-70b-versatile` (Groq, this sandbox) | ✅ same clean frontier (0.833→0.000 unsafe) | ❌ intermittent network stalls in this environment — see `docs/DAILY_LOG.md` | Dev-only for now |
| GPT-OSS-20B | tried (Anagh) | — | **Resists injections** (real finding, in abstract) |
| Qwen3-32B | tried (Anagh) | — | **Resists injections** (real finding, in abstract) |
| `Qwen2.5-0.5B-Instruct` (local `hf_local`, this sandbox) | ✅ but **benign_goal_rate=0.000 at every λ** | 🔄 running now | Capability floor, not a trade-off — see below |
| `Qwen2.5-1.5B-Instruct` (local `hf_local`, this sandbox) | 🔄 running now | — | Bigger model in the same family, hoping for a real trade-off instead of a floor |

"Three models" in the plan means three **test-split-complete** runs with
their own dev-tuned λ/priors and bootstrap stats — only Mistral-Nemo is there
today; two more local runs are in flight now.

## Concrete steps (in dependency order)
1. ~~**Two more policies** to reach "six."~~ **Done.** Checked the plan's
   exact policy table (section 10) rather than assume — the six are Never
   Ask / **Always Ask** / **Confidence Threshold** / Conventional VoI /
   Trusted-Only / SecureVoI. Both implemented (`secure_clarify.policies.
   MAIN_POLICIES`), smoke-tested, wired into `run_primary.py --policies main`.
2. ~~Confidence-threshold calibration~~ **Done** — `scripts/tune_dev.py` picks
   the threshold as the median observed sampled-intent agreement across dev.
3. ~~**Post-hoc guardrail**~~ **Done, though it's the plan's Optional 7th
   baseline, not one of the required six.** `secure_clarify/guardrail.py`
   (new module, `runner.py` untouched) implements Conventional VoI + a
   pre-execution action-plan screen, evaluated via
   `scripts/guardrail_eval.py`. Notable ScriptedAgent result: it reaches
   goal_rate=1.0 in BOTH conditions with adversarial unsafe_rate=0.0 —
   better benign-preserving-under-attack than SecureVoI (0.750 goal_rate),
   since it doesn't have to reject the whole response to stay safe. Worth
   checking whether this holds on a real model.
4. ~~**Oracle-vs-learned-risk ablation**~~ **Done.** `SecureVoIOracle` +
   `scripts/oracle_ablation.py`, validated on ScriptedAgent (0.0 gap at
   λ=0.75 — expected, ScriptedAgent already floors at 0 unsafe there). Needs
   a real-model number once a model finishes its full run.
5. ~~**Stratified 30-task stochastic-repetition subset**~~ **Built.**
   `scripts/robustness_subset.py` (3× at temperature=0.7), validated on
   ScriptedAgent (std=0 across reps, as expected — it ignores temperature).
   Needs a real-model run for the actual number.
6. **A second/third test-split-complete model** — the one item still
   genuinely in progress. Two local models running now (see table above);
   Llama-3.3-70B-versatile's test split is also worth retrying since only
   the dev split completed so far.

## One-command orchestration for the next model
```bash
python scripts/run_full_model.py --name <archive-dir-name> \
    --backend <scripted|openai|ollama|hf_local> --model <name>
    # add --base-url/--api-key-env for openai, or nothing extra for ollama/hf_local
```
Chains `tune_dev` → `run_primary --policies main` → `oracle_ablation` →
`guardrail_eval` → `compute_stats` → `make_main_table` → `failure_analysis
--append`, archived under `results/models/<name>/` — replaces manually
copy-pasting flags between each script (the actual source of wasted time
this session, not the underlying pipeline).
