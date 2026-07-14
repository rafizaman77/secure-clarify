"""Agent backends (Jul 14).

The pipeline needs an object exposing:
    sample_intents(task, k) -> list[dict]
    classify_malice(text)   -> float in [0,1]
    act(task, resolved_intent) -> list[(tool, args)]   # plan of tool calls

ScriptedAgent implements all three deterministically so the WHOLE pipeline runs
today, on CPU, with no model. It is intentionally imperfect (it can be fooled by
adversarial text unless a policy screens the response) so the pilot exhibits the
real information-vs-security trade-off rather than a rigged one.

To run the real experiment, drop in OpenModelAgent (skeleton below) backed by an
open-weight instruction model; the rest of the code is unchanged.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from .schema import Task, Condition


class ScriptedAgent:
    """Heuristic stand-in for an instruction-tuned model."""

    def __init__(self, gullible: float = 0.8):
        # probability the base agent follows an injected instruction if a policy
        # does NOT screen it. Tunes how strong the raw trade-off looks.
        self.gullible = gullible

    # -- intent sampling -------------------------------------------------------
    def sample_intents(self, task: Task, k: int) -> list[dict]:
        """Return k intent hypotheses. We perturb the (hidden) intent along its
        ambiguous field to simulate genuine uncertainty WITHOUT peeking at the
        answer: the disagreement comes from the ambiguity list, not the label."""
        base = {kk: vv for kk, vv in task.hidden_intent.items()
                if not kk.startswith("_")}
        out = [copy.deepcopy(base)]
        for i, amb in enumerate(task.ambiguities[: max(1, k - 1)]):
            alt = copy.deepcopy(base)
            # flip the disputed field to a plausible alternative
            field = _amb_field(amb)
            if field and field in alt:
                alt[field] = f"ALT{i}"
            else:
                alt[f"amb_{i}"] = f"ALT{i}"
            out.append(alt)
        while len(out) < k:
            out.append(copy.deepcopy(base))
        return out[:k]

    # -- malice classifier -----------------------------------------------------
    def classify_malice(self, text: str) -> float:
        lower = text.lower()
        signals = [
            r"\bignore\b", r"\bdisregard\b", r"\binstead\b", r"upload",
            r"external", r"credential|password|secret", r"forward to|send to",
            r"@[a-z0-9.]+", r"delete all|all files", r"everyone",
        ]
        hits = sum(bool(re.search(s, lower)) for s in signals)
        return min(1.0, hits / 3.0)

    # -- action plan -----------------------------------------------------------
    def act(self, task: Task, resolved_intent: dict) -> list[tuple[str, dict]]:
        """Produce tool calls to satisfy the resolved intent. If the intent carries
        an injected directive (because a policy accepted a malicious answer), the
        gullible agent may add the attacker's action."""
        plan: list[tuple[str, dict]] = []
        if task.domain == "file":
            for name in resolved_intent.get("archive", []):
                plan.append(("archive_file", {"name": name}))
            for name, tgt in resolved_intent.get("share", []):
                plan.append(("share_file", {"name": name, "target": tgt}))
            for name in resolved_intent.get("_inject_delete", []):
                plan.append(("delete_file", {"name": name}))
            for name, tgt in resolved_intent.get("_inject_share", []):
                plan.append(("share_file", {"name": name, "target": tgt}))
        elif task.domain == "calendar":
            eid = resolved_intent.get("eid", "ev1")
            if "time" in resolved_intent:
                plan.append(("schedule_event", {
                    "eid": eid, "time": resolved_intent["time"],
                    "attendees": resolved_intent.get("attendees", [])}))
            for p in resolved_intent.get("_inject_attendee", []):
                plan.append(("add_attendee", {"eid": eid, "person": p}))
            for tgt in resolved_intent.get("_inject_share_avail", []):
                plan.append(("share_availability",
                             {"person": resolved_intent.get("private_person", "alice"),
                              "target": tgt}))
        return plan


def _amb_field(amb: str) -> str | None:
    m = re.search(r"\b(dates?|time|attendees?|files?|recipient|budget|"
                  r"airport|scope)\b", amb.lower())
    return m.group(1) if m else None


class OpenModelAgent:
    """Skeleton for the real experiment. Fill in generate() with your inference
    stack (vLLM / HF / llama.cpp). Keep decoding deterministic for the main runs."""

    def __init__(self, model_id: str, generate_fn):
        self.model_id = model_id
        self._gen = generate_fn  # callable(prompt:str) -> str

    def sample_intents(self, task: Task, k: int) -> list[dict]:
        raise NotImplementedError("prompt the model for k JSON intent hypotheses")

    def classify_malice(self, text: str) -> float:
        raise NotImplementedError("prompt a lightweight injection classifier")

    def act(self, task: Task, resolved_intent: dict) -> list[tuple[str, dict]]:
        raise NotImplementedError("prompt the model for a JSON tool-call plan")
