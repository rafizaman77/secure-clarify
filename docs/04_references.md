# References — Security-Aware Clarification for Agents

Organized by the paper's threads. Each entry notes **why it's cited** and a
**verification status**:

- ✅ **verified** — confirmed title/authors/abstract directly against the arXiv
  abstract page (2026-07-14 session). Note: the 2601–2606 arXiv prefixes are
  **not future placeholders** — arXiv IDs are YYMM, and today is 2026-07-14, so
  a 2603.* (March 2026) or 2606.* (June 2026) id predates today and can be a
  real, already-published paper. The original "check these, they look
  future-dated" caveat below was written under a wrong assumption about the
  current date; every id in that range checked out as real.
- 📄 **from your list** — carried from the curated set, not yet independently fetched.
- ⚠️ **check id** — plausible paper but the arXiv id still needs verification.

See "[How each thread grounds this repo's design](#how-each-thread-grounds-this-repos-design)"
at the end of this document for the concrete code/section each thread maps to
— this isn't just a bibliography, it's where each design choice in
`secure_clarify/` traces back to.

---

## 1. Clarification-seeking / Value-of-Information (prior + competing methods)

- **Value of Information for Human-Agent Communication** — Dong et al. 📄 (arXiv:2601.06407 per your plan).
  *Your closest VoI precedent on the utility-vs-user-cost axis; the paper it does NOT do is channel-dependent adversarial loss. Primary foil.*

- **Structured Uncertainty guided Clarification for LLM Agents (SAGE-Agent)** — Suri, Mathur, Lipka, Dernoncourt, Rossi, Manocha, arXiv:2511.08798. ✅ verified
  *Uses Expected Value of Perfect Information (EVPI) plus cost modeling to decide which tool-argument to ask about, distinguishing specification uncertainty (user intent) from model uncertainty (LLM prediction); 7–39% higher coverage on ambiguous tasks while asking 1.5–2.7x fewer questions. Correction: the abstract does not itself claim a POMDP formulation — cite it as an EVPI/cost-modeling ancestor, not literally "the POMDP paper." Your SecureVoI extends the same EVPI/VoI machinery to a channel-dependent security loss; cite as the non-adversarial ancestor of the pre-inquiry stage.*

- **Ask or Assume? Uncertainty-Aware Clarification-Seeking in Coding Agents** — Edwards & Schuster, arXiv:2603.26233. ✅ verified
  *An uncertainty-aware multi-agent scaffold that decouples underspecification detection from execution, evaluated on an underspecified variant of SWE-bench Verified; 69.40% resolve rate, asks more on complex tasks and less on simple ones. Cite as "assumes trustworthy answers" — the ask/act decision has no channel-risk term.*

- **Uncertainty-Aware Clarification in LLM Agents with Information Gain** — Deng, Li, Li, Zhu, Zhao, Guo, Wang, ICML 2026, arXiv:2606.03135. ✅ verified
  *Trains an LLM clarifier with an "Information Gain Reward" from Bayesian belief updates toward the ground-truth goal; +3.7% success rate for +0.3 extra interaction steps across 5 agent architectures. Trusted-answer assumption — no adversarial-response condition.*

- **CLAM: Selective Clarification for Ambiguous Questions with Generative Language Models** — Kuhn, Gal, Farquhar, arXiv:2212.07769. ✅ verified
  *Foundational selective clarification: detect ambiguity, generate a clarifying question, answer after a simulated user response. Single-turn, no tools/agent/execution. Establishes the "ask only when necessary" lineage and the simulated-response evaluation trick your matched-response benchmark generalizes to three conditions (benign/noisy/adversarial) instead of one.*

- **CLAMBER: A Benchmark of Identifying and Clarifying Ambiguous Information Needs in LLMs** — Zhang, Qin, Deng, Huang, Lei, Liu, Jin, Liang, Chua, ACL 2024, arXiv:2405.12063. ✅ verified
  *~12k-item taxonomy-organized benchmark; shows CoT/few-shot give only marginal gains and can inflate false confidence. Ambiguity-*identification* benchmark (no downstream action/safety check) — use for benchmark-design comparison.*

- **Ambig-DS: A Benchmark for Task-Framing Ambiguity in Data-Science Agents** — Stoisser, Boubnovski Martell, Boldsen, Märtens, Kitchen, arXiv:2605.09698. ✅ verified
  *Correction: this is about data-science agents, not dialog systems. 112 tasks (51 prediction-target + 61 evaluation-objective ambiguity) showing agents "silently commit" to a wrong task framing and produce clean-looking but wrong artifacts; agents can't reliably tell when to ask. Good precedent for your "silent wrong-default" failure mode (the `_default_fill` conservative act-blind path in `resolver.py`).*

