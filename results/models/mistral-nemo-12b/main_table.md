# Main results table

_Generated from `results/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:mistral-nemo:12b**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 0.500 [0.406, 0.604] | -0.550 [-0.831, -0.269] |
| Trusted-Only | 0.750 [0.667, 0.833] | 0.675 [0.583, 0.767] | 0.000 [0.000, 0.000] | 0.425 [0.318, 0.535] |
| SecureVoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 0.083 [0.031, 0.146] | 0.617 [0.429, 0.773] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.4167 [-0.5208, -0.3229], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.2750 [0.1833, 0.3667], p=0.0000 (**significant** at α=0.05)
