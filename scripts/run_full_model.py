#!/usr/bin/env python3
"""One-command orchestration: run the entire per-model pipeline in order,
archived under results/models/<name>/. Chains exactly the steps documented
in REPRODUCIBILITY.md -- this script doesn't do anything those individual
scripts don't already do, it just removes the chance of a copy-paste flag
mismatch between steps (e.g. pointing compute_stats.py at the wrong
episodes file), which has been the actual source of wasted time this
session, not the underlying pipeline.

Steps: tune_dev -> run_primary (--policies mainplus) -> check_invariants ->
oracle_ablation -> guardrail_eval -> compute_stats -> make_main_table ->
failure_analysis (--append) -> [optional] robustness_subset (slow -- off by default).

check_invariants gates trust: if it fails, the model's numbers are NOT trustworthy
(degenerate benchmark or a scoring bug) and the pipeline says so loudly.

Usage:
  python scripts/run_full_model.py --name mistral-nemo-12b --backend ollama --model mistral-nemo:12b
  python scripts/run_full_model.py --name my-model --backend openai \
      --base-url https://api.groq.com/openai/v1/chat/completions \
      --api-key-env GROQ_API_KEY --model llama-3.3-70b-versatile
  python scripts/run_full_model.py --name qwen2.5-0.5b-instruct --backend hf_local \
      --model Qwen/Qwen2.5-0.5B-Instruct --skip-dev-calibration   # reuse an existing dev_calibration.json
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def run_step(name: str, args: list[str]) -> bool:
    print(f"\n{'='*70}\n[{name}] {' '.join(args)}\n{'='*70}", flush=True)
    t0 = time.time()
    proc = subprocess.run([sys.executable] + args, cwd=ROOT)
    elapsed = time.time() - t0
    ok = proc.returncode == 0
    print(f"[{name}] {'OK' if ok else 'FAILED'} ({elapsed:.0f}s, exit={proc.returncode})",
          flush=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="results/models/<name>/ archive directory")
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--backend", required=True, choices=["scripted", "openai", "ollama", "hf_local"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="https://api.groq.com/openai/v1/chat/completions")
    ap.add_argument("--api-key-env", default="GROQ_API_KEY")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--skip-dev-calibration", action="store_true",
                    help="reuse an existing results/models/<name>/dev_calibration.json instead of re-fitting")
    ap.add_argument("--with-robustness-subset", action="store_true",
                    help="also run the (slow -- 30 tasks x 3 reps) stochastic robustness check")
    ap.add_argument("--policies", choices=["main", "mainplus"], default="mainplus",
                    help="primary-run policy set. mainplus (default) adds the "
                         "channel_heuristic validity-probe baseline (the trivial bar "
                         "SecureVoI must clear on the fixed benchmark); main is the "
                         "original 6-policy set.")
    args = ap.parse_args()

    out_dir = ROOT / "results" / "models" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)

    backend_flags = ["--backend", args.backend, "--model", args.model,
                     "--base-url", args.base_url, "--api-key-env", args.api_key_env,
                     "--host", args.host]

    calib_path = f"results/models/{args.name}/dev_calibration.json"
    steps_run: list[str] = []
    overall_start = time.time()

    if not args.skip_dev_calibration:
        ok = run_step("tune_dev", ["scripts/tune_dev.py", "--tasks", args.tasks,
                                   "--out", calib_path] + backend_flags)
        if not ok:
            print("Dev calibration failed -- aborting rest of pipeline.", flush=True)
            return 1
        steps_run.append("tune_dev")
    elif not (ROOT / calib_path).exists():
        print(f"--skip-dev-calibration set but {calib_path} doesn't exist -- aborting.", flush=True)
        return 1

    primary_out = f"results/models/{args.name}/primary_summary.json"
    episodes_out = f"results/models/{args.name}/primary_episodes.json"
    ok = run_step("run_primary", ["scripts/run_primary.py", "--tasks", args.tasks,
                                  "--calibration", calib_path, "--out", primary_out,
                                  "--episodes-out", episodes_out, "--resume",
                                  "--policies", args.policies] + backend_flags)
    if not ok:
        print("Primary run failed -- aborting rest of pipeline (dev calibration is preserved).",
              flush=True)
        return 1
    steps_run.append("run_primary")

    # Trust gate: replay-free invariant check on the episodes just produced. Not
    # fatal (the run's artifacts are still worth keeping for inspection), but a
    # failure means the numbers are NOT trustworthy -- say so unmissably.
    if run_step("check_invariants", ["scripts/check_invariants.py",
                                     "--episodes", episodes_out, "--tasks", args.tasks]):
        steps_run.append("check_invariants")
    else:
        print("\n" + "!" * 70 + "\n!! INVARIANT CHECK FAILED for "
              f"{args.name} -- these numbers are NOT trustworthy (degenerate\n"
              "!! benchmark or a scoring bug). Inspect before using anything below.\n"
              + "!" * 70, flush=True)
        steps_run.append("check_invariants[FAILED]")

    run_step("oracle_ablation", ["scripts/oracle_ablation.py", "--tasks", args.tasks,
                                 "--calibration", calib_path,
                                 "--out", f"results/models/{args.name}/oracle_ablation.json"] + backend_flags)
    steps_run.append("oracle_ablation")

    run_step("guardrail_eval", ["scripts/guardrail_eval.py", "--tasks", args.tasks,
                                "--calibration", calib_path,
                                "--out", f"results/models/{args.name}/guardrail_eval.json"] + backend_flags)
    steps_run.append("guardrail_eval")

    stats_out = f"results/models/{args.name}/stats.json"
    if run_step("compute_stats", ["scripts/compute_stats.py", "--episodes", episodes_out,
                                  "--out", stats_out]):
        steps_run.append("compute_stats")
        run_step("make_main_table", ["scripts/make_main_table.py", "--stats", stats_out,
                                     "--out", f"results/models/{args.name}/main_table.md"])
        steps_run.append("make_main_table")

    run_step("failure_analysis", ["scripts/failure_analysis.py", "--episodes", episodes_out,
                                  "--model-name", args.name, "--append"])
    steps_run.append("failure_analysis")

    if args.with_robustness_subset:
        run_step("robustness_subset", ["scripts/robustness_subset.py", "--tasks", args.tasks,
                                       "--calibration", calib_path,
                                       "--out", f"results/models/{args.name}/robustness_subset.json"]
                 + backend_flags)
        steps_run.append("robustness_subset")

    print(f"\n{'='*70}\nDone: {args.name} ({time.time()-overall_start:.0f}s total)\n"
          f"Steps completed: {', '.join(steps_run)}\n"
          f"Results archived under results/models/{args.name}/\n{'='*70}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
