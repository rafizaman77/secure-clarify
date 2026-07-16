#!/usr/bin/env python3
"""Jul 22-23 deliverable: oracle-vs-learned-risk ablation.

Runs SecureVoI (learned classify_malice) and SecureVoIOracle (ground-truth
carries_attack) side by side on the SAME test-split tasks with the SAME
frozen lambda, and reports how much of the gap to a perfect classifier
remains. This never touches dev/test-split hygiene: lambda still comes from
scripts/tune_dev.py's dev-only fit; the oracle policy only uses ground truth
at evaluation/accept time (a legitimate ablation upper bound), never to
re-tune anything.

Usage:
  python scripts/oracle_ablation.py --tasks tasks/main_120.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import SecureVoI, SecureVoIOracle  # noqa: E402
from secure_clarify.runner import run_grid, summarize  # noqa: E402
from secure_clarify import estimators  # noqa: E402
from scripts.model_backends import build_agent, add_backend_args  # noqa: E402


def load_tasks(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [load_task(d) for d in data]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--calibration", default="results/dev_calibration.json")
    ap.add_argument("--out", default="results/oracle_ablation.json")
    add_backend_args(ap)
    args = ap.parse_args()

    calib = json.loads((ROOT / args.calibration).read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    priors = {Channel(ch): p for ch, p in calib["fitted_channel_priors"].items()}
    estimators.set_priors(priors)

    all_tasks = load_tasks(ROOT / args.tasks)
    test_tasks = [t for t in all_tasks if t.split == "test"]
    if not test_tasks:
        raise SystemExit(f"No test-split tasks found in {args.tasks}")

    raw_agent = build_agent(args.backend, args.model, args.base_url,
                            args.api_key_env, args.host)
    agent = CachingAgent(raw_agent)
    policies = [SecureVoI(lam=lam), SecureVoIOracle(lam=lam)]
    eps = run_grid(test_tasks, policies, agent,
                   conditions=[Condition.BENIGN, Condition.ADVERSARIAL],
                   sev_profile="medium")
    table = summarize(eps)

    learned_adv = table["secure_voi|adversarial"]
    oracle_adv = table["secure_voi_oracle|adversarial"]
    learned_benign = table["secure_voi|benign"]
    oracle_benign = table["secure_voi_oracle|benign"]

    remaining_gap = learned_adv["unsafe_rate"] - oracle_adv["unsafe_rate"]

    backend_label = ("ScriptedAgent (placeholder -- no open-weight model wired in yet)"
                     if args.backend == "scripted" else f"{args.backend}:{args.model}")
    result = {
        "agent_backend": backend_label,
        "lambda_used": lam,
        "n_test_tasks": len(test_tasks),
        "learned_classify_malice": {
            "adversarial_unsafe_rate": learned_adv["unsafe_rate"],
            "benign_utility": learned_benign["utility"],
        },
        "oracle_ground_truth": {
            "adversarial_unsafe_rate": oracle_adv["unsafe_rate"],
            "benign_utility": oracle_benign["utility"],
        },
        "remaining_unsafe_rate_gap_to_oracle": round(remaining_gap, 4),
        "interpretation": (
            "remaining_unsafe_rate_gap_to_oracle is the adversarial unsafe rate "
            "a PERFECT classify_malice could still remove -- i.e. how much "
            "SecureVoI's current safety comes from stage-1 acquisition "
            "discipline (asking the right question of the right channel) "
            "versus stage-2's imperfect learned malice classifier."
        ),
    }
    out_path = ROOT / args.out
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"Agent backend: {backend_label}, lambda={lam}\n")
    print(f"{'':32s} {'adv_unsafe':>11} {'benign_util':>12}")
    print(f"{'SecureVoI (learned)':32s} {learned_adv['unsafe_rate']:>11.3f} {learned_benign['utility']:>12.3f}")
    print(f"{'SecureVoIOracle (ground truth)':32s} {oracle_adv['unsafe_rate']:>11.3f} {oracle_benign['utility']:>12.3f}")
    print(f"\nRemaining unsafe-rate gap to a perfect classifier: {remaining_gap:.4f}")
    print(f"Wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
