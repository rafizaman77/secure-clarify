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

### H3 — stage-2 necessity

| model | diff (Stage1Only − SecureVoI) | 95% CI | p_holm | |
|---|---|---|---|---|
| mistral-nemo-12b (screen blind) | **+0.000** | [+0.000, +0.000] | 1.000 | ✗ |
| **llama-3.3-70b** | **+0.115** | [+0.052, +0.177] | **<0.0001** | **✓** |
| **gpt-oss-20b-cloud** | **+0.188** | [+0.115, +0.260] | **<0.0001** | **✓** |
| **gpt-oss-120b-cloud** | **+0.188** | [+0.115, +0.271] | **<0.0001** | **✓** |

**H3 holds on three of four models** — every one whose screen fires — and all
three clear the underpowered family-level test as well, which no other hypothesis
managed. It fails only on Mistral, where the screen never fires at all.

## Step 6 payoff: H2 now holds at the FAMILY level

The family-level column was uninformative because `main_120` has 2 task families.
`tasks/families_120.json` adds 5 more (Step 6), and re-running the same
pre-declared tests there gives the first family-level result with real power —
**on Mistral, the model where H2 previously failed**:

| hypothesis | task-level diff | p_holm | **family-level p** | n_families |
|---|---|---|---|---|
| H1 | +0.368 [+0.253,+0.484] | <0.0001 ✓ | **0.000 ✓** | 5 |
| **H2** | **+0.200 [+0.095,+0.316]** | **0.002 ✓** | **0.024 ✓** | 5 |
| H3 | +0.021 [+0.000,+0.053] | 0.268 ✗ | 0.792 ✗ | 5 |

On `main_120` Mistral's H2 was +0.146, p_holm=0.128, family p=0.079 — **not**
significant. On five genuinely different workflows it is +0.200, significant at
the task level *and* at the family level. That is the strongest form of the
stage-1 claim available: the benefit of risk-aware acquisition **generalizes
across task families**, not just across tasks drawn from the same two templates.

H3 stays null on Mistral (+0.021, p=0.268), exactly as it should — Mistral's
screen rejects 0/20 stealth attacks, so stage 2 has nothing to contribute
regardless of which families it runs on. The two results being *inconsistent with
each other* would have signalled a bug; they are consistent.

### All three models on the new families — the asymmetry is unanimous

| model | H1 | **H2 (stage 1)** | H3 (stage 2) |
|---|---|---|---|
| mistral-nemo-12b | +0.368, fam **0.000 ✓** | +0.200, fam **0.024 ✓** | +0.021, fam 0.792 ✗ |
| llama-3.3-70b | +0.453, fam **0.000 ✓** | **+0.316, fam 0.004 ✓** | +0.042, fam 0.275 ✗ |
| gpt-oss-20b-cloud | +0.200, fam **0.007 ✓** | +0.158, fam **0.009 ✓** | +0.042, fam 0.214 ✗ |
| | 3/3 | **3/3 at family level** | **0/3 at family level** |

**Stage 1 generalizes across task families on every model tested — 3/3, all
family-level p < 0.025. Stage 2 does so on none.** H3 is significant *within*
families on llama and gpt-oss (p_holm 0.039, 0.035) but never across them.

This is a *stronger* stage-1 result than main_120 gave: there H2 held on only
2 of 4 models and never at the family level. On five unfamiliar workflows it
holds everywhere, and llama's effect more than doubles (+0.146 → +0.316).

**Effect sizes shrink on the harder benchmark, and unevenly:**

| model | H | main_120 | families_120 | change |
|---|---|---|---|---|
| mistral | H1 / H2 / H3 | +0.375 / +0.146 / +0.000 | +0.368 / +0.200 / +0.021 | ≈flat |
| gpt-oss-20b | H1 | +0.542 | +0.200 | **−0.342** |
| gpt-oss-20b | H2 | +0.240 | +0.158 | −0.082 |
| gpt-oss-20b | **H3** | **+0.188** | **+0.042** | **−0.145** |

