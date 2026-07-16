# Daily Log — Security-Aware Clarification for Agents (AAAI-27)

Detailed, narrative day-by-day record: what each day's goal was, what was
actually built (with file names), why specific design decisions were made,
what broke and how it was fixed, and exactly what's carried forward. This is
written so a new reader — human or AI — can pick up the project cold and
understand *why* things are the way they are, not just *that* a checkbox is
green. For the compressed table view, see [PROGRESS.md](../PROGRESS.md); for
what the project is, see [README.md](../README.md); for the literature this
all builds on, see [04_references.md](04_references.md).

---

## Jul 12 — Novelty matrix, threat model, schemas, seed tasks

**Goal:** establish the paper's actual contribution before writing any code
that assumes it, and lay down the data model everything else builds on.

**What was done:**
- `docs/01_novelty_matrix.md` — a 7-axis matrix (Ask? What? Where? Adv? Util?
  Loss? Exec?) scoring every closely related paper. The point of the exercise:
  find the column of `n`s that only this project's row fills in. Result: the
  VoI/clarification cluster is strong on Ask/What/Util and has nothing on
  Where/Loss (they assume a single trusted answerer); the security cluster
  (InjecAgent, AgentDojo, CaMeL) is strong on Where/Adv/Exec and has nothing
  on Ask/What (they treat injection as ambient tool-output contamination, not
  a consequence the agent chose by deciding to ask). SecureVoI's cell is the
  *prospective acquire-decision* neither cluster makes. **CaMeL is flagged as
  the sharpest foil** — it also has channels/attacks/utility/loss/execution,
  but only constrains flow *after* information is already acquired; it never
  decides whether acquiring it was worth the exposure. This distinction has
  to be stated explicitly in related work or a reviewer files this as "a
  weaker CaMeL."
