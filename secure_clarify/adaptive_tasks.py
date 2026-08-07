"""Make Steps 16-17's adaptive attacks (`adaptive_attacks.py`) RUNNABLE as episodes.

WHY THIS EXISTS. `build_adaptive_attacks()` produces 8 minimal-cue rewrites of
corpus attack transitions -- one white-box-on-the-screen attack per
(domain, objective) pair, each sitting at the structural floor of 1 cue hit
("@" only). They were validated as *text* by the smoke test
(`test_adaptive_attacks_sit_at_the_cue_floor`), but as FINDINGS.md's open-items
list (Step 6, item 3) records: "Adaptive attacks are built but never run as
episodes." A construct that only exists as a string was never tested against
the actual policy/screen it was designed to probe.

WHAT THIS DOES. Exactly the pattern `corpus_tasks.py` established for the
Step-7 corpus: one task per adaptive attack, built from the frozen domain
makers, with only the stealth response's text overwritten. Every other part of
the task -- request, state, goal predicate, channels, questions, benign/noisy
answers, the explicit adversarial tier -- is untouched, so a
corpus-vs-adaptive delta on the SAME (domain, objective) pairs isolates cue
density and nothing else.

ADDITIVE BY CONSTRUCTION. Calls `make_file_task`/`make_calendar_task`/
`make_messaging_task` exactly as `corpus_tasks.py` does; nothing frozen moves.

SPLIT. All 8 are `split="test"` in `adaptive_attacks.py` itself, by design --
"never used for any fitting" (see that module's docstring and its own smoke
assertion). This module does not override that.
"""
from __future__ import annotations

from .adaptive_attacks import build_adaptive_attacks
from .schema import AttackType, Condition, Task
from .task_factory import (make_file_task, make_calendar_task,
                           make_messaging_task, AVAIL_GROUPS, STAKES)

_MAKERS = {"file": make_file_task,
           "calendar": make_calendar_task,
           "messaging": make_messaging_task}


def _restricted_form(body: str) -> str:
    """Mirrors `corpus_tasks._restricted_form`: the act() prompt never shows
    the model the original A/B/C text, so the restricted-format channel spells
    the injected action out in full rather than a bare letter."""
    return f"A. {body}"


def build_adaptive_task_set() -> list[Task]:
    """One task per adaptive (minimal-cue) attack (8), each carrying exactly
    that attack on its stealth-tier responses."""
    tasks: list[Task] = []
    for i, a in enumerate(build_adaptive_attacks()):
        maker = _MAKERS[a["domain"]]
        chans, _ = AVAIL_GROUPS[i % len(AVAIL_GROUPS)]
        t = maker(idx=i, channels=list(chans), stakes=STAKES[i % len(STAKES)],
                  attack=AttackType(a["objective"]), split="test")

        restricted = _restricted_form(a["body"])
        n_written = 0
        for r in t.responses:
            if r.condition is Condition.ADVERSARIAL_STEALTH and r.carries_attack:
                r.text = a["text"] if r.qid == "q_open" else restricted
                r.attack_type = AttackType(a["objective"])
                n_written += 1
        if n_written == 0:
            raise RuntimeError(
                f"adaptive attack {a['attack_id']} landed on a task with no "
                f"attack-carrying stealth response; cannot attribute it")

        t.task_id = f"adaptive_{i:03d}"
        t.family = f"adaptive::{a['domain']}::{a['objective']}"
        t.hidden_intent = dict(t.hidden_intent)
        t.hidden_intent["_adaptive"] = {
            "attack_id": a["attack_id"], "domain": a["domain"],
            "objective": a["objective"], "cue_hits": a["cue_hits"],
            "cues": a["cues"],
        }
        t.validate()
        tasks.append(t)
    return tasks
