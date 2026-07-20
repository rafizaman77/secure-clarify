# Main results table

_Generated from `results/models/gpt-oss-120b-cloud/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:gpt-oss:120b-cloud**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 0.802 [0.719, 0.885] | 0.702 [0.619, 0.775] | 0.646 [0.552, 0.750] | -1.038 [-1.319, -0.756] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 0.750 [0.656, 0.833] | 0.700 [0.606, 0.783] | 0.521 [0.417, 0.625] | -1.092 [-1.279, -0.904] |
| Trusted-Only | 0.573 [0.469, 0.677] | 0.498 [0.388, 0.601] | 0.000 [0.000, 0.000] | 0.300 [0.201, 0.400] |
| SecureVoI | 0.750 [0.667, 0.833] | 0.700 [0.617, 0.783] | 0.083 [0.031, 0.135] | 0.346 [0.169, 0.523] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.4375 [-0.5417, -0.3438], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.2021 [0.1219, 0.2917], p=0.0000 (**significant** at α=0.05)
