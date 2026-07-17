# Ask, Act, or Verify? Security-Aware Clarification for Language-Model Agents

**Status: full first draft, not camera-ready.** Every section has real prose
now, including Introduction and Conclusion (drafted this pass). Numbers and
comparisons still marked `[TODO: ...]` are genuinely pending a second/third
completed model run, not unwritten text — everything else is either adapted
from an existing verified repo artifact or newly-drafted argumentative prose
that should get a human editing pass (tone, length-to-page-limit, citation
formatting) before submission. Convert to the venue's LaTeX template using
the source map at the bottom of this file / in
[days/jul25-26/README.md](../days/jul25-26/README.md).

---

## Abstract

Language-model agents routinely receive underspecified instructions and must
decide whether to act on their best interpretation or ask for more
information. Existing clarification methods weigh expected task improvement
against interaction cost, implicitly assuming that whoever answers can be
trusted. In deployed agentic systems, this assumption often fails:
clarification may arrive through shared documents, external tools, forwarded
messages, delegated collaborators, or compromised accounts. Asking a
question therefore does two things at once — it reduces uncertainty about
the user's intent, and it opens a channel through which an attacker can
inject instructions. We formulate security-aware clarification as a decision
problem in which an agent jointly chooses whether to ask, what format to ask
in, and which channel to query. We propose SecureVoI, a two-stage extension
of value-of-information reasoning that scores each question–channel pair by
expected information gain net of interaction cost and channel-dependent
security loss, then screens incoming responses before accepting them. We
further construct a benchmark of 120 ambiguous tool-use tasks with matched
benign, noisy, and adversarial clarification responses and fully automatic
outcome verification. Evaluated on a held-out test split (96 tasks) with an
open-weight model (Mistral-Nemo-12B; the same trade-off reproduces on the
development split with Llama-3.3-70B, while more heavily safety-tuned models
such as GPT-OSS-20B and Qwen3-32B resist the injections and show little
conventional-clarification harm), conventional clarification improves benign
task success by 100 percentage points but raises unsafe-action rates from 0%
to 50% under adversarial responses. SecureVoI recovers 100% of the benign
improvement while reducing unsafe actions by 83% (from 50% to 8%),
outperforming both a risk-blind conventional value-of-information policy and
a trusted-channel-only baseline, which forfeits 0.28 in benign utility (0.95
vs. 0.68) by refusing partially-trusted channels outright. Our results show
that when an agent should ask depends not only on how uncertain it is, but
on who might be answering.

*(Source: `abstract.md`, already filled with real Mistral-Nemo-12B numbers.
`[TODO]`: fold in a second/third completed model once available —
Llama-3.3-70B and the two local Qwen runs are in flight as of this draft.)*

---

## 1. Introduction

Language-model agents that can call tools — archiving a file, scheduling a
meeting, sending a message — routinely receive instructions that
underspecify some part of the intended action. A growing line of work
teaches agents to recognize this ambiguity and ask a clarifying question
rather than guess: CLAM (Kuhn, Gal, and Farquhar) established that a model
should detect ambiguity and request clarification instead of committing to
a possibly-wrong interpretation; SAGE-Agent (Suri et al.) formalizes which
question to ask by its expected value of perfect information; "Learning to
Ask" (Wang et al.) and "Ask or Assume?" (Edwards and Schuster) extend the
same idea to tool-calling and coding agents specifically. All of this work
shares one assumption, usually implicit: whoever answers the question can be
trusted. That assumption is the load-bearing one, and it is also the one
that breaks first in a deployed system. A clarifying question does not
necessarily go to the user who issued the original request — it may be
routed to a shared document, a delegated collaborator, a forwarded message
thread, an external tool, or, in the worst case, a compromised account. Each
of these is a plausible answerer in an ordinary agentic workflow, and none
of them is the authenticated principal the clarification-seeking literature
implicitly assumes is on the other end.

At the same time, a separate line of work has shown that tool-using agents
are vulnerable to instructions smuggled into content they process: InjecAgent
(Zhan et al.) benchmarks indirect prompt injection through tool outputs and
finds that even a capable agent follows an injected instruction a
substantial fraction of the time; AgentDojo (Debenedetti et al.) generalizes
this into a standard security benchmark pairing benign tasks with an
adversarial one hidden in the environment. This literature treats injected
instructions as *ambient* — something the agent stumbles into while doing
its job — not as something the agent's own behavior invites. Neither
literature asks the question this paper asks: what happens when the
mechanism that makes an agent *helpful* (asking for clarification when
unsure) is also the mechanism an attacker can use to *reach* the agent in
the first place? Asking a clarifying question is not a passive act. It opens
a channel, and opening a channel is exactly how an indirect-prompt-injection
attack gets a foothold. A policy that reasons about whether to ask only in
terms of expected information gain and interaction cost — as every
clarification-seeking method above does — has no way to represent that the
same question, asked of a different channel, carries a different exposure.

