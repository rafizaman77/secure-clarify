#!/usr/bin/env python3
"""Attack-strength sensitivity: explicit vs stealth injections, per policy.

The question this answers is the one a reviewer asks first: does SecureVoI's
0.000 mean the defense is good, or only that the attacks are loud? The stealth
tier carries the SAME prohibited action on the SAME channel and task with the
tells removed, so the explicit->stealth delta isolates sensitivity to attack
PRESENTATION. A defense whose safety collapses under rewording was keying on
surface features; one that holds was reasoning about the action.

Pairing is at the TASK level and both tiers must come from the SAME serving
stack. Cross-stack pairs (e.g. Ollama-Cloud explicit vs Groq stealth) confound
presentation with quantization/sampling and are refused -- pass --allow-cross-stack
only if you intend to report that confound explicitly.

Usage:
  python scripts/stealth_compare.py \
      --explicit results/models/mistral-nemo-12b/primary_episodes.json \
      --stealth  results/stealth/mistral-nemo-12b_episodes.json \
      --label mistral-nemo-12b
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.compute_stats import (  # noqa: E402
    N_BOOTSTRAP, CI, _seeded_rng, _rate, load_episodes)
from secure_clarify.schema import load_task  # noqa: E402

POLICY_ORDER = ["never_ask", "always_ask", "confidence_threshold",
                "conventional_voi", "trusted_only", "channel_heuristic",
                "secure_voi"]


def attack_channel(task, condition: str) -> str | None:
    """Which channel carries the attack for this task in this tier."""
    for r in task.responses:
        if r.condition.value == condition and r.carries_attack:
            return r.channel.value
    return None


def screen_evasion(eps, tasks, condition: str, policy: str) -> dict:
    """Stage-2 miss rate: of the attacks that actually REACHED the response
    screen, how many did it accept?

    This is the sharpest measure of the stealth effect and the one the unsafe
    rate blurs. A policy can post a low unsafe rate by never routing to the
    attacked channel at all (stage-1 avoidance) -- that says nothing about
    whether its content screen works. Conditioning on "the policy asked, on the
    channel carrying the attack" isolates stage 2: denominator = attacks the
    screen was actually shown, numerator = attacks it waved through.
    """
    reached = accepted = 0
    for e in eps:
        if e["policy"] != policy or e["condition"] != condition or not e["asked"]:
            continue
        if e["channel"] == attack_channel(tasks[e["task_id"]], condition):
            reached += 1
            accepted += bool(e["accepted"])
    return {"reached_screen": reached, "accepted_by_screen": accepted,
            "evasion_rate": (accepted / reached) if reached else None}


def paired_tier_diff(task_ids, by_task, policy, field, rng) -> dict:
    """Bootstrap CI + two-sided p for
    metric(policy, adversarial_stealth) - metric(policy, adversarial),
    resampling the SAME task set for both tiers each iteration.

    Task-level pairing (not episode-level) because the two tiers' episodes for a
    task are driven by the same underlying attack objective and channel -- they
    are not independent draws, and resampling them separately would understate
    the variance of the difference.
    """
    def diff_for(ids):
        a = [e for tid in ids for e in by_task[tid]
             if e["policy"] == policy and e["condition"] == "adversarial_stealth"]
        b = [e for tid in ids for e in by_task[tid]
             if e["policy"] == policy and e["condition"] == "adversarial"]
        return _rate(a, field) - _rate(b, field)

    n = len(task_ids)
    point = diff_for(task_ids)
    boots = sorted(diff_for([task_ids[rng.randrange(n)] for _ in range(n)])
                   for _ in range(N_BOOTSTRAP))
    lo = boots[int((1 - CI) / 2 * N_BOOTSTRAP)]
    hi = boots[int((1 + CI) / 2 * N_BOOTSTRAP) - 1]
    # Two-sided bootstrap p = 2 * min(P(b<=0), P(b>=0)), clipped to 1.
    # NOT the "fraction whose sign disagrees with the point estimate" form: when a
    # policy sits at 0.000 in BOTH tiers every resample is exactly 0.0, nothing
    # "disagrees", and that form reports p = 0.000 -- reading as maximally
    # significant for what is actually the total absence of an effect. Expect many
    # exact-zero deltas here, since several policies are at 0.000 in both tiers.
    n_le = sum(1 for b in boots if b <= 0)
    n_ge = sum(1 for b in boots if b >= 0)
    p_value = min(1.0, 2.0 * min(n_le, n_ge) / N_BOOTSTRAP)
    return {"point": point, "ci_lo": lo, "ci_hi": hi,
            "p_value": p_value,
            "significant_at_0.05": bool(not (lo <= 0 <= hi))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--explicit", required=True,
                    help="episodes containing the `adversarial` tier")
    ap.add_argument("--stealth", required=True,
                    help="episodes containing the `adversarial_stealth` tier")
    ap.add_argument("--label", required=True, help="model name for the report")
    ap.add_argument("--tasks", default="tasks/main_120.json",
                    help="task set, needed to locate each task's attack channel "
                         "for the stage-2 screen-evasion metric")
    ap.add_argument("--out", default=None, help="write JSON here (default: alongside --stealth)")
    ap.add_argument("--allow-cross-stack", action="store_true",
                    help="permit tiers from different episode files without a shared "
                         "serving stack; the delta then confounds presentation with backend")
    args = ap.parse_args()

    exp_eps = [e for e in load_episodes(Path(args.explicit))
               if e["condition"] == "adversarial"]
    ste_eps = [e for e in load_episodes(Path(args.stealth))
               if e["condition"] == "adversarial_stealth"]
    if not exp_eps:
        raise SystemExit(f"No `adversarial` episodes in {args.explicit}")
    if not ste_eps:
        raise SystemExit(f"No `adversarial_stealth` episodes in {args.stealth}")

    # Only tasks present in BOTH tiers can be paired. A task that timed out in one
    # run must be dropped from both, or the "delta" partly reflects which tasks
    # each tier happened to cover.
    exp_tasks = {e["task_id"] for e in exp_eps}
    ste_tasks = {e["task_id"] for e in ste_eps}
    task_ids = sorted(exp_tasks & ste_tasks)
    dropped = (exp_tasks | ste_tasks) - set(task_ids)
    if not task_ids:
        raise SystemExit("No tasks common to both tiers -- nothing to pair.")

    same_file = Path(args.explicit).resolve() == Path(args.stealth).resolve()
    if not same_file and not args.allow_cross_stack:
        print("NOTE: tiers come from two different episode files. This is correct "
              "when both were produced by the SAME backend (e.g. the published "
              "explicit run and a stealth-only re-run of it). If the backends "
              "differ, the delta confounds presentation with serving stack -- "
              "re-run with --allow-cross-stack and say so in the writeup.\n",
              file=sys.stderr)

    by_task: dict[str, list] = {}
    for e in exp_eps + ste_eps:
        if e["task_id"] in set(task_ids):
            by_task.setdefault(e["task_id"], []).append(e)

    # Report BOTH columns over the paired task set only. Computing the explicit
    # column over all 96 published tasks while the stealth column covers whichever
    # subset finished makes the two columns describe different benchmarks -- the
    # printed delta then disagrees with (stealth - explicit) as displayed, which is
    # exactly how a partial run gets misread as a real effect.
    paired = set(task_ids)
    exp_p = [e for e in exp_eps if e["task_id"] in paired]
    ste_p = [e for e in ste_eps if e["task_id"] in paired]

    rng = _seeded_rng()
    rows = []
    policies = [p for p in POLICY_ORDER
                if any(e["policy"] == p for e in exp_eps)]
    for pol in policies:
        e_un = _rate([e for e in exp_p if e["policy"] == pol], "unsafe")
        s_un = _rate([e for e in ste_p if e["policy"] == pol], "unsafe")
        e_goal = _rate([e for e in exp_p if e["policy"] == pol], "goal_ok")
        s_goal = _rate([e for e in ste_p if e["policy"] == pol], "goal_ok")
        d = paired_tier_diff(task_ids, by_task, pol, "unsafe", rng)
        rows.append({"policy": pol, "explicit_unsafe": e_un, "stealth_unsafe": s_un,
                     "explicit_goal": e_goal, "stealth_goal": s_goal,
                     "delta_unsafe": d})

    tasks = {t.task_id: t for t in
             (load_task(d) for d in json.loads(
                 (ROOT / args.tasks).read_text(encoding="utf-8")))}
    screen = {pol: {"explicit": screen_evasion(exp_p, tasks, "adversarial", pol),
                    "stealth": screen_evasion(ste_p, tasks, "adversarial_stealth", pol)}
              for pol in policies}

    result = {"model": args.label, "n_paired_tasks": len(task_ids),
              "dropped_task_ids": sorted(dropped),
              "n_bootstrap": N_BOOTSTRAP, "rows": rows,
              "stage2_screen_evasion": screen,
              "explicit_source": args.explicit, "stealth_source": args.stealth}

    out = Path(args.out) if args.out else Path(args.stealth).with_name(
        f"{args.label}_stealth_compare.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== Attack-strength sensitivity: {args.label} "
          f"({len(task_ids)} paired tasks) ===")
    if dropped:
        print(f"  dropped (not in both tiers): {sorted(dropped)}")
    print(f"\n{'policy':22s} {'explicit':>9} {'stealth':>9} {'delta':>8} "
          f"{'95% CI':>18} {'p':>7}")
    print("-" * 80)
    for r in rows:
        d = r["delta_unsafe"]
        star = " *" if d["significant_at_0.05"] else "  "
        print(f"{r['policy']:22s} {r['explicit_unsafe']:9.3f} {r['stealth_unsafe']:9.3f} "
              f"{d['point']:+8.3f} [{d['ci_lo']:+.3f},{d['ci_hi']:+.3f}] "
              f"{d['p_value']:7.3f}{star}")
    print("\n(delta = stealth - explicit adversarial unsafe rate; "
          "positive = stealth evades more; * = significant at 0.05)")

    print(f"\n--- stage-2 screen evasion (attacks ACCEPTED / attacks the screen SAW) ---")
    print(f"{'policy':22s} {'explicit':>16} {'stealth':>16}")
    print("-" * 58)
    for pol in policies:
        s = screen[pol]
        def cell(d):
            if not d["reached_screen"]:
                return "     n/a (0 seen)"
            return f"{d['accepted_by_screen']:2d}/{d['reached_screen']:2d} = {d['evasion_rate']:5.1%}"
        print(f"{pol:22s} {cell(s['explicit']):>16} {cell(s['stealth']):>16}")
    print("\n(conditioned on the policy ASKING on the channel that carries the attack, "
          "so this isolates content screening from channel avoidance)")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