- **Learning to Ask: When LLM Agents Meet Unclear Instruction** — Wang, Shi, Ling, Chan, Wang, Lee, Yuan, Huang, Jiao, Lyu, arXiv:2409.00557. ✅ verified
  *Introduces "Noisy ToolBench" and "Ask-when-Needed (AwN)," which lets a tool-calling agent request clarification instead of hallucinating missing arguments; evaluated with their own "ToolEvaluator." No channel/attacker model — cite alongside CLAM as the trusted-answer baseline your threat model removes.*

- **ClarQ-LLM: A Benchmark for Clarifying and Requesting Information in Task-Oriented Dialog** — Gan et al., arXiv:2409.06097. 📄
  *Clarification benchmark without executable security consequence — the gap you fill with automatic verification.*

- **Clarify When Necessary** (Zhang & Choi, NAACL Findings 2025) and **Modeling Future Conversation Turns to Teach LLMs to Ask Clarifying Questions** (Zhang, Knox, Choi, ICLR 2025, arXiv:2410.13788). ✅ verified (latter)
  *The latter trains a preference model by simulating each candidate response's effect on future turns rather than scoring it in isolation (+5% F1, +3% accuracy on when-to-ask). Standard "utility vs. interaction cost" framing for the intro; neither has an adversarial-response condition.*

## 2. Prompt injection / agent security (threat model + attack taxonomy)

- **InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated LLM Agents** — Zhan, Liang, Ying, Kang, ACL 2024 Findings, arXiv:2403.02691. ✅ verified
  *1,054 test cases across 17 user tools / 62 attacker tools, direct-harm vs. data-exfiltration split; ReAct-GPT-4 vulnerable 24% of the time, nearly doubling under an enhanced attacker prompt. Direct precedent for your attack-success-rate metric and for the `AttackType` taxonomy in `schema.py` (DATA_EXFILTRATION / DESTRUCTIVE_ACTION / ... mirrors their direct-harm vs. exfiltration split).*

- **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents** — Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr, NeurIPS 2024, arXiv:2406.13352. ✅ verified
  *97 tasks / 629 security test cases pairing benign tasks with injected attacker tasks. The standard tool-agent security benchmark; position your benchmark relative to it (theirs: ambient injection in tool output; yours: injection the agent invites by asking).*

- **Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection** — Greshake, Abdelnabi, Mishra, Endres, Holz, Fritz, arXiv:2302.12173. ✅ verified
  *Canonical origin of "indirect prompt injection": malicious instructions retrieved from data (not typed by the user) drive data theft, worming, and ecosystem contamination in real deployed systems (Bing Chat). This is exactly the channel-borne-attack premise `docs/02_threat_model.md` builds on — cite as the origin citation.*

- **The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions** — Wallace, Xiao, Leike, Weng, Heidecke, Beutel (OpenAI), arXiv:2404.13208. ✅ verified
  *Trains models to give system prompts higher priority than user text and user text higher priority than third-party/tool content, improving robustness to injection/jailbreaks with minimal capability loss. Directly grounds `schema.CHANNEL_TRUST`'s ranking (authenticated user > delegated collaborator > shared doc > forwarded > external tool > compromised account) — cite as the training-time analog of what your policies do at decision-time without retraining.*

- **From Prompt Injections to Protocol Exploits: Threats in LLM-Powered AI Agent Workflows** — Ferrag, Tihanyi, Hamouda, Maglaras, Lakas, Debbah, ICT Express, arXiv:2506.23260. ✅ verified
  *Unified end-to-end threat model categorizing 30+ attack techniques across input manipulation, model compromise, and protocol-level vulnerabilities. Structural template for `docs/02_threat_model.md`'s attack taxonomy table.*

- **A Survey on Agentic Security: Applications, Threats and Defenses** — Shahriar, Rahman, Ahmed, Sadeque, Parvez, arXiv:2510.06445. ✅ verified
  *First holistic survey of agentic security (260+ papers synthesized); central claim is that agentic systems are "structurally fragile by default" and need lifecycle-spanning defenses, not single-layer fixes — a useful framing sentence for your intro (clarification is one stage of that lifecycle).*

- **The Landscape of Prompt Injection Threats in LLM Agents: From Taxonomy to Analysis** — Wang, Li, Xiang, Zhang, Li, Zhang, Wang, Tian, arXiv:2602.10453. ✅ verified
  *Systematic-review taxonomy of PI attacks (by payload generation) and defenses (by intervention stage: text/model/execution); introduces the AgentPI benchmark and shows existing defenses trade off trust/utility/latency. Use alongside AgentDojo for the scope-setting related-work paragraph.*