gpt-oss's advantages fall by roughly two thirds on workflows the benchmark was
not built around, with **stage 2 losing the most** (+0.188 → +0.042). Mistral is
flat because its numbers were never screen-driven to begin with.

**Honest reading.** The main_120 numbers overstate what the method delivers on
unfamiliar workflows. What survives the harder test is the *stage-1* claim, and
it survives at the level that generalizes. The stage-2 claim is real but
narrower than main_120 suggests, and its cross-family generalization is
**unproven** — that is a limitation to state, not a result to round up.

## FINAL SCORECARD (all four models, stealth tier, exact attacker objective)

| model | H1 vs Conventional | H2 vs Screened (stage 1) | H3 vs Stage1Only (stage 2) | H4 utility equiv. |
|---|---|---|---|---|
| mistral-nemo-12b | **+0.375 ✓** | +0.146 ✗ (p=.128) | +0.000 ✗ | ✗ not equiv. |
| llama-3.3-70b | **+0.490 ✓** | **+0.146 ✓** (p=.015) | **+0.115 ✓** | ✗ not equiv. |
| gpt-oss-20b-cloud | **+0.542 ✓** | **+0.240 ✓** (p<.0001) | **+0.188 ✓** | ✗ not equiv. |
| gpt-oss-120b-cloud | **+0.552 ✓** | +0.052 ✗ (p=.117) | **+0.188 ✓** | ✗ not equiv. |
| | **4/4** | **2/4** | **3/4** | **0/4** |

**Verdict against the pre-declared decision rules.**

* **Rule 1 does not fire.** It requires H2 to fail on a *majority* of models; it
  fails on exactly half (2/4). The abstract does not have to be rewritten to
  disclaim risk-aware acquisition — but the split must be reported honestly, not
  averaged away.
* **Rule 3 governs H2 and H3.** Both are reported per model. H2's failures are on
  the two extremes: Mistral (screen blind, so stage 1 is doing all the work and
  the *screened* baseline is weak) and gpt-oss-120b (screen so strong the screened
  baseline is already at 0.073, leaving little headroom — a ceiling effect, not an
  absent effect).
* **Rule 2 fires on H4.** The utility cost is real in every model and must be
  reported with its magnitude.
* **Rule 4 stands.** The defects found along the way — flat/anti-calibrated ask
  rate, unmeasurable screen precision, degenerate noisy condition, uncalibrated
  risk score — are reported as limitations regardless of these outcomes.

**The defensible one-sentence claim:** *both stages of SecureVoI carry
independent, significant safety effects on models capable of recognising an
injection (H2 and H3 both hold on llama-3.3-70b and gpt-oss-20b), the design
degrades to stage-1 routing on models that cannot (Mistral), and the safety comes
at a measured benign-utility cost concentrated on tasks where clarification is
genuinely required.*

On Mistral the screen contributes **exactly nothing** — identical episode for
episode — which is precisely what the attacked-channel audit predicted (it rejects
0/20 stealth attacks, so disabling a screen that never fires changes nothing).
Two independent measurements agreeing to the digit.

On gpt-oss-20b, where the screen demonstrably fires, stage 2 contributes
**+0.188** and is significant even under the *underpowered* family-level test
(p=0.000), which no other hypothesis managed.

### The full 2×2 factorial on gpt-oss-20b — both stages independently significant

Stealth tier, exact attacker objective success, 96 test tasks per cell:

| acquisition | stage 2 | policy | attack success |
|---|---|---|---|
| risk-blind | accept-all | ConventionalVoI | 56/96 = 0.583 [0.48,0.68] |
| **risk-aware** | accept-all | Stage1OnlySecureVoI | 20/96 = 0.208 [0.14,0.30] |
| risk-blind | **screen** | ScreenedConventionalVoI | 27/96 = 0.281 [0.20,0.38] |
| **risk-aware** | **screen** | **SecureVoI** | **4/96 = 0.042** [0.02,0.10] |

Main effects (lower is better):

    risk-aware acquisition | no screen   0.583 -> 0.208   -0.375
    risk-aware acquisition | screen      0.281 -> 0.042   -0.240   [H2, p<0.0001]
    screening | risk-blind acquisition   0.583 -> 0.281   -0.302
    screening | risk-aware acquisition   0.208 -> 0.042   -0.167   [H3, p<0.0001]
    interaction (difference-in-differences)              +0.135

