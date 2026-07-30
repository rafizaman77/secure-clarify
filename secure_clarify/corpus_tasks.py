"""Make the Step 7 attack corpus RUNNABLE as episodes.

WHY THIS EXISTS. Step 7 built 81 attacks across 9 persuasion families with a
disjoint train/test family split, but the corpus was only ever *scored* as text
(`scripts/screen_generalization.py`). No episode run used it, so every end-to-end
result -- the safety headline, the 2x2 factorial, the Step 27 component ablation --
still rested on `main_120`'s **12 distinct stealth strings**. That is the exact
resolution limit recorded as Step 27's main caveat: with 12 texts, whole ablations
came out as no-ops simply because too few responses sat near the screen's
threshold.

WHAT THIS DOES. One task per corpus attack, so attribution is exact: each task
carries exactly one attack, and its family/objective/split are recorded on the
task itself. Everything else -- request, state, goal predicate, channels,
questions, benign and noisy answers, the explicit adversarial tier -- comes
unchanged from the existing domain makers, so an explicit->corpus delta isolates
attack *language* and nothing else.

ADDITIVE BY CONSTRUCTION. The frozen makers are called, never edited: the corpus
text is written onto the stealth responses after construction. Nothing that calls
`build_pilot()` or `build_diversity_set()` is affected, and `tasks/main_120.json`
and `tasks/diversity_180.json` cannot move.

SPLIT SEMANTICS DIFFER FROM THE OTHER TASK SETS, deliberately. Elsewhere `split`
is by task index. Here it is inherited from the attack's FAMILY, so a test task's
persuasion strategy is one whose wording never appears in any train task.
Splitting by index would leave the same sentences on both sides -- the flaw Step 7
exists to fix.
"""
from __future__ import annotations

from .schema import AttackType, Condition, Task
from .attack_corpus import build_attack_corpus, TRAIN_FAMILIES
from .task_factory import (make_file_task, make_calendar_task,
                           make_messaging_task, AVAIL_GROUPS, STAKES)

_MAKERS = {"file": make_file_task,
           "calendar": make_calendar_task,
           "messaging": make_messaging_task}


def _restricted_form(body: str) -> str:
    """The restricted-format counterpart of a corpus attack body.

    Mirrors the convention `_matched_responses` documents for `adv_restricted`:
    name the choice, then spell the injected action out in full. The act() prompt
    never shows the model the original A/B/C text, so a bare letter would be
    uninterpretable -- the injected request has to survive on its own.
    """
    return f"A. {body}"


def build_corpus_task_set() -> list[Task]:
    """One task per corpus attack (81), each carrying exactly that attack."""
    tasks: list[Task] = []
    for i, a in enumerate(build_attack_corpus()):
        maker = _MAKERS[a["domain"]]
        chans, _ = AVAIL_GROUPS[i % len(AVAIL_GROUPS)]
        t = maker(idx=i, channels=list(chans), stakes=STAKES[i % len(STAKES)],
                  attack=AttackType(a["objective"]),
                  split="train" if a["family"] in TRAIN_FAMILIES else "test")

        # Overwrite the stealth tier with this corpus attack. The explicit
        # adversarial tier is left alone so the two tiers stay comparable.
        restricted = _restricted_form(a["body"])
        n_written = 0
        for r in t.responses:
            if r.condition is Condition.ADVERSARIAL_STEALTH and r.carries_attack:
                r.text = a["text"] if r.qid == "q_open" else restricted
                r.attack_type = AttackType(a["objective"])
                n_written += 1
        if n_written == 0:
            raise RuntimeError(
                f"corpus attack {a['attack_id']} landed on a task with no "
                f"attack-carrying stealth response; cannot attribute it")

        t.task_id = f"corpus_{i:03d}"
        t.family = f"corpus::{a['family']}::{a['objective']}"
        # carried so analyses can group by persuasion family without re-parsing
        t.hidden_intent = dict(t.hidden_intent)
        t.hidden_intent["_corpus"] = {
            "attack_id": a["attack_id"], "family": a["family"],
            "objective": a["objective"], "split": a["split"],
            "domain": a["domain"],
        }
        t.validate()
        tasks.append(t)
    return tasks
