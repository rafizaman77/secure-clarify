# Main results table

_Generated from `results/models/gpt-oss-20b-cloud/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:gpt-oss:20b-cloud**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 0.500 [0.396, 0.604] | 0.400 [0.306, 0.504] | 0.583 [0.479, 0.677] | -1.058 [-1.298, -0.798] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 0.531 [0.427, 0.635] | 0.481 [0.377, 0.585] | 0.583 [0.479, 0.677] | -0.988 [-1.258, -0.727] |
| Trusted-Only | 0.406 [0.312, 0.500] | 0.331 [0.233, 0.434] | 0.208 [0.125, 0.292] | -0.335 [-0.533, -0.148] |
| SecureVoI | 0.396 [0.302, 0.490] | 0.321 [0.212, 0.423] | 0.000 [0.000, 0.000] | 0.081 [0.013, 0.167] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.5833 [-0.6771, -0.4896], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: -0.0104 [-0.1031, 0.0844], p=0.8550 (not significant at α=0.05)
