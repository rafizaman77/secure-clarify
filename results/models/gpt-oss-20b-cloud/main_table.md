# Main results table

_Generated from `results/models/gpt-oss-20b-cloud/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:gpt-oss:20b-cloud**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 0.500 [0.396, 0.604] | 0.400 [0.306, 0.504] | 1.000 [1.000, 1.000] | -2.100 [-2.100, -2.100] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 0.562 [0.469, 0.656] | 0.512 [0.408, 0.606] | 1.000 [1.000, 1.000] | -2.050 [-2.050, -2.050] |
| Trusted-Only | 0.438 [0.333, 0.542] | 0.362 [0.262, 0.469] | 0.000 [0.000, 0.000] | 0.227 [0.137, 0.325] |
| SecureVoI | 0.562 [0.469, 0.656] | 0.512 [0.419, 0.606] | 0.000 [0.000, 0.000] | 0.419 [0.325, 0.523] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -1.0000 [-1.0000, -1.0000], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.1500 [0.0854, 0.2281], p=0.0000 (**significant** at α=0.05)
