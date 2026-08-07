"""Step 12 of RESEARCH_PLAN.md: does stage 1 survive an attacker who ignores the
placement rule its priors were fit to?

THE THREAT. `_pick_adv_channel` places attacks with weight $\\propto (1-\\mathrm{trust})$.
`fit_priors` then estimates the channel prior from dev-split `carries_attack`
labels produced by *that same rule*. So stage 1 is handed a fitted estimate of the
attacker's own placement distribution, and the fitted priors track it closely:

    channel        trust   1-trust   fitted prior
    collaborator   0.70    0.30      0.35
    shared_doc     0.60    0.40      0.55
    external       0.30    0.70      0.65
    compromised    0.05    0.95      0.85

Stage 1's advantage may therefore be an artifact of knowing the generative
process, not a property of risk-aware acquisition. This is the deepest threat to
the one claim that survived every other test (H2 at the family level, 3/3 models).

THE TEST. Rebuild the task set with attack placement changed, and **do not
refit**: the policy keeps its dev-fitted priors, which are now misspecified. If
the stage-1 effect survives, the claim is much stronger than currently stated. If
it collapses, stage 1 was reading the generator.

Three placement regimes:

    matched    the shipped rule, weight (1 - trust)      -- priors correct
    uniform    every non-user channel equally likely     -- priors uninformative
    inverted   weight proportional to trust              -- priors ANTI-correlated
               (attacks concentrate on channels stage 1 believes are safe)

`inverted` is the adversarial case: an attacker who has read the defense and
places attacks exactly where it is least expecting them. `uniform` is the neutral
case: an attacker with no channel preference at all.

ADDITIVE. New module; the frozen generators and task files are untouched. The
placement override is injected by monkeypatching `_pick_adv_channel` for the
duration of the build, so the rest of the task construction is byte-identical to
the shipped path and only the attacked channel moves.
"""
from __future__ import annotations

import contextlib

from . import task_factory as TF
from .schema import Channel, Task

REGIMES = ("matched", "uniform", "inverted")


def _weights(regime: str, channels: list[Channel]) -> list[float]:
    if regime == "matched":
        return [max(1e-6, 1.0 - TF._trust(c)) for c in channels]
    if regime == "uniform":
        return [1.0 for _ in channels]
    if regime == "inverted":
        return [max(1e-6, TF._trust(c)) for c in channels]
    raise ValueError(f"unknown regime {regime!r}")


def _make_picker(regime: str):
    """A `_pick_adv_channel` with the same deterministic hash, different weights.

    Keeping Knuth's multiplicative hash means task *i* draws the same fraction in
    every regime, so a task whose attack moves does so because the weights moved
    -- not because the sampling stream shifted underneath it.
    """
    def pick(non_user, idx):
        if not non_user:
            return None
        by_trust = sorted(non_user, key=TF._trust)
        w = _weights(regime, by_trust)
        total = sum(w)
        frac = ((idx * 2654435761) % 2 ** 20) / float(2 ** 20)
        cum = 0.0
        for c, wi in zip(by_trust, w):
            cum += wi / total
            if frac < cum:
                return c
        return by_trust[-1]
    return pick


@contextlib.contextmanager
def placement(regime: str):
    """Temporarily swap the attack-placement rule."""
    orig = TF._pick_adv_channel
    TF._pick_adv_channel = _make_picker(regime)
    try:
        yield
    finally:
        TF._pick_adv_channel = orig


def build_shifted(regime: str, builder=None, **kwargs) -> list[Task]:
    """Build a task set under `regime`. Defaults to the 5 Step-6 families."""
    if builder is None:
        from .task_families import build_family_set
        builder = build_family_set
    with placement(regime):
        return builder(**kwargs)


def attack_rates(tasks: list[Task]) -> dict[str, float]:
    """Realized P(attacked) per channel -- what the priors *should* have been."""
    from collections import defaultdict
    seen = defaultdict(lambda: [0, 0])
    for t in tasks:
        for r in t.responses:
            if r.channel is Channel.USER:
                continue
            if r.condition.value != "adversarial":
                continue
            s = seen[r.channel.value]
            s[0] += 1
            s[1] += bool(r.carries_attack)
    return {c: round(v[1] / v[0], 4) for c, v in sorted(seen.items()) if v[0]}
