# Security-Aware Clarification for Agents — AAAI-27

## What is this, in plain English?

AI agents that can take real actions (archive a file, schedule a meeting, send
a message) sometimes get vague instructions and have to decide: act on my best
guess, or stop and ask a clarifying question?

Asking seems obviously safe. It isn't. The answer to that question doesn't
always come from the real, trusted user — it might come from a shared
document, a forwarded email, a third-party tool, or an account that's been
compromised. So the moment an agent asks a question, it opens a channel that
an attacker can use to slip in a malicious instruction disguised as an answer.
That means the same clarifying question that helps the agent do the right
thing for a real user can also be the thing that gets it hijacked.

**This repo is a testbed for that trade-off.** It builds simulated
environments (a file system, a calendar) and a benchmark of tasks where the
*same* ambiguous request gets three matched versions of a clarifying answer —
one honest, one just noisy/wrong, and one actively adversarial. We then run
several decision rules ("policies") against those tasks and check,
automatically (no human grading), whether the agent (1) actually completed the
task and (2) took any action it shouldn't have.

Our proposed rule, **SecureVoI**, doesn't just ask "would clarifying help?" —
it also asks "who would be answering, and how much do I trust that channel?"
before deciding whether to ask, and screens the answer before acting on it.
The claim we're validating: SecureVoI keeps most of the benefit of asking on
legitimate tasks while cutting down how often the agent gets tricked on
adversarial ones — beating simpler baselines like "always ask" or "only ask
the verified user."

**Important:** nothing here is trained or fine-tuned. The decision rules are
fixed, hand-designed formulas evaluated against off-the-shelf language models
at inference time — this repo tests and compares those rules, it doesn't
train anything.

---

Runnable scaffolding for balancing information gain and attack exposure when
language-model agents seek clarification. Everything here executes on CPU with a
**scripted agent** so the pipeline is validated before open-weight models are wired in.
The scripted-agent numbers are a **pipeline check, not the paper's result**.

## Layout

```
secure_clarify/
  schema.py        # Task/Question/Response dataclasses + validation (Jul 12)
  simulators.py    # FileEnv/CalendarEnv, immutable action log (Jul 13)
  verifiers.py     # goal_verifier + safety_verifier, both non-LLM (Jul 13)
  estimators.py    # info-gain + pre/post risk estimators (Jul 14)
  policies.py      # NeverAsk, ConventionalVoI, TrustedOnly, SecureVoI (Jul 14)
  agent.py         # ScriptedAgent + OpenModelAgent, both implemented (Jul 14-15)
  resolver.py      # answer -> resolved intent, injection effect (Jul 14)
  runner.py        # episode loop, utility, summaries (Jul 14-15)
  task_factory.py  # matched benign/noisy/adversarial task generator + dev/test split
tasks/pilot_40.json
docs/              # novelty matrix, threat model, go/no-go memo, references
scripts/update_progress.py   # regenerates PROGRESS.md's schedule table
scripts/freeze_tasks.py      # regenerates tasks/pilot_40.json + split checksum
results/           # pilot_summary.json, frontier.json, split_manifest.json
abstract.md
```

## Pilot result (scripted agent — pipeline check only)

- Benign: Conventional VoI goal 1.00 vs Never Ask 0.00 → asking helps.
- Adversarial: Conventional VoI unsafe **0.425**; SecureVoI drops it to **0.30** (λ=1),
  **0.125** (λ=2), **0.00** (λ≥4), while holding benign utility ≈0.95 until λ≈4.
- SecureVoI beats Trusted-Only on benign utility (0.95 vs 0.64) → not degenerate.

Three real bugs were found and fixed during the audit (answer leakage, risk-blind
policy dodging the attack, info/risk scale mismatch). See `docs/03_gonogo_memo.md`.

## Honest limitations (carry into the paper)

- Scripted-agent trade-off is *constructed to be possible*, not measured on an LM.
- `classify_malice` and channel priors are seeded heuristics; fit on dev, and report the
  oracle-vs-learned-risk ablation.
- Simulator evidence shows the trade-off's existence and policy ordering, not real-world safety.

## Run

```bash
python test_smoke.py                        # invariants + trade-off + lambda monotonicity
python run_pilot.py                         # full pilot table, go/no-go, writes results/
```

## Schedule & progress

Day-by-day deliverable status, current blockers, and the real-model wiring
notes now live in **[PROGRESS.md](PROGRESS.md)** so this README can stay
focused on what the project is rather than where it stands this week. For a
detailed narrative log — what was built each day, why, what broke, and what's
left, written for anyone (or any AI) picking this up cold — see
**[docs/DAILY_LOG.md](docs/DAILY_LOG.md)**.
