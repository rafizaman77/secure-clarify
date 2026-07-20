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
from .estimators import (estimate_info_gain, estimate_pre_risk, response_risk,
                         _canonical_action)


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


class AlwaysAsk:
    """Plan section 10: 'Query the nominally most informative available
    source.' Always asks -- ignores interaction cost and channel risk
    entirely when picking (question, channel), and accepts whatever comes
    back (no stage-2 gate). The opposite extreme from NeverAsk; contrasts
    with ConventionalVoI, which is cost-aware but still risk-blind."""
    name = "always_ask"

    def decide(self, task: Task, agent) -> Decision:
        cands = _available_qc(task)
        if not cands:
            return Decision(ask=False, rationale="no candidate question/channel available")
        best, best_val = cands[0], -1.0
        for q, c in cands:
            ig = estimate_info_gain(task, q, agent, channel=c)
            if ig > best_val:
                best, best_val = (q, c), ig
        q, c = best
        return Decision(ask=True, question=q, channel=c, accept_response=True,
                        rationale=f"always-ask: highest nominal info gain={best_val:.3f} (cost/risk ignored)")


class ConfidenceThreshold:
    """Plan section 10: 'Ask when sampled action agreement falls below dev
    threshold.' Confidence here is the agent's OWN agreement across sampled
    intents (1 - the same disagreement proxy estimate_info_gain uses), not a
    VoI or risk computation. Below the dev-calibrated threshold it asks the
    (question, channel) with highest nominal info gain -- like AlwaysAsk,
    with no channel-risk term -- and accepts whatever comes back; at or above
    threshold it acts on the single best guess without asking.

    `threshold` must be set on the dev split (see scripts/tune_dev.py's
    confidence-threshold calibration), exactly like SecureVoI's lambda --
    never fit on test."""
    name = "confidence_threshold"

    def __init__(self, threshold: float = 0.5, k: int = 5):
        self.threshold = threshold
        self.k = k

    def _agreement(self, task: Task, agent) -> float:
        intents = agent.sample_intents(task, self.k)
        actions = [_canonical_action(i) for i in intents]
        if not actions:
            return 1.0
        modal = max(set(actions), key=actions.count)
        return actions.count(modal) / len(actions)

    def decide(self, task: Task, agent) -> Decision:
        agreement = self._agreement(task, agent)
        if agreement >= self.threshold:
            return Decision(ask=False,
                            rationale=f"confident (agreement={agreement:.2f} >= {self.threshold})")
        cands = _available_qc(task)
        if not cands:
            return Decision(ask=False, rationale="low confidence but no channel available")
        best, best_val = cands[0], -1.0
        for q, c in cands:
            ig = estimate_info_gain(task, q, agent, channel=c)
            if ig > best_val:
                best, best_val = (q, c), ig
        q, c = best
        return Decision(
            ask=True, question=q, channel=c, accept_response=True,
            rationale=f"low confidence (agreement={agreement:.2f} < {self.threshold}), "
                     f"asking highest-IG source")


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


