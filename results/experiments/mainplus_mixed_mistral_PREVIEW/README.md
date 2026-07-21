# PREVIEW: mainplus on the channel-mixed benchmark (mistral-nemo:12b)

**Status: PREVIEW / DECISION-SUPPORT ONLY — NOT an official result, NOT committed.**

Provenance: run in a throwaway git worktree combining `main`'s code (ChannelHeuristic
+ mainplus + rescore/invariant infra) with the UNMERGED `channel-mix-fix-draft`
branch's mixed tasks. Calibration (lambda + priors) was RE-FIT on the mixed dev
split (dev_calibration_mixed.json: lambda=4.0). Test split = 96 tasks. All 8
invariants pass (scripts/check_invariants.py, exit 0); primary verdict GO.

To make this official: merge `channel-mix-fix-draft` -> main (needs Rafi), then
re-run all 3 models with `--policies mainplus`.

## Headline (adversarial, mixed test split)
| policy            | benign util | adv unsafe | adv util |
|-------------------|-------------|------------|----------|
| never_ask / conf  | -0.150      | 0.000      | -0.150   |
| always_ask        |  0.900      | 0.583      | -0.558   |
| conventional_voi  |  0.950      | 0.583      | -0.508   |
| trusted_only      |  0.675      | 0.208      | -0.096   |
| channel_heuristic |  0.950      | 0.333      | -0.133   |
| **secure_voi**    |  **0.675**  | **0.073**  | **+0.071** |

SecureVoI is the ONLY policy net-positive under attack (+0.071) and ~4.5x safer
than the trivial channel_heuristic (0.073 vs 0.333 unsafe) -- REVERSING the
ScriptedAgent result where the heuristic won. Real-model stage-2 screening is what
closes the gap. Cost: lower benign utility (0.675 vs 0.95) -- a genuine
security/utility tradeoff (lambda=4.0 is risk-averse).
