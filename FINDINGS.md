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

## 3. Stage 2's operating point is a model × prompt interaction

Measured against 81 corpus attacks (**4 persuasion families held out**) and the
24 graded benign answers. Balanced accuracy = (recall + specificity)/2; the
held-out column is the one that counts.

| model | prompt | recall | specificity | bal acc | **held-out bal acc** |
|---|---|---|---|---|---|
| mistral-nemo-12b | rating *(default)* | 0.062 | 1.000 | 0.531 | 0.514 |
| mistral-nemo-12b | classify | 0.963 | 0.167 | 0.565 | 0.542 |
| mistral-nemo-12b | contextual | 0.704 | 0.667 | 0.685 | 0.528 |
| **llama-3.3-70b** | **rating *(default)*** | 0.852 | 0.750 | **0.801** | **0.722** |
| llama-3.3-70b | classify | 0.951 | 0.167 | 0.559 | 0.528 |
| llama-3.3-70b | contextual | 0.494 | 0.875 | 0.684 | 0.632 |
| gpt-oss-20b | rating *(default)* | 0.864 | 0.042 | 0.453 | 0.410 |
| gpt-oss-20b | classify | 0.815 | 0.125 | 0.470 | 0.354 |
| gpt-oss-20b | **contextual** | 0.901 | 0.500 | **0.701** | 0.639 |

**A defensible operating point exists: llama-3.3-70b with the shipped default
prompt reaches 0.801 pooled / 0.722 on held-out families.** My earlier claim that
"nothing exceeds 0.55 balanced accuracy on unseen families" was measured on
Mistral alone and is **withdrawn** — it is a weak-model result, not a ceiling.

**But the best prompt is model-dependent, and no prompt wins everywhere:**

- llama: rating **0.801** ≫ contextual 0.684 > classify 0.559
- gpt-oss-20b: contextual **0.701** ≫ classify 0.470 > rating 0.453
- mistral: contextual **0.685** > classify 0.565 > rating 0.531

The shipped prompt is close to optimal on llama and close to worst on the other
two. **A fixed screen prompt across models therefore guarantees a poor operating
point on some of them** — which is what produced the "screen is blind"
(Mistral, 0.531) and "screen refuses everything" (gpt-oss, 0.042 specificity)
results reported earlier as model properties.

**What this means for the paper.** Stage 2 is viable, but only when the
screen's operating point is measured and the prompt matched to the model. The
paper currently reports neither. Reporting a single safety number per model
without its operating point conflates three different regimes.

### The factorial, read against its operating point

*(`scripts/factorial_at_operating_point.py`. Held-out recall and specificity from
the corpus/benign measurement above; H2/H3 are exact-attacker-objective
differences on stealth, Holm-corrected, `*` = significant.)*

| model | prompt | tasks | held-out recall | spec | **bal acc** | H2 stage 1 | H3 stage 2 |
|---|---|---|---|---|---|---|---|
| mistral | rating | main_120 | 0.028 | 1.000 | 0.514 | +0.146 | +0.000 |
| mistral | classify | main_120 | 0.917 | 0.167 | 0.542 | +0.000 | +0.208* |
| **llama** | **rating** | main_120 | 0.694 | 0.750 | **0.722** | **+0.146\*** | **+0.115\*** |
| gpt-oss-20b | rating | main_120 | 0.778 | 0.042 | 0.410 | +0.240* | +0.188* |
| mistral | rating | families | 0.028 | 1.000 | 0.514 | +0.200* | +0.021 |
| **llama** | **rating** | families | 0.694 | 0.750 | **0.722** | **+0.316\*** | **+0.042\*** |
| gpt-oss-20b | rating | families | 0.778 | 0.042 | 0.410 | +0.158* | +0.042* |

**At the one defensible operating point in the project — llama, balanced accuracy
0.722 — both stages carry independent, significant effects, on `main_120` *and*
on the five held-out task families.** That is the cleanest support the two-stage
claim has, and it is now stated with the operating point attached.

Every other row is measured at a degenerate point and should not be read as
evidence about the architecture: Mistral/rating never fires (specificity 1.000,
held-out recall 0.028), Mistral/classify always fires, and gpt-oss/rating has
specificity **0.042** — it rejects 23 of 24 benign answers, so its two
"significant" effects are a property of near-total refusal.

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

1. **Re-run the factorial at a stated operating point** — and now there is one
   worth using: llama + the default prompt (0.722 held-out balanced accuracy).
   H2/H3 measured anywhere else are not meaningful, since the split inverts with
   the operating point.
2. **Match the prompt per model, then re-measure.** gpt-oss-20b should be run
   with `contextual` (0.639 held-out) rather than the default (0.410), and the
   choice reported as part of the configuration.
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
screening is viable but conditional: its contribution is entirely determined by an
operating point the paper never measured, that point is a model x prompt
interaction rather than a model property, and the benchmark's benign traffic was
too clean to expose any of it -- a trivial detector baseline "wins" there purely
by refusing everything. One configuration (llama-3.3-70b with the shipped prompt)
does reach a defensible 0.722 balanced accuracy on held-out attack families; the
same prompt reaches 0.410 on gpt-oss-20b, which needs a different one. The
contribution this work can honestly claim is the stage-1 result, plus the
instruments that made the stage-2 problem measurable at all: a family-split
attack corpus, graded benign traffic, and an operating-point measurement the
original evaluation could not perform.
