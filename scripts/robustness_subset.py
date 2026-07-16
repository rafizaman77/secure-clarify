#!/usr/bin/env python3
"""Jul 22-23 deliverable: 3 stochastic repetitions on a stratified 30-task
subset (plan section 11, Main experiment: "Add three stochastic repetitions
on a stratified 30-task subset rather than repeating the entire grid.").

Operationalization (the plan states the requirement, not the mechanism): the
main runs are deterministic at temperature=0 by design (scripts/tune_dev.py,
run_primary.py). "Stochastic repetition" here means re-running the SAME
frozen lambda/priors against the SAME subset of test tasks 3 times with
temperature>0 sampling instead of greedy decoding, to measure how much the
primary run's numbers could vary from decoding randomness alone -- a
robustness check on the primary result, not a re-tuning of anything.

Subset selection is deterministic (no randomness): stratified by domain,
taking every ceil(n_per_domain/15)-th test task by index so all stakes tiers,
channel-availability groups, and attack types in the cycling generator are
represented, same spirit as task_factory.assign_split().

Usage:
  python scripts/robustness_subset.py --tasks tasks/main_120.json \
      --calibration results/dev_calibration.json --backend hf_local --model <name>
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import ConventionalVoI, SecureVoI  # noqa: E402
from secure_clarify.runner import run_grid, summarize  # noqa: E402
from secure_clarify import estimators  # noqa: E402
from scripts.model_backends import build_agent, add_backend_args  # noqa: E402

SUBSET_SIZE = 30
N_REPS = 3
TEMPERATURE = 0.7


def load_tasks(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [load_task(d) for d in data]


def _task_idx(task_id: str) -> int:
    m = re.search(r"(\d+)$", task_id)
    return int(m.group(1)) if m else 0


def select_stratified_subset(test_tasks: list, n: int = SUBSET_SIZE) -> list:
    by_domain: dict = {}
    for t in test_tasks:
        by_domain.setdefault(t.domain, []).append(t)
    per_domain = n // len(by_domain)
    subset = []
    for domain, tasks in sorted(by_domain.items()):
        tasks = sorted(tasks, key=lambda t: _task_idx(t.task_id))
        k = min(per_domain, len(tasks))
        # evenly spaced indices across the full range (not a rounded-up
        # stride, which systematically undershoots the target count)
        if k == 1:
            idxs = [0]
        else:
            idxs = [round(i * (len(tasks) - 1) / (k - 1)) for i in range(k)]
        seen = set()
        for i in idxs:
            if i not in seen:
                seen.add(i)
                subset.append(tasks[i])
    return subset


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--calibration", default="results/dev_calibration.json")
    ap.add_argument("--out", default="results/robustness_subset.json")
    add_backend_args(ap)
    args = ap.parse_args()

    calib = json.loads((ROOT / args.calibration).read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    priors = {Channel(ch): p for ch, p in calib["fitted_channel_priors"].items()}
    estimators.set_priors(priors)

    all_tasks = load_tasks(ROOT / args.tasks)
    test_tasks = [t for t in all_tasks if t.split == "test"]
    subset = select_stratified_subset(test_tasks, SUBSET_SIZE)
    if not subset:
        raise SystemExit(f"No test-split tasks found in {args.tasks}")

    reps = []
    for rep in range(N_REPS):
        raw_agent = build_agent(args.backend, args.model, args.base_url,
                                args.api_key_env, args.host, temperature=TEMPERATURE)
        agent = CachingAgent(raw_agent)  # cache is per-repetition (fresh sampling each rep)
        eps = run_grid(subset, [ConventionalVoI(), SecureVoI(lam=lam)], agent,
                       conditions=[Condition.BENIGN, Condition.ADVERSARIAL],
                       sev_profile="medium")
        table = summarize(eps)
        reps.append(table)

    def stats_across_reps(policy: str, cond: str, field: str) -> dict:
        vals = [r[f"{policy}|{cond}"][field] for r in reps]
        mean = sum(vals) / len(vals)
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        return {"values": vals, "mean": round(mean, 4), "std": round(variance ** 0.5, 4)}

    backend_label = ("ScriptedAgent (placeholder -- no open-weight model wired in yet)"
                     if args.backend == "scripted" else f"{args.backend}:{args.model}")
    summary = {}
    for pol in ("conventional_voi", "secure_voi"):
        for cond in ("benign", "adversarial"):
            for field in ("goal_rate", "unsafe_rate", "utility"):
                summary[f"{pol}|{cond}|{field}"] = stats_across_reps(pol, cond, field)

    result = {
        "agent_backend": backend_label,
        "temperature": TEMPERATURE,
        "n_repetitions": N_REPS,
        "subset_size": len(subset),
        "subset_task_ids": sorted(t.task_id for t in subset),
        "lambda_used": lam,
        "per_repetition_tables": reps,
        "cross_repetition_stats": summary,
    }
    out_path = ROOT / args.out
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"Agent backend: {backend_label}, temperature={TEMPERATURE}, "
          f"{N_REPS} reps on {len(subset)} tasks\n")
    for key, d in summary.items():
        print(f"{key:30s} mean={d['mean']:.3f} std={d['std']:.4f} values={d['values']}")
    print(f"\nWrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
