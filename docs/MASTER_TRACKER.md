# Master Tracker — Security-Aware Clarification for Agents (AAAI-27)

One table, all 17 schedule days, specific "what we have" vs. "what we need"
per row — built so status can be checked at a glance without opening every
`days/*/README.md`. This is a **hand-maintained companion** to
[PROGRESS.md](../PROGRESS.md)'s auto-generated table (which remains the
source of truth for the ✅/🟡/⬜ status itself — never hand-edit that one).
Update this file's "What we have" / "What we need" columns as real results
land; re-check against `PROGRESS.md` after any `scripts/update_progress.py
--write` run so the two never silently diverge.

| Day | Deliverable | Status | What we have (specific) | What we need (specific) |
|---|---|---|---|---|
| Jul 12 | Novelty matrix, threat model, schemas, 10 seed tasks | ✅ Done | `docs/01_novelty_matrix.md` (7-axis matrix, frozen novelty statement), `docs/02_threat_model.md` (principal/channel/attacker model), `schema.py` (Task/Question/Response + validation), 40 tasks | — |
| Jul 13 | File/calendar simulators, verifiers, 20 tasks | ✅ Done | `simulators.py` (FileEnv/CalendarEnv, immutable log), `verifiers.py` (goal_verifier, safety_verifier, both non-LLM), 40 tasks | — |
| Jul 14 | Four policies, 40 pilot tasks, matched responses | ✅ Done | `policies.py` (NeverAsk/ConventionalVoI/TrustedOnly/SecureVoI), `estimators.py`, `agent.py`'s ScriptedAgent, `task_factory.py`, `runner.py`, 40 matched benign/noisy/adversarial tasks | — |
| Jul 15 | Two-model pilot and full unsafe-trajectory audit | ✅ Done | `run_pilot.py`, `docs/03_gonogo_memo.md` (3 real bugs found+fixed: answer leakage, risk-blind channel dodge, info/risk scale mismatch), `results/pilot_summary.json` | — |
| Jul 16 | Go/no-go, freeze method, split tasks | ✅ Done | Verdict **GO** (all 4 checks pass), `OpenModelAgent` fully implemented (not a stub), `tasks/pilot_40.json` frozen 8 dev/32 test + checksum manifest | — |
| Jul 17-18 | 120 tasks, development runs, tune lambda and priors | ✅ Done | `tasks/main_120.json` (24 dev/96 test, exact plan ratio), `results/dev_calibration.json` — **Mistral-Nemo-12B** (Ollama) λ=0.75; **Llama-3.3-70B-versatile** (Groq) λ=1.0, dev-validated same clean monotone frontier (0.833→0.000 unsafe as λ 0→1); `results/models/qwen2.5-0.5b-instruct/dev_calibration.json` — λ=0.0 chosen, but **benign_goal_rate=0.000 at every λ** (model too weak to complete tasks — capability floor, not a trade-off) | Nothing outstanding for this row itself |
| Jul 19 | Freeze development choices; primary test runs | ✅ Done (Mistral-Nemo); 🔄 in progress (2 more models) | Mistral-Nemo-12B: `results/primary_summary.json`, verdict **GO**, SecureVoI 0.500→0.083 unsafe (p<0.001) | Llama-3.3-70B-versatile primary test-split run **running now** (`results/models/llama-3.3-70b-versatile/`); Qwen2.5-0.5B primary run **running now** (expected to reproduce the 0.000-everywhere capability-floor result, not a trade-off) |
| Jul 20 | Statistics, main table, frontier, real abstract | ✅ Done (Mistral-Nemo) | `results/stats.json`, `results/main_table.md`, `results/frontier.json`, `abstract.md` filled with Mistral-Nemo's real numbers | Re-run `compute_stats.py`/`make_main_table.py` against Llama-3.3-70B-versatile once its primary run lands, to get a genuine **second** model's numbers for the main table (currently only 1 of the intended 2-3) |
| Jul 21 | Abstract submission | ✅ Done (artifact); ⬜ not done (action) | `abstract.md` has 0 placeholders, numbers verified against `main_table.md` | **Actual portal submission** — a human action, not something the repo can verify |
| Jul 22-23 | Third model, ablations, robustness subset | 🟡 In progress | All 5 concrete sub-items built: `AlwaysAsk` + `ConfidenceThreshold` (`MAIN_POLICIES`, 6 total, dev-calibrated); `SecureVoIOracle` + `scripts/oracle_ablation.py`; `secure_clarify/guardrail.py`'s `PostHocGuardrail` + `scripts/guardrail_eval.py` (the plan's optional 7th baseline, built anyway — notable ScriptedAgent finding: beats SecureVoI's benign-goal-rate-under-attack); `scripts/robustness_subset.py`; `scripts/run_full_model.py` one-command orchestration; `scripts/aggregate_models.py` cross-model table. All validated on ScriptedAgent. | Real-model numbers for all of the above — `Llama-3.3-70B-versatile` (dev-complete, test in progress), `Qwen2.5-0.5B` (primary running, likely capability floor) and `Qwen2.5-1.5B-Instruct` (full pipeline running) are the in-flight second/third models |
| Jul 24 | Failure analysis and final figures | ⬜ Not started | — | `docs/failure_analysis.md` (read every unsafe/failed episode in real-model `primary_episodes.json`, categorize failure modes); `figures/` directory (frontier plot, main-table bar chart, per-channel unsafe rate) |
| Jul 25-26 | Write full seven-page paper | 🟡 In progress | `docs/paper_draft.md` — full first draft: Abstract/Related Work/Threat Model/Method/Benchmark/Setup/Results/Limitations adapted from verified repo artifacts, Introduction and Conclusion newly drafted as argumentative prose | Convert to venue LaTeX template; fold in real second/third-model numbers (marked `[TODO]` throughout, not silently gapped); human editing pass for tone/length/citation formatting |
| Jul 27 | Revision, anonymity, reproduction, citation audit | 🟡 Partial | `docs/04_references.md` — every curated citation fetched and verified directly against its arXiv abstract (not recalled from memory), 2 mischaracterizations caught and fixed | `REPRODUCIBILITY.md`, `CITATIONS.md`, anonymity pass (strip author-identifying content if double-blind) |
| Jul 28 | Full paper and supplement submission | ⬜ Not started | — | Everything above, `SUBMISSION.md` marker |

