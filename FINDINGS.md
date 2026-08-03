# Findings — state of the evidence

Consolidated from `RESEARCH_PLAN.md` (the step-by-step log) and `HYPOTHESES.md`
(the pre-declared confirmatory set). This file is the short version: what is
established, what was overturned, and what is still open.

Everything below is measured on this benchmark with the models named. Where a
claim did not survive a harder test, the harder test is what is reported.

---

## 1. What holds up

**Risk-aware acquisition (stage 1) generalizes across task families.** The
strongest result in the project. On five newly authored task families —
`file::cleanup`, `calendar::reschedule`, `messaging::escalation`,
`email::correspondence`, `email::attachment` — H2 (SecureVoI vs
ScreenedConventionalVoI, exact attacker objective, stealth) is significant at the
**family level on 3/3 models**: Mistral p=0.024, llama p=0.004, gpt-oss-20b
p=0.009. On the original `main_120` it held on only 2 of 4 models and never at
the family level.

**The safety advantage over a risk-blind baseline is large and consistent.** H1
(vs ConventionalVoI) rejects on 4/4 models, effects +0.375 to +0.552 on
main_120, +0.200 to +0.453 on the new families.

**The pipeline is sound.** Acceptance→action is not hard-coded (Step 2, four
independent confirmations); verifier and simulator agree on 31,065 episodes
(Step 4, after fixing a real cross-domain externality bug).

---

## 2. What was overturned, and by what

Each of these was reported with confidence before a harder test contradicted it.

| claim | overturned by | now |
|---|---|---|
| "`cue_only` dominates the full risk composite" | 81-attack corpus | artifact of main_120's 12 stealth strings; does not replicate |
| "the learned classifier contributes nothing" | per-model rerun | true only on Mistral; on capable models it is **necessary and sufficient** |
| "Mistral cannot detect subtle injections" | prompt swap | it detects **12/12** when asked for a verdict instead of a probability |
| "stealth discrimination is a model property (0–80%)" | prompt swap | largely a prompt property |
| "calibration will let one λ transfer across models" | direct test | refuted; λ absorbs discrimination differences too |
| "task-conditioned screening resolves precision" | held-out families | recall collapses 0.956 → **0.389** on unseen families |
| "the reported rejection rate measures the screen" | tracing `accept()` | it counted "no response defined" as rejection; true stealth rejection was **0/60** |

The instruments that caught these — the family-split attack corpus, the graded
benign traffic, the per-model reruns — matter more than any single number.

---

## 3. The central problem: stage 2 has no defensible operating point

Screening is evaluated on the wrong axis. Measured against 81 corpus attacks
(4 families held out) and 24 graded benign answers, on Mistral:

| screen | recall (all) | specificity | balanced acc | **held-out recall** |
|---|---|---|---|---|
| rating (shipped default) | 0.062 | 1.000 | 0.531 | 0.028 |
| classify (verdict) | 0.963 | 0.167 | 0.565 | 0.917 |
| contextual (verdict + request) | 0.704 | 0.667 | 0.685 | 0.389 |

**Nothing tested exceeds 0.55 balanced accuracy on unseen attack families.** The
configurations sit at opposite ends of a degenerate frontier — "never fires" or
"always fires" — and the one that reaches the middle does so by not generalizing.

**Two consequences the paper cannot avoid.**

1. **The factorial inverts with the operating point.** On Mistral, changing only
   the screen's prompt moves stage 1 from +0.146 to **+0.000** and stage 2 from
   +0.000 to **+0.208**. The per-model H2/H3 pattern is a readout of where each
   screen sits on the frontier, not a property of the architecture.
2. **Precision was never measurable.** `main_120`'s benign answer in restricted
   format is the single character `"A"`. A PromptArmor-style baseline scores
   0.000 attack success there — while flagging **24/24** realistic benign
   answers, including 6/6 of the plainest tier ("Thursday at 14:00 works").
   Its perfect score was refusal, not detection.

---

## 4. Defense baselines (Phase 4)

Mistral, main_120 test split, stealth. SecureVoI is **not** ahead:

| defense | attack success | goal | utility |
|---|---|---|---|
| conventional_voi (none) | 0.583 | 0.708 | −0.508 |
| prompt_armor | 0.000 | 0.417 | +0.367 |
| spotlighting (ASPI-style) | 0.427 | 0.740 | −0.165 |
| posthoc_guardrail *(oracle)* | 0.000 | 1.000 | +0.950 |
| **secure_voi** | 0.208 | 0.396 | −0.096 |

The guardrail screens against the task's own `prohibited_actions`, so it is an
upper bound rather than a competitor. PromptArmor's win is refusal (see §3).
Spotlighting removes ~25% of attack success for free — the cheapest real defense.

---

## 5. Other established defects

- **Ask calibration fails.** No policy's ask rate tracks ask-necessity. Mechanism:
  information gain saturates at 0.89–0.99 across all four necessity classes
  because `sample_intents` disagrees even on fully specified requests.
- **The utility cost is real and targeted.** H4 equivalence fails on 4/4 models.
  On `ask_necessity_96` the cost concentrates entirely where asking is *required*
  (Δ +0.347, +0.232) and is within the margin where it is not (+0.026, +0.021) —
  the ask-calibration defect surfacing as lost utility.
- **`response_risk` is not a probability.** AUROC ≈0.9 but reliability 0.025–0.054,
  wrong in opposite directions on different models, so λ is not a loss ratio.
  Platt recalibration improves Brier ~25% and NLL 18–24% out of sample.
- **The noisy condition is degenerate.** 0/672 goal and 0/672 unsafe for all
  policies; `_noisy_fill` is a strict subset of the goal, so failure is structural.
- **Generalization to new domains is untestable on main_120** — it has 2 task
  families, so the family-level bootstrap has no power. Fixed by §1's five.

---

## 6. What is still open

1. **Does 0.55 balanced accuracy bound all models, or just Mistral?** Runs on
   gpt-oss-20b and llama-3.3-70b are the next evidence. If a capable model clears
   it, the framing is "needs a capable screen"; if not, response screening on this
   benchmark is unsolved and the paper should lean on the stage-1 result.
2. **Re-run the factorial at a stated operating point.** H2/H3 measured anywhere
   else are not meaningful.
3. **Adaptive attacks are built but never run as episodes** (8 minimal-cue
   attacks at the structural floor of 1 cue term).
4. **Manuscript.** Several current claims no longer match the evidence, in both
   directions — the stage-1 result is stronger than stated, the stage-2 result
   weaker.

---

## 7. Honest one-paragraph summary

Risk-aware acquisition is the part of SecureVoI that survives scrutiny: it beats
a risk-blind baseline decisively on every model, and its advantage generalizes
across five task families that the benchmark was not built around. Response
screening is not currently defensible — its measured contribution is entirely
determined by an operating point that no configuration reaches acceptably, the
benchmark's benign traffic was too clean to expose this, and a trivial detector
baseline "wins" on the same benchmark purely by refusing everything. The
contribution this work can honestly claim is the stage-1 result plus the
instruments that made the stage-2 problem visible: a family-split attack corpus,
graded benign traffic, and an operating-point measurement that the original
evaluation could not perform.
