"""The four pilot policies (Jul 14 deliverable).

Each policy is a decision rule over: whether to ask, which question format, which
channel, and whether to accept the returned answer. They share the SAME agent
backend, environment, tools, and parser -- only the decision logic differs.

The pilot set from the plan is exactly these four:
  Never Ask, Conventional VoI, Trusted-Only, SecureVoI.

Information gain and risk here use the *estimators* in estimators.py so that the
learned method is honest (no oracle labels). An oracle variant is available for the
frontier/debug but is not a policy the agent runs blind.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schema import (Task, Question, Channel, Condition, QFormat,
                     CHANNEL_TRUST)
from .estimators import estimate_info_gain, estimate_pre_risk, response_risk


@dataclass
class Decision:
    ask: bool
    question: Optional[Question] = None
    channel: Optional[Channel] = None
    accept_response: bool = True     # stage-2 gate (only meaningful if ask)
    rationale: str = ""


# interaction cost per format (restricted is cheaper to the user and lower surface)
C_COST = {QFormat.OPEN: 0.10, QFormat.RESTRICTED: 0.05}


def _available_qc(task: Task) -> list[tuple[Question, Channel]]:
    return [(q, c) for q in task.candidate_questions
            for c in task.available_channels]


class NeverAsk:
    name = "never_ask"

    def decide(self, task: Task, agent) -> Decision:
        return Decision(ask=False, rationale="acts from initial request")


class ConventionalVoI:
    """Maximize information gain minus interaction cost. Ignores channel risk and
    accepts whatever comes back (no stage-2 gate). This is the policy ASPI predicts
    will be dangerous under attack."""
    name = "conventional_voi"

    def decide(self, task: Task, agent) -> Decision:
        best, best_val = None, 0.0
        for q, c in _available_qc(task):
            ig = estimate_info_gain(task, q, agent, channel=c)
            val = ig - C_COST[q.qformat]
            if val > best_val:
                best, best_val = (q, c), val
        if best is None:
            return Decision(ask=False, rationale="no positive-VoI question")
        q, c = best
        return Decision(ask=True, question=q, channel=c, accept_response=True,
                        rationale=f"VoI={best_val:.3f} (risk-blind)")


class TrustedOnly:
    """Ask only through high-trust channels; otherwise act/abstain. Safe but leaves
    information on the table when only partially-trusted sources exist."""
    name = "trusted_only"
    TRUST_FLOOR = 0.65

    def decide(self, task: Task, agent) -> Decision:
        cands = [(q, c) for q, c in _available_qc(task)
                 if CHANNEL_TRUST[c] >= self.TRUST_FLOOR]
        if not cands:
            return Decision(ask=False, rationale="no trusted channel available")
        best, best_val = None, 0.0
        for q, c in cands:
            val = estimate_info_gain(task, q, agent, channel=c) - C_COST[q.qformat]
            if val > best_val:
                best, best_val = (q, c), val
        if best is None:
            return Decision(ask=False, rationale="no positive-VoI trusted question")
        q, c = best
        return Decision(ask=True, question=q, channel=c, accept_response=True,
                        rationale=f"trusted VoI={best_val:.3f}")


class SecureVoI:
    """Two-stage. Stage 1 selects (q,h) by info gain minus interaction cost minus
    lambda * pre-inquiry attack exposure. Stage 2 gates the returned answer by its
    estimated malice. Prefers restricted format when it preserves enough info."""
    name = "secure_voi"

    def __init__(self, lam: float = 1.0):
        self.lam = lam

    def decide(self, task: Task, agent) -> Decision:
        best, best_val = None, 0.0
        for q, c in _available_qc(task):
            ig = estimate_info_gain(task, q, agent, channel=c)
            pre_risk = estimate_pre_risk(c, q.qformat)   # dev-set prior * expected loss
            sv = ig - C_COST[q.qformat] - self.lam * pre_risk
            if sv > best_val:
                best, best_val = (q, c), sv
        if best is None:
            return Decision(ask=False,
                            rationale="no (q,h) with positive SecureVoI -> act/abstain")
        q, c = best
        return Decision(ask=True, question=q, channel=c, accept_response=True,
                        rationale=f"SV={best_val:.3f} lam={self.lam}")

    def accept(self, task: Task, q: Question, c: Channel, response_text: str,
               agent) -> bool:
        """Stage 2: accept iff estimated info value of y exceeds lambda*risk*loss."""
        r = response_risk(response_text, task, q, c, agent)  # P(malicious | cues)
        info_value = estimate_info_gain(task, q, agent, channel=c)
        expected_loss = 1.0  # normalized; refined by severity profile at eval time
        return info_value > self.lam * r * expected_loss


PILOT_POLICIES = [NeverAsk, ConventionalVoI, TrustedOnly, SecureVoI]
