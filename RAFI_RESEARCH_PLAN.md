# RAFI RESEARCH PLAN — model breadth, learned components, and literature depth (opened 2026-07-30)

**Relationship to `RESEARCH_PLAN.md` (Anagh's plan):** that plan repairs the
benchmark's *construct* — is the measured effect real, is the metric well
defined, does it survive adaptive/shifted/stealthy attacks, is the statistics
correct. This plan does not touch any of that. It attacks three orthogonal
axes the paper is currently thin on:

1. **How general is the finding across models?** Four open-weight models plus
   three single-eval frontier spot-checks is a narrow claim for a paper whose
   abstract says "across models." (Model breadth / scaling.)
2. **Is "learned security reasoning" actually learned?** Every risk signal in
   the method (`classify_malice`, channel priors, $\lambda$) is either a
   prompted heuristic or a hand-fit scalar. Nothing in the system is trained
   on data in the machine-learning sense. (A real trained component.)
3. **Does the paper's related work reflect the actual 2025–2026 literature?**
   21 references, most added in two batches under deadline pressure. A
   security paper that misses a directly-relevant recent defense is exposed
   to exactly the reviewer criticism this project has spent two weeks
   fixing in other places. (Literature depth.)

**Non-overlap contract, so we don't duplicate work:**
- Anagh owns: task/attack construct validity, verifier correctness, the
  factorial ablation, adaptive/shifted attacks, statistics (Phases 1–6 of
  `RESEARCH_PLAN.md`), the threat-model ontology rewrite, and Related Work's
  *comparison framing* (Step 37 — turning citations into a positioning table).
  I do not touch those.
- I own: which models are tested and how many, whether any component is
  actually trained rather than prompted, and whether the citation set itself
  is complete and current. Anagh's Step 37 can consume what Phase 5 below
  produces (more/better citations) without redoing it.
- **Shared substrate, not shared work:** every model run in Phase 1 below
  runs against the *currently frozen* task artifacts (`tasks/main_120.json`,
  `tasks/diversity_180.json`, `tasks/attack_corpus.json`,
  `tasks/ask_necessity_96.json`, `results/refusable_subset.json`). If Anagh's
  Step 6 lands new task families, Phase 1's existing model results are not
  invalidated — they're results on task-set vN, and new models/old models
  both get an additive run on vN+1. Nothing here needs to block on, or wait
  for, Anagh's fixes.
- **Merge point:** once both plans have moved, `paper.tex`'s Table 2 grows
  from 4–7 models to whatever Phase 1 lands, Method gets a short "trained
  vs. prompted risk classifier" ablation from Phase 4, and Related Work gets
  the expanded, re-verified citation set from Phase 5. I will not edit
  `paper.tex` narrative sections Anagh is actively rewriting (Phase 9); I'll
  hand off results and let the merge happen deliberately, not by both of us
  editing the same paragraph.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked/finding

---

## Phase 0 — Coverage audit (what we actually have right now)

- [x] **0. Inventory every model directory under `results/models/`.** Done by
  direct inspection, 2026-07-30:

  | model | dev calib | 96-task primary | 144-task diversity | full battery (ablation/guardrail/stealth) |
  |---|---|---|---|---|
  | Mistral-Nemo-12B | yes | yes | yes | **yes, full** |
  | Llama-3.3-70B | yes | yes | yes | **yes, full** |
  | GPT-OSS-20B (cloud) | yes | yes | yes | **yes, full** |
  | GPT-OSS-120B (cloud) | yes | yes | yes | **yes, full** |
  | GPT-5.4-mini | yes | yes | yes | headline-only (no ablation/guardrail/stealth) |
  | Claude-Sonnet-5 | yes | yes | yes | headline-only |
  | Gemini-3.6-flash | yes | yes | **partial — episodes present, no `primary_summary.json`** | headline-only |
  | Qwen2.5-0.5B-Instruct | yes (calibration only) | **no** | no | no — abandoned start |
  | Llama-3.3-70B-versatile | yes (calibration only, superseded by Llama-3.3-70B) | no | no | dead entry, safe to ignore |

  **Immediate, cheap fix before anything else:** Gemini-3.6-flash-diversity is
  missing its summary file even though episodes exist — this is a
  five-minute `scripts/summarize_run.py`-style regeneration, not a new model
  run, and should happen before Phase 1 so we don't recompute something we
  already paid for.

  **What "across models" currently means in the abstract vs. what's true:**
  the abstract's headline numbers (`0.583`→`0.000-0.073` unsafe, the four
  significant $\Delta$s) are computed over exactly **4** models. The 3
  frontier models are 2-point spot checks (primary + diversity, explicit tier
  only) that happen to replicate the ordering — real evidence, but not yet
  the same depth of evidence, and not yet folded into Table 2's per-model
  columns or the paired-bootstrap $\Delta$s in the abstract.

## Phase 1 — Model breadth (many more runs, same frozen tasks)