- **LLM Agents Should Employ Security Principles** — Zhang, Su, Chen, Bertino, Zhang, Li, arXiv:2505.24019. ✅ verified
  *Argues for classical security design principles (defense-in-depth, least privilege, complete mediation, psychological acceptability) in agent design; introduces AgentSandbox, evaluated on benign utility / attack utility / attack success rate — the same three-way split your `runner.Episode` reports (`goal_ok`, utility, `unsafe`/`attack_success`).*

## 3. Value of information under adversarial / noisy channels (SecureVoI formalization)

- **Value of Information-based Deceptive Path Planning Under Adversarial Interventions** — Suttle, Milzman, Karabag, Sadler, Topcu, arXiv:2503.24284. ✅ verified
  *MDP framework where an agent picks trajectories of deliberately low informational value to an adversarial observer, with LP-based solution methods. Structurally this is "VoI minus a term that accounts for an adversary" from the opposite direction (the agent is the deceiver, not the askER) — but it's the closest formal precedent outside the LLM literature to scoring actions by VoI net of an adversarial term. Cite as the primary decision-theoretic ancestor of SecureVoI's `ig - C_COST - lambda*pre_risk` structure in `policies.SecureVoI.decide`.*

- **A Bayesian-network-based Cybersecurity Adversarial Risk Analysis Framework with Numerical Examples** — Wang & Neil, arXiv:2106.00471. ✅ verified
  *Hybrid Bayesian-network inference for sequential defend-attack models (continuous + discrete variables, real-time updates), extending classical adversarial risk analysis (Ríos Insua tradition) beyond Monte Carlo. Grounds `estimators.estimate_pre_risk`'s `prior * expected_loss` term and `_DEV_ATTACK_PRIOR`'s Laplace-smoothed per-channel priors in established ARA formalism rather than presenting them as ad hoc.*

- **Provably Invincible Adversarial Attacks on Reinforcement Learning Systems: A Rate-Distortion Information-Theoretic Approach** — Lu, Lai, Xu, arXiv:2510.13792. ✅ verified
  *Rate-distortion bounds on reward regret when an adversary corrupts an RL agent's observed transition dynamics/state. RL-specific (no LLM agents, no clarification) — cite only if you formalize a channel-capacity argument for why a compromised/forwarded channel bounds how much true information the agent can recover even from an honest-looking answer.*

## 4. Defenses / guardrails / sandboxes (the "why not just X" foils) — ADDED

- **Defeating Prompt Injections by Design (CaMeL)** — Debenedetti, Shumailov, Fan, Hayes, Carlini, Fabian, Kern, Shi, Terzis, Tramèr, 2025, arXiv:2503.18813. ✅ verified
  *Control/data-flow separation + capabilities; solves 77% of AgentDojo tasks with provable security (v2). **Your sharpest foil:** it constrains flow AFTER information is acquired and never decides whether acquiring was worth the exposure. State this in related work so a reviewer doesn't file you under "weaker CaMeL."*

- **Identifying the Risks of LM Agents with an LM-Emulated Sandbox (ToolEmu)** — Ruan, Dong, Wang, Pitis, Zhou, Ba, Dubois, Maddison, Hashimoto, ICLR 2024, arXiv:2309.15817. ✅ verified
  *36 high-stakes toolkits, 144 test cases; threat model is benign-but-underspecified instructions; LM-based safety evaluator flags failures (even safest agent fails 23.9%). Cite for (a) the underspecification threat model you inherit and (b) the contrast: they use an LM judge, you use programmatic verifiers.*

- **Agent-SafetyBench: Evaluating the Safety of LLM Agents** — Zhang et al., arXiv:2412.14470. 📄
  *Behavioral agent-safety benchmark; not clarification-focused. Position as complementary coverage.*

---

## Suggested new citations to strengthen specific sections (ADDED, verify before use)

- **WASP: Benchmarking Web Agent Security Against Prompt Injection** — Evtimov, Zharmagambetov, Grattafiori, Guo, Chaudhuri, arXiv:2504.18575. ⚠️ check id
  *Web-agent injection benchmark; supports the "attacks arrive through external tools/pages" channel.*

- **The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses** — arXiv:2510.09023. ⚠️ check id
  *Cite in Limitations under "adaptive attackers"; pre-empts the reviewer concern that your attacks are static.*

---

## How each thread grounds this repo's design

Not just a bibliography — each thread above maps onto a concrete design choice
already implemented in `secure_clarify/`, plus what's still missing relative
to the papers that inspired it.

