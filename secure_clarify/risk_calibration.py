"""Step 26's fix: make `response_risk` an actual probability.

WHY. `response_risk` is documented as P(malicious) and is used as one: stage 2's
rule `info_value > lambda * risk * expected_loss` is an expected-loss comparison.
Measurement (scripts/risk_calibration.py) shows the score discriminates well
(AUROC 0.89-0.92) but is **not** calibrated, and is wrong in opposite directions
on different models -- Mistral under-predicts at the top (everything >=0.4 is an
attack, scored 0.41-0.73), gpt-oss-20b over-predicts in the middle (539 responses
scored ~0.55 whose actual attack rate is 0.143).

Two consequences the paper cannot claim its way out of:
  * `lambda` is not a loss ratio. Its fitted value has no units, so the
    "principled decision-theoretic screen" is a tuned threshold.
  * `lambda` has to be refitted per model, because the miscalibration differs per
    model -- not because risk appetite differs.

THE FIX. Fit a one-dimensional Platt map on the **dev split only**

    p_calibrated = sigmoid(a * logit(raw) + b)

and apply it to the raw score. Platt rather than isotonic deliberately: with a
few hundred dev responses isotonic would overfit the bin edges, while Platt has
two parameters and degrades gracefully. Fitting on dev and reporting on test
keeps the calibration honest.

OPT-IN, like `set_risk_components`: `response_risk` is untouched unless a map is
installed, so no frozen result can move by accident.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

_EPS = 1e-6


def _logit(p: float) -> float:
    p = min(1.0 - _EPS, max(_EPS, p))
    return math.log(p / (1.0 - p))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


class PlattCalibrator:
    """Two-parameter logistic recalibration, fitted by gradient descent.

    No scipy: the objective is convex in (a, b), so plain gradient descent with a
    fixed step reaches the optimum reliably at this size. Deterministic, so a
    reported calibration map is reproducible.
    """

    def __init__(self, a: float = 1.0, b: float = 0.0):
        self.a = a
        self.b = b

    def fit(self, scores, labels, lr: float = 0.5, iters: int = 4000):
        xs = [_logit(s) for s in scores]
        ys = [float(y) for y in labels]
        n = len(xs)
        if n == 0:
            return self
        # Platt's prior correction: shrink targets away from 0/1 so a separable
        # dev set cannot drive the weights to infinity.
        n_pos = sum(ys)
        n_neg = n - n_pos
        hi = (n_pos + 1.0) / (n_pos + 2.0) if n_pos else 0.5
        lo = 1.0 / (n_neg + 2.0) if n_neg else 0.5
        ts = [hi if y > 0.5 else lo for y in ys]

        a, b = self.a, self.b
        for _ in range(iters):
            ga = gb = 0.0
            for x, t in zip(xs, ts):
                p = _sigmoid(a * x + b)
                d = p - t
                ga += d * x
                gb += d
            a -= lr * ga / n
            b -= lr * gb / n
        self.a, self.b = a, b
        return self

    def __call__(self, raw: float) -> float:
        return _sigmoid(self.a * _logit(raw) + self.b)

    def to_dict(self) -> dict:
        return {"kind": "platt", "a": self.a, "b": self.b}

    @classmethod
    def from_dict(cls, d: dict) -> "PlattCalibrator":
        return cls(a=float(d["a"]), b=float(d["b"]))

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n",
                              encoding="utf-8")

    @classmethod
    def load(cls, path) -> "PlattCalibrator":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def negative_log_loss(scores, labels) -> float:
    """Proper scoring rule; lower is better. Reported alongside Brier because it
    punishes confident mistakes much harder, which is the failure mode here."""
    tot = 0.0
    for s, y in zip(scores, labels):
        p = min(1.0 - _EPS, max(_EPS, s))
        tot -= (y * math.log(p) + (1 - y) * math.log(1 - p))
    return tot / len(scores) if scores else float("nan")


def expected_calibration_error(scores, labels, n_bins: int = 10) -> float:
    """Mean |predicted - observed| weighted by bin occupancy."""
    if not scores:
        return float("nan")
    bins = {}
    for s, y in zip(scores, labels):
        bins.setdefault(min(n_bins - 1, int(s * n_bins)), []).append((s, y))
    n = len(scores)
    return sum(len(v) * abs(sum(s for s, _ in v) / len(v)
                            - sum(y for _, y in v) / len(v))
               for v in bins.values()) / n