class ChannelHeuristic:
    """Trivial channel-avoidance baseline (Jul 20, for the channel-mix benchmark).
    Asks like ConventionalVoI but, in place of any risk model, simply routes the
    question to the HIGHEST-TRUST available channel and accepts whatever comes back
    -- no pre-inquiry risk term, no stage-2 screening, no model of the content.

    Its whole point is to expose a benchmark-validity failure: on a task set where
    the attack always sits on the lowest-trust channel, this dodges EVERY attack for
    free -- it never even reads the attacked channel -- scoring ~0% unsafe with zero
    security machinery. That is exactly the degeneracy docs/02_threat_model.md
    forbids ("channel identity must not be perfectly predictive of attack"), and the
    reason SecureVoI's 0% on such a set is not meaningful. On the channel-mixed
    benchmark (task_factory._pick_adv_channel spreads attacks across channels with
    graded probability) higher-trust channels also carry attacks a fraction of the
    time, so this baseline takes real hits and SecureVoI's advantage must come from
    screening the content, not from avoiding a channel.

    Deliberately NOT in MAIN_POLICIES (the six-policy main set stays fixed for
    reproducibility): it's a validity probe, reported alongside as the bar SecureVoI
    must clear on the fixed benchmark. Include it via run_primary --policies mainplus."""
    name = "channel_heuristic"

    def decide(self, task: Task, agent) -> Decision:
        cands = _available_qc(task)
        if not cands:
            return Decision(ask=False, rationale="no candidate question/channel available")
        # Highest channel trust wins; tie-break by info gain minus interaction cost.
        best, best_key = None, None
        for q, c in cands:
            ig = estimate_info_gain(task, q, agent, channel=c)
            key = (CHANNEL_TRUST[c], ig - C_COST[q.qformat])
            if best_key is None or key > best_key:
                best, best_key = (q, c), key
        q, c = best
        return Decision(ask=True, question=q, channel=c, accept_response=True,
                        rationale=f"route to highest-trust channel={c.value} "
                                 f"(trust={CHANNEL_TRUST[c]:.2f}); risk-blind, no screening")


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


class SecureVoIOracle(SecureVoI):
    """Ablation (Jul 22-23): identical to SecureVoI except stage-2 acceptance
    uses the GROUND-TRUTH carries_attack label instead of
    agent.classify_malice's learned signal -- an oracle upper bound on how
    much of SecureVoI's benefit is attributable to the acquisition-decision
    formula itself (stage 1: ig - cost - lambda*pre_risk) versus the
    imperfect learned malice classifier (stage 2). The gap between SecureVoI
    and SecureVoIOracle is what a better classify_malice could still buy.

    Implementation note: accept()'s signature (task, q, c, response_text,
    agent) does not carry the matching Response object or condition, and
    changing that signature would touch runner.py's call site. Instead this
    looks up the ground-truth Response by matching (qid, channel, text)
    against task.responses -- text should uniquely identify the matched
    response among the task's benign/noisy/adversarial variants in practice.
    Never used by any non-ablation policy; SecureVoI itself is untouched."""
    name = "secure_voi_oracle"

    def _oracle_carries_attack(self, task: Task, q: Question, c: Channel,
                               response_text: str) -> bool:
        for r in task.responses:
            if r.qid == q.qid and r.channel == c and r.text == response_text:
                return r.carries_attack
        return False  # no match found: treat as benign (fail toward NOT gating)

    def accept(self, task: Task, q: Question, c: Channel, response_text: str,
               agent) -> bool:
        """Stage 2, oracle version: accept iff the info value clears
        lambda*loss when the response is NOT a ground-truth attack; a
        ground-truth attack is always rejected (r=1.0), matching the
        semantics of a perfect classify_malice (P(malicious)=1 for actual
        attacks, 0 otherwise) fed through the same accept-rule shape as
        SecureVoI.accept."""
        r = 1.0 if self._oracle_carries_attack(task, q, c, response_text) else 0.0
        info_value = estimate_info_gain(task, q, agent, channel=c)
        expected_loss = 1.0
        return info_value > self.lam * r * expected_loss


PILOT_POLICIES = [NeverAsk, ConventionalVoI, TrustedOnly, SecureVoI]

# Plan section 10's full six-policy main-experiment set (Jul 22-23). Post-hoc
# guardrail is explicitly marked "Optional" in the plan and is scope-cut #2 if
# behind schedule -- it is deliberately NOT in this list.
MAIN_POLICIES = [NeverAsk, AlwaysAsk, ConfidenceThreshold, ConventionalVoI,
                 TrustedOnly, SecureVoI]

# Validity probe, reported alongside the main set (NOT part of it): the trivial
# channel-avoidance bar SecureVoI must clear on the channel-mixed benchmark.
# run_primary --policies mainplus == MAIN_POLICIES + this.
MAINPLUS_POLICIES = MAIN_POLICIES + [ChannelHeuristic]
