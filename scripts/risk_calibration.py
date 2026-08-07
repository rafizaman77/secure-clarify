#!/usr/bin/env python3
"""Step 26 of RESEARCH_PLAN.md: is `response_risk` a calibrated probability?

`response_risk` is documented as "P(malicious | cues)" and is used as a
probability: the stage-2 rule `info_value > lambda * risk * expected_loss` is an
expected-loss comparison, which is only meaningful if `risk` really is a
probability. If it is merely a monotone score, lambda is not a loss ratio, its
fitted value has no units, and the "principled decision-theoretic" framing is
decoration over an arbitrary threshold.

Three things are measured against ground truth (`carries_attack`), which the
policy never sees:

  DISCRIMINATION  AUROC -- can it rank an attack above a benign answer at all?
  ACCURACY        Brier score, decomposed into reliability / resolution /
                  uncertainty (Murphy). Reliability is the part that says whether
                  the numbers mean what they claim.
  CALIBRATION     a reliability table: among responses scored ~p, what fraction
                  actually carry an attack? A calibrated score sits on the
                  diagonal.

Every model call this needs (`classify_malice` per distinct text) is already in
the disk cache from earlier runs, so it costs no inference.

Usage:
  SECURE_CLARIFY_CACHE=.cache/agent python3 scripts/risk_calibration.py \
      --model mistral-nemo-12b --backend ollama --backend-model mistral-nemo:12b
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify import estimators as E  # noqa: E402
from secure_clarify.confirmatory import wilson_interval  # noqa: E402
from scripts.model_backends import build_agent  # noqa: E402


def auroc(pos, neg):
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def brier_decomposition(scores, labels, n_bins=10):
    """Brier = reliability - resolution + uncertainty (Murphy 1973).

    reliability: mean squared gap between predicted and observed frequency
                 (LOWER is better; 0 = perfectly calibrated)
    resolution : how far bin frequencies depart from the base rate
                 (HIGHER is better; 0 = the score says nothing)
    uncertainty: base-rate variance, a property of the data not the model
    """
    n = len(scores)
    base = sum(labels) / n
    brier = sum((s - y) ** 2 for s, y in zip(scores, labels)) / n
    bins = {}
    for s, y in zip(scores, labels):
        b = min(n_bins - 1, int(s * n_bins))
        bins.setdefault(b, []).append((s, y))
    rel = res = 0.0
    table = []
    for b in sorted(bins):
        vals = bins[b]
        nk = len(vals)
        mean_p = sum(s for s, _ in vals) / nk
        obs = sum(y for _, y in vals) / nk
        rel += nk * (mean_p - obs) ** 2
        res += nk * (obs - base) ** 2
        lo, hi = wilson_interval(int(round(obs * nk)), nk)
        table.append({"bin": f"[{b / n_bins:.1f},{(b + 1) / n_bins:.1f})",
                      "n": nk, "mean_predicted": round(mean_p, 4),
                      "observed": round(obs, 4),
                      "observed_ci95": [round(lo, 4), round(hi, 4)],
                      "gap": round(mean_p - obs, 4)})
    return {"brier": round(brier, 4), "reliability": round(rel / n, 4),
            "resolution": round(res / n, 4),
            "uncertainty": round(base * (1 - base), 4),
            "base_rate": round(base, 4), "n": n, "table": table}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--backend-model", default="mistral-nemo:12b")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--cache", default=".cache/agent")
    ap.add_argument("--out", default="results/risk_calibration.json")
    args = ap.parse_args()

    calib = json.loads((ROOT / f"results/models/{args.model}/dev_calibration.json")
                       .read_text(encoding="utf-8"))
    E.set_priors({Channel(c): p for c, p in calib["fitted_channel_priors"].items()})
    agent = CachingAgent(build_agent(args.backend, args.backend_model,
                                     args.base_url, args.api_key_env, args.host),
                         disk_cache_dir=args.cache or None)

    tasks = [load_task(d) for d in
             json.loads((ROOT / args.tasks).read_text(encoding="utf-8"))]
    scores, labels, by_cond = [], [], {}
    for t in tasks:
        for q in t.candidate_questions:
            for r in t.responses:
                if r.qid != q.qid:
                    continue
                s = E.response_risk(r.text, t, q, r.channel, agent)
                y = 1.0 if r.carries_attack else 0.0
                scores.append(s)
                labels.append(y)
                cond = r.condition.value if hasattr(r.condition, "value") else r.condition
                by_cond.setdefault(cond, []).append(s)

    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    dec = brier_decomposition(scores, labels)
    rep = {"model": args.model, "n": len(scores),
           "auroc_attack_vs_benign": round(auroc(pos, neg), 4),
           **dec,
           "mean_risk_by_condition": {c: round(sum(v) / len(v), 4)
                                      for c, v in sorted(by_cond.items())}}

    dest = ROOT / args.out
    existing = {}
    if dest.exists():
        try:
            existing = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing[args.model] = rep
    dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    print(f"\n{args.model}: response_risk as a probability of attack  (n={rep['n']})")
    print(f"  AUROC (attack vs non-attack) : {rep['auroc_attack_vs_benign']:.3f}")
    print(f"  Brier                        : {rep['brier']:.4f}")
    print(f"    reliability (lower better) : {rep['reliability']:.4f}   <- miscalibration")
    print(f"    resolution  (higher better): {rep['resolution']:.4f}")
    print(f"    uncertainty (base rate var): {rep['uncertainty']:.4f}  "
          f"(base rate {rep['base_rate']:.3f})")
    print(f"\n  reliability table -- a calibrated score sits on the diagonal:")
    print(f"    {'bin':12s} {'n':>4s} {'predicted':>10s} {'observed':>10s} "
          f"{'95% CI':>16s} {'gap':>8s}")
    for row in rep["table"]:
        ci = f"[{row['observed_ci95'][0]:.2f},{row['observed_ci95'][1]:.2f}]"
        print(f"    {row['bin']:12s} {row['n']:4d} {row['mean_predicted']:10.3f} "
              f"{row['observed']:10.3f} {ci:>16s} {row['gap']:+8.3f}")
    print(f"\n  mean risk by condition: "
          + "  ".join(f"{c}={v:.3f}" for c, v in rep["mean_risk_by_condition"].items()))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
