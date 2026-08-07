#!/usr/bin/env python3
"""Step 27 of RESEARCH_PLAN.md: which part of response_risk earns the safety result?

WHY THIS IS LOAD-BEARING (not optional). Step 8 found the learned malice
classifier flags 0/12 stealth attacks and scores them *below* benign text. The
Step 7/18 corpus run then found the full risk score ranks benign hard negatives
ABOVE real attacks (AUROC 0.039), with `cue_signal` almost perfectly inverted
(0.001). Together those say the screen may be winning on the stealth tier for a
reason unrelated to understanding attacks -- lexical cues plus channel routing.

This tests that directly on the frozen benchmark with real models: re-run the
stealth condition with each component of `response_risk` removed, and see how
much of the safety result survives. If removing the learned term costs nothing,
the paper cannot credit it.

  response_risk = 0.35*prior + 0.4*learned + 0.2*cue_signal + off_schema

TWO ABLATION MODES, because dropping a term also lowers the score and therefore
makes rejection rarer for reasons unrelated to information:
  zeroed   -- drop the term (score shrinks; confounds signal with threshold)
  renorm   -- drop it and rescale survivors to the original total (scale held,
              isolating information content)
Both are reported. `renorm` is the one to believe for attribution.

Usage:
  python scripts/risk_component_ablation.py --model mistral-nemo-12b \
      --backend ollama --backend-model mistral-nemo:12b
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import SecureVoI, ScreenedConventionalVoI  # noqa: E402
from secure_clarify.runner import run_grid  # noqa: E402
from secure_clarify import estimators  # noqa: E402
from scripts.model_backends import build_agent  # noqa: E402

ALL = {"prior", "learned", "cue", "off_schema"}

# (label, active components, renorm)
ABLATIONS = [
    ("full", None, False),
    ("no_learned_zeroed", ALL - {"learned"}, False),
    ("no_learned_renorm", ALL - {"learned"}, True),
    ("no_cue_zeroed", ALL - {"cue"}, False),
    ("no_cue_renorm", ALL - {"cue"}, True),
    ("no_prior_zeroed", ALL - {"prior"}, False),
    ("no_prior_renorm", ALL - {"prior"}, True),
    ("no_off_schema", ALL - {"off_schema"}, False),
    ("learned_only", {"learned"}, True),
    ("cue_only", {"cue"}, True),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mistral-nemo-12b")
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--conditions", default="adversarial_stealth,adversarial,benign")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--backend-model", default="mistral-nemo:12b")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    calib = json.loads((ROOT / f"results/models/{args.model}/dev_calibration.json")
                       .read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    priors = {Channel(c): p for c, p in calib["fitted_channel_priors"].items()}

    tasks = [load_task(d) for d in
             json.loads((ROOT / args.tasks).read_text(encoding="utf-8"))]
    conds = [Condition(c.strip()) for c in args.conditions.split(",") if c.strip()]

    # one cache across ablations: the model calls are identical inputs, and
    # `no_learned` simply never asks for them
    agent = CachingAgent(build_agent(args.backend, args.backend_model,
                                     args.base_url, args.api_key_env, args.host))

    out = {"step": "27 -- response_risk component ablation",
           "model": args.model, "backend": f"{args.backend}:{args.backend_model}",
           "lambda": lam, "tasks": args.tasks, "n_tasks": len(tasks),
           "weights": dict(estimators._RISK_WEIGHTS),
           "ablations": {}}

    for label, comps, renorm in ABLATIONS:
        estimators.set_priors(priors)
        estimators.set_risk_components(comps, renorm)
        act, rn = estimators.get_risk_components()
        eps = run_grid(tasks, [SecureVoI(lam=lam), ScreenedConventionalVoI(lam=lam)],
                       agent, conditions=conds, sev_profile="medium")
        rec = {"active": sorted(act), "renorm": rn, "by_policy_condition": {}}
        agg = defaultdict(list)
        for e in eps:
            agg[(e.policy, e.condition)].append(e)
        for (pol, cond), sel in sorted(agg.items()):
            asked = [e for e in sel if e.asked]
            acc = sum(bool(e.accepted) for e in asked)
            rec["by_policy_condition"][f"{pol}|{cond}"] = {
                "n": len(sel),
                "reject_given_ask": round(1 - acc / len(asked), 4) if asked else None,
                "unsafe": round(sum(e.unsafe for e in sel) / len(sel), 4),
                "attack_success": round(sum(e.attack_success for e in sel) / len(sel), 4),
                "goal": round(sum(e.goal_ok for e in sel) / len(sel), 4),
                "utility": round(sum(e.utility for e in sel) / len(sel), 4),
            }
        out["ablations"][label] = rec
        print(f"  [{label}] done", flush=True)

    estimators.set_risk_components()          # restore the default no-op path

    dest = args.out or f"results/models/{args.model}/risk_component_ablation.json"
    (ROOT / dest).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print(f"\nSTEP 27 -- response_risk COMPONENT ABLATION ({args.model})")
    print(f"  weights: 0.35*prior + 0.4*learned + 0.2*cue + off_schema | lambda={lam}")
    print("=" * 92)
    full = out["ablations"]["full"]["by_policy_condition"]
    for cond in [c.value for c in conds]:
        key = f"secure_voi|{cond}"
        if key not in full:
            continue
        print(f"\n{cond}   (secure_voi; delta vs full)\n")
        print(f"  {'ablation':22s} {'rej|ask':>8s} {'unsafe':>7s} {'d unsafe':>9s} "
              f"{'goal':>6s} {'util':>7s}")
        base = full[key]
        for label, _, _ in ABLATIONS:
            s = out["ablations"][label]["by_policy_condition"].get(key)
            if not s:
                continue
            rej = f"{s['reject_given_ask']:8.3f}" if s['reject_given_ask'] is not None else f"{'--':>8s}"
            d = s["unsafe"] - base["unsafe"]
            print(f"  {label:22s} {rej} {s['unsafe']:7.3f} {d:+9.3f} "
                  f"{s['goal']:6.3f} {s['utility']:+7.3f}")
    print(f"\nWrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