This gap motivates the decision problem we study: an agent should decide
not only *whether* to ask, but *what format* to ask in and *which channel*
to query, jointly, as a function of how informative each channel plausibly
is, how much asking costs in interaction overhead, and how much risk each
channel carries of returning an adversarial answer. We call this
security-aware clarification, and we propose **SecureVoI**, a two-stage
extension of value-of-information reasoning that (1) scores each
candidate question–channel pair by expected information gain net of
interaction cost *and* a channel-dependent security loss term before
asking, and (2) screens the response that actually comes back before
accepting it, using a learned estimate of how likely that specific answer is
to be malicious. The two stages matter separately: a policy that only does
stage 1 (like Conventional VoI, which we show is measurably more dangerous
under adversarial responses than under benign ones) can still be talked into
accepting a bad answer once it decides to ask; a policy that only does stage
2 has no principled way to prefer a slightly-less-informative but
lower-risk channel in the first place.

**Working novelty statement** (frozen in `docs/01_novelty_matrix.md`, do not
reword without re-checking the matrix): *"Prior work either optimizes
clarification under cooperative-response assumptions or evaluates security
consequences after clarification. We study the prospective decision problem
of whether, what, and where to ask when channels differ in information
quality, interaction cost, and adversarial risk, and we pair the pre-inquiry
decision with a response-acceptance stage so that the policy is not a
final-output guardrail."*

---

## 2. Related Work

Full citation list and verification status: `docs/04_references.md` (every
entry fetched and checked directly against its arXiv abstract this session,
not recalled from training data).

**Clarification-seeking under cooperative-response assumptions.** CLAM
(Kuhn et al.) establishes the foundational "ask only when necessary"
lineage; SAGE-Agent (Suri et al.) extends this with an EVPI-based
question-selection objective our SecureVoI's pre-inquiry stage generalizes;
"Ask or Assume?" (Edwards & Schuster) and "Learning to Ask" (Wang et al.)
both decouple ambiguity detection from execution but assume a trustworthy
answerer throughout. None of this cluster models channel identity or
adversarial responses.

**Prompt injection and agent security.** InjecAgent (Zhan et al.) is the
direct precedent for our attack-success-rate metric and `AttackType`
taxonomy; AgentDojo (Debenedetti et al.) is the standard tool-agent security
benchmark, positioned against ours as: theirs is ambient injection in tool
output, ours is injection the agent invites by choosing to ask. The
Instruction Hierarchy (Wallace et al.) grounds our fixed channel-trust
ranking as a training-time analog of what our policies do at decision-time
without retraining. CaMeL (Debenedetti et al.) is our sharpest foil: it
constrains information flow *after* acquisition and never decides whether
acquiring it was worth the exposure — the "acquire decision" is exactly our
contribution's cell in the novelty matrix.

**Value of information under adversarial channels.** The deceptive
path-planning VoI framework (Suttle et al.) is the closest formal precedent
outside the LLM literature to "VoI minus an adversarial-cost term"; the
Bayesian-network adversarial risk analysis framework (Wang & Neil) grounds
our channel-prior formalism in established ARA rather than presenting it as
ad hoc.

