#!/usr/bin/env python3
"""Jul 20 deliverable: render results/stats.json as the paper's main table
(markdown, ready to paste into the seven-page draft once results are final).

Usage:
  python scripts/make_main_table.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

POLICY_LABEL = {
    "never_ask": "Never Ask",
    "conventional_voi": "Conventional VoI",
    "trusted_only": "Trusted-Only",
    "secure_voi": "SecureVoI",
}
ROW_ORDER = ["never_ask", "conventional_voi", "trusted_only", "secure_voi"]


def fmt(d: dict) -> str:
    lo, hi = d["ci95"]
    return f"{d['point']:.3f} [{lo:.3f}, {hi:.3f}]"


def main() -> int:
    stats_path = ROOT / "results" / "stats.json"
    if not stats_path.exists():
        raise SystemExit("results/stats.json not found -- run scripts/compute_stats.py first.")
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    pp = stats["per_policy_condition"]

    lines = [
        "# Main results table",
        "",
        f"_Generated from `results/stats.json` -- {stats['n_tasks']} test tasks, "
        f"{stats['n_bootstrap']} bootstrap resamples, {int(stats['ci_level']*100)}% CI. "
        f"Agent backend: **{stats['agent_backend']}**._",
        "",
        "| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate | Adversarial utility |",
        "|---|---|---|---|---|",
    ]
    for pol in ROW_ORDER:
        b = pp.get(f"{pol}|benign")
        a = pp.get(f"{pol}|adversarial")
        if not b or not a:
            continue
        lines.append(
            f"| {POLICY_LABEL[pol]} | {fmt(b['goal_rate'])} | {fmt(b['utility'])} | "
            f"{fmt(a['unsafe_rate'])} | {fmt(a['utility'])} |"
        )

    lines += ["", "## Key comparisons (paired bootstrap, same test tasks)", ""]
    for key, d in stats["comparisons"].items():
        sig = "**significant**" if d["significant_at_0.05"] else "not significant"
        pretty = key.replace("_", " ")
        lines.append(f"- {pretty}: {d['point']:+.4f} [{d['ci_lo']:.4f}, {d['ci_hi']:.4f}], "
                     f"p={d['p_value']:.4f} ({sig} at α=0.05)")

    if "ScriptedAgent" in str(stats.get("agent_backend", "")):
        lines += [
            "",
            "**This table is still ScriptedAgent, not a measured result on a real "
            "open-weight model.** Re-run `scripts/run_primary.py` and "
            "`scripts/compute_stats.py` with `--backend hf_local`/`openai`/`ollama` "
            "before using these numbers in the paper.",
        ]

    out_path = ROOT / "results" / "main_table.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
