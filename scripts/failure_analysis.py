#!/usr/bin/env python3
"""Jul 24 deliverable: read every unsafe/failed episode in a real-model
primary_episodes.json and categorize failure modes -- not just report rates,
explain WHAT happened (which policy, which channel, which prohibited-action
pattern, benign-vs-adversarial) so the paper's failure analysis section has
real material instead of just the summary numbers already in main_table.md.

Usage:
  python scripts/failure_analysis.py --episodes results/primary_episodes.json --model-name mistral-nemo-12b
  python scripts/failure_analysis.py --episodes results/models/llama-3.3-70b-versatile/primary_episodes.json --model-name llama-3.3-70b-versatile
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]


def load_episodes(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze(eps: list[dict]) -> dict:
    unsafe = [e for e in eps if e["unsafe"]]
    failed_goal = [e for e in eps if not e["goal_ok"]]
    attack_success = [e for e in eps if e["attack_success"]]

    def by(field_fn, items):
        c = Counter(field_fn(e) for e in items)
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))

    unsafe_reason_patterns = Counter()
    for e in unsafe:
        for reason in (e.get("reasons") or "").split(";"):
            reason = reason.strip()
            if reason:
                unsafe_reason_patterns[reason] += 1

    return {
        "n_episodes": len(eps),
        "n_unsafe": len(unsafe),
        "n_goal_failed": len(failed_goal),
        "n_attack_success": len(attack_success),
        "unsafe_by_policy": by(lambda e: e["policy"], unsafe),
        "unsafe_by_condition": by(lambda e: e["condition"], unsafe),
        "unsafe_by_channel": by(lambda e: e.get("channel") or "none", unsafe),
        "unsafe_reason_patterns": dict(sorted(unsafe_reason_patterns.items(),
                                              key=lambda kv: -kv[1])),
        "goal_failed_by_policy": by(lambda e: e["policy"], failed_goal),
        "goal_failed_by_condition": by(lambda e: e["condition"], failed_goal),
        "goal_failed_by_domain": by(lambda e: e["domain"], failed_goal),
        "attack_success_by_policy": by(lambda e: e["policy"], attack_success),
    }


def render_markdown(model_name: str, a: dict) -> str:
    lines = [
        f"## {model_name}",
        "",
        f"{a['n_episodes']} episodes: **{a['n_unsafe']} unsafe** "
        f"({a['n_unsafe']/a['n_episodes']*100:.1f}%), "
        f"**{a['n_goal_failed']} goal-failed** "
        f"({a['n_goal_failed']/a['n_episodes']*100:.1f}%), "
        f"**{a['n_attack_success']} attack-succeeded**.",
        "",
        "### Unsafe episodes by policy",
        "| Policy | Count |",
        "|---|---|",
    ]
    for k, v in a["unsafe_by_policy"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "### Unsafe episodes by condition", "| Condition | Count |", "|---|---|"]
    for k, v in a["unsafe_by_condition"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "### Unsafe episodes by channel", "| Channel | Count |", "|---|---|"]
    for k, v in a["unsafe_by_channel"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "### Prohibited-action patterns triggered (safety_verifier reasons)",
             "| Pattern | Count |", "|---|---|"]
    for k, v in a["unsafe_reason_patterns"].items():
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "### Goal failures by policy", "| Policy | Count |", "|---|---|"]
    for k, v in a["goal_failed_by_policy"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "### Goal failures by domain", "| Domain | Count |", "|---|---|"]
    for k, v in a["goal_failed_by_domain"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", default="results/primary_episodes.json")
    ap.add_argument("--model-name", default="model")
    ap.add_argument("--out", default="docs/failure_analysis.md")
    ap.add_argument("--append", action="store_true",
                    help="append this model's section instead of overwriting the file")
    args = ap.parse_args()

    eps_path = ROOT / args.episodes
    if not eps_path.exists():
        raise SystemExit(f"{args.episodes} not found")
    eps = load_episodes(eps_path)
    analysis = analyze(eps)
    section = render_markdown(args.model_name, analysis)

    out_path = ROOT / args.out
    if args.append and out_path.exists():
        existing = out_path.read_text(encoding="utf-8")
        out_path.write_text(existing.rstrip() + "\n\n---\n\n" + section, encoding="utf-8")
    else:
        header = (
            "# Failure Analysis\n\n"
            "Generated by `scripts/failure_analysis.py` from real-model "
            "`primary_episodes.json` files -- not ScriptedAgent. One section "
            "per model; re-run with `--append` to add the next model rather "
            "than overwriting.\n\n---\n\n"
        )
        out_path.write_text(header + section, encoding="utf-8")

    print(section)
    print(f"\nWrote/updated {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
