# Jul 20 — Statistics, main table, frontier, real abstract

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal (from the plan)
Turn the primary test-split run into the paper's actual reporting artifacts:
significance-tested statistics, the main results table, the safety-utility
frontier figure's data, and a filled-in abstract.

## What's done, on real data (agent_backend: `ollama:mistral-nemo:12b`)

| Item | Evidence |
|---|---|
| Bootstrap confidence intervals, per policy × condition | `results/stats.json` — 2000 task-level bootstrap resamples, 95% CI, over `results/primary_episodes.json` |
| Paired significance tests | SecureVoI vs. Conventional VoI's adversarial unsafe rate: **−0.417 [−0.521, −0.323], p<0.001**. SecureVoI vs. Trusted-Only's benign utility: **+0.275 [0.183, 0.367], p<0.001**. |
| Publication-style main table | `results/main_table.md` (reproduced below) |
| Safety-utility frontier | `results/frontier.json` |
| Abstract filled with real numbers | `abstract.md` — `scripts/fill_abstract.py`'s honesty guard (which refuses to run on a ScriptedAgent backend) let this through because the backend is now real |

## Main table (96 test tasks)
| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |
|---|---|---|---|---|
| Never Ask | 0.000 | −0.150 | 0.000 | −0.150 |
| Conventional VoI | 1.000 | 0.950 | 0.500 [0.406, 0.604] | −0.550 |
| Trusted-Only | 0.750 | 0.675 | 0.000 | 0.425 |
| SecureVoI | 1.000 | **0.950** | **0.083** [0.031, 0.146] | 0.617 |

SecureVoI matches Conventional VoI's benign utility exactly (1.000/0.950 vs.
1.000/0.950) while cutting adversarial unsafe actions by 83% (0.500 → 0.083).

## The abstract now reads (real numbers, not placeholders)
> Evaluated on a held-out test split (96 tasks) with an open-weight model
> (Mistral-Nemo-12B; the same trade-off reproduces on the development split
> with Llama-3.3-70B, while more heavily safety-tuned models such as
> GPT-OSS-20B and Qwen3-32B resist the injections and show little
> conventional-clarification harm), conventional clarification improves
> benign task success by 100 percentage points but raises unsafe-action
> rates from 0% to 50% under adversarial responses. SecureVoI recovers 100%
> of the benign improvement while reducing unsafe actions by 83% (from 50%
> to 8%) [...]

Note this is honestly scoped to **the two baselines actually implemented and
run** (risk-blind Conventional VoI, Trusted-Only) — the abstract does not
claim results for confidence-threshold or post-hoc-guardrail baselines,
which aren't built yet (Jul 22-23).

## What's still open
- A second/third **test-split-complete** model (Llama-3.3-70B only reached
  dev; GPT-OSS-20B/Qwen3-32B were tried and found to resist injections, which
  is itself reported, but weren't run to a full test-split statistics pass).
- `docs/failure_analysis.md` and `figures/` (Jul 24) still don't exist.

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#gap-closed--real-open-weight-models-wired-in-held-out-numbers-obtained).
