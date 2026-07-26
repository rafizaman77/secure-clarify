# What lives in `results/`

## The rule
**`results/models/<name>/` is authoritative for a model. Top-level `results/*.json`
is a convenience mirror of the DEFAULT model run (currently `mistral-nemo-12b`).**

Most scripts default to the top-level paths (`--episodes results/primary_episodes.json`,
`--calibration results/dev_calibration.json`, ...), so those files must never be allowed
to drift from the run they claim to represent. They have drifted twice, and both times
it silently produced wrong published numbers:

- `aggregate_models.py` published `cross_model_comparison.md` with a **pre-merge**
  mistral row (conv `1.000` / secure `0.000`) instead of the real `0.583` / `0.073`.
- `make_figures.py` charted `secure_voi = 0.000` from a stale top-level `stats.json`.

Both scripts now prefer `results/models/<name>/` and ignore `_`-prefixed archives, and
the top-level mirror has been refreshed from `results/models/mistral-nemo-12b/`.

## If you re-run the default model
Refresh the mirror so the defaults stay honest:

    D=results/models/mistral-nemo-12b
    cp $D/{primary_episodes,primary_summary,stats,dev_calibration,oracle_ablation,guardrail_eval}.json results/
    cp $D/main_table.md results/
    python scripts/check_invariants.py     # uses the top-level defaults

## Naming conventions
- `results/models/<name>/` — one completed model pipeline (authoritative).
- `results/models/_<something>/` — **archive of a superseded run.** The leading
  underscore is load-bearing: `aggregate_models.py` skips these, because they carry the
  same `agent_backend` label as the live run and would otherwise win the dedupe.
- `results/cross_model_comparison.md` — regenerate with `python scripts/aggregate_models.py`.

## Not model-specific (do not overwrite from a model dir)
`split_manifest.json`, `main120_manifest.json`, `frontier.json`, `progress_state.json`,
`cross_model_comparison.md`.

## Before trusting any number
    python scripts/check_invariants.py --episodes <episodes> --tasks tasks/main_120.json
    python scripts/rescore.py --episodes <episodes> --tasks tasks/main_120.json
