#!/usr/bin/env python3
"""Jul 22-23: compare Conventional VoI, Post-Hoc Guardrail, and SecureVoI on
the SAME frozen test split with the SAME dev-tuned lambda. Post-Hoc Guardrail
and SecureVoI represent the two positions the plan wants measured against
each other: gate the response before acting on it (SecureVoI) vs. let the
agent decide freely and screen the resulting action plan afterward
(Post-Hoc Guardrail).

Usage:
  python scripts/guardrail_eval.py --tasks tasks/main_120.json \
      --calibration results/models/<name>/dev_calibration.json --backend <...> --model <...>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import ConventionalVoI, SecureVoI  # noqa: E402
from secure_clarify.guardrail import run_posthoc_grid  # noqa: E402
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
    ap.add_argument("--out", default="results/guardrail_eval.json")
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

    conditions = [Condition.BENIGN, Condition.ADVERSARIAL]
    eps = run_grid(test_tasks, [ConventionalVoI(), SecureVoI(lam=lam)], agent, conditions=conditions)
    eps += run_posthoc_grid(test_tasks, agent, conditions=conditions)
    table = summarize(eps)

    backend_label = ("ScriptedAgent (placeholder -- no open-weight model wired in yet)"
                     if args.backend == "scripted" else f"{args.backend}:{args.model}")
    result = {
        "agent_backend": backend_label,
        "lambda_used": lam,
        "n_test_tasks": len(test_tasks),
        "table": table,
    }
    out_path = ROOT / args.out
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"Agent backend: {backend_label}, lambda={lam}\n")
    print(f"{'policy|condition':32s} {'goal':>6} {'unsafe':>7} {'util':>7} {'n':>4}")
    print("-" * 60)
    for key in sorted(table):
        r = table[key]
        print(f"{key:32s} {r['goal_rate']:6.3f} {r['unsafe_rate']:7.3f} {r['utility']:7.3f} {r['n']:4d}")
    print(f"\nWrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
