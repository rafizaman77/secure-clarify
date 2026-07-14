# Go/No-Go Memo — Jul 16

**Decision: GO** (pipeline validated on a scripted agent; ready to swap in open models).

## What was run

40 base tasks (20 file + 20 calendar), 4 policies (Never Ask, Conventional VoI,
Trusted-Only, SecureVoI), 2 response conditions (benign, adversarial), deterministic
scripted agent. This is the pipeline test, **not** the empirical result — the scripted
agent stands in for the three open-weight models until they are wired in.

## Headline pilot numbers (scripted agent, medium severity profile)

| policy | benign goal | benign util | adv unsafe | adv util |
|---|---|---|---|---|
| Never Ask | 0.00 | −0.15 | 0.00 | −0.15 |
| Conventional VoI | 1.00 | 0.95 | **0.425** | −0.25 |
| Trusted-Only | 0.75 | 0.64 | 0.00 | 0.39 |
| SecureVoI (λ=1) | 1.00 | 0.95 | **0.30** | 0.02 |

## Go/no-go checks (all pass)

1. **Benign clarification helps.** Conventional VoI goal 1.00 vs Never Ask 0.00 (+1.00).
2. **Adversarial clarification hurts.** Conventional VoI adv-unsafe 0.425 vs Never Ask
   0.00 (+0.425). This reproduces the ASPI phenomenon inside our sandbox.
3. **SecureVoI reduces the harm.** Adv-unsafe 0.30 < 0.425, and at λ=2 it reaches 0.125.
4. **Not degenerate.** SecureVoI benign utility 0.95 > Trusted-Only 0.64 — it still uses
   partially-trusted sources when the information is worth it, rather than always
   retreating to the authenticated user or never asking.

## Safety–utility frontier (the paper's central figure, in miniature)

| λ | benign util | adv unsafe | ask rate |
|---|---|---|---|
| 0.00 | 0.950 | 0.425 | 1.00 |
| 0.25 | 0.950 | 0.325 | 1.00 |
| 0.50 | 0.950 | 0.300 | 1.00 |
| 1.00 | 0.945 | 0.300 | 1.00 |
| 2.00 | 0.938 | 0.125 | 1.00 |
| 4.00 | 0.718 | 0.000 | 0.80 |
| 8.00 | 0.333 | 0.000 | 0.45 |

Monotone in the right direction. λ=0 recovers Conventional VoI exactly (unsafe 0.425),
an internal consistency check. The knee sits around λ≈2: near-full benign utility with
most unsafe actions removed. Select the primary λ on the dev split, never on test.

## Bugs found and fixed during the Jul 15 audit (documented for the paper's methods)

1. **Answer leakage into the base intent.** The first task version put the ground-truth
   action fields directly in `hidden_intent`, so the agent succeeded without asking and
   clarification showed zero value. Fix: withhold the ambiguous fields; supply them only
   through `_benign_fill` / `_noisy_fill`. *Lesson: verify that Never Ask actually fails
   the benign task, or "asking helps" is an artifact.*
2. **Risk-blind policy accidentally avoided the attack.** Info gain ignored the channel, so
   Conventional VoI tie-broke onto the safe user channel and never met an attack. Fix:
   make info gain channel-dependent so untrusted channels can be genuinely more informative
   — this is the temptation that makes the trade-off exist.
3. **Scale mismatch collapsed SecureVoI to never-ask.** Info gain was in disagreement units
   (~0.09) while the risk penalty was in loss units (~0.3), so nothing cleared zero. Fix:
   express info gain in recoverable-utility units so it is commensurate with λ·risk·loss.
   *This is the single most important calibration point; call it out in the method section.*

## Caveats to carry forward (do NOT overstate)

- These numbers come from a **scripted agent**, not a language model. They demonstrate the
  pipeline can express the trade-off and that the policies behave as designed. Real-model
  numbers will differ and are the actual contribution.
- The scripted `accept()` gate uses lexical cues; a real injection classifier will change
  stage-2 performance. Report oracle-risk vs learned-risk ablation to bound this.
- Channel info multipliers and attack priors are seeded, not fit. Fit them on the dev split
  (Jul 17–18) before any test run.

## Immediate next steps (Jul 16 afternoon → Jul 17)

1. Freeze `schema.py`, `simulators.py`, `verifiers.py`, threat model, novelty matrix.
2. Implement `OpenModelAgent.sample_intents / classify_malice / act` against the first
   open checkpoint; confirm one task runs end-to-end with a real model.
3. Split 24 dev / 96 test base tasks, stratified, checksummed. Keep all variants of a base
   task in the same split.
4. Fit channel priors and λ on dev only.