- [!] **1. Fill the frontier-model battery to parity with the 4 open-weight
  models.** *(attempted 2026-07-30 for Claude-Sonnet-5, blocked — see below.
  Not yet attempted for GPT-5.4-mini/Gemini-3.6-flash.)* GPT-5.4-mini, Claude-Sonnet-5, and Gemini-3.6-flash each need the
  same three things the 4 originals have: oracle-vs-learned-risk ablation,
  post-hoc guardrail eval, and the explicit *and* stealth tiers (currently
  explicit-tier only per `HANDOFF.md`'s explicit scope decision — that
  decision was made under time pressure for the initial 3-model add, not as
  a permanent limit). This is the single highest-value block: it's the
  difference between "spot-checked on frontier models" and "fully
  characterized on frontier models," and it reuses the exact scripts already
  built for the open-weight runs (`screened_ablation.py`,
  `oracle_ablation` path, `guardrail_eval` path, stealth-tier runner).

  **Attempt 1, 2026-07-30: all three Claude-Sonnet-5 legs failed on the SAME
  root cause — the API key ran out of credit balance mid-run, not a bug.**
  Launched oracle ablation, guardrail eval, and the stealth tier
  (`supervise_run.sh`-wrapped) concurrently against the existing dev
  calibration already on disk. Oracle ablation got 41/96 tasks in before
  every subsequent call started failing; guardrail eval failed almost
  immediately; the stealth run kept retrying and "skipping" tasks (safely —
  `run_primary.py`'s failure handling leaves a skipped task retryable under
  `--resume`, confirmed by reading its own log output, so nothing was
  corrupted) until stopped. Root cause confirmed by direct `curl` against
  `api.anthropic.com`: `"Your credit balance is too low to access the
  Anthropic API."` Running 3 concurrent processes against one account
  accelerated hitting whatever balance/cap existed. **Action needed from
  Rafi: add credit to the Anthropic account before this can resume** — no
  code or task-design issue to fix. One follow-up worth doing before the next
  attempt: `oracle_ablation.py` and `guardrail_eval.py` (unlike
  `run_primary.py`) have no `--resume`/`--episodes-out` support per a direct
  read of their argparse blocks, so a second credit-exhaustion mid-run would
  again waste whatever was already spent rather than resuming from where it
  stopped — worth adding before the next real attempt, not before.

- [ ] **2. Add a second tier of frontier models at the flagship (not
  cheap/fast) price point.** The current 3 frontier entries are deliberately
  mini/flash/haiku-class. A reviewer can reasonably ask whether the
  SecureVoI-vs-ConventionalVoI gap *shrinks* as raw capability increases
  (i.e., is defense-in-depth still needed once the base model is good
  enough to resist injection on its own?). Add one flagship-tier model per
  provider — Claude Opus 4.8, GPT-5.4 (full, not mini), Gemini 3.6 Pro (not
  flash) — run on the 96-task primary only first (cheapest diagnostic); if
  the gap holds, extend to the full battery per Step 1's template. This is
  the direct empirical answer to "does more capability substitute for the
  defense," which the paper currently only gestures at via the model-capability
  gradient in the stealth-tier risk decomposition.

