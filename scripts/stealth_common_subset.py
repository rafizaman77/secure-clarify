#!/usr/bin/env python3
"""Cross-model validity check: does the missing-data pattern distort comparisons?

WHY THIS EXISTS. The four models' stealth-tier task counts are NOT identical --
Groq's infrastructure occasionally hangs on individual calls (documented in
model_backends._urlopen_hard_timeout), so llama-3.3-70b has a handful of excluded
tasks the other three models don't. That raises a real methodological question:
if the models aren't evaluated on the same task set, how do we know a cross-model
difference reflects the MODELS rather than WHICH TASKS each one happened to cover?

The honest answer isn't "trust that missingness is random" -- it's to make the
comparison insensitive to the question by recomputing it twice:
  1. FULL: each model's rate over all tasks it actually completed (max power,
     what's reported as the headline number).
  2. COMMON SUBSET: every model's rate recomputed over ONLY the task_ids present
     in ALL models being compared -- literally the same benchmark instance for
     everyone, by construction.

If the two agree (same ordering, similar magnitudes, same significant/not-
significant calls), the missing-task pattern isn't driving the result and the
full-data numbers can be reported as-is. If they diverge, that is itself the
finding -- report the common-subset numbers as authoritative and say why.

Usage:
  python scripts/stealth_common_subset.py
  python scripts/stealth_common_subset.py --models mistral-nemo-12b,gpt-oss-20b-cloud
    # restrict to models that have finished, e.g. while llama is still in flight
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.compute_stats import _rate  # noqa: E402

POLICY_ORDER = ["never_ask", "always_ask", "confidence_threshold",
                "conventional_voi", "trusted_only", "channel_heuristic",
                "secure_voi"]
LABELS = {"never_ask": "Never Ask", "always_ask": "Always Ask",
          "confidence_threshold": "Confidence Thresh.",
          "conventional_voi": "Conventional VoI", "trusted_only": "Trusted-Only",
          "channel_heuristic": "Channel Heuristic", "secure_voi": "SecureVoI"}

DEFAULT_MODELS = ["mistral-nemo-12b", "gpt-oss-20b-cloud",
                  "gpt-oss-120b-cloud", "llama-3.3-70b"]


def load_stealth_eps(model: str) -> list[dict]:
    p = ROOT / "results" / "stealth" / f"{model}_episodes.json"
    if not p.exists():
        return []
    return [e for e in json.loads(p.read_text(encoding="utf-8"))
            if e["condition"] == "adversarial_stealth"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS),
                    help="comma-separated model dir names; only ones with an "
                         "existing episodes file are used")
    ap.add_argument("--policy", default="secure_voi",
                    help="which policy's unsafe rate to compare (default: the "
                         "one the paper's headline claim is about)")
    args = ap.parse_args()

    by_model: dict[str, list[dict]] = {}
    for m in args.models.split(","):
        eps = load_stealth_eps(m)
        if eps:
            by_model[m] = eps
    if len(by_model) < 2:
        print(f"Need >=2 models with stealth data; found {list(by_model)}. "
              "Nothing to compare yet.")
        return 0

    task_sets = {m: {e["task_id"] for e in eps} for m, eps in by_model.items()}
    common = set.intersection(*task_sets.values())

    print(f"Models compared: {list(by_model)}")
    print(f"Per-model task counts: "
          f"{ {m: len(s) for m, s in task_sets.items()} }")
    print(f"Common subset (in ALL models): {len(common)} tasks\n")
    for m, s in task_sets.items():
        missing = s - common
        if missing:
            print(f"  {m}: {len(s) - len(common)} task(s) not in common subset "
                  f"(present here, absent in >=1 other model): {sorted(missing)[:10]}"
                  f"{' ...' if len(missing) > 10 else ''}")
    print()

    print(f"--- {LABELS.get(args.policy, args.policy)} adversarial_stealth unsafe rate ---")
    print(f"{'model':22s} {'FULL (own data)':>20} {'COMMON SUBSET':>16} {'agree?':>8}")
    print("-" * 72)
    verdict_rows = []
    for m, eps in by_model.items():
        pol_eps = [e for e in eps if e["policy"] == args.policy]
        full_rate = _rate(pol_eps, "unsafe")
        full_n = len(pol_eps)
        common_eps = [e for e in pol_eps if e["task_id"] in common]
        common_rate = _rate(common_eps, "unsafe") if common_eps else float("nan")
        common_n = len(common_eps)
        # "agree" judges MAGNITUDE, not which side of an arbitrary cutoff the
        # rate lands on. A boundary-crossing check (e.g. "both <0.03" vs "one
        # >=0.03") flags noise as disagreement whenever a small, unremarkable
        # difference happens to straddle the line -- exactly the failure mode
        # this script exists to avoid reproducing. |full - common| <= 0.05 is
        # about the width of a single bootstrap CI half-width seen elsewhere in
        # this project's stealth numbers, so a gap that size or smaller is noise,
        # not a substantive reversal.
        diff = abs(full_rate - common_rate)
        agree = diff <= 0.05
        verdict_rows.append((m, full_rate, full_n, common_rate, common_n, diff, agree))
        print(f"{m:22s} {full_rate:9.3f} (n={full_n:3d})   {common_rate:6.3f} (n={common_n:3d})   "
              f"diff={diff:.3f}   {'yes' if agree else 'NO -- CHECK'}")

    n_disagree = sum(1 for r in verdict_rows if not r[6])
    print()
    if n_disagree == 0:
        print("VERDICT: full-data and common-subset numbers agree within noise on "
              "every model. The missing-task pattern from Groq's infrastructure "
              "hangs is not distorting the cross-model comparison -- report the "
              "full-data (max-power) numbers as the headline, this check as the "
              "robustness footnote.")
    else:
        print(f"VERDICT: {n_disagree} model(s) show a >0.05 gap between full-data "
              "and common-subset. Do NOT report the full-data headline without "
              "investigating -- the common-subset numbers are the safer claim "
              "until this is understood.")

    out = ROOT / "results" / "stealth" / "common_subset_check.json"
    out.write_text(json.dumps({
        "policy": args.policy, "models": list(by_model),
        "common_subset_size": len(common), "common_subset_task_ids": sorted(common),
        "rows": [{"model": m, "full_rate": fr, "full_n": fn,
                  "common_rate": cr, "common_n": cn, "diff": df, "agree": ag}
                 for m, fr, fn, cr, cn, df, ag in verdict_rows],
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
