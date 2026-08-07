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
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataclasses import asdict  # noqa: E402

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import SecureVoI, SecureVoIOracle  # noqa: E402
from secure_clarify.runner import run_grid, summarize, Episode  # noqa: E402
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
    # RAFI_RESEARCH_PLAN.md Phase 1 Step 1 follow-up (2026-07-30): this script
    # previously had no checkpointing at all -- a single mid-run failure (a
    # 2026-07-30 Claude-Sonnet-5 attempt hit "credit balance too low" 41/96
    # tasks in) lost the ENTIRE run's spend with nothing to resume from.
    # --resume/--episodes-out mirror run_primary.py's exact pattern: write
    # after every task, skip already-done task_ids on restart.
    ap.add_argument("--episodes-out", default="results/oracle_ablation_episodes.json",
                    help="checkpoint file; written after every task so a mid-run "
                         "failure loses at most one task's progress")
    ap.add_argument("--resume", action="store_true",
                    help="load --episodes-out if present and skip task_ids already there")
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

    episodes_path = ROOT / args.episodes_out
    episodes_path.parent.mkdir(parents=True, exist_ok=True)
    eps_dicts: list[dict] = []
    done_task_ids: set[str] = set()
    if args.resume and episodes_path.exists():
        try:
            eps_dicts = json.loads(episodes_path.read_text(encoding="utf-8"))
            done_task_ids = {e["task_id"] for e in eps_dicts}
            print(f"--resume: {len(done_task_ids)} tasks already completed in "
                  f"{episodes_path}, skipping those", file=sys.stderr, flush=True)
        except (json.JSONDecodeError, KeyError):
            print(f"--resume: {episodes_path} unreadable, starting fresh",
                  file=sys.stderr, flush=True)
            eps_dicts, done_task_ids = [], set()

    remaining = [t for t in test_tasks if t.task_id not in done_task_ids]
    failed_task_ids: list[str] = []
    t_start = time.time()
    for i, task in enumerate(remaining, 1):
        try:
            new_eps = run_grid([task], policies, agent,
                               conditions=[Condition.BENIGN, Condition.ADVERSARIAL],
                               sev_profile="medium")
        except Exception as e:
            # A backend can fail cleanly (model_backends' own retry loop gives
            # up and raises RuntimeError -- e.g. the 2026-07-30 "credit balance
            # too low" case) rather than hang. Skip and keep going: one failed
            # task must not cost the whole run's already-completed progress.
            failed_task_ids.append(task.task_id)
            elapsed = time.time() - t_start
            print(f"  [{i}/{len(remaining)} remaining, {len(eps_dicts)}/{len(test_tasks)} total] "
                  f"{task.task_id} FAILED ({type(e).__name__}: {e}) -- skipping "
                  f"({elapsed:.0f}s elapsed). Re-run with --resume to retry it.",
                  file=sys.stderr, flush=True)
            continue
        eps_dicts.extend(asdict(e) for e in new_eps)
        episodes_path.write_text(json.dumps(eps_dicts, indent=2) + "\n", encoding="utf-8")
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(remaining)} remaining, {len(eps_dicts)}/{len(test_tasks)} total] "
              f"{task.task_id} done ({elapsed:.0f}s elapsed, {elapsed/i:.1f}s/task avg, "
              f"cache={agent.cache_sizes()})", file=sys.stderr, flush=True)

    if failed_task_ids:
        print(f"\nWARNING: {len(failed_task_ids)} task(s) failed and were skipped: "
              f"{failed_task_ids}. Re-run with --resume before trusting a "
              f"partial-coverage result.", file=sys.stderr, flush=True)

    eps = [Episode(**d) for d in eps_dicts]
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
        "n_tasks_completed": len(test_tasks) - len(failed_task_ids),
        "failed_task_ids": failed_task_ids,
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