## Model coverage detail (the actual "separation of metrics" the paper needs)

| Model | Backend | Dev calibration | Test-split primary run | Adversarial unsafe rate (Conv VoI → SecureVoI) | Verdict |
|---|---|---|---|---|---|
| Mistral-Nemo-12B | Ollama (Anagh's machine) | ✅ λ=0.75 | ✅ Complete | 0.500 → 0.083 (−0.417, p<0.001) | **GO** |
| Llama-3.3-70B-versatile | Groq (this session) | ✅ λ=1.0, clean 0.833→0.000 frontier on dev | 🔄 Running now | TBD | TBD |
| Qwen2.5-0.5B-Instruct | Local `transformers` (this session) | ✅ λ=0.0 (degenerate — no unsafe rate to trade off against) | 🔄 Running now | Expected: N/A — **benign_goal_rate=0.000 at every λ tested**, i.e. the model doesn't complete tasks regardless of policy | Capability floor, not a safety finding |
| GPT-OSS-20B | Groq (Anagh, prior session) | Tried | Not run | Resists injections entirely (qualitative finding) | Reported in abstract, not in main table |
| Qwen3-32B | Groq (Anagh, prior session) | Tried | Not run | Resists injections entirely (qualitative finding) | Reported in abstract, not in main table |

**Why this table matters for "separation of metrics":** the paper's central
claim needs at least 2 models showing the SecureVoI-vs-Conventional-VoI
separation clearly (Mistral-Nemo already does, cleanly). Llama-3.3-70B's dev
frontier (0.833→0.000, monotone, λ knee at 1.0) is the cleanest of any model
tested so far — if its test-split run reproduces that, it's the strongest
second data point available. Qwen2.5-0.5B is being run to completion for
honesty/completeness, but its result is a *different kind* of finding
(capability floor: too weak to attempt the task at all) and shouldn't be
presented as a second point on the safety-utility trade-off curve — it
belongs in Limitations or a small-model appendix note, not the main table.

## What's genuinely blocking Jul 25+ right now
1. Llama-3.3-70B-versatile's primary run finishing (in progress).
2. `compute_stats.py` + `make_main_table.py` re-run with 2 real models in the
   main table instead of 1.
3. The oracle ablation and robustness subset each need at least one real
   primary run to point at (Llama-3.3-70B, once done, unblocks both).
4. Failure analysis (Jul 24) needs real unsafe/failed episodes to read —
   available now from Mistral-Nemo, will have more from Llama-3.3-70B.

Nothing above requires new code — every script exists and is tested. This is
now purely a "run it and report the number" phase.
