#!/usr/bin/env python3
"""Jul 20-21 deliverable: fill abstract.md's bracketed placeholders from
results/stats.json + results/models_evaluated.json.

Refuses to run if the backend is still ScriptedAgent -- same honesty guard
used by scripts/update_progress.py's _uses_real_model_backend(). Filling the
abstract with placeholder-backend numbers would misrepresent a heuristic
stand-in as the paper's actual result, which is exactly what this repo's
tooling exists to prevent (see docs/DAILY_LOG.md).

Mapping (matches abstract.md's sentence structure):
  [N] = number of test-split tasks evaluated
  [M] = number of distinct model families evaluated (results/models_evaluated.json)
  [X] = benign task-success percentage-point lift, Conventional VoI - Never Ask
  [Y] = Never Ask adversarial unsafe rate (%), the "before" side of the range
  [Z] = Conventional VoI adversarial unsafe rate (%), the "after" side
  [B] = % of the benign goal-rate improvement SecureVoI recovers vs. Never Ask,
        relative to Conventional VoI's improvement
  [A] = % reduction in adversarial unsafe rate, SecureVoI vs. Conventional VoI

Usage:
  python scripts/fill_abstract.py --stats results/stats.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default="results/stats.json")
    ap.add_argument("--models-evaluated", default="results/models_evaluated.json")
    ap.add_argument("--abstract", default="abstract.md")
    ap.add_argument("--force", action="store_true",
                    help="override the real-backend guard -- do not use for the actual submission")
    args = ap.parse_args()

    stats = json.loads((ROOT / args.stats).read_text(encoding="utf-8"))
    backend = str(stats.get("agent_backend", ""))
    if not args.force and ("scriptedagent" in backend.lower() or "placeholder" in backend.lower()):
        raise SystemExit(
            f"Refusing to fill abstract.md: agent_backend={backend!r} is still the "
            "ScriptedAgent placeholder, not a real model. Re-run scripts/run_primary.py "
            "and scripts/compute_stats.py with a real --backend first. "
            "(--force overrides this for local experimentation only -- never for submission.)"
        )

    models_path = ROOT / args.models_evaluated
    n_models = len(json.loads(models_path.read_text(encoding="utf-8"))) if models_path.exists() else 1

    pp = stats["per_policy_condition"]
    never_benign_goal = pp["never_ask|benign"]["goal_rate"]["point"]
    conv_benign_goal = pp["conventional_voi|benign"]["goal_rate"]["point"]
    secure_benign_goal = pp["secure_voi|benign"]["goal_rate"]["point"]
    never_adv_unsafe = pp["never_ask|adversarial"]["unsafe_rate"]["point"]
    conv_adv_unsafe = pp["conventional_voi|adversarial"]["unsafe_rate"]["point"]
    secure_adv_unsafe = pp["secure_voi|adversarial"]["unsafe_rate"]["point"]

    n_tasks = stats["n_tasks"]
    x_lift_pp = round((conv_benign_goal - never_benign_goal) * 100, 1)
    y_pct = round(never_adv_unsafe * 100, 1)
    z_pct = round(conv_adv_unsafe * 100, 1)
    conv_improvement = conv_benign_goal - never_benign_goal
    secure_improvement = secure_benign_goal - never_benign_goal
    b_pct = round(100 * secure_improvement / conv_improvement, 1) if conv_improvement else 0.0
    a_pct = round(100 * (conv_adv_unsafe - secure_adv_unsafe) / conv_adv_unsafe, 1) if conv_adv_unsafe else 0.0

    fills = {
        "N": str(n_tasks), "M": str(n_models), "X": str(x_lift_pp),
        "Y": str(y_pct), "Z": str(z_pct), "B": str(b_pct), "A": str(a_pct),
    }

    abstract_path = ROOT / args.abstract
    text = abstract_path.read_text(encoding="utf-8")
    for letter, value in fills.items():
        text = re.sub(rf"\[{letter}\]", value, text)
    remaining = re.findall(r"\[[A-Z]\]", text)
    if remaining:
        raise SystemExit(f"Unfilled placeholders remain: {remaining} -- update the mapping above.")
    abstract_path.write_text(text, encoding="utf-8")

    print(f"Filled: {fills}")
    print(f"Wrote {abstract_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