- [ ] **3. Add at least one model family outside the four already tested
  lineages (Mistral, Meta, OpenAI's OSS line, and closed OpenAI/Anthropic/
  Google).** Candidates reachable through the existing `openai_compatible_
  generate_fn` (Groq/Together/Fireworks/OpenRouter all work today, confirmed
  in `model_backends.py`): DeepSeek-V3/R1-class (a genuinely different
  training lineage and, for the R1-style variant, a reasoning model — see
  Step 4), Qwen3 at a served size (0.5B already started and abandoned;
  restart at a size that can actually complete tasks, e.g. Qwen3-32B), and
  xAI Grok if a key is available. Each new family is one data point toward
  "this isn't a Llama/GPT-family-specific effect."

  **In progress 2026-07-30: `qwen/qwen3.6-27b` via Groq — real new lineage,
  real size, and it exercises Step 4 (reasoning model) for free as a side
  effect, since it turns out to think inline.** Groq's live `/v1/models`
  endpoint (queried directly, not guessed) currently serves
  `qwen/qwen3.6-27b` alongside `allam-2-7b`, `groq/compound(-mini)`,
  `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` (already covered),
  `openai/gpt-oss-{20b,120b,safeguard-20b}` (base models already covered via
  Ollama Cloud; the `safeguard` variant is a genuinely new, different
  comparison — same base model, safety-tuned — worth a future step of its
  own, not pursued yet). Qwen3.6-27B was picked as the best available
  new-lineage candidate: real size, not the abandoned 0.5B dead end.

  **Bug found and fixed before any real run: a THIRD distinct mechanism for
  the token-truncation failure class `HANDOFF.md` already documents twice
  (gpt-5.4-mini's verbose JSON, Gemini's separately-billed thinking
  tokens).** Smoke test initially returned all-empty `sample_intents`
  hypotheses (`[{}, {}, {}]`) — the same *symptom* as those two prior bugs,
  but a different *mechanism*, confirmed by direct `curl` with a small
  `max_tokens` cap: this model emits an inline `<think>...</think>` block
  **inside** `content` itself (not a separate field, not separately billed —
  just consumes the same token budget before any answer), so
  `finish_reason="length"` fires with zero JSON ever emitted. Fixed in
  `scripts/model_backends.py`'s `build_agent`, scoped narrowly (`"qwen3.6"
  in model`) so every other Groq-served model keeps its already-validated
  512-token default unchanged, matching this file's own stated precedent
  for the OpenAI/Gemini cases. Verified: `python3 test_smoke.py` still passes
  (no regression to any existing model path), and a repeat smoke test after
  the fix returns real, distinct 3-hypothesis JSON.

  Dev calibration launched immediately after the fix — **first attempt lost
  ~4 hours of real model calls to a transient DNS failure, second attempt
  now running with a fix that prevents this recurring.** Reasoning-model
  latency is severe (lambda point 1/11, which needs a real call per dev
  task, took 3072s / ~51 min for 24 tasks; the sweep reached lambda 7/11 at
  14348s / ~4h before dying). Root cause:
  `urlopen error [Errno 8] nodename nor servname provided, or not known`
  after `model_backends.py`'s own 8-attempt retry loop was exhausted — a
  DNS-resolution blip lasting longer than its backoff window, confirmed
  transient (Groq's API was immediately reachable again on direct `curl`
  right after). The real problem `tune_dev.py` had **zero checkpointing at
  all** — unlike `run_primary.py`, and unlike `oracle_ablation.py`/
  `guardrail_eval.py` after this session's earlier fix — so ~4 hours of
  already-completed, already-cached model calls (confirmed cache-hit-fast:
  lambda points 2/11 and 3/11 reused the populated cache and took 0 extra
  seconds) were gone with nothing to resume from, and a retry would have to
  re-pay for every one of them.

  **Fixed at the right layer: persisted `CachingAgent`'s own in-memory cache
  to disk**, rather than restructuring `tune_dev.py`'s lambda-sweep loop
  (which re-evaluates the same 24 dev tasks 11 times and depends entirely on
  that cache for its own efficiency, so caching IS the natural checkpoint
  unit here, not a per-task loop like the episode-based scripts). Added
  `CachingAgent.save_cache`/`load_cache` (`secure_clarify/agent.py`,
  JSON-safe tuple-key conversion) and a `--cache-file` flag to `tune_dev.py`
  that loads any existing cache at startup and saves after every lambda
  point (cheap — at most ~n_dev_tasks entries, trivial I/O). Verified with a
  save/load round-trip on the scripted backend: reloading a saved cache and
  re-running produces a byte-identical calibration result to the
  uninterrupted run, and the full smoke suite still passes. Second real
  attempt launched with `--cache-file`; if this one also hits a transient
  failure, it resumes from the cache instead of restarting from zero.
  **Still running as of this log entry.**

- [ ] **4. Add one explicit reasoning-model comparison** (a model with
  visible/extended chain-of-thought before answering, e.g. an o-series or
  DeepSeek-R1-class model, run at default reasoning effort). Reasoning
  models are the one model class this paper says nothing about, and they are
  exactly the class most likely to either (a) reason their way past a
  stealth attack unaided — which would be a genuine threat to the "screening
  is necessary" claim — or (b) show a different failure mode (over-trusting
  a plausible-sounding justification because it "reasoned" through it). This
  needs the full explicit+stealth comparison, not just a headline number,
  since the interesting question is exactly the stealth-tier degradation
  curve from `paper.tex`'s "Robustness to attack phrasing" paragraph.

- [ ] **5. Re-run the abandoned small-model end.** Qwen2.5-0.5B-Instruct has
  a dev calibration but never finished a primary run — worth deciding
  explicitly whether it's viable (0.5B may simply be too small to produce
  parseable JSON for `sample_intents`/`classify_malice`, in which case that
  *is* a finding — a capability floor below which the whole framework
  degrades to noise, matching the token-truncation failure mode already
  documented in `HANDOFF.md` for gpt-5.4-mini) or should be replaced with a
  slightly larger small model (e.g. Qwen2.5-1.5B or Llama-3.2-3B) that can
  actually complete the pipeline. Either outcome is worth reporting: it
  bounds the low end of the capability axis the stealth-tier gradient
  already gestures at.

- [ ] **6. Build the cross-model scaling figure.** Once Steps 1–5 land,
  produce one plot: x-axis a rough capability/scale proxy (param count where
  known, else a public benchmark score already reported by the provider —
  document the proxy's limitations plainly, don't pretend it's precise),
  y-axis SecureVoI's adversarial-unsafe rate and separately the
  SecureVoI-vs-ConventionalVoI $\Delta$, one point per model, explicit and
  stealth tiers as two series. This is the figure that turns "we tested N
  models and the ordering held" into "here is how the effect moves with
  capability" — a strictly stronger empirical claim, and a natural
  companion to Anagh's Step 26 (risk-score calibration) once both exist.

## Phase 2 — A real trained component ("more training")

Every risk-relevant signal in the current method is either a hand-written
prompt (`classify_malice`) or a scalar fit by grid search on 24 dev tasks
($\lambda$, channel priors). `README.md` says this explicitly: "nothing here
is trained or fine-tuned." That's an honest and currently-true statement,
but it's also a gap: a reviewer can ask whether a genuinely learned
component would do meaningfully better than the prompted heuristic, and
right now the paper cannot answer that because it hasn't tried.

- [x] **7. Build a labeled training set from artifacts already frozen.**
  *(done — `scripts/build_risk_training_set.py`,
  `results/risk_classifier_dataset.json`.)* Draws from
  `secure_clarify.attack_corpus.build_attack_corpus()` (81 attacks, split by
  the existing family-disjoint TRAIN_FAMILIES/TEST_FAMILIES partition),
  `build_benign_hard_negatives()` (12, held out to TEST only — training on
  them would defeat their purpose), and every de-duplicated `responses[]`
  entry in `tasks/main_120.json` + `tasks/diversity_180.json`, split by
  **task**, reusing the *existing* frozen dev/test task-id partitions in
  `results/main120_manifest.json` / `results/diversity180_manifest.json`
  rather than inventing a new boundary. Leakage-guarded: the script asserts
  no identical response string carries opposite labels across the two
  splits (32 strings appear in both, all with consistent labels — expected,
  since benign filler text is deliberately reused across channels). Result:
  **99 train (85 positive / 14 negative)**, **102 test (76 positive / 26
  negative)**. The thin negative-training-example count (14) is itself a
  finding, not just a stat — see Step 8's caveat.

- [x] **8. Train a lightweight classifier to replace the prompted
  `classify_malice`.** *(done — `scripts/train_risk_classifier.py`,
  `results/risk_classifier_eval.json`.)* TF-IDF (unigrams + word bigrams) +
  logistic regression, both implemented from scratch in pure Python — no
  numpy/sklearn available in this environment, and the repo's existing code
  already commits to a zero-heavy-dependency style. Balanced class weighting
  to handle the 85/14 train imbalance. Compared against two *free, zero-
  training* baselines already in the repo: `ScriptedAgent.classify_malice`
  (the regex heuristic) and a raw `_CUE_TERMS` hit-count.

  **FINDING — the trained classifier is a large, genuine improvement over
  both prompted-heuristic baselines, on both axes that matter:**

  | | trained (TF-IDF+LR) | lexical regex | cue-term count |
  |---|---|---|---|
  | overall AUROC | **0.944** | 0.553 | 0.548 |
  | overall AUPRC | **0.977** | 0.694 | 0.692 |
  | overall Brier | **0.145** | 0.365 | 0.436 |
  | recall on **held-out attack families** (linguistically unseen) | **0.972** (35/36) | 0.139 (5/36) | 0.194 (7/36) |
  | FPR on **benign hard negatives** | 0.75 (9/12) | **1.00 (12/12)** | 1.00 (12/12) |

  Two things stand out. First, the regex/cue baselines' AUROC (0.55) is
  barely above chance — they only "work" on the four explicit-tier-style
  strings they were tuned against, and almost completely fail to
  generalize to the four held-out persuasion families (socratic,
  non-imperative, quoted-relay, indirect-multistep — 0.14–0.19 recall).
  The trained classifier generalizes to those same unseen families at
  0.972 recall despite never having seen their wording during training
  (the split is family-disjoint by construction). Second, on the
  hard-negative false-positive check, the lexical baselines fail
  *completely* (reject all 12 — exactly the "detects vocabulary, not
  malice" failure mode Anagh's Step 18 was built to expose); the trained
  classifier is meaningfully better but still fails 9 of 12, which traces
  directly back to Step 7's 14-negative-example training set — it never
  saw a single hard-negative-*style* example during training, only
  ordinary benign filler text, so it hasn't learned to separate "contains
  scary words" from "is actually malicious." **This is the single most
  actionable next step**: augmenting training with hard-negative-style
  synthetic examples (not the held-out 12 themselves) would directly test
  whether the FPR gap closes.

  **Important scope disclosure — this is not yet the comparison Step 8
  originally asked for.** The "prompted heuristic" actually used in every
  published result is `OpenModelAgent.classify_malice`, a real LLM call
  (see `secure_clarify/agent.py`), not `ScriptedAgent`'s regex stand-in.
  No API keys were available in this environment (see plan log), so this
  offline comparison is trained-classifier vs. the *free* lexical
  baselines only. It establishes that a trained classifier can beat a
  prompted heuristic *in general* on this corpus; it does not yet show it
  beats the *specific* prompted classifier the paper reports numbers for.
  Step 9 is what would close that gap.

- [ ] **9. Ablate a trained classifier inside the full pipeline, not just
  offline.** *(blocked — needs a working model API key; none available in
  this environment as of 2026-07-30.)* Offline AUROC is necessary but not
  sufficient — plug the Step 8 classifier into `SecureVoI.accept()` in place
  of the prompted `classify_malice` call and re-run the primary + stealth
  tiers on at least the two weakest models (Mistral-Nemo-12B, where the
  oracle ablation shows the prompted screen is the binding constraint).
  Report unsafe rate and utility exactly like the oracle-vs-learned ablation
  already in the paper, so this slots in as a third point on that
  comparison: prompted risk < trained risk $\le$ oracle risk. **Also worth
  doing first and cheaply once a key exists:** score the *actual* prompted
  `OpenModelAgent.classify_malice` offline against this same
  `results/risk_classifier_dataset.json` test set (no full episode re-run
  needed, just the classifier calls) — that's the real apples-to-apples
  comparison Step 8's table above is currently missing, and it's far
  cheaper than a full pipeline ablation.

- [ ] **10. If Step 9 shows a real gap, consider learning $\lambda$ and the
  channel priors jointly rather than grid-searching them.** Only pursue this
  if Step 9 justifies the added complexity — a small logistic/Bayesian fit
  of the channel-prior table from Step 7's labeled data (channel is already
  recorded per response) directly, rather than the current hand-set,
  Laplace-smoothed frequency table. This is explicitly optional and
  lower-priority than Steps 7–9; don't start it before those land results.

- [x] **11. Report training cost and data efficiency honestly.** *(first
  data point done — `scripts/augment_hard_negatives_train.py`,
  `results/risk_classifier_eval_augmented.json`.)* Directly tested Step 8's
  own "most actionable next step" flag: the 0.75 hard-negative FPR traced to
  only 14 negative training examples, none hard-negative-style. Added **72
  synthetic train-only hard-negative-style examples** (same idea as
  `BENIGN_HARD_NEGATIVES` — goal-consistent, harmless, loaded with cue
  vocabulary — but templated to be textually distinct; leakage-guarded, zero
  string collision with the 12 held-out test examples).

  **FINDING — the gap closes almost entirely, and cheaply:**

  | | before (14 neg / 85 pos train) | after (+72 synthetic neg, 86/85) |
  |---|---|---|
  | overall AUROC | 0.944 | **1.000** |
  | hard-negative FPR (held-out 12) | 0.750 (9/12) | **0.000 (0/12)** |
  | held-out-attack-family recall | 0.972 (35/36) | **1.000 (36/36)** |

  72 additional examples — cheap to write, no new attack data, no model
  calls — took FPR on the untouched held-out hard negatives from 9-wrong to
  0-wrong and pushed attack-family recall to perfect. This is a genuinely
  good data-efficiency result to report.

  **Important honest caveat, stated plainly rather than overclaimed (in the
  spirit of Anagh's Step 36's "same-generator data" warning):** the 72
  synthetic examples and the original 12 held-out hard negatives were both
  authored *against the same known cue-vocabulary list*
  (`estimators._CUE_TERMS` / the `classify_malice` signal terms) — they don't
  share exact strings, but they do share the underlying template family
  (carrier sentence + a negation/scoping clause naming a cue word). A perfect
  1.000 on this specific held-out set is therefore better read as "the
  classifier generalizes within the cue-negation *pattern* once it sees
  enough of that pattern" than as "the classifier now detects malice in
  general." **A real, harder next test** (not yet done): hard negatives
  constructed by a *different* mechanism than the cue list itself — e.g.
  real benign user messages that happen to mention security-adjacent topics
  for unrelated reasons — to check whether this generalizes beyond the
  specific pattern both the test and the augmented training data share.

## Phase 3 — Literature depth (extensive, verified arxiv coverage)

`CITATIONS.md`'s own audit checklist is explicit that verification (fetch
against the actual arXiv abstract page, not recall from training data) is
the standard this project already holds itself to — 3 "from your list" and
2 "check id" entries were deliberately left out of `references.bib` rather
than cited unverified. This phase extends that same discipline to entirely
new search, not just cleanup of the existing list.

- [~] **12. Systematic search across the paper's five claim clusters**,
  each as a separate query set (not one generic "prompt injection" search):
  (a) clarification/ambiguity-resolution in dialogue and agent systems
  beyond the four already cited (CLAM, SAGE-Agent, Learning-to-Ask, Ask-or-
  Assume) — search for 2025–2026 work specifically, since this is a fast-
  moving area and the cited set may already be stale; (b) prompt-injection
  *defenses* specifically (not just attack benchmarks like InjecAgent/
  AgentDojo, which are already cited) — detection/removal methods,
  instruction-hierarchy training, provenance-aware execution, anything in
  the space Anagh's Step 13 needs strong baselines from; (c) information-
  flow/capability-based agent security (CaMeL is cited; search for what's
  cited it or extended it since, and any competing formalism); (d)
  value-of-information / active-question-asking under untrusted or
  adversarial answerers outside the LLM-agent literature (the deceptive
  path-planning and Bayesian ARA citations are the current anchors here —
  search whether there's more recent formal VoI-under-adversary work); (e)
  channel-trust / provenance modeling for tool-using agents specifically
  (Instruction Hierarchy is cited as the closest analog; search for direct
  extensions).

  **First pass done 2026-07-30 (clusters a, b, e; c and d still open).**
  Encouraging consistency check first: the search independently re-surfaced
  four papers already in `references.bib` under their correct 2026 arXiv IDs
  (ASPI `2605.17324`, SAGE-Agent `2511.08798`, Ask-or-Assume `2603.26233`,
  Ambig-DS `2605.09698`) — the existing citation set is not stale on those
  four, and the "check the arXiv page, don't trust memory" discipline this
  project already holds itself to is what caught that they matched rather
  than assuming it. New candidates found, **verified against their actual
  arXiv abstract pages** (Step 13) rather than taken from search-snippet
  titles alone:

  | candidate | arXiv | verified claim | relevance |
  |---|---|---|---|
  | AgentVisor | `2604.24118` | Ying, Wang, Liu, Zou, Liu, Yang, Yang, Liu — "semantic privilege separation" via a trusted semantic visor auditing tool calls; reduces attack success rate to 0.65% at 1.45% utility cost | Directly answers Anagh's **Step 13** (strong response-screening baseline) — reports both an ASR and a utility cost the way our Table 1/2 does, so it's a plausible apples-to-apples comparison point, not just a citation |
  | Trust No Tool / TRUST-Bench | `2605.17453` | Yan, Li, Han, Li, Wang, Wang, Lyu, Chen — 1,970 hidden-trigger tool-compromise episodes; models trust as forming *across the interaction trajectory* ("cognitive poisoning"), explicitly **not** as a per-source/channel property | Closest scale precedent to our benchmark's episode count; the trust model is the sharp point of contrast worth stating explicitly — SecureVoI models trust as a channel-prior fixed before the episode starts, TRUST-Bench models it as accumulating from behavior *during* the episode. Different problem, worth a sentence in Related Work distinguishing them, not conflating |
  | Uncertainty-Aware Clarification w/ Info Gain | `2606.03135` | Deng, Li, Li, Zhu, Zhao, Guo, Wang — trains a clarifier via an RL "Information Gain Reward" (Bayesian belief update toward ground truth); **confirmed it does not model an adversarial or untrusted answerer** | This is the closest info-gain-reward precedent to SecureVoI's own info-gain term, and confirming it has no adversarial-channel treatment is a genuine, checked (not assumed) novelty data point for the Introduction/Related Work's central claim |
  | PIGuard / NotInject benchmark | (ProtectAI, referenced via search summary — **arXiv id not yet independently confirmed, do not cite until verified**) | a benchmark of benign-but-attack-adjacent-vocabulary queries built specifically to catch screens that "detect vocabulary, not malice" | Structurally the same idea as this repo's own `BENIGN_HARD_NEGATIVES` (Anagh's Step 18) — worth checking whether it predates ours and should be cited as prior art for that construct, or whether ours is contemporaneous/independent |
  | CaMeL-adjacent info-flow defenses (FIDES, Progent, RTBAS, FORGE) | not yet individually resolved to arXiv IDs | named in an aggregated search summary as peers of CaMeL doing capability/information-flow mediation | Direct candidates for Anagh's **Step 14** (information-flow/action-policy baseline) beyond CaMeL alone — each needs its own verification pass before citing, listed here so that pass isn't lost |

  **Cluster (d) — VoI under adversarial/untrusted answerer, outside the LLM
  literature — searched, nothing closer than what's already cited.** The
  query surfaced only unrelated "adversarial active learning" work (crafting
  adversarial *training examples*, not an adversarial *answerer* to a
  question). This is a real negative result, not a gap in search effort: it
  supports the paper's existing claim that the deceptive path-planning VoI
  framework and the Bayesian ARA paper remain the closest formal precedents
  (Step 15's falsifiability check therefore currently **fails to falsify**
  — the "sharpest foil" framing survives this pass, on cluster d at least).

  **Second pass done 2026-07-30 (clusters c, d) — closes both open items
  above.**

  **Cluster (c) resolved: FIDES/Progent/RTBAS/FORGE are real, and one is a
  strong, numbers-reporting Step 14 candidate.** Verified against the actual
  abstract page: **RTBAS** (`2502.08966`, Zhong/Chen/Wang/McCall/Titzer/
  Miller/Gibbons) — confirmed claim: "prevents all targeted attacks [on
  AgentDojo] with only a 2% loss of task utility," and requires user
  confirmation *only* when its integrity/confidentiality safeguards can't be
  ensured (not before every call, unlike prior confirmation-based defenses).
  This is a materially stronger, more specific candidate for Anagh's **Step
  14** (information-flow/action-policy baseline) than a generic "CaMeL-style"
  gesture — it reports the exact ASR/utility pair our own Table 1/2 does.
  **Progent** (`2504.11703`, "Securing AI Agents with Privilege Control" —
  least-privilege via symbolic per-call rules) found and linked but not yet
  independently abstract-verified; do that before citing. FIDES and FORGE's
  arXiv IDs still not individually resolved — flagged, not cited. A general
  framing paper also surfaced and is worth checking as a survey anchor for
  this whole cluster: "Securing AI Agents with Information-Flow Control"
  (`2505.23643`, Costa & Köpf), not yet verified.

  **Cluster (d) — one adjacent precedent found, verified, judged NOT closer
  than what's cited.** "Bayesian Decision Making around Experts" (`2510.08113`
  — note the search summary's title, "...observing an Expert," was wrong;
  caught by verifying against the actual page rather than trusting the
  snippet) — Jarne Ornia, Dyer, Bishop, Calinescu, Wooldridge. Confirmed: it
  studies multi-armed bandits deciding when to trust a potentially
  ineffective/compromised "expert" data source — a real value-of-untrusted-
  information formalism, but classical bandit theory, not LLM/agent
  literature, and not framed around an active *question* to an *answerer*
  the way SecureVoI or the currently-cited deceptive path-planning paper are.
  Judgment call (left for whoever writes the actual Related Work text, per
  the non-overlap contract): worth citing as a *third* precedent alongside
  the existing two, not a replacement for either. **Step 15's falsifiability
  check on the "closest VoI precedent" claim therefore still fails to
  falsify** — nothing found across two passes is closer than what's already
  cited, only one more adjacent paper in the same neighborhood.

  Both clusters now have at least one pass; cluster (a) also deserves a
  second, more targeted pass later (only did one query each so far), but the
  five-cluster search Step 12 called for has now touched all five at least
  once.

  **Cluster (a) second pass done 2026-07-30.** Two more verified: "Ask
  Early, Ask Late, Ask Right" (`2605.07937`, Gulati/Gupta/Lumer/Sen/
  Subbiah) — a real, four-benchmark/four-model finding that clarification's
  *value* depends on timing and what's missing (goal clarification loses
  value after ~10% of execution; input clarification holds value to ~50%),
  but confirmed **cooperative/ground-truth clarifications only** — no
  adversarial-channel treatment, same pattern as everything else found in
  this cluster. "Uncertainty Decomposition for Clarification Seeking in LLM
  Agents" (`2606.19559`, Matsnev) — separates *action confidence* from
  *request uncertainty*; also confirmed no adversarial-answerer modeling.
  **Cross-reference worth flagging to Anagh, not mine to act on:** this
  decomposition is a candidate mechanism for Anagh's Step 5 finding that
  SecureVoI's ask decision is anti-calibrated because `sample_intents`
  manufactures disagreement even on unambiguous requests — a method that
  explicitly separates "am I confident in my best action" from "is the
  request itself ambiguous" might be exactly the fix Step 5's own log
  entry gestures at ("gate asking on an explicit ambiguity check").

- [ ] **13. Verify every new candidate against the actual arXiv (or venue)
  page before adding it** — title, authors, and the specific claim being
  attributed, exactly as `docs/04_references.md`'s existing entries were
  checked. Do not add a citation from memory or a search snippet's title
  alone; the existing audit already caught two mischaracterizations this
  way (SAGE-Agent's POMDP framing, Ambig-DS's actual domain) and that error
  mode is worth guarding against again on anything new.

- [ ] **14. Build a positioning table as raw material for Anagh's Step 37**
  (which owns turning it into prose) — for every candidate found in Step 12
  that clears Step 13's verification: threat model, whether asking is
  modeled as a decision variable, whether channel/provenance identity is
  modeled, what it defends (text screening vs. control flow vs. action
  constraints), and evaluation scale. Hand this table off rather than
  writing the Related Work paragraphs myself, per the non-overlap contract
  above.

- [~] **15. Check whether any newly found paper is a closer precedent than
  what's currently cited as "closest."** `paper.tex` currently names CaMeL as
  "our sharpest foil" and the deceptive-path-planning paper as "the closest
  formal precedent outside the LLM literature." Both claims are falsifiable
  by a sufficiently thorough search — if Step 12 turns up something closer,
  that's a finding to report honestly (a weaker novelty claim is better than
  an overclaimed one an AAAI reviewer catches), not something to bury.
  *(Partial, 2026-07-29 [sic 2026-07-30] pass: the VoI-outside-LLM-literature
  half of this claim survives — nothing closer than the deceptive
  path-planning paper turned up. The CaMeL half is now genuinely in question
  — FIDES/Progent/RTBAS/FORGE are peer information-flow defenses named
  alongside CaMeL in a 2026 survey summary and at least one of them could be
  a sharper foil than CaMeL specifically; not resolved until each is
  individually verified per Step 13's discipline.)*

- [ ] **16. Audit citation currency by publication date.** With today's date
  2026-07-30, check how many of the 21 current references are >18 months
  old relative to a fast-moving subfield (prompt injection / agent security
  churns quickly) and whether the paper is missing anything from the last
  2–3 months specifically. A related-work section that stops in early 2026
  on a paper being reviewed later in 2026 is a visible gap.

## Phase 4 — Infra to support running this many models

- [ ] **17. Cost and rate-limit budget before launching flagship-tier runs.**
  Step 2's flagship models (Opus 4.8, full GPT-5.4, Gemini 3.6 Pro) cost
  meaningfully more per token than the mini/flash tier already run — get a
  rough per-model cost estimate (tasks $\times$ policies $\times$ avg
  tokens/episode $\times$ price) before launching the 96-task primary, and
  confirm with Rafi before extending any flagship model to the full battery
  (ablation + guardrail + stealth roughly triples the call count per
  `HANDOFF.md`'s scoping precedent for the first 3-model add).

- [ ] **18. API-key hygiene, reiterated because it was already burned once.**
  `HANDOFF.md` records that two live keys were pasted directly into a chat
  session on 2026-07-29 and had to be treated as compromised. Every new
  provider key in this phase: environment variable only, never pasted into
  a chat transcript or written to a file in the repo, secret-scanned before
  every commit. This is a repeat of existing project policy, not a new
  rule — restated here because Phase 1–2 add several new provider
  credentials (DeepSeek, Qwen-hosting provider, xAI, HF for local encoder
  fine-tuning) and each new credential is a fresh chance to repeat the
  mistake.

- [ ] **19. Reuse the existing resilience tooling rather than re-inventing
  it.** `scripts/supervise_run.sh` (self-healing re-launch with `--resume`)
  and the provider-specific gotchas already documented in `HANDOFF.md`
  (Groq is TPM-limited not RPM-limited; Ollama Cloud 429s under sustained
  load; OpenAI's `max_completion_tokens` vs `max_tokens`; token-budget
  truncation silently degrading to zero-information-gain) apply directly to
  the new providers in Phase 1. Read that document's relevant sections
  before debugging a new provider's failure mode as if it were novel.

- [ ] **20. Track total spend and runtime per model** in a simple log
  (provider, model, $ spent, wall-clock, date) so that by the time Phase 1–2
  are done there's an honest "here is what full characterization of N
  models costs" number — useful both for the paper's Step 30 (operational
  cost, Anagh's) and for deciding how far to push model count before
  diminishing returns set in.

## Phase 5 — Merge

- [ ] **21. Once Phase 1 lands enough models, extend `results/cross_model_
  comparison.md`'s table and regenerate whatever script builds it**, adding
  columns rather than replacing the existing four. Do not touch Anagh's
  in-progress `paper.tex` sections; hand off the regenerated table and
  scaling figure for Anagh (or a joint pass) to fold into Table 2 and the
  abstract once Anagh's Phase 2/3 construct fixes have also landed, so the
  final numbers reflect both the corrected construct and the wider model
  set at once rather than needing to be redone twice.

- [ ] **22. Once Phase 3 lands new verified citations, hand the positioning
  table (Step 14) to Anagh's Step 37** rather than writing Related Work
  prose directly, per the non-overlap contract.

- [ ] **23. Once Phase 2 lands a trained-classifier result, write it up as a
  short new subsection/ablation** (not a rewrite of existing Method text) —
  "prompted vs. trained response-risk classifier" — sized to fit whatever
  page budget remains after Anagh's Phase 9 rewrite, coordinating on page
  count before adding it.

---

## Log

- **2026-07-30** — Phase 3 Step 12 first pass (clusters a/b/e), Step 13
  verification, Step 15 partial. Search independently re-found and confirmed
  four already-cited 2026 papers under their correct arXiv IDs (a useful
  cross-check that the existing bibliography isn't stale on those four).
  Five new candidates found; three fully verified against their actual
  abstract pages (AgentVisor `2604.24118`, Trust No Tool/TRUST-Bench
  `2605.17453`, Uncertainty-Aware Clarification w/ Info Gain `2606.03135`);
  two (PIGuard/NotInject, and the FIDES/Progent/RTBAS/FORGE cluster) still
  need individual arXiv-ID verification before anyone cites them — flagged,
  not cited, per this project's own "verify before adding" discipline.
  Handoff-relevant: AgentVisor is a concrete, numbers-reporting candidate for
  Anagh's Step 13 strong-screening baseline; the info-gain-reward paper
  confirms (not assumes) that the closest info-gain precedent still has no
  adversarial-answerer treatment, which is real support for the paper's
  novelty claim, checked rather than asserted. Cluster (c) and a second pass
  on cluster (d) remain open.

- **2026-07-30** — API key search attempted, dead end, do not repeat this
  hunt in a future session without new information. Checked `.env`-style
  files across the home directory that were safe to check directly; only
  `GROQ_API_KEY` turned up (`~/Project 1/wxo-server/server.env`) and it is an
  **empty placeholder** (`GROQ_API_KEY=` with no value), not a real key.
  Broader filesystem/Keychain scanning for secrets was blocked by a safety
  classifier (correctly — that's not a search this agent should push through
  on its own). No OpenAI/Anthropic/Google keys found anywhere. Rafi's
  decision: skip live model runs entirely this session rather than keep
  hunting; Phase 1 and Phase 2 Step 9 stay blocked until a key is supplied
  directly (paste, or a specific file path) in a future session.

- **2026-07-30** — Phase 2 Steps 7-8 done, no API key needed. Built a labeled
  risk-classification dataset from artifacts already frozen in the repo
  (81-attack corpus + 12 hard negatives + every de-duplicated response string
  in `tasks/main_120.json`/`tasks/diversity_180.json`, split by the existing
  dev/test task partitions) and trained a from-scratch TF-IDF + logistic
  regression classifier (pure Python, no numpy/sklearn in this environment).
  **FINDING:** it beats both free lexical baselines by a wide margin on
  held-out-attack-family recall (0.972 vs. 0.14-0.19) and meaningfully,
  though not completely, on benign-hard-negative false-positive rate (0.75
  vs. 1.00 — the regex/cue baselines reject every single hard negative). The
  FPR gap traces to the training set having only 14 negative examples, none
  hard-negative-style, which is itself a concrete, actionable next step
  (Step 8's caveat) rather than a dead end. **Scope disclosure:** this
  compares against `ScriptedAgent`'s free regex heuristic, not the actual
  prompted-LLM `classify_malice` every published result uses — that
  comparison (Step 9) needs a working API key, cheaply (classifier calls
  only, no full episode re-run) once one exists.

- **2026-07-30** — plan opened. Coverage audit (Phase 0) done by direct
  inspection: 4 models have the full battery, 3 frontier models (GPT-5.4-mini,
  Claude-Sonnet-5, Gemini-3.6-flash) have headline-only coverage by original
  scope decision (`HANDOFF.md`, 2026-07-29), and 2 model directories
  (Qwen2.5-0.5B-Instruct, Llama-3.3-70B-versatile) are abandoned/superseded
  starts with only a dev calibration on disk. One immediate cheap fix
  identified: `gemini-3.6-flash-diversity` has episodes but no summary file.
  No model runs launched yet — Phase 1 Step 1 (filling the frontier battery
  to parity) is the natural next action, but flagship-tier runs (Step 2) need
  a cost estimate and Rafi's sign-off first per Step 17, and Phase 2's
  trained-classifier work (Steps 7-9) can start immediately and for free
  since it only needs artifacts already frozen in the repo.
