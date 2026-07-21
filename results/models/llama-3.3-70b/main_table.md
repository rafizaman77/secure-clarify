# Main results table

_Generated from `results/models/llama-3.3-70b/stats.json` -- 96 test tasks, 2000 bootstrap resamples, 95% CI. Agent backend: **openai:llama-3.3-70b-versatile**._

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Always Ask | 0.979 [0.948, 1.000] | 0.858 [0.785, 0.900] | 0.594 [0.490, 0.688] | -0.892 [-1.173, -0.590] |
| Confidence Threshold | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] | 0.000 [0.000, 0.000] | -0.150 [-0.150, -0.150] |
| Conventional VoI | 1.000 [1.000, 1.000] | 0.950 [0.950, 0.950] | 0.573 [0.469, 0.667] | -0.779 [-1.081, -0.487] |
| Trusted-Only | 0.750 [0.667, 0.833] | 0.675 [0.583, 0.767] | 0.188 [0.115, 0.271] | -0.158 [-0.373, 0.038] |
| SecureVoI | 0.750 [0.656, 0.833] | 0.675 [0.572, 0.767] | 0.000 [0.000, 0.000] | 0.217 [0.126, 0.314] |

## Key comparisons (paired bootstrap, same test tasks)

- secure voi minus conventional voi  adversarial unsafe rate: -0.5729 [-0.6667, -0.4792], p=0.0000 (**significant** at α=0.05)
- secure voi minus trusted only  benign utility: +0.0000 [-0.1260, 0.1260], p=0.9080 (not significant at α=0.05)
