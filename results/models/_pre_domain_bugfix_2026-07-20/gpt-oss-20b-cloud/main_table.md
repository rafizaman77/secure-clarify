# Main results table

_Generated from `results/models/gpt-oss-20b-cloud/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:gpt-oss:20b-cloud**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 0.583 [0.479, 0.688] | 0.483 [0.390, 0.577] | 0.625 [0.531, 0.719] | -0.975 [-1.256, -0.694] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 0.573 [0.479, 0.677] | 0.502 [0.398, 0.606] | 0.500 [0.396, 0.604] | -1.050 [-1.238, -0.863] |
| Trusted-Only | 0.417 [0.312, 0.510] | 0.321 [0.215, 0.427] | 0.000 [0.000, 0.000] | 0.206 [0.117, 0.302] |
| SecureVoI | 0.573 [0.469, 0.667] | 0.502 [0.398, 0.606] | 0.094 [0.042, 0.156] | 0.200 [0.033, 0.367] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.4062 [-0.5104, -0.3021], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.1813 [0.1104, 0.2698], p=0.0000 (**significant** at α=0.05)
