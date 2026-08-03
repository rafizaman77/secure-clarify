#!/usr/bin/env python3
"""Report the 2x2 factorial NEXT TO the screen's operating point.

WHY THESE BELONG IN ONE TABLE. The stage-1/stage-2 split is not a property of the
architecture -- it inverts with where the screen sits on the recall/precision
frontier. Measured on Mistral, changing only the screen's prompt moves stage 1
from +0.146 to +0.000 and stage 2 from +0.000 to +0.208. A factorial reported
without its operating point is therefore uninterpretable, and three per-model
safety numbers reported side by side can silently pool three different regimes.

This joins:
  results/screen_operating_point.json   recall / specificity / balanced accuracy
                                        on 81 corpus attacks (4 families held
                                        out) and 24 graded benign answers
  results/confirmatory_*.json           H1/H2/H3 at that configuration

and reports, per model, the operating point of the prompt actually used followed
by the factorial measured under it.

Usage:
  python scripts/factorial_at_operating_point.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# model -> (prompt mode used for that factorial, confirmatory file, label)
CONFIGS = [
    ("mistral-nemo-12b", "rating", "results/confirmatory_tests.json", "main_120"),
    ("mistral-nemo-12b", "classify", "results/confirmatory_classify.json", "main_120"),
    ("llama-3.3-70b", "rating", "results/confirmatory_tests.json", "main_120"),
    ("gpt-oss-20b-cloud", "rating", "results/confirmatory_tests.json", "main_120"),
    ("gpt-oss-20b-cloud", "contextual", "results/confirmatory_ctx.json", "main_120"),
    ("mistral-nemo-12b", "rating", "results/confirmatory_families.json", "families"),
    ("llama-3.3-70b", "rating", "results/confirmatory_families.json", "families"),
    ("gpt-oss-20b-cloud", "rating", "results/confirmatory_families.json", "families"),
]


def load(path):
    p = ROOT / path
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/factorial_at_operating_point.json")
    args = ap.parse_args()

    op = load("results/screen_operating_point.json") or {}
    report = {"note": ("the factorial inverts with the screen's operating point, "
                       "so the two are only meaningful together"),
              "rows": []}

    print("FACTORIAL AT ITS OPERATING POINT")
    print("  operating point: 81 corpus attacks (4 families held out) x 24 graded "
          "benign answers")
    print("  factorial: exact attacker objective, stealth, Holm-corrected\n")
    hdr = (f"  {'model':18s} {'prompt':11s} {'tasks':9s} | {'held-out':>9s} "
           f"{'spec':>6s} {'bal':>6s} | {'H2 stage1':>11s} {'H3 stage2':>11s}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for model, mode, cpath, label in CONFIGS:
        conf = load(cpath)
        if not conf or model not in conf.get("models", {}):
            continue
        h = conf["models"][model]["hypotheses"]
        pt = ((op.get(model) or {}).get("modes") or {}).get(mode)
        if pt:
            k, n = [int(x) for x in pt["recall_by_split"]["test"].split("/")]
            ho, spec = k / n, pt["specificity"]
            bal = (ho + spec) / 2
            ptxt = f"{ho:9.3f} {spec:6.3f} {bal:6.3f}"
        else:
            ho = spec = bal = None
            ptxt = f"{'--':>9s} {'--':>6s} {'--':>6s}"

        def cell(hid):
            e = h.get(hid, {})
            if "task_level" not in e:
                return f"{'n/a':>11s}"
            d = e["task_level"]["diff"]
            star = "*" if e.get("reject_after_holm") else " "
            return f"{d:+10.3f}{star}"

        print(f"  {model:18s} {mode:11s} {label:9s} | {ptxt} | "
              f"{cell('H2')} {cell('H3')}")
        report["rows"].append({
            "model": model, "prompt": mode, "tasks": label,
            "held_out_recall": round(ho, 4) if ho is not None else None,
            "specificity": spec, "balanced_accuracy": round(bal, 4) if bal else None,
            "H2": h.get("H2", {}).get("task_level", {}).get("diff"),
            "H2_significant": h.get("H2", {}).get("reject_after_holm"),
            "H3": h.get("H3", {}).get("task_level", {}).get("diff"),
            "H3_significant": h.get("H3", {}).get("reject_after_holm"),
        })

    print("\n  * = significant after Holm correction")
    print("\n  Read the rows for one model together: where the screen sits decides")
    print("  which stage carries the effect. A factorial without its operating")
    print("  point does not identify the architecture.")
    (ROOT / args.out).write_text(json.dumps(report, indent=2) + "\n",
                                 encoding="utf-8")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
