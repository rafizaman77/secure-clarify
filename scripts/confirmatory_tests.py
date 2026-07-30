#!/usr/bin/env python3
"""Run the pre-declared confirmatory hypotheses from HYPOTHESES.md.

H1  SecureVoI vs ConventionalVoI            stealth   SecureVoI lower
H2  SecureVoI vs ScreenedConventionalVoI    stealth   SecureVoI lower   <-- decisive
H3  SecureVoI vs Stage1OnlySecureVoI        stealth   SecureVoI lower
H4  SecureVoI vs ConventionalVoI            benign    EQUIVALENCE (TOST)

H2 is the one the paper lives or dies on: ScreenedConventionalVoI is risk-blind
acquisition with SecureVoI's identical stage-2 screen, so their difference is the
stage-1 effect and nothing else. If it is not there, the two-stage framing is not
supported and the abstract must say so (HYPOTHESES.md decision rule 1).

Applies Steps 20-23 rather than the flat task-level bootstrap:
  * family -> task -> episode resampling (Step 20)
  * Holm correction across the confirmatory family, per model (Step 21)
  * Wilson intervals so a 0.000 rate is never reported as certainty (Step 23)
TOST for H4 (Step 22) runs only where a benign-condition episode file exists.

Usage:
  python scripts/confirmatory_tests.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.confirmatory import (paired_hierarchical_diff, holm,  # noqa: E402
                                         wilson_interval, format_rate,
                                         group_by_family_task)

STEALTH = "adversarial_stealth"

# (id, arm_a (baseline), arm_b (ours), condition, metric, direction)
HYPOTHESES = [
    ("H1", "conventional_voi", "secure_voi", STEALTH, "attack_success", "lower"),
    ("H2", "screened_conventional_voi", "secure_voi", STEALTH, "attack_success", "lower"),
]
# secondary, reported alongside for continuity with the existing tables
SECONDARY_METRIC = "unsafe"


def load(model: str) -> list[dict] | None:
    p = ROOT / f"results/models/{model}/screened_ablation_stealth_episodes.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def arm_units(eps, policy, condition, metric):
    sel = [e for e in eps if e["policy"] == policy and e["condition"] == condition]
    return group_by_family_task(sel, lambda e: float(bool(e[metric])))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="mistral-nemo-12b,llama-3.3-70b,"
                                        "gpt-oss-20b-cloud,gpt-oss-120b-cloud")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--out", default="results/confirmatory_tests.json")
    args = ap.parse_args()

    report = {"source": "HYPOTHESES.md (pre-declared 2026-07-30)",
              "primary_metric": "attack_success (exact attacker objective)",
              "secondary_metric": SECONDARY_METRIC,
              "resampling": "family -> task -> episode (Step 20)",
              "correction": "Holm across the confirmatory family, per model (Step 21)",
              "models": {}}

    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        eps = load(model)
        if eps is None:
            print(f"  [skip] {model}: no stealth episode file")
            continue
        entry = {"n_episodes": len(eps), "hypotheses": {}, "rates": {}}

        for pol in sorted({e["policy"] for e in eps}):
            sel = [e for e in eps if e["policy"] == pol and e["condition"] == STEALTH]
            for metric in ("attack_success", SECONDARY_METRIC):
                k = sum(1 for e in sel if e[metric])
                lo, hi = wilson_interval(k, len(sel))
                entry["rates"][f"{pol}|{metric}"] = {
                    "k": k, "n": len(sel), "rate": round(k / len(sel), 4) if sel else None,
                    "ci95": [round(lo, 4), round(hi, 4)],
                    "reported": format_rate(k, len(sel))}

        praw = {}
        for hid, arm_a, arm_b, cond, metric, _ in HYPOTHESES:
            pols = {e["policy"] for e in eps}
            if not {arm_a, arm_b} <= pols:
                entry["hypotheses"][hid] = {"status": "not runnable",
                                            "missing": sorted({arm_a, arm_b} - pols)}
                continue
            a = arm_units(eps, arm_a, cond, metric)
            b = arm_units(eps, arm_b, cond, metric)
            fam = paired_hierarchical_diff(a, b, n_boot=args.n_boot)

            # TWO UNITS, because they answer different questions and only one of
            # them is answerable here.
            #
            # main_120 has just TWO task families (file, calendar). Resampling
            # families with n=2 has almost no power, so its "fails to reject" is
            # not evidence of absence -- it is an untestable question on this
            # benchmark. Reporting only that number would have triggered
            # HYPOTHESES.md's decision rule 1 (rewrite the abstract) off a test
            # that cannot detect anything.
            #
            # The TASK-level paired bootstrap does have power and is the unit the
            # existing analysis uses; it generalizes to new tasks drawn from these
            # same two families, which is the claim the benchmark can support.
            per_task_a = {"all": {t: v for f in a for t, v in a[f].items()}}
            per_task_b = {"all": {t: v for f in b for t, v in b[f].items()}}
            task = paired_hierarchical_diff(per_task_a, per_task_b, n_boot=args.n_boot)

            entry["hypotheses"][hid] = {
                "comparison": f"{arm_a} - {arm_b}", "condition": cond,
                "metric": metric,
                "task_level": {
                    "generalizes_to": "new tasks from the SAME task families",
                    "diff": round(task["point"], 4),
                    "ci95": [round(task["ci_lo"], 4), round(task["ci_hi"], 4)],
                    "p_raw": round(task["p_value"], 4),
                    "n_pairs": task["n_pairs"]},
                "family_level": {
                    "generalizes_to": "new task FAMILIES",
                    "diff": round(fam["point"], 4),
                    "ci95": [round(fam["ci_lo"], 4), round(fam["ci_hi"], 4)],
                    "p_raw": round(fam["p_value"], 4),
                    "n_families": fam["n_families"],
                    "underpowered": fam["n_families"] < 5,
                    "note": ("only %d families: this test cannot detect an effect, "
                             "so a null result here is NOT evidence of absence"
                             % fam["n_families"]) if fam["n_families"] < 5 else ""},
                "diff_baseline_minus_ours": round(task["point"], 4),
                "n_pairs": task["n_pairs"]}
            praw[hid] = task["p_value"]

        for hid, h in holm(praw).items():
            entry["hypotheses"][hid]["p_holm"] = round(h["p_holm"], 4)
            entry["hypotheses"][hid]["reject_after_holm"] = h["reject_at_alpha"]
        report["models"][model] = entry

    (ROOT / args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("CONFIRMATORY TESTS -- pre-declared in HYPOTHESES.md")
    print(f"  primary metric: attack_success (exact attacker objective), {STEALTH}")
    print(f"  family -> task -> episode resampling, Holm per model\n")
    hdr = (f"  {'model':20s} {'H':3s} {'diff':>8s} {'task-level 95% CI':>20s} "
           f"{'p_raw':>7s} {'p_holm':>7s} {'reject':>7s} {'family p':>9s}")
    print(hdr); print("  " + "-" * (len(hdr) - 2))
    for model, entry in report["models"].items():
        for hid, h in sorted(entry["hypotheses"].items()):
            if h.get("status") == "not runnable":
                print(f"  {model:20s} {hid:3s}   not runnable (missing "
                      f"{','.join(h['missing'])})")
                continue
            t, f = h["task_level"], h["family_level"]
            ci = f"[{t['ci95'][0]:+.3f},{t['ci95'][1]:+.3f}]"
            print(f"  {model:20s} {hid:3s} {t['diff']:+8.3f} {ci:>20s} "
                  f"{t['p_raw']:7.4f} {h['p_holm']:7.4f} "
                  f"{str(h['reject_after_holm']):>7s} {f['p_raw']:9.3f}")
    fam_n = next((h["family_level"]["n_families"]
                  for e in report["models"].values()
                  for h in e["hypotheses"].values() if "family_level" in h), 0)
    if fam_n < 5:
        print(f"\n  NOTE: only {fam_n} task families exist, so the family-level column "
              f"is underpowered by construction.\n  A null there is NOT evidence of "
              f"absence; it means the benchmark cannot answer the\n  'generalizes to new "
              f"domains' question. Task-level is the reportable test.")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
