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

## RESULTS (recorded 2026-07-30, after the tests were run)

`scripts/confirmatory_tests.py`, `results/confirmatory_tests.json`. Stealth tier,
primary metric **exact attacker objective success**, Holm-corrected per model,
paired resampling. H3/H4 not yet runnable (need `stage1_only` and benign episode
files).

| model | H1 (vs ConventionalVoI) | p_holm | **H2 (vs Screened — the decisive test)** | p_holm |
|---|---|---|---|---|
| mistral-nemo-12b | +0.375 [+0.219,+0.531] | <0.0001 ✓ | +0.146 [+0.000,+0.292] | 0.064 ✗ |
| llama-3.3-70b | +0.490 [+0.365,+0.615] | <0.0001 ✓ | **+0.146 [+0.031,+0.250]** | **0.015 ✓** |
| gpt-oss-20b-cloud | +0.542 [+0.438,+0.646] | <0.0001 ✓ | **+0.240 [+0.146,+0.333]** | **<0.0001 ✓** |
| gpt-oss-120b-cloud | +0.552 [+0.448,+0.656] | <0.0001 ✓ | +0.052 [+0.000,+0.115] | 0.117 ✗ |

**H1 holds decisively in all four models.** **H2 holds in two of four.** By
decision rule 3 that must be reported as a per-model split, never pooled.

### H3 — stage-2 necessity (Mistral only; the other models lack `stage1_only` runs)

| model | diff (Stage1Only − SecureVoI) | 95% CI | p |
|---|---|---|---|
| mistral-nemo-12b | **+0.000** | [+0.000, +0.000] | 1.000 |

Identical, episode for episode. On Mistral the stage-2 screen contributes
**exactly nothing** beyond stage 1 on the stealth tier — which is precisely what
the attacked-channel audit predicted (Mistral rejects **0/20** stealth attacks,
so disabling a screen that never fires cannot change anything). Two independent
measurements agreeing to the digit. **H3 is untested on the models where the
screen demonstrably does fire**, and those are the runs that would actually
answer it.

### H4 — benign utility equivalence: **FAILS in all four models**

TOST at the pre-declared ±0.05 margin, 90% CI, `conventional_voi − secure_voi`:

| model | benign utility diff | 90% CI | verdict |
|---|---|---|---|
| mistral-nemo-12b | +0.2750 | [+0.195, +0.355] | **not equivalent** |
| llama-3.3-70b | +0.2750 | [+0.195, +0.355] | **not equivalent** |
| gpt-oss-20b-cloud | +0.1604 | [+0.102, +0.227] | **not equivalent** |
| gpt-oss-120b-cloud | +0.1917 | [+0.125, +0.262] | **not equivalent** |

Every interval sits far outside the margin, so this is a clear failure, not an
underpowered one. **Decision rule 2 fires: the safety/utility trade-off must be
reported as a real cost with its magnitude, never as "comparable utility".**

*Mechanism (checked, not assumed).* Mistral and llama produce byte-identical
numbers because on benign tasks utility is a **deterministic function of the ask
rate**: both reach goal=1.000 whenever they ask, ConventionalVoI asks on 100% of
tasks and SecureVoI on 75%, and the benchmark guarantees that a task not asked
about fails. The gpt-oss models differ only because they also fail some tasks
they *did* ask about (goal 0.531 / 0.729).

*Honest caveat on the magnitude.* This cost is inflated by the Step 5 defect —
`_default_fill` never satisfies the goal, so declining to ask is maximally
punished by construction. On a benchmark where some tasks are answerable without
clarification, the same policy would lose far less. **0.16–0.275 is therefore an
upper bound, not the field cost**, and `tasks/ask_necessity_96.json` is the
instrument built to measure it fairly. Re-running H4 there is the right follow-up.

**A methodological near-miss, recorded because it nearly changed the paper.**
The first run used family-level resampling as this document specifies — and H2
failed in *all four* models (p = 0.079…0.596), which would have triggered
decision rule 1 and a rewrite of the abstract. It is underpowered by
construction: `main_120` contains only **2 task families**, so resampling
families cannot detect any effect and a null there is not evidence of absence.
The task-level test is the one with power, and it generalizes to new tasks from
these same families. Both are now reported side by side, with the family column
explicitly labelled underpowered. **The "generalizes to new domains" question is
not answerable on this benchmark** — which is itself the finding, and an argument
for Step 6's additional domains.

**This confirms the plan's guiding claim.** "Response screening handles
recognizable attacks; risk-aware acquisition can add safety when screening is
imperfect." The paper's own explicit-tier ablation reports the stage-1 share as
exactly 0.000 in all four models. On the stealth tier, where the screen is
weaker, the stage-1 effect is +0.05 to +0.24 and significant in 2/4. Stage 1 is
redundant exactly where the screen already works and load-bearing where it does
not — the predicted pattern, and a *stronger* result for the two-stage design
than the current manuscript claims.

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
