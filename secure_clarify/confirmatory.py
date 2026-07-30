"""Steps 20-23 of RESEARCH_PLAN.md: the statistics HYPOTHESES.md commits to.

Four things the current analysis does not do, each of which can turn a real
result into an overstated one:

  20. CORRECT INDEPENDENT UNIT. Episodes within a task share a request, a channel
      set and an attack, and tasks within a family share a template. Resampling
      episodes independently treats correlated observations as independent and
      understates the standard error. `hierarchical_bootstrap` resamples
      family -> task -> episode, so the CI reflects the level the claim
      generalizes to.

  21. MULTIPLE COMPARISONS. Four confirmatory hypotheses x several models is
      enough for one to reach p<0.05 by chance. `holm` reports corrected
      alongside uncorrected, never instead of it.

  22. EQUIVALENCE. "Matches baseline utility" is not supported by failing to
      reject a difference -- that is absence of evidence. `tost` requires the
      90% CI of the difference to sit inside a PRE-DECLARED margin (HYPOTHESES.md
      fixes these at 0.05).

  23. ZERO RATES. "0 unsafe actions" is not "eliminates attacks": 0/96 is
      consistent with a true rate up to ~3.8%. `wilson_interval` gives the bound,
      and `format_rate` renders it with its denominator so the claim cannot be
      read as certainty.

Pure functions over plain lists -- no numpy, matching the repo's dependency-free
style, and deterministic given a seed so every reported number is reproducible.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict


# ---------------------------------------------------------------------------
# Step 23: uncertainty for rates, including zero
# ---------------------------------------------------------------------------
def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Unlike normal-approximation it stays inside [0,1]
    and remains meaningful at 0 or n successes, which is exactly the case the
    paper reports ("0.000 unsafe")."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def format_rate(successes: int, n: int) -> str:
    """A rate that cannot be misread as certainty."""
    lo, hi = wilson_interval(successes, n)
    if successes == 0:
        return (f"no events observed in {n} episodes "
                f"(95% CI [0.000, {hi:.3f}])")
    return f"{successes}/{n} = {successes / n:.3f} (95% CI [{lo:.3f}, {hi:.3f}])"


# ---------------------------------------------------------------------------
# Step 20: hierarchical / cluster resampling
# ---------------------------------------------------------------------------
def hierarchical_bootstrap(units: dict[str, dict[str, list[float]]],
                           n_boot: int = 2000, seed: int = 20260730,
                           statistic=None) -> dict:
    """Resample family -> task -> observation, preserving the nesting.

    `units` maps family -> task_id -> list of per-episode values (0/1 for a
    rate, float for utility). Each bootstrap replicate draws families with
    replacement, then tasks within each drawn family, then observations within
    each drawn task -- so a replicate can lose an entire family, which is what
    makes the interval generalize to *new families* rather than to new episodes
    of the same three templates.
    """
    rng = random.Random(seed)
    stat = statistic or (lambda xs: sum(xs) / len(xs) if xs else float("nan"))
    fams = sorted(units)
    if not fams:
        return {"point": float("nan"), "ci_lo": float("nan"),
                "ci_hi": float("nan"), "n_families": 0, "n_tasks": 0}

    flat = [v for f in fams for t in units[f] for v in units[f][t]]
    point = stat(flat)

    reps = []
    for _ in range(n_boot):
        vals = []
        for _ in fams:
            f = rng.choice(fams)
            tids = sorted(units[f])
            if not tids:
                continue
            for _ in tids:
                t = rng.choice(tids)
                obs = units[f][t]
                if not obs:
                    continue
                vals.extend(rng.choice(obs) for _ in obs)
        if vals:
            reps.append(stat(vals))
    reps.sort()
    lo = reps[int(0.025 * len(reps))] if reps else float("nan")
    hi = reps[int(0.975 * len(reps))] if reps else float("nan")
    return {"point": point, "ci_lo": lo, "ci_hi": hi,
            "n_families": len(fams),
            "n_tasks": sum(len(units[f]) for f in fams),
            "n_obs": len(flat), "n_boot": len(reps)}


def paired_hierarchical_diff(units_a: dict, units_b: dict, n_boot: int = 2000,
                             seed: int = 20260730) -> dict:
    """Paired A-B difference resampled at family -> task level.

    Pairing is preserved: a replicate that draws task T takes A(T) and B(T)
    together, so the difference is not contaminated by which tasks each arm
    happened to receive.
    """
    rng = random.Random(seed)
    fams = sorted(set(units_a) & set(units_b))
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0

    def diff_over(pairs):
        a = [v for (av, _) in pairs for v in av]
        b = [v for (_, bv) in pairs for v in bv]
        return mean(a) - mean(b)

    all_pairs = [(units_a[f][t], units_b[f][t])
                 for f in fams for t in sorted(set(units_a[f]) & set(units_b[f]))]
    if not all_pairs:
        return {"point": float("nan"), "ci_lo": float("nan"),
                "ci_hi": float("nan"), "p_value": float("nan")}
    point = diff_over(all_pairs)

    reps = []
    for _ in range(n_boot):
        pairs = []
        for _ in fams:
            f = rng.choice(fams)
            tids = sorted(set(units_a[f]) & set(units_b[f]))
            for _ in tids:
                t = rng.choice(tids)
                pairs.append((units_a[f][t], units_b[f][t]))
        if pairs:
            reps.append(diff_over(pairs))
    reps.sort()
    lo = reps[int(0.025 * len(reps))]
    hi = reps[int(0.975 * len(reps))]
    # two-sided bootstrap p: how often the replicate crosses zero
    n_le = sum(1 for r in reps if r <= 0)
    n_ge = sum(1 for r in reps if r >= 0)
    p = min(1.0, 2.0 * min(n_le, n_ge) / len(reps))
    return {"point": point, "ci_lo": lo, "ci_hi": hi, "p_value": p,
            "n_families": len(fams), "n_pairs": len(all_pairs), "n_boot": len(reps)}


# ---------------------------------------------------------------------------
# Step 21: multiple-comparison correction
# ---------------------------------------------------------------------------
def holm(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm-Bonferroni. Uniformly more powerful than Bonferroni and needs no
    independence assumption, which matters because the confirmatory hypotheses
    are computed on overlapping episodes."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj                      # enforce monotonicity
        out[name] = {"p_raw": p, "p_holm": adj, "reject_at_alpha": adj <= alpha}
    return out


# ---------------------------------------------------------------------------
# Step 22: equivalence testing
# ---------------------------------------------------------------------------
def tost(diff_point: float, ci90_lo: float, ci90_hi: float,
         margin: float) -> dict:
    """Two one-sided tests via the 90% CI.

    Equivalence is claimed only if the whole 90% interval lies inside +/-margin.
    A wide interval means UNDERPOWERED, never "equivalent" -- reported
    explicitly so the distinction cannot be glossed.
    """
    equivalent = (ci90_lo > -margin) and (ci90_hi < margin)
    width = ci90_hi - ci90_lo
    return {"diff": diff_point, "ci90": [ci90_lo, ci90_hi], "margin": margin,
            "equivalent": equivalent,
            "verdict": ("equivalent within +/-%.3f" % margin) if equivalent
                       else ("NOT equivalent (CI exceeds margin)"
                             if abs(diff_point) > margin
                             else "inconclusive / underpowered "
                                  "(CI wider than the margin)"),
            "ci_width": width}


def group_by_family_task(episodes, value_fn, family_fn=None) -> dict:
    """Shape episodes into the family -> task -> [values] form the bootstraps take."""
    fam = family_fn or (lambda e: (e.get("domain") if isinstance(e, dict)
                                   else getattr(e, "domain", "?")) or "?")
    out = defaultdict(lambda: defaultdict(list))
    for e in episodes:
        tid = e["task_id"] if isinstance(e, dict) else e.task_id
        out[fam(e)][tid].append(float(value_fn(e)))
    return {f: dict(t) for f, t in out.items()}
