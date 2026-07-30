# Pre-declared confirmatory hypotheses

**Declared 2026-07-30, before the Phase 3 confirmatory runs (Steps 10–12).**

## What this document can and cannot claim

Be precise about its status, because overclaiming here is worse than not having it.

This is **not** a pre-registration of the analyses already performed. Steps 2–9,
18, 26 and 27 were exploratory: they were run on the frozen benchmark, they found
several defects (exposure/compliance conflation, a flat ask rate, an inverted
screen ranking, a degenerate noisy condition), and those findings *informed* the
hypotheses below. Presenting them as pre-registered would be false.

What it does do: it fixes the **confirmatory set** — which comparisons count as
tests of the paper's claims, on which metric, with which correction — *before* the
full-factorial runs across models in Phase 3, which have **not** yet been run.
Everything not listed here is secondary and will be reported as exploratory,
without inferential claims.

Any change to this file after the Phase 3 runs begin must be recorded as an
amendment with its date and reason, not by editing in place.

## Primary outcome metric

**Exact attacker objective success** under the stealth condition — not the pooled
`unsafe` flag. Step 2 showed `unsafe = EXPOSURE × COMPLIANCE`, and that pooled
`unsafe` mostly measures exposure (a policy property) because compliance is ≈1.0
on 6 of 7 models. Exact-objective success is the outcome an attacker actually
wants and is the harder test.

Secondary safety metric: pooled `unsafe`, reported alongside for continuity with
the existing tables.

## Confirmatory hypotheses

Four, deliberately few, so Holm correction over the family is not self-defeating.

| id | claim | comparison | condition | metric | direction |
|---|---|---|---|---|---|
| **H1** | risk-aware acquisition + screening beats conventional acquisition | SecureVoI vs ConventionalVoI | stealth | exact attacker success | SecureVoI lower |
| **H2** | *stage 1 adds safety beyond the screen alone* — the decisive ablation | SecureVoI vs ScreenedConventionalVoI | stealth | exact attacker success | SecureVoI lower |
| **H3** | *stage 2 is necessary* | SecureVoI vs Stage1OnlySecureVoI | stealth | exact attacker success | SecureVoI lower |
| **H4** | safety is not bought with utility | SecureVoI vs ConventionalVoI | benign | task utility | **equivalence**, not superiority |

**H2 is the hypothesis the paper lives or dies on.** If the screen alone accounts
for the effect, the two-stage framing is not supported, and the paper must say so.
Step 9 already found the stage-1 effect is ≈0 on unanimously-refusable attacks and
significantly *negative* on contested ones for Mistral (−0.375, p=0.002), so H2 is
a genuine open question, not a formality.

## Equivalence margins (H4, and any future "matches" claim)

Declared now, because a margin chosen after seeing the data proves nothing.

| quantity | margin | scale note |
|---|---|---|
| benign task utility | **0.05** | utility runs roughly −1…+1; 0.05 is ~2.5% of range |
| unsafe rate | **0.05** | absolute percentage points |
| task completion | **0.05** | absolute percentage points |

TOST at α=0.05: equivalence is claimed only if the two one-sided tests both
reject, equivalently if the 90% CI for the difference lies entirely within
±margin. A wide CI means "underpowered", never "equivalent".

## Correction and independence

- **Correction:** Holm–Bonferroni across the four confirmatory hypotheses, per
  model. Corrected *and* uncorrected p-values both reported (Step 21).
- **Independent unit:** the **task**, resampled hierarchically as
  task family → attack family → instance (Step 20). Episodes within a task share
  a request, a channel set, and an attack, so treating episodes as independent
  overstates precision. The existing paired task-level bootstrap is the right
  unit but flat; the hierarchical version is what these hypotheses are tested with.
- **Generalization target:** stated explicitly per CI — a task-level CI
  generalizes to new instances of the *same three task families*, not to new
  domains. Claims about new domains require the family-level resample.
- **Zero rates:** never reported as 0 alone. Wilson score interval plus the
  explicit denominator, phrased "no unsafe actions observed in *n* episodes"
  (Step 23). "Eliminates attacks" is forbidden.

## Pre-declared decision rules

Written down so the conclusion is not chosen after the fact.

1. If **H2** fails to reject after correction on the majority of models, the
   abstract and contributions must be rewritten to claim only that *response
   screening* drives the safety result, with risk-aware acquisition reported as
   not independently supported on this benchmark.
2. If **H4** fails (utility not equivalent), the safety/utility trade-off must be
   reported as a real cost with its magnitude, not as "comparable utility".
3. If a hypothesis is significant on some models and not others, report the
   per-model split and the heterogeneity; do not pool to manufacture
   significance, and do not describe it as "significant" without the split.
4. Findings already established as defects (flat ask rate, inverted screen
   ranking, degenerate noisy condition, unmeasurable precision) are reported as
   limitations **regardless** of how the confirmatory tests come out.
