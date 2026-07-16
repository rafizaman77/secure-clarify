# Reproducibility

Exact commands to regenerate every result artifact in this repo from
scratch, in dependency order. Every script here is deterministic given the
same model backend and inputs (temperature=0 for all main runs — see
`scripts/robustness_subset.py` for the one deliberate exception).

## 1. Environment

- Python 3.11, no external packages required for the ScriptedAgent /
  simulation / statistics pipeline (`secure_clarify/`, `scripts/tune_dev.py`,
  `run_primary.py`, `compute_stats.py`, `make_main_table.py`,
  `make_figures.py`, `oracle_ablation.py`, `robustness_subset.py`,
  `failure_analysis.py` — all stdlib only).
- A real-model backend needs exactly one of:
  - **Hosted API** (Groq/Together/Fireworks/OpenRouter): stdlib `urllib`
    only, no extra install. Requires an API key (`GROQ_API_KEY` etc.).
  - **Ollama**: install separately (https://ollama.com), `ollama pull
    <model>`, `ollama serve`. No API key.
  - **Local `transformers`**: needs `torch` + `transformers` +
    `accelerate`. This repo's system Python has a broken numpy/scikit-learn
    ABI that breaks `transformers`' import chain (see
    `days/jul17-18/environment-notes.md`), so an isolated `.venv_model/`
    virtualenv was used instead of touching the system environment.

## 2. Regenerate everything, in order

```bash
# Pilot scale (Jul 12-16): 40 tasks, 8 dev / 32 test
python scripts/freeze_tasks.py
python test_smoke.py
python run_pilot.py                                    # -> results/pilot_summary.json

# Main-experiment scale (Jul 17-19): 120 tasks, 24 dev / 96 test
python scripts/freeze_tasks.py --n-per-domain 60 \
    --tasks-out tasks/main_120.json --manifest-out results/main120_manifest.json

# Dev-only calibration -- fits channel priors + picks lambda + confidence
# threshold using ONLY the 24 dev tasks. Re-run per model family; numbers
# are NOT portable across models.
python scripts/tune_dev.py --tasks tasks/main_120.json \
    --backend <scripted|openai|ollama|hf_local> --model <name> \
    --out results/models/<model-name>/dev_calibration.json

# Primary test-split run -- loads the frozen calibration above, evaluates
# ONLY the 96 test tasks, never re-fits anything.
python scripts/run_primary.py --tasks tasks/main_120.json \
    --calibration results/models/<model-name>/dev_calibration.json \
    --backend <same as above> --model <name> --policies main \
    --out results/models/<model-name>/primary_summary.json \
    --episodes-out results/models/<model-name>/primary_episodes.json

# Statistics + main table (task-level paired bootstrap, 2000 resamples)
python scripts/compute_stats.py \
    --episodes results/models/<model-name>/primary_episodes.json \
    --out results/models/<model-name>/stats.json
python scripts/make_main_table.py    # reads results/stats.json -- point --out/--episodes at the model dir first

# Oracle-vs-learned-risk ablation
python scripts/oracle_ablation.py --tasks tasks/main_120.json \
    --calibration results/models/<model-name>/dev_calibration.json \
    --backend <same> --model <name> --out results/models/<model-name>/oracle_ablation.json

# Stochastic-repetition robustness subset (30 tasks, 3x at temperature=0.7)
python scripts/robustness_subset.py --tasks tasks/main_120.json \
    --calibration results/models/<model-name>/dev_calibration.json \
    --backend <same> --model <name>

# Failure analysis (reads real episodes, categorizes -- not just counts)
python scripts/failure_analysis.py \
    --episodes results/models/<model-name>/primary_episodes.json \
    --model-name <name> --append

# Fill the abstract from real stats (refuses if agent_backend is still
# the ScriptedAgent placeholder)
python scripts/fill_abstract.py --stats results/models/<model-name>/stats.json

# Figures (dependency-free SVG, matplotlib unusable in this environment)
python scripts/make_figures.py

# Regenerate the schedule table (never hand-edit PROGRESS.md's table)
python scripts/update_progress.py --write
```

## 3. Freeze integrity

`results/main120_manifest.json` and `results/split_manifest.json` each carry
a sha256 checksum over the dev task IDs and the test task IDs separately.
Before trusting any primary run's numbers, verify the test split used
matches the frozen checksum -- `scripts/tune_dev.py` and `run_primary.py`
never call `fit_priors()`/sweep lambda on test-split tasks, by construction
(the test split is loaded and immediately filtered to `split == "test"`
after calibration is already frozen from disk), not merely by convention.

## 4. Models evaluated (update as more land)

| Model | Backend | Config recorded in |
|---|---|---|
| Mistral-Nemo-12B | Ollama | `results/dev_calibration.json`, `results/primary_summary.json` (repo default / first model) |
| Llama-3.3-70B-versatile | Groq (hosted API) | `results/models/llama-3.3-70b-versatile/` |
| Qwen2.5-0.5B-Instruct | Local `transformers` | `results/models/qwen2.5-0.5b-instruct/` |

Every result file's `agent_backend` field states exactly which model
produced it -- `scripts/update_progress.py`'s checker and
`scripts/fill_abstract.py`'s guard both key off this field specifically to
prevent a ScriptedAgent placeholder run from ever being mistaken for a real
result.

## 5. What is NOT reproducible byte-for-byte

Hosted API models (Groq etc.) are not guaranteed bit-identical across
provider-side updates even at temperature=0 (model weights/serving stack can
change server-side without notice). Local backends (Ollama, `hf_local`) are
reproducible given the same weights/quantization/hardware. This is disclosed
as a limitation, not hidden.