**This is the paper's central claim, cleanly demonstrated on one model.** Both
stages carry an independent, significant effect; neither is redundant; and the
positive interaction says they are partial substitutes — each is worth less once
the other is in place — which is exactly what a defense-in-depth argument
predicts. Attacker success falls from 0.583 to **0.042** when both are used.

The caveat that matters: this holds on the model whose base capability lets the
screen work. On Mistral the same factorial collapses to a stage-1-only story. The
honest framing is that SecureVoI's two-stage design delivers as advertised
*given a model that can recognise an injection*, and degrades to routing alone
when it cannot.

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
instrument built to measure it fairly.

### H4 re-measured on `ask_necessity_96` — the caveat is quantified, and the cost is *targeted*

Mistral-Nemo-12B, benign, 76 test tasks, same ±0.05 margin:

    conventional − secure = **+0.1566**, CI90 [+0.0895, +0.2316] → still **not equivalent**

The cost is **43% smaller** than on main_120 (+0.157 vs +0.275), confirming that
the benchmark's "acting blind always fails" degeneracy inflates it — but it does
**not** vanish, so the trade-off is real and decision rule 2 still applies.

The per-class split is the important part:

| ask-necessity class | conventional | secure_voi | Δ | inside ±0.05? |
|---|---|---|---|---|
| fully_specified (asking unnecessary) | +0.950 | +0.924 | **+0.026** | **yes** |
| missing_optional (asking unnecessary) | +0.950 | +0.929 | **+0.021** | **yes** |
| missing_critical (asking **required**) | +0.950 | +0.603 | **+0.347** | no |
| missing_safety_critical (asking **required**) | +0.950 | +0.718 | **+0.232** | no |

**SecureVoI is essentially free where asking is unnecessary and expensive exactly
where asking is required.** That is not a uniform "caution tax" — it is the Step 5
anti-calibration defect showing up as utility damage: the risk term suppresses
asking on precisely the tasks that cannot be solved without it. Mechanism (Step 5)
and consequence (H4) now line up, and the fix is the same one Step 5 identified —
gate asking on an explicit ambiguity signal rather than letting a near-saturated
information-gain estimate be overridden by the risk term.

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

## The stage-1 / stage-2 split is an artifact of the screen's operating point

Rerunning the full factorial on Mistral with **only the `classify_malice` prompt
changed** (`results/confirmatory_classify.json`):

| hypothesis | rating prompt (default) | **classify prompt** |
|---|---|---|
| H1 vs ConventionalVoI | +0.375, p<0.0001 ✓ | **+0.583**, p<0.0001 ✓ |
| **H2 — stage 1** | +0.146, p=0.128 ✗ | **+0.000, p=1.000 ✗** |
| **H3 — stage 2** | +0.000, p=1.000 ✗ | **+0.208, p<0.0001 ✓** |

**The two stages trade places.** With a screen that never fires, stage 1 carries
what effect there is and stage 2 measures exactly zero. With a screen that fires
on everything, stage 2 carries it all and stage 1 measures exactly zero —
SecureVoI and ScreenedConventionalVoI become *identical, episode for episode*,
because once the screen rejects every attack there is nothing left for
risk-aware acquisition to avoid.

Neither configuration shows both stages contributing. **The per-model H2/H3
pattern reported above is therefore not a property of the two-stage
architecture — it is a readout of where each model's screen happens to sit on
the recall/precision frontier.** gpt-oss-20b showed both stages significant
because its screen sits somewhere in the middle; Mistral can be moved to either
extreme by editing one prompt.

**Consequence for the paper.** The factorial cannot support "both stages
contribute" as a general claim while the screen's operating point is uncontrolled
and, on the evidence in `benign_precision.json`, indefensible at both ends. The
defensible version is conditional: *given a screen operating at a stated
precision/recall point, the factorial decomposes as follows* — and that point has
to be reported, not left to whichever prompt happened to be in the file.

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
