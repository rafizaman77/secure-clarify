#!/usr/bin/env python3
"""Jul 20 deliverable: statistics for the main table -- bootstrap confidence
intervals per policy x condition, and a paired bootstrap significance test
for SecureVoI vs ConventionalVoI's adversarial unsafe rate (the paper's
central comparison).

Task-level (not episode-level) resampling: every policy is evaluated on the
SAME set of test tasks, so policies are paired within a task. Resampling
task IDs with replacement and recomputing each policy's rate over that
resample is the statistically appropriate bootstrap here -- resampling
episodes independently would break the pairing and understate correlation
between policies' performance on easy/hard tasks.

Usage:
  python scripts/compute_stats.py --episodes results/primary_episodes.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

N_BOOTSTRAP = 2000
CI = 0.95


def _seeded_rng():
    # Date.now()/random module's default seeding is fine here (this is a
    # plain script, not a Workflow) -- but pin a fixed seed for reproducible
    # confidence intervals across re-runs of the same episode data.
    import random
    rng = random.Random(20260720)
    return rng


def load_episodes(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rate(episodes: list[dict], field: str) -> float:
    if not episodes:
        return 0.0
    return sum(1.0 if e[field] else 0.0 for e in episodes) / len(episodes)


def _mean(episodes: list[dict], field: str) -> float:
    if not episodes:
        return 0.0
    return sum(e[field] for e in episodes) / len(episodes)


def bootstrap_ci(task_ids: list[str], by_task: dict, policy: str, condition: str,
                 field: str, metric_fn, rng) -> tuple[float, float, float]:
    """metric_fn(episodes) -> float. Resample task_ids with replacement,
    recompute the metric over the matching episodes each time."""
    point_eps = [e for tid in task_ids for e in by_task[tid]
                if e["policy"] == policy and e["condition"] == condition]
    point = metric_fn(point_eps, field)

    boots = []
    n = len(task_ids)
    for _ in range(N_BOOTSTRAP):
        sample_ids = [task_ids[rng.randrange(n)] for _ in range(n)]
        eps = [e for tid in sample_ids for e in by_task[tid]
              if e["policy"] == policy and e["condition"] == condition]
        boots.append(metric_fn(eps, field))
    boots.sort()
    lo = boots[int((1 - CI) / 2 * N_BOOTSTRAP)]
    hi = boots[int((1 + CI) / 2 * N_BOOTSTRAP) - 1]
    return point, lo, hi


def paired_bootstrap_diff(task_ids: list[str], by_task: dict, policy_a: str, policy_b: str,
                          condition: str, field: str, metric_fn, rng) -> dict:
    """Bootstrap CI for metric(policy_a) - metric(policy_b) on the SAME
    resampled task set each iteration (paired), plus a two-sided bootstrap
    p-value (fraction of resamples where the sign disagrees with the point
    estimate's sign)."""
    n = len(task_ids)

    def diff_for(ids: list[str]) -> float:
        eps_a = [e for tid in ids for e in by_task[tid]
                if e["policy"] == policy_a and e["condition"] == condition]
        eps_b = [e for tid in ids for e in by_task[tid]
                if e["policy"] == policy_b and e["condition"] == condition]
        return metric_fn(eps_a, field) - metric_fn(eps_b, field)

    point = diff_for(task_ids)
    boots = []
    for _ in range(N_BOOTSTRAP):
        sample_ids = [task_ids[rng.randrange(n)] for _ in range(n)]
        boots.append(diff_for(sample_ids))
    boots.sort()
    lo = boots[int((1 - CI) / 2 * N_BOOTSTRAP)]
    hi = boots[int((1 + CI) / 2 * N_BOOTSTRAP) - 1]
    # two-sided bootstrap p-value: fraction crossing zero, mirrored
    n_cross = sum(1 for b in boots if (b >= 0) != (point >= 0))
    p_value = min(1.0, 2 * n_cross / N_BOOTSTRAP)
    return {"point": point, "ci_lo": lo, "ci_hi": hi, "p_value": p_value,
           "significant_at_0.05": bool(not (lo <= 0 <= hi))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", default="results/primary_episodes.json")
    ap.add_argument("--out", default="results/stats.json")
    args = ap.parse_args()

    episodes_path = ROOT / args.episodes
    if not episodes_path.exists():
        raise SystemExit(
            f"{args.episodes} not found -- run scripts/run_primary.py first "
            "(it now also writes the raw per-episode file needed here)."
        )
    episodes = load_episodes(episodes_path)
    agent_backend = None
    summary_path = ROOT / "results" / "primary_summary.json"
    if summary_path.exists():
        agent_backend = json.loads(summary_path.read_text(encoding="utf-8")).get("agent_backend")

    by_task: dict = defaultdict(list)
    for e in episodes:
        by_task[e["task_id"]].append(e)
    task_ids = sorted(by_task)

    policies = sorted({e["policy"] for e in episodes})
    conditions = sorted({e["condition"] for e in episodes})

    rng = _seeded_rng()
    per_policy = {}
    for pol in policies:
        for cond in conditions:
            goal_pt, goal_lo, goal_hi = bootstrap_ci(
                task_ids, by_task, pol, cond, "goal_ok", _rate, rng)
            unsafe_pt, unsafe_lo, unsafe_hi = bootstrap_ci(
                task_ids, by_task, pol, cond, "unsafe", _rate, rng)
            util_pt, util_lo, util_hi = bootstrap_ci(
                task_ids, by_task, pol, cond, "utility", _mean, rng)
            per_policy[f"{pol}|{cond}"] = {
                "goal_rate": {"point": round(goal_pt, 4), "ci95": [round(goal_lo, 4), round(goal_hi, 4)]},
                "unsafe_rate": {"point": round(unsafe_pt, 4), "ci95": [round(unsafe_lo, 4), round(unsafe_hi, 4)]},
                "utility": {"point": round(util_pt, 4), "ci95": [round(util_lo, 4), round(util_hi, 4)]},
                "n": len(task_ids),
            }

    comparisons = {}
    if "secure_voi" in policies and "conventional_voi" in policies:
        comparisons["secure_voi_minus_conventional_voi__adversarial_unsafe_rate"] = paired_bootstrap_diff(
            task_ids, by_task, "secure_voi", "conventional_voi",
            "adversarial", "unsafe", _rate, rng)
        comparisons["secure_voi_minus_trusted_only__benign_utility"] = paired_bootstrap_diff(
            task_ids, by_task, "secure_voi", "trusted_only",
            "benign", "utility", _mean, rng)

    result = {
        "agent_backend": agent_backend,
        "n_tasks": len(task_ids),
        "n_bootstrap": N_BOOTSTRAP,
        "ci_level": CI,
        "resampling_unit": "task_id (paired across policies within a task)",
        "per_policy_condition": per_policy,
        "comparisons": comparisons,
    }
    out_path = ROOT / args.out
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"Bootstrapped over {len(task_ids)} tasks, {N_BOOTSTRAP} resamples, {int(CI*100)}% CI\n")
    for key, d in sorted(per_policy.items()):
        print(f"{key:32s} goal={d['goal_rate']['point']:.3f} {d['goal_rate']['ci95']}  "
              f"unsafe={d['unsafe_rate']['point']:.3f} {d['unsafe_rate']['ci95']}  "
              f"util={d['utility']['point']:.3f} {d['utility']['ci95']}")
    print()
    for key, d in comparisons.items():
        sig = "SIGNIFICANT" if d["significant_at_0.05"] else "not significant"
        print(f"{key}: {d['point']:+.4f} [{d['ci_lo']:.4f}, {d['ci_hi']:.4f}] "
              f"p={d['p_value']:.4f} ({sig} at alpha=0.05)")
    print(f"\nAgent backend: {agent_backend}")
    print(f"Wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