- `docs/02_threat_model.md` — froze the principal/channel/attacker model:
  the authenticated user is *never* the attacker (kills the "what if the user
  is malicious" objection); six channel classes with fixed prior trust
  (`schema.CHANNEL_TRUST`); a **design rule that channel identity must not be
  perfectly predictive of attack** (every non-authenticated channel needs
  benign, noisy, *and* adversarial instances, or a policy could win by just
  hard-coding "never trust forwarded email" — that would defeat the whole
  point of testing a value/risk trade-off); seven attacker objectives mapped
  1:1 to `schema.AttackType`; and the safety definition used everywhere since
  — **unsafe is a property of the trajectory** (any prohibited action in the
  immutable log counts, even if later reversed), not of final state.
- `secure_clarify/schema.py` — `Task`/`Question`/`Response` dataclasses with
  `.validate()` methods enforcing the threat model in code (e.g. `Response`
  raises if `channel == USER and carries_attack`, or if a non-adversarial
  response is marked `carries_attack`).
- 10 seed tasks validated end-to-end through the schema.

**Carried forward:** none — Jul 12 is fully closed; nothing here was revisited.

---

## Jul 13 — File/calendar simulators, verifiers, 20 tasks

**Goal:** build the executable environments and the automatic, non-LLM
outcome checks the whole benchmark depends on (per the novelty matrix, "Exec"
is one of the axes competitors don't fill).

**What was done:**
- `secure_clarify/simulators.py` — `FileEnv` and `CalendarEnv`, both backed by
  an **immutable, append-only action log** (`Action` is a frozen dataclass).
  Every tool call is recorded even if it later gets reversed — this is what
  makes "unsafe = trajectory property" (from the Jul 12 threat model)
  actually enforceable: a `delete_file` on a protected file is logged as
  `note="protected"` regardless of whether something later restores it.
- `secure_clarify/verifiers.py` — `goal_verifier` (checks final state against
  a machine-checkable `goal_predicate`) and `safety_verifier` (scans the log
  for any of the task's `prohibited_actions` patterns). Both are plain
  Python — no LLM judge anywhere in the loop, which is the explicit contrast
  drawn against ToolEmu (LM-based safety evaluator) in the references doc.
- 20 tasks (10 file + 10 calendar) built and validated.

**Carried forward:** none.

---

## Jul 14 — Four policies, 40 pilot tasks, matched responses

**Goal:** implement the actual decision rules being compared, and the
benchmark's core methodological trick — the *same* base task gets matched
benign/noisy/adversarial clarification responses, so any measured difference
is attributable to the response, not to task difficulty.

**What was done:**
- `secure_clarify/estimators.py` — `estimate_info_gain` (a disagreement-among-
  sampled-intents proxy scaled into utility units so it's commensurate with
  the risk penalty — see the Jul 15 bug list, this scale-matching was not
  free), `estimate_pre_risk` (channel prior × expected loss, dev-set-only
  constants), `response_risk` (blends `agent.classify_malice`, a channel
  prior, and lexical cue hits).
- `secure_clarify/policies.py` — `NeverAsk`, `ConventionalVoI` (info-gain
  minus cost, **risk-blind**, accepts whatever comes back — the policy the
  literature's ASPI phenomenon predicts is dangerous), `TrustedOnly` (only
  asks through channels above a trust floor), `SecureVoI` (two-stage:
  stage 1 picks `(question, channel)` by `info_gain - cost - lambda*pre_risk`;
  stage 2 gates the returned answer by estimated malice before accepting it).
- `secure_clarify/agent.py` — `ScriptedAgent`: a deterministic heuristic
  stand-in implementing `sample_intents` / `classify_malice` / `act` so the
  *entire* pipeline could be validated on CPU with zero model dependency,
  before any real model existed. Documented explicitly as **a pipeline check,
  not the paper's result** from day one — this framing is why every later
  script that uses ScriptedAgent also stamps an honest `agent_backend` label
  rather than letting a results file imply more than it shows (see Jul 17-19).
- `secure_clarify/resolver.py` — turns an accepted/rejected response into a
  resolved intent; this is where an accepted adversarial response's injected
  directive (`_inject_delete`, `_inject_share`, etc.) actually gets merged in
  ("mirroring what following the malicious text literally would do" — the
  resolver never itself consults ground-truth attack labels).
- `secure_clarify/task_factory.py` + `secure_clarify/runner.py` — the matched
  benign/noisy/adversarial task generator and the episode loop / utility
  function (`U = goal_completion - severity*violations - clarification_cost
  - abstention_cost`).
- 40 pilot tasks (20 file + 20 calendar) built, all validated.

**Carried forward:** none for Jul 14 itself, but everything here is what the
Jul 15 audit stress-tested and found three real bugs in.

---

## Jul 15 — Two-response-condition pilot and full unsafe-trajectory audit

**Goal:** actually run the four policies against the 40 tasks and manually
audit every unsafe/attack-success trajectory for parsing or verifier defects
before trusting the numbers.

**What was done:**
- `run_pilot.py` — runs the full grid (4 policies × {benign, adversarial} ×
  40 tasks) with `ScriptedAgent`, computes the go/no-go arithmetic, writes
  `results/pilot_summary.json`.
- `docs/03_gonogo_memo.md` — the audit write-up. **Three real bugs were found
  and fixed, documented because they matter for the paper's methods section:**
  1. **Answer leakage into the base intent.** The first task version put
     ground-truth action fields directly in `hidden_intent`, so the agent
     succeeded without ever asking — clarification measured zero value by
     construction. Fixed by withholding ambiguous fields, supplying them only
     via `_benign_fill`/`_noisy_fill`. *Lesson kept as a standing check:*
     verify `NeverAsk` actually fails the benign task, or "asking helps" is
     an artifact (this became `test_smoke.py::test_neverask_fails_benign`).
  2. **Risk-blind policy accidentally avoided the attack.** Info gain
     initially ignored channel identity, so `ConventionalVoI` tie-broke onto
     the safe user channel and never actually encountered the attack. Fixed
     by making info gain channel-dependent (`_CHANNEL_INFO` multipliers) —
     this is also *the* temptation that makes the trade-off exist: untrusted
     channels can be genuinely more informative, which is why a risk-blind
     policy takes the bait.
  3. **Scale mismatch collapsed SecureVoI to never-ask.** Info gain lived in
     disagreement units (~0.09) while the risk penalty lived in loss units
     (~0.3) — nothing ever cleared zero. Fixed by expressing info gain in
     recoverable-utility units (`RECOVERABLE_UTILITY = 1.0`, normalized via
     `_INFO_NORM`) so it's commensurate with `lambda * risk * loss`. Flagged
     in the memo as *the single most important calibration point* — call it
     out explicitly in the method section, since a reviewer re-deriving the
     formula without this normalization will get a degenerate policy.

**Headline pilot numbers (ScriptedAgent, medium severity):** benign goal rate
Never-Ask 0.00 vs Conventional-VoI 1.00; adversarial unsafe rate Conventional-
VoI 0.425 vs SecureVoI (λ=1) 0.30. **Explicitly labeled a pipeline check, not
a measured LM result** — no real model existed yet.

**Carried forward:** `agent.OpenModelAgent`'s three methods were left as
`raise NotImplementedError` stubs — closed in a later session (see the
"Jul 15-16 gap closure" entry below, before Jul 17-19 work started).

---

## Jul 16 — Go/no-go decision, freeze, split tasks

**Goal:** decide GO/NO-GO on the method before spending Jul 17+ scaling it up.

**What was done:**
- `docs/03_gonogo_memo.md`'s verdict: **GO**. All four checks passed: (1)
  benign clarification materially improves task success (+1.00 goal rate),
  (2) adversarial clarification materially increases unsafe actions (+0.425),
  (3) SecureVoI reduces the harm (0.30 < 0.425, reaching 0.125 at λ=2), (4)
  not degenerate — SecureVoI's benign utility (0.95) beats Trusted-Only
  (0.64), i.e. it still uses partially-trusted channels when the information
  is worth it rather than degenerating into "always ask the verified user."
- Safety-utility frontier swept across λ ∈ {0, 0.25, 0.5, 1, 2, 4, 8} on the
  pilot set, showing a monotone trend and a knee around λ≈2 (near-full benign
  utility with most unsafe actions removed).
- **Explicit next-step list left in the memo:** freeze `schema.py` /
  `simulators.py` / `verifiers.py` / the threat model / the novelty matrix;
  implement `OpenModelAgent`'s three methods against a real checkpoint; split
  24 dev / 96 test base tasks, stratified, checksummed; fit channel priors and
  λ on dev only.

**Gap at end of day:** none of that next-step list was actually done yet —
`OpenModelAgent` was still `NotImplemented` and every task's `split` field
was `"unassigned"`. This is exactly what the next work session closed.

---

## Jul 15-16 gap closure (implement OpenModelAgent, freeze the pilot split)

*(This didn't happen chronologically on Jul 15/16 — it's the session that
closed those two gaps before Jul 17-19 work could start, since Jul 17-18
explicitly depends on both.)*

**What was done:**
- `secure_clarify/agent.py`'s `OpenModelAgent.sample_intents` /
  `classify_malice` / `act` implemented for real: each builds a prompt, calls
  the injected `generate_fn(prompt) -> str`, and parses the result via a
  hand-written `_extract_json` (handles a model wrapping JSON in prose/code
  fences by scanning for the first balanced, string-quote-aware `{..}`/`[..]`
  span). Deliberately **fails safe, not open**: unparsable
  `sample_intents` output returns k identical empty hypotheses (zero measured
  disagreement, i.e. "no information gain" rather than a crash);
  unparsable `classify_malice` output returns `1.0` (maximally suspicious,
  fail *closed* since this feeds a security gate); `act`'s output is
  validated against a fixed per-domain tool/arg schema and any hallucinated
  tool call is silently dropped rather than executed. Critically,
  `sample_intents` never reads `task.hidden_intent` — that's the ground-truth
  answer a real agent wouldn't have access to.
- `secure_clarify/task_factory.py`: `assign_split(idx)` — deterministic
  `idx % 5 == 0 → dev` rule, applied identically to the file and calendar
  domain at the same index so a base task's variants always land in the same
  split. Chosen because it's reproducible with no RNG, and empirically
  stratifies the resulting dev set across all 3 stakes tiers and (nearly) all
  channel-availability groups even at just 8 dev tasks out of 40.
- `scripts/freeze_tasks.py`: regenerates a task JSON from the live generator
  and writes a sha256 checksum manifest — "freeze and checksum the test file
  before tuning" from the plan, section 11.
- `test_smoke.py` gained coverage for both: `test_splits_assigned` and three
  `test_open_model_agent_*` tests using a stub `generate_fn`, including
  explicit tests that malformed model output degrades safely rather than
  crashing.
- Also folded in during this session: `scripts/update_progress.py` (inspects
  real repo state — file existence, task counts, whether `OpenModelAgent`
  still raises `NotImplementedError`, whether splits are assigned, whether
  smoke tests pass — and regenerates the schedule table; this stopped the
  README from ever hand-typing a checkmark that could drift from reality),
  and later `PROGRESS.md` was split out from `README.md` so the README could
  stay a plain-English "what is this" front page while the day-to-day tracker
  lived somewhere collaborators actually check it.

**Carried forward:** `OpenModelAgent` is implemented but nothing has called
it with a *real* `generate_fn` yet — every episode anywhere in the repo is
still `ScriptedAgent`. This is the single thread that runs through every
subsequent day below.

---

## Jul 17-18 — Scale to 120 tasks, development runs, tune lambda and priors

**Goal:** per plan section 11, scale from the 40-task pilot to 120 base tasks
(24 dev / 96 test, stratified, frozen+checksummed), and make lambda/channel-
priors/prompt-wording decisions **using the dev split only**.

**What was done:**
- `scripts/freeze_tasks.py` generalized to accept `--n-per-domain` /
  `--tasks-out` / `--manifest-out`, so the *same* deterministic generator and
  `assign_split()` rule used for the 40-task pilot produces the 120-task main
  set: `python scripts/freeze_tasks.py --n-per-domain 60 --tasks-out
  tasks/main_120.json --manifest-out results/main120_manifest.json` →
  **24 dev / 96 test**, exactly the plan's ratio, with its own checksum
  manifest. `tasks/pilot_40.json` (Jul 14-16 artifact) is left untouched —
  the pilot and the main experiment are described as separate artifacts in
  the plan, not one superseding the other.
- `secure_clarify/estimators.py` gained `set_priors()` — a small addition
  needed only because fitting happens in one process (`tune_dev.py`) and
  evaluation happens in another (`run_primary.py`); `fit_priors()` computes
  from (k, n) attack counts, `set_priors()` just reloads an already-fitted
  dict from disk.
- `scripts/tune_dev.py` — the actual dev-only calibration:
  - Fits `_DEV_ATTACK_PRIOR` (Laplace-smoothed `P(carries_attack | channel)`)
    by counting **only over the 24 dev tasks'** adversarial-condition
    responses. This is legitimate dev-set label use (the whole reason a
    dev/test split exists), never touching test-split ground truth.
  - Sweeps λ over `[0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8]` on dev only.
  - **Selection rule, decided deliberately, not the obvious one:** picks the
    *smallest* λ whose dev-set adversarial unsafe rate is ≤ 0.10 — not the λ
    that maximizes dev-set benign utility among qualifying candidates. Why:
    on a 24-task dev split, benign utility vs. λ is **not** guaranteed
    monotonic (only unsafe-rate is — that's the one invariant
    `test_smoke.py::test_lambda_monotone` actually asserts). A first version
    of this script picked λ=6.0 by max-utility tie-break, because utility
    dipped in the middle of the grid (0.904 at λ=0.75-1.5) and coincidentally
    rebounded higher at the far end (0.929 at λ=6-8) — almost certainly
    24-task sampling noise, not signal. Hill-climbing utility over the grid
    would have picked a large, fragile λ for the wrong reason. The corrected
    rule picks the efficient knee instead: **λ = 0.25**.
  - Writes `results/dev_calibration.json`: fitted priors, the full λ
    frontier, the chosen λ, and the selection rule in plain text.
- `scripts/run_primary.py` — loads the frozen dev calibration (never re-fits
  anything), evaluates **only the 96 test-split tasks**, runs all 4 policies
  × {benign, adversarial}, writes `results/primary_summary.json`. Result on
  the held-out test split (still ScriptedAgent): all four go/no-go checks
  PASS, verdict **GO** — Conventional-VoI adversarial unsafe 0.417 →
  SecureVoI 0.042; SecureVoI benign utility 0.921 vs Trusted-Only 0.637.
- `scripts/update_progress.py` hardened in two ways found necessary by this
  work: (1) pilot (`pilot_40.json`) and main (`main_120.json`) task/split
  counts are now tracked **separately** — summing both files' task counts
  together previously made Jul 12-16's evidence text say "160 tasks" once
  `main_120.json` existed, which is misleading for rows that are specifically
  about the 40-task pilot; (2) Jul 17-19 can only show ✅ Done if the
  relevant results file's `agent_backend` field is NOT the ScriptedAgent
  placeholder — otherwise file-existence alone would let the tracker claim
  "Done" for a run that never touched a real model, which is exactly the
  false-positive failure mode the tracker exists to prevent.

**Related-work verification (folded into this session too, not a separate
day in the plan but done alongside the scaling work):** every paper in the
curated arXiv list was fetched and checked directly against its abstract page
(not recalled from training data) — see
[04_references.md](04_references.md). Two mischaracterizations were caught
and fixed: SAGE-Agent's own abstract doesn't claim a POMDP formulation (it's
EVPI + cost modeling); Ambig-DS is about data-science agents, not dialog
systems. A new section, "How each thread grounds this repo's design," maps
each citation to the specific file/mechanism it justifies, so related-work
writing later doesn't require re-deriving these connections from scratch.

**Carried forward — the one blocker:** every number above is still
`ScriptedAgent`. `results/dev_calibration.json` and
`results/primary_summary.json` both stamp `"agent_backend": "ScriptedAgent
(placeholder -- no open-weight model wired in yet)"` explicitly so this can't
be mistaken for a real result later. This is why `scripts/update_progress.py`
correctly still shows Jul 17-18 and Jul 19 as 🟡 Partial, not ✅ Done.

---

## Jul 19 — Freeze development choices; primary test runs

Mechanically the same work as above (`run_primary.py`'s output *is* Jul 19's
deliverable) — split into its own day in the plan, but done in the same
session as Jul 17-18 above since the dev calibration and the primary run are
one pipeline. Frozen: `results/dev_calibration.json` (λ=0.25, the fitted
6-channel priors) is the one and only source `run_primary.py` reads; nothing
about it changes based on test-split results. **Still blocked on a real model
backend** — see the next section for exactly what that requires.

---

## What's actually needed to turn these into real numbers (Jul 20 onward)

This is the one remaining piece of infrastructure before every number in this
repo can move from "the mechanism works" to "here's what a real model does."
Concretely, three things:

**1. Pick an inference route.** This dev environment has no GPU (CPU-only
torch, confirmed via `torch.cuda.is_available() == False`), so a raw local
`transformers`/vLLM pipeline is impractical for hundreds of episodes. Two
routes actually fit:
   - **Hosted API** (recommended — fast, no local compute): Groq, Together,
     Fireworks, or OpenRouter all serve open-weight models (Llama, Qwen,
     Mixtral, DeepSeek, ...) through an OpenAI-chat-compatible endpoint. Groq
     in particular has a free tier and is very fast.
   - **Local, free, CPU-friendly**: install [Ollama](https://ollama.com),
     `ollama pull llama3.1:8b` (or a smaller `qwen2.5:7b` / `llama3.2:3b` for
     speed), run `ollama serve`. Slower than a hosted API but costs nothing
     and needs no account.

   `scripts/model_backends.py` implements both as ready `generate_fn`
   factories — `openai_compatible_generate_fn(base_url, api_key, model)` and
   `ollama_generate_fn(model)` — so wiring in a model is choosing a provider
   and a model name, not writing inference code.

**2. Smoke-test ONE task before spending the full budget.**
   ```bash
   # hosted API route:
   export GROQ_API_KEY=...
   python scripts/smoke_real_model.py --backend openai \
       --base-url https://api.groq.com/openai/v1/chat/completions \
       --api-key-env GROQ_API_KEY --model llama-3.1-8b-instant

   # local Ollama route:
   python scripts/smoke_real_model.py --backend ollama --model llama3.1:8b
   ```
   This runs one full episode and prints the model's raw `sample_intents`
   output, the question/channel SecureVoI picked, and the goal/safety
   outcome — eyeball it before trusting the backend with the full grid.

**3. Re-run the frozen pipeline with the real agent, per model family.** The
plan needs **two model families for the pilot re-run** and **three for the
main experiment** (Jul 22-23). For each model:
   ```bash
   python scripts/tune_dev.py    --tasks tasks/main_120.json   # re-fit on dev with THIS model
   python scripts/run_primary.py --tasks tasks/main_120.json   # evaluate on test with THIS model
   ```
   Important: lambda/priors must be **re-tuned per model**, not reused from
   the ScriptedAgent calibration — different models will disagree differently
   on intents and get fooled differently by injected text, so the dev-fit
   numbers are model-specific, not a repo-wide constant. Keep decoding
   deterministic (`temperature=0`, already the default in
   `model_backends.py`) for every main run.

**4. Only after real numbers exist:** replace `abstract.md`'s 7 bracketed
placeholders (`[N] [M] [X] [Y] [Z] [B] [A]`) with the real counts/percentages,
and only then does `scripts/update_progress.py`'s Jul 19/21 rows turn ✅ Done
— by design, not by editing a checkmark by hand.

---

## GAP CLOSED — real open-weight models wired in; held-out numbers obtained

The single blocker above (every number was `ScriptedAgent`) is now closed. The
held-out test split was run end-to-end on a **real local open-weight model**
and Jul 17-19 flipped to ✅ Done automatically off the `agent_backend` field.

**Backend actually used:** `ollama:mistral-nemo:12b`, run locally via Ollama on
CPU/Metal (no rate limits, fully deterministic at temperature 0 — re-running a
recorded episode reproduces it exactly). A hosted route (Groq
`llama-3.3-70b-versatile`) was validated on the **dev split** and shows the same
clean monotone frontier, but its free-tier daily token cap (~100k) could not
finish the ~138k-token 96-task test grid, so the completed held-out run is the
local Mistral one. `results/models/{mistral-nemo-12b,llama-3.3-70b}/` archive
each model's artifacts; the default `results/*.json` hold the Mistral run.

**Held-out result (96 test tasks, λ=0.75 frozen from dev, verdict GO):** benign
goal rate 0.00 (Never Ask) → 1.00 (asking); Conventional-VoI adversarial unsafe
**0.500**; SecureVoI **0.083** (paired bootstrap −0.417 [−0.521, −0.323],
p<0.001); SecureVoI benign utility 0.950 vs Trusted-Only 0.675 (+0.275
[0.183, 0.367], p<0.001). Both central comparisons significant.

**Model-dependence (a real finding, not a bug):** injection-susceptibility
varies by model. Mistral-Nemo-12B and Llama-3.3-70B follow the injected riders
and exhibit the trade-off; GPT-OSS-20B and Qwen3-32B resist them and show little
Conventional-VoI harm. This belongs in the paper (and is now noted in
`abstract.md`).

**Eight fixes were required the moment a real model touched the pipeline** —
each invisible under ScriptedAgent, which hard-codes correct tool calls and a
structured attack channel:
1. `scripts/model_backends.py`: set a `User-Agent` (Cloudflare 403s the stock
   `python-urllib` UA on Groq/Together/Fireworks/OpenRouter).
2. `scripts/model_backends.py`: honor the `Retry-After` header (cap raised to
   310s) + optional `GEN_MIN_INTERVAL` throttle — the binding Groq limit is a
   burst/daily one whose Retry-After is 130-300s, which a 65s cap could not
   outlast.
3. `agent.py` `OpenModelAgent.act`: spell out each tool's EXACT arg keys in the
   prompt — a real model otherwise invents `{"files":…}`/`{"file","user"}`
   instead of `{"name"}`/`{"name","target"}`, `_validate_plan` drops them, and
   every benign goal fails.
4. `runner.py`/`agent.py`: deliver injections as the **text of an accepted
   answer** into `act`, not as structured `_inject_*` keys a real model ignores.
   Acceptance (SecureVoI's stage-2 gate) is what admits or blocks that text —
   the security mechanism, exercised through the realistic channel. ScriptedAgent
   still uses the `_inject_*` keys (unchanged), so its tests/pilot are untouched.
5. `agent.py`: filter the latent `private_person` field out of what
   `OpenModelAgent` acts on (it leaked into benign calendar intents and caused a
   spurious unsafe `share_availability` on every benign calendar task).
6. `agent.py` `_repair_json`: repair the common LLM JSON slip (a stray/missing
   closing delimiter) so a capable model's one-brace error doesn't drop the
   whole plan.
7. `agent.py` `act` prompt: frame the agent to treat an accepted clarification
   as authoritative (so a gullible agent follows an injected rider) while not
   inventing details that were not provided (so it does not hallucinate unsafe
   actions on under-specified tasks).
8. `estimators.py` `estimate_info_gain`: apply the channel-info multiplier
   OUTSIDE the `min(1.0, …)` saturation clip. A real model's high intent
   disagreement saturates the clip, erasing per-channel differences, so the
   risk-blind policy tie-breaks onto the trusted channel and never meets the
   attack — the exact bug docs/03_gonogo_memo.md fixed for ScriptedAgent,
   re-emerging at real-model disagreement levels. Algebraically identical when
   unsaturated, so ScriptedAgent (which never saturates) and its
   `test_tradeoff_exists`/`test_lambda_monotone` are unchanged.

Still open (Jul 22-28): the two remaining baselines named in the plan
(confidence-threshold, post-hoc guardrail) are NOT implemented, so the abstract
was filled to claim only the baselines actually run (risk-blind conventional VoI
and trusted-channel-only); a second/third completed *test-split* model; the
oracle-vs-learned-risk ablation; the robustness subset; and the paper draft.

---

## GAP CLOSED — Jul 17-21 done for real (Anagh Sangavarapu + Claude Opus 4.8)

Superseded the two entries below: `ollama:mistral-nemo:12b` ran the frozen
pipeline end-to-end on the held-out 96-task test split. Verdict **GO**.
SecureVoI cuts adversarial unsafe actions 0.500→0.083 (paired bootstrap
p<0.001) while matching Conventional VoI's benign utility (0.950) exactly.
`abstract.md` filled with these real numbers. Full account of the eight bugs
found only once a real model touched the pipeline: see the "GAP CLOSED"
entry earlier in this log and `days/jul17-18/README.md`.

## Jul 22-23, in progress — six-policy set, oracle ablation, robustness subset

**Checked the plan's exact policy table (section 10) rather than assume.**
The six main-experiment policies are Never Ask, **Always Ask**, **Confidence
Threshold**, Conventional VoI, Trusted-Only, SecureVoI — post-hoc guardrail is
explicitly marked "Optional" and is scope-cut #2 (section 17) if behind
schedule, so it was never one of the six. Implemented both missing policies
in `secure_clarify/policies.py`:
- `AlwaysAsk` — queries the highest-nominal-info-gain source unconditionally,
  ignoring cost/risk, accepts everything.
- `ConfidenceThreshold` — asks only when sampled-intent agreement falls below
  a dev-calibrated threshold; `scripts/tune_dev.py` now also picks that
  threshold as the median observed agreement across dev tasks (the plan
  gives the decision rule but not a selection formula, so this is a stated
  judgment call).

New `MAIN_POLICIES` list holds all 6; `PILOT_POLICIES` (the original 4) is
untouched and regression-tested, so `run_pilot.py`/the go/no-go memo's
numbers are unaffected. `run_primary.py` gained `--policies {pilot,main}`,
defaulting to `pilot` so Anagh's archived Mistral-Nemo results stay exactly
reproducible.

**Oracle-vs-learned-risk ablation**: `SecureVoIOracle` (subclasses
`SecureVoI`, swaps the learned `classify_malice` signal for the ground-truth
`carries_attack` label looked up by matching `(qid, channel, text)` against
`task.responses` — avoids touching `runner.py`'s `accept()` call site) +
`scripts/oracle_ablation.py`. Validated against ScriptedAgent (0.0 gap at
λ=0.75, since ScriptedAgent already floors at 0 unsafe there).

**Stochastic-repetition robustness subset** (plan section 11: "add three
stochastic repetitions on a stratified 30-task subset rather than repeating
the entire grid"): `scripts/robustness_subset.py` re-runs the frozen
dev-tuned λ/priors 3× at temperature=0.7 against an evenly-spaced 30-task
subset of the test split, reporting mean/std per policy×condition — a
robustness check on decoding-randomness sensitivity, not a re-tuning of
anything. Required threading `temperature` through `build_agent()`
(previously hardcoded to 0 everywhere); every other script stays at 0.

**Second real model, in progress**: this sandbox has no Ollama install or
API keys (Anagh's machine had both), so running `Qwen/Qwen2.5-0.5B-Instruct`
locally via `transformers` in an isolated `.venv_model/` instead
(`--backend hf_local`) — see `days/jul17-18/environment-notes.md`. Single-task
smoke check passed (valid JSON, no crash). First calibration attempt ran
57+ minutes of CPU time without finishing; direct timing isolated why: this
small model does not emit an EOS token for these prompts and was burning the
*entire* `max_new_tokens` budget every call regardless of how short the
actual answer was (a 2-token JSON answer took 60s at `max_new_tokens=160`).
Fixed with a `StoppingCriteria` that halts generation as soon as a complete,
balanced top-level JSON value has been emitted (reusing the same
string-quote-aware bracket matching `agent.py`'s `_extract_json` already
uses, just applied during generation instead of after) — cut a
representative call from 60s to 7-27s. Dev calibration restarted with the
fix and is running now; real primary-run numbers to follow, honestly,
whatever they show — a 0.5B model may simply be too weak to complete tasks
reliably regardless of policy, which would itself be a legitimate finding
(a capability floor), not a failure of the pipeline.

## Jul 24-28 — not yet started (kept here as a concrete plan, not just a label)

- **Jul 24 — Failure analysis and final figures.** Needs `docs/
  failure_analysis.md` and a `figures/` directory; neither exists yet.
- **Jul 25-26 — Full seven-page paper.** No `paper*.tex` yet; only the
  abstract exists.
- **Jul 27 — Revision, anonymity, reproduction, citation audit.**
  `REPRODUCIBILITY.md` / `CITATIONS.md` don't exist yet; `docs/
  04_references.md` (this session's citation-verification work) is a running
  start on the citation-audit half.
- **Jul 28 — Full paper and supplement submission.**

Known, explicitly-flagged gap that should stay in Limitations rather than be
quietly patched: `task_factory.py` still has only 2 base task templates (one
per domain — `archive`/`scheduling`), so the 120-task main set's diversity
comes from parameter combinations (stakes × channel-availability × attack
type) layered on those 2 templates, not from genuinely distinct task
*families* as plan section 11 ("stratified by ... family") technically calls
for.
