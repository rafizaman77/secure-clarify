# Jul 20 — Statistics, main table, frontier, real abstract

**Status: 🟡 Partial** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal (from the plan)
Turn the primary test-split run into the paper's actual reporting artifacts:
significance-tested statistics, the main results table, the safety-utility
frontier figure's data, and a filled-in abstract.

## What's fully done

| Item | Evidence |
|---|---|
| Bootstrap confidence intervals, per policy × condition | `scripts/compute_stats.py` → `results/stats.json` — 2000 task-level bootstrap resamples, 95% CI, on `results/primary_episodes.json` |
| Paired significance tests | Same script: SecureVoI vs. ConventionalVoI's adversarial unsafe rate (**p < 0.001**, −0.375 [−0.469, −0.281]) and SecureVoI vs. Trusted-Only's benign utility (**p < 0.001**, +0.283 [0.197, 0.371]) |
| Publication-style main table | `scripts/make_main_table.py` → `results/main_table.md` |
| Safety-utility frontier | `results/frontier.json` (built earlier from the pilot's λ sweep, docs/03_gonogo_memo.md) |
| Per-episode raw data for reproducibility | `results/primary_episodes.json` (768 episodes: 96 tasks × 4 policies × 2 conditions) |

## Key methodological decision: task-level, not episode-level, bootstrap
All 4 policies are evaluated on the **same 96 test tasks** — policies are
paired within a task, not independent samples. `compute_stats.py` resamples
*task IDs* with replacement (not individual episodes), so the correlation
between "this task is easy/hard for every policy" is preserved in the CIs.
Resampling episodes independently would understate the true uncertainty.

## The one blocker (same root cause as every day since Jul 17)
`results/stats.json`'s `agent_backend` is still the ScriptedAgent placeholder.
Every confidence interval and p-value above is real statistics **computed
correctly on synthetic-for-now data** — the bootstrap machinery doesn't need
to change at all once a real model exists, only the input episodes do.

`abstract.md`'s 7 bracketed placeholders (`[N] [M] [X] [Y] [Z] [B] [A]`)
remain unfilled **on purpose**: filling them with ScriptedAgent numbers would
misrepresent a heuristic stand-in as the paper's actual open-weight-model
result, which is exactly the kind of overclaiming this repo's tooling
(`scripts/update_progress.py`'s `_uses_real_model_backend()` check) exists to
catch and prevent.

## What's needed to fully finish
1. A real model backend run through `scripts/run_primary.py` (see
   [jul17-18](../jul17-18/README.md) and [jul19](../jul19/README.md)).
2. Re-run `scripts/compute_stats.py` and `scripts/make_main_table.py` against
   that real `results/primary_episodes.json` — no code changes needed, just
   re-invocation.
3. Map the real numbers into `abstract.md`'s placeholders:
   - `[N]` = task count (120, or however many survive real-model validation)
   - `[M]` = number of model families evaluated
   - `[X]` = benign task-success percentage-point lift (Conventional VoI −
     Never Ask, benign goal rate)
   - `[Y]`/`[Z]` = adversarial unsafe-rate range (Never Ask → Conventional VoI)
   - `[B]` = % of the benign improvement SecureVoI recovers vs. Conventional VoI
   - `[A]` = % reduction in unsafe actions SecureVoI achieves vs. Conventional VoI

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md).
