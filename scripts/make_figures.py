#!/usr/bin/env python3
"""Jul 24 deliverable: final figures, generated as dependency-free SVG.

matplotlib is unusable in this environment (broken numpy ABI on the system
Python -- same root cause documented in days/jul17-18/environment-notes.md),
so this hand-builds SVG directly: no external dependencies, works with plain
Python anywhere. Two figures:
  1. figures/frontier.svg   -- safety-utility frontier (results/frontier.json)
  2. figures/main_table.svg -- per-policy bar chart (results/stats.json)

Usage:
  python scripts/make_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

W, H = 640, 420
PAD = 60
PLOT_W, PLOT_H = W - 2 * PAD, H - 2 * PAD

COLORS = {
    "benign_util": "#2b8a3e",
    "adv_unsafe": "#c92a2a",
    "bar_goal": "#4263eb",
    "bar_unsafe": "#c92a2a",
    "bar_util": "#2b8a3e",
    "axis": "#495057",
    "grid": "#dee2e6",
}


def _svg_header(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{width/2}" y="24" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>',
    ]


def make_frontier_svg(frontier: list[dict], out_path: Path, subtitle: str = "") -> None:
    lines = _svg_header(W, H, "Safety-Utility Frontier")
    if subtitle:
        lines.append(f'<text x="{W/2}" y="42" text-anchor="middle" font-size="11" fill="#666">{subtitle}</text>')

    lambdas = [f["lambda"] for f in frontier]
    max_lam = max(lambdas) or 1
    # x = lambda (log-ish spacing not needed, linear is fine for 0-8 range), y = rate 0..1
    def x(lam):
        return PAD + (lam / max_lam) * PLOT_W

    def y(val):
        return PAD + 20 + (1 - val) * (PLOT_H - 20)

    # axes
    lines.append(f'<line x1="{PAD}" y1="{PAD+20}" x2="{PAD}" y2="{H-PAD}" stroke="{COLORS["axis"]}"/>')
    lines.append(f'<line x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}" stroke="{COLORS["axis"]}"/>')
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        yy = y(frac)
        lines.append(f'<line x1="{PAD}" y1="{yy}" x2="{W-PAD}" y2="{yy}" stroke="{COLORS["grid"]}" stroke-dasharray="2,2"/>')
        lines.append(f'<text x="{PAD-8}" y="{yy+4}" text-anchor="end" font-size="10">{frac:.2f}</text>')
    lines.append(f'<text x="{PAD-45}" y="{PAD+10}" font-size="11" fill="{COLORS["axis"]}">rate</text>')
    lines.append(f'<text x="{W/2}" y="{H-15}" text-anchor="middle" font-size="11">lambda (risk weight)</text>')

    for key, label, color in (("benign_util", "benign utility", COLORS["benign_util"]),
                              ("adv_unsafe", "adversarial unsafe rate", COLORS["adv_unsafe"])):
        pts = " ".join(f"{x(f['lambda']):.1f},{y(f[key]):.1f}" for f in frontier)
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for f in frontier:
            lines.append(f'<circle cx="{x(f["lambda"]):.1f}" cy="{y(f[key]):.1f}" r="3.5" fill="{color}"/>')

    legend_y = PAD + 5
    for i, (label, color) in enumerate([("benign utility", COLORS["benign_util"]),
                                        ("adversarial unsafe rate", COLORS["adv_unsafe"])]):
        ly = legend_y + i * 16
        lines.append(f'<rect x="{W-PAD-140}" y="{ly-8}" width="12" height="12" fill="{color}"/>')
        lines.append(f'<text x="{W-PAD-122}" y="{ly+2}" font-size="10">{label}</text>')

    for f in frontier:
        lines.append(f'<text x="{x(f["lambda"]):.1f}" y="{H-PAD+15}" text-anchor="middle" font-size="9">{f["lambda"]}</text>')

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def make_main_table_svg(stats: dict, out_path: Path) -> None:
    pp = stats["per_policy_condition"]
    policy_order = ["never_ask", "always_ask", "confidence_threshold",
                    "conventional_voi", "trusted_only", "secure_voi"]
    labels = {"never_ask": "Never Ask", "always_ask": "Always Ask",
             "confidence_threshold": "Confidence Thresh.", "conventional_voi": "Conventional VoI",
             "trusted_only": "Trusted-Only", "secure_voi": "SecureVoI"}
    rows = [p for p in policy_order if f"{p}|adversarial" in pp]

    height = 100 + len(rows) * 46
    lines = _svg_header(W, height, "Adversarial Unsafe Rate by Policy")
    bar_x0 = PAD + 130
    bar_max_w = W - PAD - bar_x0 - 60

    for i, pol in enumerate(rows):
        d = pp[f"{pol}|adversarial"]["unsafe_rate"]
        yy = 60 + i * 46
        val = d["point"]
        lo, hi = d["ci95"]
        bar_w = val * bar_max_w
        lines.append(f'<text x="{bar_x0-8}" y="{yy+16}" text-anchor="end" font-size="12">{labels.get(pol, pol)}</text>')
        lines.append(f'<rect x="{bar_x0}" y="{yy}" width="{bar_max_w}" height="24" fill="#f1f3f5"/>')
        lines.append(f'<rect x="{bar_x0}" y="{yy}" width="{max(bar_w,1):.1f}" height="24" fill="{COLORS["bar_unsafe"]}"/>')
        ci_x0, ci_x1 = bar_x0 + lo * bar_max_w, bar_x0 + hi * bar_max_w
        lines.append(f'<line x1="{ci_x0:.1f}" y1="{yy+12}" x2="{ci_x1:.1f}" y2="{yy+12}" stroke="black" stroke-width="1.5"/>')
        lines.append(f'<text x="{bar_x0+bar_max_w+8}" y="{yy+16}" font-size="11">{val:.3f} [{lo:.2f},{hi:.2f}]</text>')

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    figures_dir = ROOT / "figures"
    figures_dir.mkdir(exist_ok=True)

    frontier_path = ROOT / "results" / "frontier.json"
    if frontier_path.exists():
        frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
        make_frontier_svg(frontier, figures_dir / "frontier.svg",
                          subtitle="ScriptedAgent pilot sweep, 40 tasks (docs/03_gonogo_memo.md)")
        print(f"Wrote {(figures_dir / 'frontier.svg').relative_to(ROOT)}")

    stats_path = ROOT / "results" / "stats.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        make_main_table_svg(stats, figures_dir / "main_table.svg")
        print(f"Wrote {(figures_dir / 'main_table.svg').relative_to(ROOT)} "
              f"(agent_backend: {stats.get('agent_backend')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
