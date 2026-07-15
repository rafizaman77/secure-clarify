# Jul 22-23 — Third model, ablations, robustness subset

**Status: ⬜ Not started**

## Goal (from the plan)
120 tasks × 3 conditions × 6 policies × 3 models = 6,480 deterministic
episodes, plus 3 stochastic repetitions on a stratified 30-task subset
(section 11).

## Concrete steps (in dependency order)
1. **Third model family.** `scripts/model_backends.py` already supports any
   `hf_local`/`openai`/`ollama` model — this is a matter of picking and
   running a third one, not new infrastructure.
2. **Two more policies** to reach "six policies" (the pilot only used 4:
   `NeverAsk`/`ConventionalVoI`/`TrustedOnly`/`SecureVoI`). Plan section 9
   lists a **confidence-threshold** baseline and a **post-hoc guardrail**
   baseline (Conventional VoI + final-action screening) as the two missing
   ones — neither is implemented in `secure_clarify/policies.py` yet.
3. **Oracle-vs-learned-risk ablation** — `docs/03_gonogo_memo.md`'s caveat:
   `classify_malice` is a learned/heuristic signal; report how much of
   SecureVoI's benefit survives if `response_risk` used the ground-truth
   `carries_attack` label instead (an "oracle" upper bound).
4. **Stratified 30-task stochastic-repetition subset** — needs a controlled
   randomness source in the agent (currently fully deterministic at
   temperature=0 by design for the main runs); decide how "stochastic
   repetition" is operationalized (temperature>0 sampling? re-running with a
   different random seed on the task_factory side?) before implementing.

## Blocked on
A real model backend from [jul17-18](../jul17-18/README.md) being wired in
for at least one model family, so the "third" model is additive rather than
the first.
