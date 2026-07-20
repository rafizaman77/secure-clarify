# Main results table

_Generated from `results/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:mistral-nemo:12b**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 1.000 [1.000, 1.000] | 0.900 [0.900, 0.900] | 1.000 [1.000, 1.000] | -1.600 [-1.694, -1.506] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 1.000 [1.000, 1.000] | -1.550 [-1.644, -1.456] |
| Trusted-Only | 0.750 [0.667, 0.833] | 0.675 [0.583, 0.767] | 0.000 [0.000, 0.000] | 0.425 [0.321, 0.528] |
| SecureVoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 0.000 [0.000, 0.000] | 0.783 [0.710, 0.856] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -1.0000 [-1.0000, -1.0000], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.2750 [0.1833, 0.3781], p=0.0000 (**significant** at α=0.05)
