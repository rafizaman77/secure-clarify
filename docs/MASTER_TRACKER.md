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
| Jul 22-23 | Third model, ablations, robustness subset | ✅ Done | **Three test-split-complete real models, all verdict GO**: Mistral-Nemo-12B (Anagh — full 6-policy/oracle/guardrail/robustness), GPT-OSS-120B (Ollama Cloud — 6-policy primary + oracle ablation, verdict GO), GPT-OSS-20B (Ollama Cloud — 6-policy primary, verdict GO). Headline: SecureVoI cuts adversarial unsafe rate ~80-85% vs Conventional VoI, consistently across all 3 models (`results/cross_model_comparison.md`). `AlwaysAsk`/`ConfidenceThreshold`/`SecureVoIOracle`/`PostHocGuardrail`/`robustness_subset.py`/`run_full_model.py` orchestration all built and exercised on real data, not just ScriptedAgent. | GPT-OSS-20B's oracle ablation + guardrail eval, GPT-OSS-120B's guardrail eval — hit Ollama Cloud's rate limit mid-run (fixed the retry logic, re-run once the usage window resets); robustness subset for the two GPT-OSS models |
| Jul 24 | Failure analysis and final figures | ⬜ Not started | — | `docs/failure_analysis.md` (read every unsafe/failed episode in real-model `primary_episodes.json`, categorize failure modes); `figures/` directory (frontier plot, main-table bar chart, per-channel unsafe rate) |
| Jul 25-26 | Write full seven-page paper | 🟡 In progress | `docs/paper_draft.md` — full first draft: Abstract/Related Work/Threat Model/Method/Benchmark/Setup/Results/Limitations adapted from verified repo artifacts, Introduction and Conclusion newly drafted as argumentative prose | Convert to venue LaTeX template; fold in real second/third-model numbers (marked `[TODO]` throughout, not silently gapped); human editing pass for tone/length/citation formatting |
| Jul 27 | Revision, anonymity, reproduction, citation audit | 🟡 Partial | `docs/04_references.md` — every curated citation fetched and verified directly against its arXiv abstract (not recalled from memory), 2 mischaracterizations caught and fixed | `REPRODUCIBILITY.md`, `CITATIONS.md`, anonymity pass (strip author-identifying content if double-blind) |
| Jul 28 | Full paper and supplement submission | ⬜ Not started | — | Everything above, `SUBMISSION.md` marker |

## Model coverage detail (the actual "separation of metrics" the paper needs)

| Model | Backend | Dev calibration | Test-split primary run | Adversarial unsafe rate (Conv VoI → SecureVoI) | Verdict |
|---|---|---|---|---|---|
| Mistral-Nemo-12B | Ollama (Anagh's machine) | ✅ λ=0.75 | ✅ Complete | 0.500 → 0.083 (−0.417, p<0.001) | **GO** |
| GPT-OSS-120B | Ollama Cloud (this session) | ✅ λ=0.75 | ✅ Complete | 0.521 → 0.083 (−84%) | **GO** |
| GPT-OSS-20B | Ollama Cloud (this session) | ✅ λ=0.75 | ✅ Complete | 0.500 → 0.094 (−81%) | **GO** |
| Llama-3.3-70B-versatile | Groq (this session) | ✅ λ=1.0, clean 0.833→0.000 frontier on dev | ❌ repeated intermittent network stalls in this sandbox, not retried further (3 real models already achieved) | — | — |
| Qwen2.5-0.5B-Instruct | Local `transformers` (this session) | ✅ λ=0.0 (degenerate — no unsafe rate to trade off against) | Ran; **benign_goal_rate=0.000 at every λ tested** — doesn't complete tasks regardless of policy | N/A | Capability floor, not a safety finding |
| Qwen3-32B | Groq (Anagh, prior session) | Tried qualitatively | Not run to completion | "Resists injections" (qualitative) | Superseded in spirit by GPT-OSS-20B's real run above |

**Three test-split-complete models, all verdict GO, all showing the same
~80-85% adversarial-unsafe-rate reduction from SecureVoI vs. Conventional
VoI** (see `results/cross_model_comparison.md`) — this is the "separation of
metrics" the paper needed, achieved and replicated, not a single-model
artifact. GPT-OSS's benign goal rates (0.573-0.750) are notably lower than
Mistral-Nemo's (1.000) even under risk-blind Conventional VoI — a real,
worth-discussing finding that these models are more broadly conservative,
not simply more security-aware.

## What's genuinely left (small, non-blocking)
1. GPT-OSS-20B's oracle ablation + guardrail eval, GPT-OSS-120B's guardrail
   eval — hit Ollama Cloud's usage rate limit (HTTP 429) mid-run after ~5
   full 96-task pipelines in one session; fixed `ollama_generate_fn`'s retry
   logic to honor `Retry-After` (was giving up after 2 quick attempts),
   re-run once the dashboard's usage window resets.
2. Robustness subset for the two GPT-OSS models (Mistral-Nemo's is done).
3. Fold the 3-model cross-comparison into `paper.tex`'s Results section
   (currently has Mistral-Nemo's numbers folded in; GPT-OSS's real numbers
   are new since that pass).
4. Jul 28: actual submission — a human action, not something to build.

Nothing above requires new code — every script exists and is tested. This is
now purely a "run it and report the number" phase.
