# Main results table

_Generated from `results/models/gpt-oss-120b-cloud/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **ollama:gpt-oss:120b-cloud**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 0.792 [0.698, 0.875] | 0.692 [0.608, 0.765] | 0.583 [0.479, 0.677] | -0.923 [-1.194, -0.631] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 0.729 [0.635, 0.812] | 0.679 [0.585, 0.762] | 0.583 [0.479, 0.677] | -0.904 [-1.185, -0.613] |
| Trusted-Only | 0.542 [0.448, 0.646] | 0.467 [0.359, 0.575] | 0.208 [0.125, 0.292] | -0.315 [-0.523, -0.120] |
| SecureVoI | 0.562 [0.469, 0.667] | 0.487 [0.377, 0.589] | 0.000 [0.000, 0.000] | 0.123 [0.045, 0.210] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.5833 [-0.6771, -0.4896], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.0208 [-0.0823, 0.1354], p=0.7180 (not significant at α=0.05)
