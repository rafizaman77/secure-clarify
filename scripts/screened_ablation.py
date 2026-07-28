#!/usr/bin/env python3
"""Jul 27-28 deliverable: the decisive ablation a mock-review pass flagged as
the single most damaging missing experiment -- ConventionalVoI's risk-blind
stage-1 acquisition paired with SecureVoI's EXACT stage-2 response screen
(secure_clarify.policies.ScreenedConventionalVoI, inherited from SecureVoI so
its accept() cannot silently diverge from the real thing).

Runs ConventionalVoI, ScreenedConventionalVoI, and SecureVoI side by side on
the SAME test-split tasks with the SAME frozen per-model lambda, so the three
numbers isolate exactly one question: does SecureVoI's advantage over
ConventionalVoI come from stage 1 (channel-risk-aware acquisition), stage 2
(the response screen), or both? If ScreenedConventionalVoI tracks SecureVoI
closely, stage 1 isn't pulling separable weight. If it tracks ConventionalVoI
(or sits meaningfully between the two, well short of SecureVoI), stage 1 is
doing real work a bolted-on filter alone would not buy.

Like oracle_ablation.py, lambda/priors come from scripts/tune_dev.py's frozen
dev-only fit -- this script never re-tunes anything, only evaluates.

Modeled on run_primary.py's per-task loop (not oracle_ablation.py's bulk
loop): a real-model run over 96 tasks can take an hour+, and this session has
already lost progress twice to a hung call or an interrupted session. Each
task gets its own timeout and the episodes file is checkpointed after every
task, so --resume can pick back up without re-paying for tasks already done.

Usage:
  python scripts/screened_ablation.py --tasks tasks/main_120.json \
      --calibration results/models/mistral-nemo-12b/dev_calibration.json \
      --out results/models/mistral-nemo-12b/screened_ablation.json \
      --episodes-out results/models/mistral-nemo-12b/screened_ablation_episodes.json \
      --backend ollama --model mistral-nemo:12b --resume
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PER_TASK_TIMEOUT = float(os.environ.get("PER_TASK_TIMEOUT", "600"))

from dataclasses import asdict  # noqa: E402

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import (ConventionalVoI, SecureVoI,  # noqa: E402
                                     ScreenedConventionalVoI)
from secure_clarify.runner import run_grid, summarize, Episode  # noqa: E402
from secure_clarify import estimators  # noqa: E402
from scripts.model_backends import build_agent, add_backend_args  # noqa: E402


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def load_tasks(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [load_task(d) for d in data]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--calibration", default="results/dev_calibration.json")
    ap.add_argument("--out", default="results/screened_ablation.json")
    ap.add_argument("--episodes-out", default="results/screened_ablation_episodes.json")
    ap.add_argument("--conditions", default="benign,adversarial",
                    help="comma-separated Condition values, same parsing as run_primary.py. "
                         "Use 'adversarial_stealth' alone for the stealth-tier ablation -- "
                         "stealth adds no benign rows by construction, so there is nothing "
                         "to gain by re-running benign alongside it.")
    ap.add_argument("--limit", type=int, default=None,
                    help="only evaluate the first N (post-skip) test tasks -- for the "
                         "per-task-process-restart pattern a single long-lived process "
                         "can't safely use on Groq (fd leak from hung calls compounds "
                         "over a multi-hour run; confirmed directly: 65 CLOSE_WAIT / 37 "
                         "ESTABLISHED simultaneously on one process after 3h with zero "
                         "progress). Not for real results on its own.")
    ap.add_argument("--skip-task-ids", default="",
                    help="comma-separated task_ids to exclude entirely -- for a task that "
                         "reproducibly fails against one backend's infrastructure specifically, "
                         "so it stops consuming retry budget on every subsequent --resume. "
                         "Document any use of this; it is a coverage gap, not a fix.")
    ap.add_argument("--resume", action="store_true",
                    help="load --episodes-out if it exists and skip task_ids already present")
    add_backend_args(ap)
    args = ap.parse_args()

    calib = json.loads((ROOT / args.calibration).read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    priors = {Channel(ch): p for ch, p in calib["fitted_channel_priors"].items()}
    estimators.set_priors(priors)

    all_tasks = load_tasks(ROOT / args.tasks)
    test_tasks = [t for t in all_tasks if t.split == "test"]
    skip_ids = {s.strip() for s in args.skip_task_ids.split(",") if s.strip()}
    if skip_ids:
        test_tasks = [t for t in test_tasks if t.task_id not in skip_ids]
        print(f"--skip-task-ids: excluding {sorted(skip_ids)} -- "
              f"{len(test_tasks)} test tasks remain", file=sys.stderr, flush=True)
    if args.limit:
        test_tasks = test_tasks[:args.limit]
    if not test_tasks:
        raise SystemExit(f"No test-split tasks found in {args.tasks}")

    raw_agent = build_agent(args.backend, args.model, args.base_url,
                            args.api_key_env, args.host)
    agent = CachingAgent(raw_agent)
    policies = [ConventionalVoI(), ScreenedConventionalVoI(lam=lam), SecureVoI(lam=lam)]
    try:
        conditions = [Condition(c.strip()) for c in args.conditions.split(",") if c.strip()]
    except ValueError as exc:
        raise SystemExit(f"--conditions: {exc}. Valid: {[c.value for c in Condition]}")
    if not conditions:
        raise SystemExit("--conditions must name at least one condition")

    episodes_path = ROOT / args.episodes_out
    episodes_path.parent.mkdir(parents=True, exist_ok=True)
    eps_dicts: list[dict] = []
    done_task_ids: set[str] = set()
    if args.resume and episodes_path.exists():
        try:
            eps_dicts = json.loads(episodes_path.read_text(encoding="utf-8"))
            done_task_ids = {e["task_id"] for e in eps_dicts}
            print(f"--resume: {len(done_task_ids)} tasks already completed in "
                  f"{rel(episodes_path)}, skipping those", file=sys.stderr, flush=True)
        except (json.JSONDecodeError, KeyError):
            print(f"--resume: {rel(episodes_path)} unreadable, starting fresh",
                  file=sys.stderr, flush=True)
            eps_dicts, done_task_ids = [], set()

    t_start = time.time()
    remaining = [t for t in test_tasks if t.task_id not in done_task_ids]
    timed_out_task_ids: list[str] = []
    for i, task in enumerate(remaining, 1):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_grid, [task], policies, agent,
                                 conditions=conditions, sev_profile="medium")
        try:
            new_eps = future.result(timeout=PER_TASK_TIMEOUT)
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            timed_out_task_ids.append(task.task_id)
            elapsed = time.time() - t_start
            print(f"  [{i}/{len(remaining)} remaining] {task.task_id} TIMED OUT after "
                  f"{PER_TASK_TIMEOUT:.0f}s -- skipping ({elapsed:.0f}s elapsed). "
                  f"Re-run with --resume to retry it.", file=sys.stderr, flush=True)
            continue
        except Exception as e:
            executor.shutdown(wait=False, cancel_futures=True)
            timed_out_task_ids.append(task.task_id)
            elapsed = time.time() - t_start
            print(f"  [{i}/{len(remaining)} remaining] {task.task_id} FAILED "
                  f"({type(e).__name__}: {e}) -- skipping ({elapsed:.0f}s elapsed). "
                  f"Re-run with --resume to retry it.", file=sys.stderr, flush=True)
            continue
        executor.shutdown(wait=False)
        eps_dicts.extend(asdict(e) for e in new_eps)
        episodes_path.write_text(json.dumps(eps_dicts, indent=2) + "\n", encoding="utf-8")
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(remaining)} remaining, {len(eps_dicts)//len(policies)//len(conditions)}/"
              f"{len(test_tasks)} total] {task.task_id} done ({elapsed:.0f}s elapsed, "
              f"{elapsed/i:.1f}s/task avg, cache={agent.cache_sizes()})",
              file=sys.stderr, flush=True)

    if timed_out_task_ids:
        print(f"\nWARNING: {len(timed_out_task_ids)} task(s) timed out/failed and were "
              f"skipped: {timed_out_task_ids}. Re-run with --resume before trusting a "
              f"partial-coverage result.", file=sys.stderr, flush=True)

    eps = [Episode(**d) for d in eps_dicts]
    table = summarize(eps)

    def g(pol, cond, field):
        return table[f"{pol}|{cond}"][field]

    cond_values = {c.value for c in conditions}
    # whichever adversarial-flavored condition is present (explicit or stealth) --
    # this is what makes --conditions adversarial_stealth alone work: the ablation
    # question ("does stage 1 add separable safety margin?") is defined per
    # adversarial condition, benign is only needed to also report the utility cost.
    adv_cond = next((c for c in ("adversarial_stealth", "adversarial") if c in cond_values), None)

    result = {
        "agent_backend": f"{args.backend}:{args.model}" if args.backend != "scripted"
                         else "ScriptedAgent (placeholder)",
        "lambda_used": lam,
        "n_test_tasks": len(test_tasks),
        "n_timed_out_or_failed": len(timed_out_task_ids),
        "conditions": [c.value for c in conditions],
        "table": {k: table[k] for k in sorted(table)},
    }
    if not timed_out_task_ids and adv_cond is not None:
        conv_adv_unsafe = g("conventional_voi", adv_cond, "unsafe_rate")
        screened_adv_unsafe = g("screened_conventional_voi", adv_cond, "unsafe_rate")
        secure_adv_unsafe = g("secure_voi", adv_cond, "unsafe_rate")
        gap = conv_adv_unsafe - secure_adv_unsafe
        stage1_share = ((screened_adv_unsafe - secure_adv_unsafe) / gap) if gap > 0 else None
        result.update({
            "adversarial_condition": adv_cond,
            "adversarial_unsafe_rate": {
                "conventional_voi": conv_adv_unsafe,
                "screened_conventional_voi": screened_adv_unsafe,
                "secure_voi": secure_adv_unsafe,
            },
            "stage1_share_of_secure_voi_gap": (
                round(stage1_share, 4) if stage1_share is not None else None
            ),
            "interpretation": (
                "stage1_share_of_secure_voi_gap is the fraction of ConventionalVoI -> "
                "SecureVoI's total adversarial unsafe-rate reduction that survives "
                "REMOVING SecureVoI's stage-1 risk-aware acquisition (i.e. that "
                "ScreenedConventionalVoI, with the same stage-2 screen as SecureVoI "
                "but risk-blind stage-1, still fails to close). ~0 means stage 2 "
                "(the response screen) explains the whole gap and stage 1 is not "
                "pulling separable weight. ~1 means ScreenedConventionalVoI is barely "
                "better than ConventionalVoI and stage 1 is doing essentially all the "
                "work. A value strictly between 0 and 1 means both stages contribute."
            ),
        })
        if "benign" in cond_values:
            result["benign_utility"] = {
                "conventional_voi": g("conventional_voi", "benign", "utility"),
                "screened_conventional_voi": g("screened_conventional_voi", "benign", "utility"),
                "secure_voi": g("secure_voi", "benign", "utility"),
            }
    elif not timed_out_task_ids:
        result["interpretation"] = (
            f"No adversarial condition in {sorted(cond_values)} -- nothing to ablate "
            f"(need 'adversarial' and/or 'adversarial_stealth').")
    else:
        result["interpretation"] = (
            f"INCOMPLETE: {len(timed_out_task_ids)} task(s) did not complete -- "
            f"re-run with --resume before trusting any of the numbers in 'table'."
        )

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"\n{'policy|condition':40s} {'goal':>6} {'unsafe':>7} {'atk':>6} {'util':>7} {'n':>4}")
    print("-" * 78)
    for key in sorted(table):
        r = table[key]
        print(f"{key:40s} {r['goal_rate']:6.3f} {r['unsafe_rate']:7.3f} "
              f"{r['attack_success']:6.3f} {r['utility']:7.3f} {r['n']:4d}")
    if "stage1_share_of_secure_voi_gap" in result:
        print(f"\nstage1_share_of_secure_voi_gap = {result['stage1_share_of_secure_voi_gap']}")
    print(f"\nWrote {rel(out_path)}")
    print(f"Wrote {rel(episodes_path)} ({len(eps)} episodes)")
    return 1 if timed_out_task_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
