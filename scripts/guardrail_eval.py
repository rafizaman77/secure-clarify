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

from dataclasses import asdict  # noqa: E402

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import ConventionalVoI, SecureVoI  # noqa: E402
from secure_clarify.guardrail import run_posthoc_grid  # noqa: E402
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
    ap.add_argument("--out", default="results/guardrail_eval.json")
    # RAFI_RESEARCH_PLAN.md Phase 1 Step 1 follow-up (2026-07-30): same
    # checkpointing gap and fix as oracle_ablation.py -- see that script's
    # comment for the incident that motivated this.
    ap.add_argument("--episodes-out", default="results/guardrail_eval_episodes.json",
                    help="checkpoint file; written after every task")
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

    conditions = [Condition.BENIGN, Condition.ADVERSARIAL]
    policies = [ConventionalVoI(), SecureVoI(lam=lam)]

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
            new_eps = run_grid([task], policies, agent, conditions=conditions)
            new_eps += run_posthoc_grid([task], agent, conditions=conditions)
        except Exception as e:
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
