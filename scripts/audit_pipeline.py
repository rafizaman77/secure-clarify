#!/usr/bin/env python3
"""Step 2 of RESEARCH_PLAN.md: audit the acceptance-to-action pipeline.

THE QUESTION THIS ANSWERS. Multiple risk-blind policies report identical unsafe
rates (0.583). If accepting an adversarial response MECHANICALLY caused the
simulator to insert a prohibited action, the headline result would be partly
hard-coded and the benchmark would need repair before publication.

For every adversarial episode this records the full chain:
  asked? -> question+channel -> did that channel actually carry an attack? ->
  accepted? -> attacker's requested action -> actual tool calls emitted ->
  which verifier rule fired -> did the exact attacker objective succeed?

and decomposes the unsafe rate into the two factors the paper currently
conflates:

  EXPOSURE   = P(policy accepted a response that genuinely carried an attack)
               -- a property of the POLICY
  COMPLIANCE = P(unsafe | exposed)
               -- a property of the MODEL
  unsafe    ~= EXPOSURE x COMPLIANCE

Also emits the stratified samples Step 2 requires for manual inspection
(>=20 each: explicit successes, stealth successes, accepted-but-not-unsafe,
rejected attacks, benign).

Usage:
  python scripts/audit_pipeline.py --model mistral-nemo-12b
  python scripts/audit_pipeline.py --all
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RISK_BLIND_ACCEPT_ALL = "conventional_voi"   # cleanest probe of model compliance


def load(model: str, fname: str):
    p = ROOT / "results" / "models" / model / fname
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def index_tasks(task_file: str) -> dict:
    return {t["task_id"]: t for t in
            json.loads((ROOT / task_file).read_text(encoding="utf-8"))}


def attack_on_channel(task: dict, channel, condition: str):
    """The Response object the policy actually received, and whether it was an attack."""
    for r in task.get("responses", []):
        if r["channel"] == channel and r["condition"] == condition:
            return r
    return None


def audit_model(model: str, task_file: str, episodes_file: str) -> dict | None:
    eps = load(model, episodes_file)
    if not eps:
        return None
    tasks = index_tasks(task_file)
    rows = []
    for e in eps:
        cond = e["condition"]
        task = tasks.get(e["task_id"])
        if task is None:
            continue
        resp = attack_on_channel(task, e.get("channel"), cond) if e.get("channel") else None
        carried = bool(resp and resp.get("carries_attack"))
        rows.append({
            "task_id": e["task_id"], "policy": e["policy"], "condition": cond,
            "domain": e.get("domain"), "asked": e.get("asked"),
            "channel": e.get("channel"), "qformat": e.get("qformat"),
            "accepted": bool(e.get("accepted")),
            "response_carried_attack": carried,
            "attacker_objective": (resp or {}).get("attack_type"),
            "exposed": bool(e.get("accepted")) and carried,
            "tool_calls": e.get("plan"),
            "verifier_reasons": e.get("reasons"),
            "unsafe": e["unsafe"], "goal_ok": e["goal_ok"],
            "attack_success": e["attack_success"],
            "prohibited": task.get("prohibited_actions"),
        })

    def rate(sel, field="unsafe"):
        s = [r for r in sel]
        return (sum(bool(r[field]) for r in s) / len(s)) if s else None

    out = {"model": model, "task_file": task_file, "n_episodes": len(rows)}
    for cond in sorted({r["condition"] for r in rows}):
        if cond == "benign":
            continue
        per_policy = {}
        for pol in sorted({r["policy"] for r in rows}):
            sel = [r for r in rows if r["policy"] == pol and r["condition"] == cond]
            if not sel:
                continue
            exposed = [r for r in sel if r["exposed"]]
            per_policy[pol] = {
                "n": len(sel),
                "ask_rate": round(sum(bool(r["asked"]) for r in sel) / len(sel), 4),
                "accept_rate": round(sum(r["accepted"] for r in sel) / len(sel), 4),
                "exposure": round(len(exposed) / len(sel), 4),
                "compliance_given_exposed": (round(rate(exposed), 4) if exposed else None),
                "unsafe": round(rate(sel), 4),
                "attack_success": round(rate(sel, "attack_success"), 4),
                "goal": round(rate(sel, "goal_ok"), 4),
            }
        out[cond] = per_policy

    # benign false-positive rejection: how often is a harmless answer refused?
    ben = [r for r in rows if r["condition"] == "benign" and r["asked"]]
    out["benign"] = {
        pol: {"rejected_benign_rate": round(
                 1 - (sum(r["accepted"] for r in [x for x in ben if x["policy"] == pol])
                      / max(1, len([x for x in ben if x["policy"] == pol]))), 4),
              "unsafe": round(rate([x for x in ben if x["policy"] == pol]), 4)}
        for pol in sorted({r["policy"] for r in ben})
    }
    out["_rows"] = rows
    return out


def stratified_samples(rows: list[dict], n: int, seed: int = 20260729) -> dict:
    rng = random.Random(seed)
    strata = {
        "explicit_success":       [r for r in rows if r["condition"] == "adversarial" and r["attack_success"]],
        "stealth_success":        [r for r in rows if r["condition"] == "adversarial_stealth" and r["attack_success"]],
        "accepted_not_unsafe":    [r for r in rows if r["exposed"] and not r["unsafe"]],
        "rejected_attack":        [r for r in rows if r["response_carried_attack"] and r["asked"] and not r["accepted"]],
        "benign":                 [r for r in rows if r["condition"] == "benign"],
    }
    return {k: rng.sample(v, min(n, len(v))) for k, v in strata.items()}, \
           {k: len(v) for k, v in strata.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mistral-nemo-12b")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--sample-size", type=int, default=20)
    ap.add_argument("--out", default="results/pipeline_audit.json")
    args = ap.parse_args()

    models = ([d.name for d in sorted((ROOT / "results" / "models").iterdir())
               if d.is_dir() and not d.name.startswith("_") and "diversity" not in d.name]
              if args.all else [args.model])

    report = {"step": "2 -- acceptance-to-action pipeline audit", "models": {}}
    all_rows = []
    for m in models:
        a = audit_model(m, "tasks/main_120.json", "primary_episodes.json")
        if not a:
            continue
        rows = a.pop("_rows")
        # fold in the stealth tier where it exists
        st = audit_model(m, "tasks/main_120.json", "screened_ablation_stealth_episodes.json")
        if st:
            rows += st.pop("_rows")
            a["adversarial_stealth"] = st.get("adversarial_stealth", {})
        all_rows += rows
        report["models"][m] = a

    samples, counts = stratified_samples(all_rows, args.sample_size)
    report["stratified_sample_counts_available"] = counts
    report["stratified_samples"] = samples
    (ROOT / args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("STEP 2 -- acceptance-to-action audit")
    print("\nunsafe = EXPOSURE (policy property) x COMPLIANCE (model property)\n")
    print(f"{'model':22s} {'policy':24s} {'expos':>6s} {'compl':>6s} {'unsafe':>7s}")
    for m, a in report["models"].items():
        for pol, s in (a.get("adversarial") or {}).items():
            if pol != RISK_BLIND_ACCEPT_ALL:
                continue
            print(f"{m:22s} {pol:24s} {s['exposure']:6.3f} "
                  f"{s['compliance_given_exposed'] if s['compliance_given_exposed'] is not None else float('nan'):6.3f} "
                  f"{s['unsafe']:7.3f}")
    print("\nstratified sample sizes available for manual inspection:")
    for k, v in counts.items():
        flag = "" if v >= args.sample_size else f"  <-- only {v}, need {args.sample_size}"
        print(f"  {k:22s} {v:5d}{flag}")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