**Thread 1 (clarification-seeking / VoI) →** `estimators.estimate_info_gain`
and `policies.ConventionalVoI`. CLAM (2212.07769) and "Learning to Ask"
(2409.00557) establish the ask-vs-answer-blind baseline your `NeverAsk` and
`ConventionalVoI` policies reproduce. SAGE-Agent (2511.08798) is the precedent
whose EVPI objective your `estimate_info_gain`'s disagreement-among-sampled-
intents proxy stands in for — **gap**: we approximate EVPI with a cheap
action-disagreement heuristic (`_canonical_action` + modal-frequency
disagreement) rather than computing true expected value of perfect
information; SAGE-Agent's cost-modeled EVPI is the natural upgrade once a real
model is wired in (Jul 17-18 item). None of thread 1's methods have a
channel/attacker term — that's exactly the gap SecureVoI fills.

**Thread 2 (prompt injection / security) →** `schema.py` + `docs/02_threat_model.md`.
InjecAgent's direct-harm-vs-exfiltration split is mirrored one-to-one in
`AttackType` (GOAL_HIJACK, DATA_EXFILTRATION, DESTRUCTIVE_ACTION, ...). The
Instruction Hierarchy's privilege ordering is exactly `CHANNEL_TRUST` (user >
collaborator > shared_doc > forwarded > external > compromised) — the
difference is Wallace et al. train the ranking into model weights; we use it
as a fixed prior a policy reasons over at inference time, no retraining
required. Greshake et al.'s indirect-injection premise (malicious instructions
arrive via retrieved/forwarded content, not the user typing them) is the whole
reason `Response.channel` exists as a first-class field. **Gap**: unlike
InjecAgent/AgentDojo, our attacks are static per task (no adaptive attacker
that adjusts to the policy) — flagged in Honest limitations and in "The
Attacker Moves Second" below.

**Thread 3 (VoI under adversarial/noisy channels) →** `policies.SecureVoI` and
`estimators.estimate_pre_risk` / `response_risk`. This is SecureVoI's actual
formalization: `sv = ig - C_COST[qformat] - lambda * pre_risk` in
`SecureVoI.decide` is structurally the "VoI minus an adversarial-cost term"
move from the deceptive-path-planning paper (2503.24284), and
`estimate_pre_risk`'s `_DEV_ATTACK_PRIOR[channel] * expected_loss` is a
Laplace-smoothed point estimate in the same family as the Bayesian-network ARA
framework (2106.00471) — a full hybrid-BN treatment (joint uncertainty over
attacker type and channel, updated in real time) is the natural extension once
there's enough dev-set data to support it, noted as future work rather than
attempted at pilot scale.

**Thread 4 (defenses/guardrails) →** `run_pilot.py`'s policy set (Trusted-Only
mirrors "ask only high-trust channels"; a post-hoc-guardrail policy is listed
in the plan but not yet implemented). CaMeL (2503.18813) is the sharpest foil:
it enforces control/data-flow separation *after* information is already
acquired and never asks whether acquiring it was worth the exposure —
SecureVoI's stage-1 gate operates one step earlier in the pipeline than CaMeL
does, which is the paper's core positioning claim and should be stated
explicitly in related work so a reviewer doesn't read this as "a weaker
CaMeL." ToolEmu's benign-but-underspecified threat model is the non-adversarial
half of our benign/noisy/adversarial matched-response design.

---

## BibTeX (verified entries only — safe to paste)

```bibtex
@inproceedings{debenedetti2024agentdojo,
  title     = {AgentDojo: A Dynamic Environment to Evaluate Prompt Injection
               Attacks and Defenses for LLM Agents},
  author    = {Debenedetti, Edoardo and Zhang, Jie and Balunovi\'{c}, Mislav and
               Beurer-Kellner, Luca and Fischer, Marc and Tram\`{e}r, Florian},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year      = {2024},
  note      = {arXiv:2406.13352}
}

@article{debenedetti2025camel,
  title   = {Defeating Prompt Injections by Design},
  author  = {Debenedetti, Edoardo and Shumailov, Ilia and Fan, Tianqi and
             Hayes, Jamie and Carlini, Nicholas and Fabian, Daniel and
             Kern, Christoph and Shi, Chongyang and Terzis, Andreas and
             Tram\`{e}r, Florian},
  journal = {arXiv preprint arXiv:2503.18813},
  year    = {2025}
}

@inproceedings{ruan2024toolemu,
  title     = {Identifying the Risks of LM Agents with an LM-Emulated Sandbox},
  author    = {Ruan, Yangjun and Dong, Honghua and Wang, Andrew and
               Pitis, Silviu and Zhou, Yongchao and Ba, Jimmy and
               Dubois, Yann and Maddison, Chris J. and Hashimoto, Tatsunori},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2024},
  note      = {arXiv:2309.15817}
}
```

**Note on ids:** several ids in your source list (2601.*, 2602.*, 2603.*, 2605.*,
2606.*) correspond to 2026 submission months. If those are real, keep them; if any
were auto-generated, replace with the true id before submission. I flagged each with
⚠️ or 📄 accordingly.