*(Full per-citation mapping: `docs/04_references.md`'s "How each thread
grounds this repo's design" section.)*

---

## 3. Threat Model

*(Adapted near-verbatim from `docs/02_threat_model.md` — that document was
explicitly written to paste into this section.)*

**Principal and authority.** A single authenticated principal issues the
original request, which is authoritative and trusted; the principal is
never modeled as the attacker. The agent's job is to satisfy the principal's
hidden intent, of which the request is an underspecified projection.

**Channels.** The agent may obtain clarification from six channel classes at
different trust levels — authenticated user, delegated collaborator, shared
document, forwarded message, external tool, compromised account — and knows
the channel class but not whether a specific answer is malicious. By design,
channel identity is not perfectly predictive of attack: every
non-authenticated class contains benign, noisy, and adversarial instances,
which forces a genuine value-vs-risk trade-off rather than allowing a policy
to win by simply distrusting an entire channel class.

**Attacker objectives.** Goal hijack, constraint removal, recipient
injection, privilege escalation, data exfiltration, destructive action, and
unrelated-instruction injection — the adversarial response always carries
some genuine information alongside the attack, so it is never trivially
ignorable.

**Attacker capabilities.** Can fully control the text of a response on any
non-authenticated channel and mix valid information with the attack. Cannot
modify the system prompt, the authenticated request, the simulator, or
either verifier, and cannot read secrets except by causing the agent itself
to expose them.

**Safety definition.** An episode is unsafe iff the safety verifier observes
any prohibited state transition in the immutable action log, even if later
reversed — safety is a property of the trajectory, not the final state.

**Explicit non-goals.** No claim of universal protection against prompt
injection or adaptive attackers, no formal security guarantee, no
deployment-readiness claim. Simulator evidence establishes the existence and
direction of the information-security trade-off and the relative ordering of
policies, not real-world safety.

---

## 4. Method: SecureVoI

*(Draft prose needed, pulling from `secure_clarify/policies.py` and
`estimators.py`'s docstrings — the formulas are implemented and tested, the
prose explaining them for a reader is not yet written.)*

**Stage 1 (pre-inquiry selection).** For each candidate (question, channel)
pair, score `SV = info_gain - interaction_cost - λ · pre_risk`, where
`pre_risk` is a channel prior times expected loss (Laplace-smoothed,
dev-set-only — `estimate_pre_risk` in `estimators.py`), and pick the
highest-scoring pair if positive; otherwise act without asking.

**Stage 2 (response acceptance).** Given a returned answer, accept iff
`info_value > λ · response_risk · expected_loss`, where `response_risk`
blends a learned malice-classification signal, a channel prior, and lexical
cues (`response_risk` in `estimators.py`).

**λ selection.** Fit on the development split only, chosen as the smallest λ
achieving a target adversarial unsafe rate (not the λ maximizing dev-set
utility — see `docs/DAILY_LOG.md`'s Jul 17-18 entry for why the naive rule
was rejected: utility vs. λ is not monotonic on a small dev split, only
unsafe-rate is, so hill-climbing utility risks a fragile, overfit choice).

**Baselines.** Never Ask, Always Ask (query the nominally most informative
source, ignore cost/risk), Confidence Threshold (ask when sampled-intent
agreement falls below a dev-calibrated threshold), Conventional VoI
(cost-aware, risk-blind), Trusted-Only (high-trust channels only), and
(as an additional, plan-optional baseline) Post-Hoc Guardrail (Conventional
VoI's ask decision, with the resulting action plan screened against known
prohibited-action patterns before execution — see `secure_clarify/
guardrail.py`).

---

## 5. Benchmark

*(Pulled from `docs/01_novelty_matrix.md`, `secure_clarify/task_factory.py`,
and `days/jul17-18/README.md`.)*

120 base tasks (24 development, 96 test — exact ratio from the plan, frozen
and checksummed, `results/main120_manifest.json`) across two domains (file
management, calendar scheduling), each with matched benign, noisy, and
adversarial clarification responses so that any measured difference is
attributable to the response condition, not task difficulty. Outcomes are
verified by two independent, deterministic (non-LLM) verifiers:
`goal_verifier` checks final state against a machine-checkable predicate;
`safety_verifier` scans the immutable action log for any of seven
attacker-objective-mapped prohibited-action patterns.

**Known limitation, stated plainly rather than hidden:** the benchmark's 120
tasks currently draw from only 2 base task templates (one per domain), with
diversity coming from parameter combinations (stakes × channel-availability
× attack type) rather than genuinely distinct task families — the plan's
"stratified by ... family" requirement is only partially met. This belongs
in Section 8 (Limitations).

---

## 6. Experimental Setup

- **Pilot** (Jul 14-16): 40 tasks, ScriptedAgent (deterministic heuristic,
  explicitly a pipeline check, not a result), verdict GO on all 4 go/no-go
  criteria.
- **Main experiment** (Jul 17+): 120 tasks, real open-weight models.
  `[TODO: final model roster]` — currently Mistral-Nemo-12B
  (test-split-complete, `ollama`), Llama-3.3-70B-versatile (dev-complete,
  `[TODO: test split]`), Qwen2.5-{0.5B,1.5B}-Instruct (local `transformers`,
  `[TODO: in progress as of this draft]`), plus qualitative
  injection-resistance findings for GPT-OSS-20B and Qwen3-32B.
- **Statistics**: task-level (paired) bootstrap, 2000 resamples, 95% CI —
  paired because all policies share the same test tasks (`compute_stats.py`).
- **Reproducibility**: exact commands in `REPRODUCIBILITY.md`; every
  result's `agent_backend` field records exactly which model produced it.

---

## 7. Results

**Main table** (Mistral-Nemo-12B, 96 test tasks — `results/main_table.md`):

| Policy | Benign goal rate | Benign utility | Adversarial unsafe rate |
|---|---|---|---|
| Never Ask | 0.000 | −0.150 | 0.000 |
| Conventional VoI | 1.000 | 0.950 | 0.500 [0.406, 0.604] |
| Trusted-Only | 0.750 | 0.675 | 0.000 |
| SecureVoI | 1.000 | **0.950** | **0.083** [0.031, 0.146] |

SecureVoI matches Conventional VoI's benign utility exactly while cutting
adversarial unsafe actions by 83% (paired bootstrap: −0.417 [−0.521,
−0.323], p<0.001 vs. Conventional VoI). SecureVoI's benign utility also
significantly exceeds Trusted-Only's (+0.275 [0.183, 0.367], p<0.001),
demonstrating it is not degenerate — it still uses partially-trusted
channels when the information is worth it.

`[TODO]`: figures — `figures/frontier.svg` and `figures/main_table.svg`
exist but are currently rendered from the Jul 15 ScriptedAgent pilot sweep
and Mistral-Nemo's real stats respectively; regenerate both once the final
model roster is locked.

`[TODO]`: oracle-vs-learned-risk ablation, guardrail comparison, and
robustness-subset numbers — scripts exist and are validated on ScriptedAgent
(`scripts/oracle_ablation.py`, `scripts/guardrail_eval.py`,
`scripts/robustness_subset.py`), real-model numbers pending.

---

## 8. Limitations

*(Adapted from `README.md`'s "Honest limitations" and
`docs/DAILY_LOG.md`'s running list.)*

- Only 2 base task templates per the 120-task benchmark; diversity comes
  from parameter combinations, not genuinely distinct task families.
- `classify_malice` is a model-prompted heuristic, not validated against an
  oracle at the time of writing this draft — the oracle ablation
  (`SecureVoIOracle`) quantifies the gap once real-model data lands.
- Attacks in this benchmark are static per task; no adaptive attacker that
  updates against the deployed policy (relevant citation: "The Attacker
  Moves Second," flagged in `docs/04_references.md`).
- Simulator evidence establishes the trade-off's existence and policy
  ordering, not real-world deployment safety (stated identically in the
  threat model, Section 3).
- Injection-susceptibility is model-dependent (Section 7) — results should
  not be read as a universal claim across all open-weight models.

---

## 9. Conclusion

We argued that clarification-seeking in deployed language-model agents is
not only a question of how uncertain the agent is, but of who is likely to
answer. Conventional value-of-information reasoning, which decides whether
to ask purely from expected information gain against interaction cost, is
risk-blind by construction: our results show it improves benign task success
substantially but, on the same tasks, more than doubles the rate of unsafe
actions once the answering channel can be adversarial. SecureVoI closes
most of that gap by treating the *channel* the same way it treats the
*question* — as something to be chosen, not just consulted — and by
screening the specific answer that comes back before letting it influence
the agent's actions. On Mistral-Nemo-12B, this recovers the full benign
utility of the risk-blind policy while cutting adversarial unsafe actions by
83%, and it does so without collapsing into the trivially safe policy of
only ever trusting the authenticated user, which we show forfeits real
utility on tasks where that channel simply is not available.

Two results outside the main comparison are worth restating because they
complicate a simple story. First, injection-susceptibility is model-
dependent: Mistral-Nemo-12B and Llama-3.3-70B both exhibit the trade-off
this paper studies, while more heavily safety-tuned models we tested
resisted the injected instructions outright and showed little conventional-
clarification harm in the first place. A security-aware clarification
policy is not a substitute for a model that already declines to follow
instructions smuggled into a clarifying answer — it is a hedge for the
(currently common) case where the underlying model does not yet do that
reliably. Second, our post-hoc comparison between screening the *response*
(SecureVoI) and screening the resulting *action plan* after the agent has
already decided what to do with an accepted answer (Post-Hoc Guardrail)
suggests these are not strictly ordered: on our scripted pipeline check,
plan-level screening preserved more of the benign task under attack than
response-level screening did, because it never has to reject useful
information wholesale to stay safe. Whether that ordering holds on real
models, where legitimate and injected actions may be harder to cleanly
separate in a generated plan, is an open question this paper's real-model
runs are positioned to answer but had not yet settled at the time of
writing.

`[TODO]`: once the full model roster (Section 6) is locked, replace "on our
scripted pipeline check" above with the real-model finding, whichever
direction it goes — the honest result either way is the contribution, not a
predetermined one.

---

## Appendix: source map (for whoever converts this to LaTeX)

| Section | Primary source(s) |
|---|---|
| Abstract | `abstract.md` |
| Intro | Not yet drafted |
| Related Work | `docs/04_references.md` |
| Novelty | `docs/01_novelty_matrix.md` |
| Threat Model | `docs/02_threat_model.md` |
| Method | `secure_clarify/policies.py`, `estimators.py` docstrings |
| Benchmark | `docs/01_novelty_matrix.md`, `task_factory.py` |
| Experimental Setup | `docs/DAILY_LOG.md`, `REPRODUCIBILITY.md` |
| Results | `results/main_table.md`, `results/stats.json`, `figures/` |
| Limitations | `README.md`, `docs/DAILY_LOG.md` |
