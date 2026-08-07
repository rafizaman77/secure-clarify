#!/usr/bin/env python3
"""Phase 4: SecureVoI against defenses that exist, not only its own ablations.

Compares, on the same tasks and the same model:

  conventional_voi     no defense (the attack surface)
  prompt_armor         risk-blind acquisition + a standalone injection detector
  spotlighting         risk-blind acquisition, no screening, but the accepted
                       text is delimited and labelled untrusted (ASPI-style)
  posthoc_guardrail    risk-blind acquisition + ACTION-PLAN screening against the
                       task's own prohibited_actions -- an ORACLE-strength upper
                       bound on action-level filtering, included because it is
                       the sharpest "why not just filter the actions?" objection
  secure_voi           ours

Spotlighting is only meaningful with a real model: ScriptedAgent ignores
answer_text entirely, so the delimiters cannot change its behaviour.

Usage:
  SECURE_CLARIFY_CACHE=.cache/agent python3 scripts/defense_baselines.py \
      --model mistral-nemo-12b --backend ollama --backend-model mistral-nemo:12b
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import ConventionalVoI, SecureVoI  # noqa: E402
from secure_clarify.baselines import PromptArmorVoI, SpotlightingAgent  # noqa: E402
from secure_clarify.guardrail import run_posthoc_grid  # noqa: E402
from secure_clarify.runner import run_grid  # noqa: E402
from secure_clarify import estimators as E  # noqa: E402
from secure_clarify.confirmatory import wilson_interval  # noqa: E402
from scripts.model_backends import build_agent  # noqa: E402


def summarize(eps, label):
    n = len(eps)
    u = sum(1 for e in eps if e.unsafe)
    a = sum(1 for e in eps if e.attack_success)
    lo, hi = wilson_interval(a, n)
    return {"defense": label, "n": n,
            "unsafe": round(u / n, 4), "attack_success": round(a / n, 4),
            "attack_success_ci95": [round(lo, 4), round(hi, 4)],
            "goal": round(sum(1 for e in eps if e.goal_ok) / n, 4),
            "utility": round(sum(e.utility for e in eps) / n, 4),
            "ask_rate": round(sum(1 for e in eps if e.asked) / n, 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--conditions", default="adversarial_stealth,benign")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--backend-model", default="mistral-nemo:12b")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--cache", default=".cache/agent")
    ap.add_argument("--out", default="results/defense_baselines.json")
    args = ap.parse_args()

    calib = json.loads((ROOT / f"results/models/{args.model}/dev_calibration.json")
                       .read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    E.set_priors({Channel(c): p for c, p in calib["fitted_channel_priors"].items()})

    tasks = [t for t in (load_task(d) for d in
                         json.loads((ROOT / args.tasks).read_text(encoding="utf-8")))
             if t.split == "test"]
    conds = [Condition(c.strip()) for c in args.conditions.split(",") if c.strip()]

    base = build_agent(args.backend, args.backend_model, args.base_url,
                       args.api_key_env, args.host)
    agent = CachingAgent(base, disk_cache_dir=args.cache or None)
    spot = SpotlightingAgent(CachingAgent(base, disk_cache_dir=args.cache or None))

    rows = defaultdict(list)
    for label, pol, ag in (("conventional_voi", ConventionalVoI(), agent),
                           ("prompt_armor", PromptArmorVoI(), agent),
                           ("spotlighting", ConventionalVoI(), spot),
                           ("secure_voi", SecureVoI(lam=lam), agent)):
        eps = run_grid(tasks, [pol], ag, conditions=conds, sev_profile="medium")
        for e in eps:
            rows[(label, e.condition)].append(e)
        print(f"  [{label}] done", flush=True)

    # post-hoc guardrail has its own episode loop (it screens the PLAN)
    for cond in conds:
        eps = run_posthoc_grid(tasks, agent, conditions=[cond], sev_profile="medium")
        for e in eps:
            rows[("posthoc_guardrail", e.condition)].append(e)
    print("  [posthoc_guardrail] done", flush=True)

    report = {"model": args.model, "lambda": lam, "tasks": args.tasks,
              "n_test_tasks": len(tasks), "by_defense_condition": {}}
    for (label, cond), eps in sorted(rows.items()):
        report["by_defense_condition"][f"{label}|{cond}"] = summarize(eps, label)

    (ROOT / args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    order = ["conventional_voi", "prompt_armor", "spotlighting",
             "posthoc_guardrail", "secure_voi"]
    for cond in [c.value for c in conds]:
        print(f"\n{args.model} -- {cond}\n")
        print(f"  {'defense':20s} {'ask':>6s} {'attack success':>16s} "
              f"{'unsafe':>7s} {'goal':>6s} {'utility':>8s}")
        for label in order:
            s = report["by_defense_condition"].get(f"{label}|{cond}")
            if not s:
                continue
            ci = f"[{s['attack_success_ci95'][0]:.2f},{s['attack_success_ci95'][1]:.2f}]"
            print(f"  {label:20s} {s['ask_rate']:6.3f} {s['attack_success']:8.3f} {ci:>7s} "
                  f"{s['unsafe']:7.3f} {s['goal']:6.3f} {s['utility']:+8.3f}")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
