#!/usr/bin/env python3
"""Step 8 of RESEARCH_PLAN.md: report the noisy condition.

WHY. The paper advertises three response conditions -- benign, noisy, and
adversarial -- but every reported table covers only two. `main_120.json` carries
540 noisy responses that no run had ever evaluated. Two things need checking:

  A. VALIDITY OF THE SCREEN. Stage 2 rejects responses whose risk exceeds a
     threshold. If it also rejects merely *unhelpful* answers, it is not
     detecting malice, it is detecting unusual text -- and the safety result
     would be an artifact of that. This compares the stage-2 risk score and
     rejection rate on benign vs noisy vs adversarial.

  B. WHETHER THE CONDITION DISCRIMINATES AT ALL. A condition earns its place in
     a benchmark only if policies can differ on it.

Usage:
  python scripts/noisy_condition.py --model mistral-nemo-12b
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

POLICY_ORDER = ["never_ask", "always_ask", "confidence_threshold",
                "conventional_voi", "channel_heuristic", "trusted_only",
                "secure_voi"]


def risk_by_condition(tasks_file: str, backend: str, model: str,
                      base_url: str, api_key_env: str, host: str,
                      limit: int) -> dict:
    """Part A: the stage-2 risk score itself, per condition, on matched responses.

    Matched by construction: the benign / noisy / adversarial responses of a
    given (task, question, channel) differ only in body text, so a difference in
    mean risk is attributable to the text and not to task or channel.
    """
    from secure_clarify.schema import load_task
    from secure_clarify.estimators import response_risk
    from secure_clarify.agent import CachingAgent
    from scripts.model_backends import build_agent

    tasks = [load_task(d) for d in
             json.loads((ROOT / tasks_file).read_text(encoding="utf-8"))][:limit]
    agent = CachingAgent(build_agent(backend, model, base_url, api_key_env, host))

    per_cond = defaultdict(list)
    # paired: same (task, qid, channel) across conditions
    paired = defaultdict(dict)
    for t in tasks:
        for q in t.candidate_questions:
            for r in t.responses:
                if r.qid != q.qid:
                    continue
                cond = r.condition.value if hasattr(r.condition, "value") else r.condition
                try:
                    risk = response_risk(r.text, t, q, r.channel, agent)
                except Exception:
                    continue
                per_cond[cond].append(risk)
                ch = r.channel.value if hasattr(r.channel, "value") else r.channel
                paired[(t.task_id, q.qid, ch)][cond] = risk

    out = {"per_condition": {}, "paired_benign_vs_noisy": None}
    for cond, v in sorted(per_cond.items()):
        out["per_condition"][cond] = {
            "n": len(v), "mean": round(sum(v) / len(v), 4),
            "min": round(min(v), 4), "max": round(max(v), 4)}

    # the decisive paired test: is noisy risk EVER above benign risk?
    both = [(d["benign"], d["noisy"]) for d in paired.values()
            if "benign" in d and "noisy" in d]
    if both:
        diffs = [n - b for b, n in both]
        out["paired_benign_vs_noisy"] = {
            "n_pairs": len(both),
            "mean_diff_noisy_minus_benign": round(sum(diffs) / len(diffs), 6),
            "n_pairs_noisy_higher": sum(1 for d in diffs if d > 1e-9),
            "max_abs_diff": round(max(abs(d) for d in diffs), 6),
        }
    return out


def outcomes(episodes_file: Path) -> dict:
    """Part B: policy outcomes on benign vs noisy, from a real run."""
    eps = json.loads(episodes_file.read_text(encoding="utf-8"))
    out = {}
    for pol in POLICY_ORDER:
        for cond in ("benign", "noisy"):
            sel = [e for e in eps if e["policy"] == pol and e["condition"] == cond]
            if not sel:
                continue
            asked = [e for e in sel if e["asked"]]
            acc = sum(bool(e.get("accepted")) for e in asked)
            out.setdefault(pol, {})[cond] = {
                "n": len(sel),
                "ask_rate": round(len(asked) / len(sel), 4),
                "accept_given_ask": round(acc / len(asked), 4) if asked else None,
                "reject_given_ask": round(1 - acc / len(asked), 4) if asked else None,
                "goal": round(sum(e["goal_ok"] for e in sel) / len(sel), 4),
                "unsafe": round(sum(e["unsafe"] for e in sel) / len(sel), 4),
                "unresolved": round(sum(bool(e.get("unresolved")) for e in sel) / len(sel), 4),
                "utility": round(sum(e["utility"] for e in sel) / len(sel), 4),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mistral-nemo-12b")
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--limit", type=int, default=24,
                    help="tasks to score for the risk comparison (Part A)")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--backend-model", default="mistral-nemo:12b")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--out", default="results/noisy_condition.json")
    args = ap.parse_args()

    epf = ROOT / f"results/models/{args.model}/noisy_episodes.json"
    if not epf.exists():
        print(f"missing {epf}", file=sys.stderr)
        return 1

    report = {"step": "8 -- the noisy condition",
              "model": args.model,
              "screen_validity": risk_by_condition(
                  args.tasks, args.backend, args.backend_model, args.base_url,
                  args.api_key_env, args.host, args.limit),
              "outcomes": outcomes(epf)}

    pc = report["screen_validity"]["per_condition"]
    pair = report["screen_validity"]["paired_benign_vs_noisy"]

    print("STEP 8 -- THE NOISY CONDITION")
    print("=" * 74)
    print("\nA. IS THE STAGE-2 SCREEN FOOLED BY ORDINARY NOISE?\n")
    print(f"   {'condition':22s} {'n':>4s} {'mean risk':>10s} {'min':>7s} {'max':>7s}")
    for cond in ("benign", "noisy", "adversarial", "adversarial_stealth"):
        s = pc.get(cond)
        if s:
            print(f"   {cond:22s} {s['n']:4d} {s['mean']:10.3f} "
                  f"{s['min']:7.3f} {s['max']:7.3f}")
    if pair:
        print(f"\n   paired within (task, question, channel), n={pair['n_pairs']}:")
        print(f"     mean risk(noisy) - risk(benign) = "
              f"{pair['mean_diff_noisy_minus_benign']:+.6f}")
        print(f"     pairs where noisy scored HIGHER = "
              f"{pair['n_pairs_noisy_higher']} / {pair['n_pairs']}")

    print("\nB. DOES THE CONDITION DISCRIMINATE BETWEEN POLICIES?\n")
    print(f"   {'policy':22s} {'cond':7s} {'ask':>6s} {'rej|ask':>8s} "
          f"{'goal':>6s} {'unsafe':>7s} {'util':>7s}")
    for pol in POLICY_ORDER:
        for cond in ("benign", "noisy"):
            s = report["outcomes"].get(pol, {}).get(cond)
            if not s:
                continue
            rej = f"{s['reject_given_ask']:8.3f}" if s['reject_given_ask'] is not None else f"{'--':>8s}"
            print(f"   {pol:22s} {cond:7s} {s['ask_rate']:6.3f} {rej} "
                  f"{s['goal']:6.3f} {s['unsafe']:7.3f} {s['utility']:+7.3f}")

    (ROOT / args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
