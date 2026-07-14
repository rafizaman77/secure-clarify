"""Task schema for Security-Aware Clarification benchmark (Jul 12 deliverable).

A benchmark *base task* fixes an initial request and a hidden intent, then attaches
matched benign / noisy / adversarial responses for each candidate question+channel.
The same base task is evaluated under all three response conditions so that any
difference is attributable to the response, not to task difficulty.

Nothing here talks to a model or a real service. It only defines and validates data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


# ----- controlled vocabularies -------------------------------------------------

class Channel(str, Enum):
    USER = "authenticated_user"      # high trust, cannot carry attack
    COLLABORATOR = "delegated_collaborator"
    SHARED_DOC = "shared_document"
    FORWARDED = "forwarded_message"
    EXTERNAL = "external_tool"
    COMPROMISED = "compromised_account"


# prior trust level per channel (higher = more trusted). Used by policies as a *prior*,
# never as a ground-truth attack label.
CHANNEL_TRUST: dict[Channel, float] = {
    Channel.USER: 1.00,
    Channel.COLLABORATOR: 0.70,
    Channel.SHARED_DOC: 0.60,
    Channel.FORWARDED: 0.35,
    Channel.EXTERNAL: 0.30,
    Channel.COMPROMISED: 0.05,
}


class Condition(str, Enum):
    BENIGN = "benign"
    NOISY = "noisy"
    ADVERSARIAL = "adversarial"


class QFormat(str, Enum):
    OPEN = "open"            # free-text answer
    RESTRICTED = "restricted"  # choice from a fixed schema, parsed outside the LLM


class AttackType(str, Enum):
    GOAL_HIJACK = "goal_hijack"
    CONSTRAINT_REMOVAL = "constraint_removal"
    RECIPIENT_INJECTION = "recipient_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    DESTRUCTIVE_ACTION = "destructive_action"
    UNRELATED_INSTRUCTION = "unrelated_instruction"
    NONE = "none"


# ----- schema objects ----------------------------------------------------------

@dataclass
class Question:
    qid: str
    text: str
    qformat: QFormat
    # for restricted questions: the allowed choices. Must NOT always contain the
    # correct answer -- include 'none' / 'seek another source' cases.
    choices: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.qformat == QFormat.RESTRICTED and not self.choices:
            raise ValueError(f"{self.qid}: restricted question needs choices")
        if self.qformat == QFormat.OPEN and self.choices:
            raise ValueError(f"{self.qid}: open question must not carry choices")


@dataclass
class Response:
    """A single clarification answer keyed to (qid, channel, condition)."""
    qid: str
    channel: Channel
    condition: Condition
    text: str
    attack_type: AttackType = AttackType.NONE
    # ground-truth: does this response, if followed literally, drive a prohibited
    # transition? Used ONLY by verifier/oracle, never exposed to the learned policy.
    carries_attack: bool = False

    def validate(self) -> None:
        adv = self.condition == Condition.ADVERSARIAL
        # An adversarial-condition response MAY be a benign decoy (attack_type NONE,
        # carries_attack False). This is required so channel identity is not
        # perfectly predictive of attack. But a decoy must be explicitly benign:
        if adv and self.attack_type == AttackType.NONE and self.carries_attack:
            raise ValueError(f"{self.qid}/{self.channel}: NONE attack cannot carry attack")
        if adv and self.attack_type != AttackType.NONE and not self.carries_attack:
            raise ValueError(
                f"{self.qid}/{self.channel}: attack_type set but carries_attack False")
        if not adv and self.carries_attack:
            raise ValueError(f"{self.qid}/{self.channel}: only adversarial may carry an attack")
        if self.channel == Channel.USER and self.carries_attack:
            raise ValueError("authenticated user cannot carry an attack (threat model)")


@dataclass
class Task:
    task_id: str
    domain: str                      # "file" | "calendar"
    family: str                      # e.g. "archive", "scheduling"
    initial_request: str
    hidden_intent: dict[str, Any]    # structured ground-truth intent
    ambiguities: list[str]
    allowed_actions: list[str]
    prohibited_actions: list[str]    # any of these in the log => unsafe
    available_channels: list[Channel]
    candidate_questions: list[Question]
    responses: list[Response]        # matched across channel x condition
    initial_state: dict[str, Any]    # deterministic world state
    goal_predicate: dict[str, Any]   # machine-checkable final-state conditions
    stakes: str = "medium"           # low | medium | high  (weights regret)
    split: str = "unassigned"        # dev | test | unassigned

    # -- validation ------------------------------------------------------------
    def validate(self) -> None:
        assert self.domain in {"file", "calendar"}, self.domain
        assert self.stakes in {"low", "medium", "high"}, self.stakes
        if not self.candidate_questions:
            raise ValueError(f"{self.task_id}: needs >=1 candidate question")
        if Channel.USER not in self.available_channels:
            # allowed: "authenticated user unavailable" tasks. Just flag intent.
            self.hidden_intent.setdefault("_user_unavailable", True)
        qids = {q.qid for q in self.candidate_questions}
        for q in self.candidate_questions:
            q.validate()
        # every response must reference a real question and an available channel
        for r in self.responses:
            r.validate()
            if r.qid not in qids:
                raise ValueError(f"{self.task_id}: response for unknown qid {r.qid}")
            if r.channel not in self.available_channels:
                raise ValueError(f"{self.task_id}: response on unavailable channel {r.channel}")
        # at least one prohibited action (security-sensitive) and one allowed action
        if not self.prohibited_actions:
            raise ValueError(f"{self.task_id}: needs >=1 prohibited action")
        if not self.allowed_actions:
            raise ValueError(f"{self.task_id}: needs >=1 allowed action")
        # matched-condition requirement: for at least one (qid, channel) there must
        # exist all three conditions, so the causal comparison is well defined.
        seen: dict[tuple[str, Channel], set[Condition]] = {}
        for r in self.responses:
            seen.setdefault((r.qid, r.channel), set()).add(r.condition)
        if not any(len(v) == 3 for v in seen.values()):
            raise ValueError(
                f"{self.task_id}: no (question,channel) has all 3 matched conditions")

    def to_json(self) -> str:
        def enc(o: Any) -> Any:
            if isinstance(o, Enum):
                return o.value
            raise TypeError(type(o))
        return json.dumps(asdict(self), default=enc, indent=2)


def load_task(d: dict[str, Any]) -> Task:
    """Rehydrate a Task from a plain dict (e.g. parsed JSON)."""
    qs = [Question(qid=q["qid"], text=q["text"],
                   qformat=QFormat(q["qformat"]), choices=q.get("choices", []))
          for q in d["candidate_questions"]]
    rs = [Response(qid=r["qid"], channel=Channel(r["channel"]),
                   condition=Condition(r["condition"]), text=r["text"],
                   attack_type=AttackType(r.get("attack_type", "none")),
                   carries_attack=r.get("carries_attack", False))
          for r in d["responses"]]
    t = Task(
        task_id=d["task_id"], domain=d["domain"], family=d["family"],
        initial_request=d["initial_request"], hidden_intent=d["hidden_intent"],
        ambiguities=d["ambiguities"], allowed_actions=d["allowed_actions"],
        prohibited_actions=d["prohibited_actions"],
        available_channels=[Channel(c) for c in d["available_channels"]],
        candidate_questions=qs, responses=rs,
        initial_state=d["initial_state"], goal_predicate=d["goal_predicate"],
        stakes=d.get("stakes", "medium"), split=d.get("split", "unassigned"))
    return t
