# References — Security-Aware Clarification for Agents

Organized by the paper's threads. Each entry notes **why it's cited** and a
**verification status**:

- ✅ **verified** — I confirmed title/authors/arXiv id against arXiv/Semantic Scholar/OpenReview this session.
- 📄 **from your list** — carried from your curated set; confirm the id before camera-ready (some ids in your list look like future-dated placeholders, e.g. 2603.*, 2606.*, 2605.* — check them).
- ⚠️ **check id** — plausible paper but the arXiv id needs verification.

---

## 1. Clarification-seeking / Value-of-Information (prior + competing methods)

- **Value of Information for Human-Agent Communication** — Dong et al. 📄 (arXiv:2601.06407 per your plan).
  *Your closest VoI precedent on the utility-vs-user-cost axis; the paper it does NOT do is channel-dependent adversarial loss. Primary foil.*

- **Structured Uncertainty-Guided Clarification (SAGE-Agent)** — Suri et al., arXiv:2511.08798. ⚠️ check id
  *Models joint tool-argument clarification as a POMDP with an EVPI objective. Your SecureVoI extends the same EVPI/VoI machinery; cite as the non-adversarial ancestor of the pre-inquiry stage.*

- **Ask or Assume? Uncertainty-Aware Clarification-Seeking in Coding Agents** — arXiv:2603.26233. 📄
  *Ask-vs-act on underspecified SWE-bench; decouples underspecification detection from execution. Cite as "assumes trustworthy answers."*

- **Uncertainty-Aware Clarification with Information Gain** — arXiv:2606.03135. 📄
  *Information-gain reward via Bayesian belief update toward the ground-truth goal. Trusted-answer assumption.*

- **CLAM: Selective Clarification for Ambiguous Questions** — Kuhn, Gal, Farquhar, arXiv:2212.07769. ⚠️ check id
  *Foundational selective clarification; single-turn, no tools/agent. Establishes the "ask only when necessary" lineage.*

- **CLAMBER** (arXiv:2405.12063) and **Ambig-DS** (arXiv:2605.09698). 📄
  *Ambiguity-identification benchmarks; use for benchmark-design comparison.*

- **Learning to Ask: When LLM Agents Meet Unclear Instruction** — arXiv:2409.00557. ⚠️ check id
  *Tool agents self-classify clarifying-question relevance; no channel/attacker model.*

- **ClarQ-LLM: A Benchmark for Clarifying and Requesting Information in Task-Oriented Dialog** — Gan et al., arXiv:2409.06097. 📄
  *Clarification benchmark without executable security consequence — the gap you fill with automatic verification.*

- **Clarify When Necessary** (Zhang & Choi, NAACL Findings 2025) and **Modeling Future Conversation Turns** (arXiv:2410.13788). 📄
  *Standard "utility vs. interaction cost" framing for the intro.*

## 2. Prompt injection / agent security (threat model + attack taxonomy)

- **InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated LLM Agents** — Zhan et al., arXiv:2403.02691. ⚠️ check id
  *1,054 test cases; direct-harm vs. data-exfiltration split. Direct precedent for your attack-success-rate metric.*

- **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents** — Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr, NeurIPS 2024, arXiv:2406.13352. ✅ verified
  *97 tasks / 629 security test cases pairing benign tasks with injected attacker tasks. The standard tool-agent security benchmark; position your benchmark relative to it (theirs: ambient injection in tool output; yours: injection the agent invites by asking).*

- **Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection** — Greshake et al. ⚠️ check id (commonly arXiv:2302.12173)
  *Canonical origin of indirect prompt injection.*

- **The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions** — Wallace et al., arXiv:2404.13208. ⚠️ check id
  *Privilege ordering over instruction sources; grounds your channel-trust ranking (user > delegated > tool > forwarded > compromised).*

- **From Prompt Injections to Protocol Exploits** — arXiv:2506.23260. 📄
  *Categorizes 30+ attack techniques with formal attacker-capability/objective formulations. Structural template for your threat-model table.*

- **A Survey on Agentic Security: Applications, Threats and Defenses** (arXiv:2510.06445) and **The Landscape of Prompt Injection Threats in LLM Agents** (arXiv:2602.10453). 📄
  *Broad surveys for a single scope-setting related-work paragraph.*

- **LLM Agents Should Employ Security Principles** — arXiv:2505.24019. 📄
  *Design-principles paper; real-world dollar-impact framing.*

## 3. Value of information under adversarial / noisy channels (SecureVoI formalization)

- **Value of Information-based Deceptive Path Planning Under Adversarial Interventions** — arXiv:2503.24284. 📄
  *Closest formal precedent to "VoI minus an adversarial penalty" outside the LLM literature. Primary decision-theoretic ancestor of your λ·E[L] term.*

- **A Bayesian-network Cybersecurity Adversarial Risk Analysis Framework** — Ríos Insua et al. tradition, arXiv:2106.00471. 📄
  *Grounds the security-loss term in established adversarial risk analysis rather than presenting it as ad hoc.*

- **Provably Invincible Adversarial Attacks on RL Systems: A Rate-Distortion View** — arXiv:2510.13792. 📄
  *Information-theoretic framing of channel corruption; RL-specific, cite only if you formalize channel capacity.*

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
