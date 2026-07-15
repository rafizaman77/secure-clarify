# Main results table

_Generated from `results/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ScriptedAgent (placeholder -- no open-weight model wired in yet)**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 0.417 [0.323, 0.521] | -0.217 [-0.477, 0.044] |
| Trusted-Only | 0.750 [0.667, 0.833] | 0.637 [0.550, 0.725] | 0.000 [0.000, 0.000] | 0.388 [0.283, 0.495] |
| SecureVoI | 1.000 [1.000, 1.000] | 0.921 [0.916, 0.926] | 0.042 [0.010, 0.083] | 0.796 [0.671, 0.891] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.3750 [-0.4688, -0.2812], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.2833 [0.1974, 0.3714], p=0.0000 (**significant** at α=0.05)

**This table is still ScriptedAgent, not a measured result on a real open-weight model.** Re-run `scripts/run_primary.py` and `scripts/compute_stats.py` with `--backend hf_local`/`openai`/`ollama` before using these numbers in the paper.
