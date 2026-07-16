# Jul 22-23 — Third model, ablations, robustness subset

**Status: 🟡 In progress** — two of five items below are done.

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
| `Qwen2.5-0.5B-Instruct` (local `hf_local`, no Ollama/API-key needed) | in progress | in progress | This sandbox has no Ollama/API keys (Anagh's machine did); running a small model locally via `transformers` in an isolated `.venv_model/` instead — see [environment-notes.md](environment-notes.md) |

"Three models" in the plan means three **test-split-complete** runs with
their own dev-tuned λ/priors and bootstrap stats — only Mistral-Nemo is there
today.

## Concrete steps (in dependency order)
1. ~~**Two more policies** to reach "six."~~ **Done.** Checked the plan's
   exact policy table (section 10) rather than assume — the six are Never
   Ask / **Always Ask** / **Confidence Threshold** / Conventional VoI /
   Trusted-Only / SecureVoI. Post-hoc guardrail is explicitly "Optional" and
   scope-cut #2 if behind schedule (section 17) — it was never one of the
   six. Both implemented in `secure_clarify/policies.py`
   (`MAIN_POLICIES`), smoke-tested, and wired into `run_primary.py` via
   `--policies main` (default stays `pilot` = the original 4, so Anagh's
   archived Mistral-Nemo results remain exactly reproducible).
2. ~~Confidence-threshold calibration~~ **Done.** `scripts/tune_dev.py` now
   also picks the threshold as the median observed sampled-intent agreement
   across dev tasks (documented reasoning: the plan gives the decision rule
   but not a selection formula, so this is a stated judgment call, not an
   arbitrary default).
3. **A second/third test-split-complete model** — in progress now (see table
   above). Also worth revisiting: Llama-3.3-70B only needs its test split
   finished (dev calibration already done) — cheapest path to model #2 if
   Ollama/Groq access becomes available in whatever environment runs it next.
4. **Oracle-vs-learned-risk ablation** — how much of SecureVoI's benefit
   survives if `response_risk` used the ground-truth `carries_attack` label
   instead of `classify_malice`'s learned signal (an oracle upper bound). Not
   started.
5. **Stratified 30-task stochastic-repetition subset** — needs a controlled
   randomness source (currently fully deterministic at temperature=0 by
   design); decide the operationalization (temperature>0 sampling vs.
   re-running task_factory with a different seed) before implementing. Not
   started.

## How to run the 6-policy set against the next model
```bash
python scripts/smoke_real_model.py --backend ollama --model <name>          # sanity check
python scripts/tune_dev.py    --tasks tasks/main_120.json --backend ollama --model <name>
python scripts/run_primary.py --tasks tasks/main_120.json --backend ollama --model <name> --policies main
python scripts/compute_stats.py
python scripts/make_main_table.py
```
Swap `--backend ollama --model <name>` for `--backend hf_local --model
<hf-repo-id>` or `--backend openai --base-url ... --model ...` depending on
what's available in the environment actually running it.
