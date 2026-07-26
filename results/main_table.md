# Main results table

_Generated from `results/models/mistral-nemo-12b/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:mistral-nemo:12b**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 1.000 [1.000, 1.000] | 0.900 [0.900, 0.900] | 0.583 [0.479, 0.677] | -0.558 [-0.808, -0.287] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 0.583 [0.479, 0.677] | -0.508 [-0.779, -0.258] |
| Trusted-Only | 0.750 [0.667, 0.833] | 0.675 [0.583, 0.767] | 0.208 [0.125, 0.292] | -0.096 [-0.275, 0.075] |
| SecureVoI | 0.750 [0.656, 0.833] | 0.675 [0.572, 0.767] | 0.073 [0.031, 0.135] | 0.071 [-0.090, 0.219] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.5104 [-0.6354, -0.3750], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.0000 [-0.1260, 0.1260], p=0.9080 (not significant at α=0.05)
