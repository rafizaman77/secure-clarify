"""Information-gain and security-risk estimators (Jul 14).

These are the *learned* quantities SecureVoI needs. They are written against an
`agent` object with two methods so the real open-weight model plugs in cleanly:

    agent.sample_intents(task, k)  -> list[dict]  (k plausible intent hypotheses)
    agent.classify_malice(text)    -> float in [0,1]  (lightweight injection prob)

For the pipeline test we ship ScriptedAgent (agent.py) that implements both with
deterministic heuristics. Nothing here reads ground-truth attack labels.
"""
from __future__ import annotations

from .schema import (Task, Question, Channel, QFormat, CHANNEL_TRUST)


# --- information gain: how much would an answer change the chosen action? -------

def _canonical_action(intent: dict) -> str:
    """Collapse an intent hypothesis to the action it implies, canonicalized so
    semantically identical plans compare equal. Cheap string signature here."""
    keys = sorted(f"{k}={intent[k]}" for k in intent if not k.startswith("_"))
    return "|".join(keys)


# Some channels genuinely carry more of the answer (a shared doc/ticket may list
# every file; the user may be terse). This is what tempts a risk-blind policy onto
# an untrusted channel. Values are relative info multipliers, set on DEV data.
_CHANNEL_INFO: dict[Channel, float] = {
    Channel.USER: 0.85,
    Channel.COLLABORATOR: 0.95,
    Channel.SHARED_DOC: 1.15,
    Channel.FORWARDED: 1.05,
    Channel.EXTERNAL: 1.20,
    Channel.COMPROMISED: 1.20,
}


def estimate_info_gain(task: Task, q: Question, agent, k: int = 5,
                       channel: Channel | None = None) -> float:
    """Info gain proxy = action disagreement among sampled intents, scaled by how
    much the question q targets a disputed field, weighted by task stakes.

    A question about a field on which all sampled intents already agree has ~0 gain.
    """
    intents = agent.sample_intents(task, k)
    actions = [_canonical_action(i) for i in intents]
    if not actions:
        return 0.0
    # disagreement = 1 - (frequency of the modal action)
    modal = max(set(actions), key=actions.count)
    disagreement = 1.0 - actions.count(modal) / len(actions)

    # does q address a field that actually varies across intents?
    varying_fields = _varying_fields(intents)
    targets = any(f.lower() in q.text.lower() for f in varying_fields)
    focus = 1.0 if targets else 0.3

    stakes_w = {"low": 0.6, "medium": 1.0, "high": 1.4}[task.stakes]
    # restricted questions retrieve slightly less info than open ones
    fmt_w = 0.85 if q.qformat == QFormat.RESTRICTED else 1.0
    chan_w = _CHANNEL_INFO[channel] if channel is not None else 1.0

    # Scale to UTILITY units. Resolving the ambiguity is worth ~the goal value the
    # agent would otherwise forfeit by acting blind (RECOVERABLE_UTILITY). This
    # makes info gain commensurate with the lambda*risk*loss penalty, which is also
    # in utility units. Without this the two terms live on different scales and
    # SecureVoI degenerates to never-ask.
    RECOVERABLE_UTILITY = 1.0
    raw = disagreement * focus * fmt_w * chan_w
    # squash the disagreement proxy into a fraction of recoverable utility, then
    # let stakes scale how much that resolution is worth.
    return RECOVERABLE_UTILITY * min(1.0, raw / _INFO_NORM) * stakes_w


# empirically, the disagreement*focus proxy tops out well below 1; normalize so a
# question that clearly targets the disputed field recovers most of the utility.
_INFO_NORM = 0.12


def _varying_fields(intents: list[dict]) -> set[str]:
    fields = set()
    if not intents:
        return fields
    keys = set().union(*[set(i) for i in intents])
    for k in keys:
        if k.startswith("_"):
            continue
        vals = {str(i.get(k)) for i in intents}
        if len(vals) > 1:
            fields.add(k)
    return fields


# --- pre-inquiry channel risk: dev-set prior * expected loss --------------------

# Laplace-smoothed attack priors per (channel, format), estimated on DEV data only.
# Seeded here with plausible values; overwritten by fit_priors() during Jul 17-18.
# p_hat = (k+1)/(n+2). Restricted format lowers surface, so its prior is discounted.
_DEV_ATTACK_PRIOR: dict[Channel, float] = {
    Channel.USER: 0.00,
    Channel.COLLABORATOR: 0.18,
    Channel.SHARED_DOC: 0.25,
    Channel.FORWARDED: 0.40,
    Channel.EXTERNAL: 0.45,
    Channel.COMPROMISED: 0.85,
}


def estimate_pre_risk(channel: Channel, qformat: QFormat) -> float:
    prior = _DEV_ATTACK_PRIOR[channel]
    if qformat == QFormat.RESTRICTED:
        prior *= 0.55   # restricted answers are parsed outside the LLM -> less surface
    expected_loss = 1.0  # normalized severity; scaled by profile at eval time
    return prior * expected_loss


def fit_priors(dev_tasks, counts: dict) -> None:
    """Overwrite _DEV_ATTACK_PRIOR from observed dev-set (channel->(#attack,#total))."""
    for ch, (k, n) in counts.items():
        _DEV_ATTACK_PRIOR[ch] = (k + 1) / (n + 2)


def set_priors(priors: dict) -> None:
    """Directly overwrite _DEV_ATTACK_PRIOR, e.g. reloading a frozen dev fit
    (results/dev_calibration.json) in a fresh process rather than re-fitting."""
    _DEV_ATTACK_PRIOR.update(priors)


# --- post-response risk: cue-based malice probability ---------------------------

_CUE_TERMS = [
    "ignore", "instead", "also ", "as well", "forward to", "send to",
    "upload", "external", "credential", "password", "delete all",
    "everyone", "disregard", "urgent", "verify by", "@",
]


def response_risk(text: str, task: Task, q: Question, c: Channel, agent) -> float:
    """Combine a channel prior, format, and content cues into P(malicious).
    Uses agent.classify_malice for the learned signal; blends with structural cues.
    """
    prior = _DEV_ATTACK_PRIOR[c] * (0.55 if q.qformat == QFormat.RESTRICTED else 1.0)
    learned = agent.classify_malice(text)
    lower = text.lower()
    cue_hits = sum(term in lower for term in _CUE_TERMS)
    cue_signal = min(1.0, cue_hits / 4.0)
    # a response that goes outside a restricted schema is itself suspicious
    off_schema = 0.0
    if q.qformat == QFormat.RESTRICTED and q.choices:
        if not any(ch.lower() in lower for ch in q.choices):
            off_schema = 0.3
    # weighted blend, clipped
    r = 0.35 * prior + 0.4 * learned + 0.2 * cue_signal + off_schema
    return max(0.0, min(1.0, r))
