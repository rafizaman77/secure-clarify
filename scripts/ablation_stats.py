#!/usr/bin/env python3
"""Bootstrap CIs and paired significance tests for the stage-1/stage-2
screened ablation (2026-07-28).

WHY: the ablation's headline numbers were reported as bare point estimates
while every other number in the paper carries a task-level bootstrap CI. That
holds the paper's central NEW claim to a weaker evidentiary standard than the
results it is meant to support. This script closes that gap.

The comparison that matters is ScreenedConventionalVoI vs SecureVoI on
adversarial unsafe rate: both stages differ by exactly one term (stage-1's
channel-risk penalty), so a significant difference is direct evidence that
stage 1 does separable work, and a non-significant one is evidence it does not.

Reuses compute_stats.py's paired_bootstrap_diff verbatim -- same task-level
resampling, same two-sided bootstrap p-value (including its all-zero-vs-
all-zero guard, which matters here because several cells sit at exactly
0.000 on the explicit tier).

Usage:
  python scripts/ablation_stats.py --out results/ablation_stats.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.compute_stats import (paired_bootstrap_diff, bootstrap_ci,  # noqa: E402
                                   _rate, _seeded_rng, N_BOOTSTRAP, CI)

A = "screened_conventional_voi"
B = "secure_voi"
C = "conventional_voi"


def load(path: Path):
    by_task = defaultdict(list)
    for e in json.loads(path.read_text(encoding="utf-8")):
        by_task[e["task_id"]].append(e)
    return by_task, sorted(by_task)


def analyze(path: Path, condition: str, label: str) -> dict | None:
    if not path.exists():
        return None
    by_task, task_ids = load(path)
    rng = _seeded_rng()
    out = {"episodes_file": str(path.relative_to(ROOT)), "n_tasks": len(task_ids),
           "condition": condition}
    for pol in (C, A, B):
        pt, lo, hi = bootstrap_ci(task_ids, by_task, pol, condition,
                                  "unsafe", _rate, _seeded_rng())
        out[f"{pol}__unsafe_rate"] = {"point": pt, "ci_lo": lo, "ci_hi": hi}
    # THE test: does removing stage 1 (keeping the identical screen) change safety?
    out["screened_minus_secure__unsafe_rate"] = paired_bootstrap_diff(
        task_ids, by_task, A, B, condition, "unsafe", _rate, rng)
    # Reference: the full method's advantage over the risk-blind baseline.
    out["secure_minus_conventional__unsafe_rate"] = paired_bootstrap_diff(
        task_ids, by_task, B, C, condition, "unsafe", _rate, _seeded_rng())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/ablation_stats.json")
    args = ap.parse_args()

    models = ["mistral-nemo-12b", "llama-3.3-70b", "gpt-oss-20b-cloud",
              "gpt-oss-120b-cloud"]
    results: dict = {"n_bootstrap": N_BOOTSTRAP, "ci": CI,
                     "resampling_unit": "task_id (paired across policies within a task)",
                     "models": {}}
    for m in models:
        entry = {}
        for fname, cond, lab in [
            ("screened_ablation_episodes.json", "adversarial", "explicit"),
            ("screened_ablation_stealth_episodes.json", "adversarial_stealth", "stealth"),
        ]:
            r = analyze(ROOT / "results" / "models" / m / fname, cond, lab)
            if r:
                entry[lab] = r
        # three-domain diversity set
        r = analyze(ROOT / "results" / "models" / f"{m}-diversity" /
                    "screened_ablation_stealth_episodes.json",
                    "adversarial_stealth", "diversity_stealth")
        if r:
            entry["diversity_stealth"] = r
        if entry:
            results["models"][m] = entry

    out_path = ROOT / args.out
    out_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print(f"Task-level paired bootstrap, {N_BOOTSTRAP} resamples, {int(CI*100)}% CI")
    print(f"\nH0: removing stage 1 (identical stage-2 screen) does not change "
          f"adversarial unsafe rate\n")
    print(f"{'model':20s} {'tier':18s} {'n':>4s} {'screened-secure':>16s} "
          f"{'95% CI':>18s} {'p':>7s}  sig")
    for m, tiers in results["models"].items():
        for lab, r in tiers.items():
            d = r["screened_minus_secure__unsafe_rate"]
            print(f"{m:20s} {lab:18s} {r['n_tasks']:4d} {d['point']:+16.4f} "
                  f"[{d['ci_lo']:+.3f},{d['ci_hi']:+.3f}] {d['p_value']:7.4f}  "
                  f"{'YES' if d['significant_at_0.05'] else 'no'}")
    print(f"\nWrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
