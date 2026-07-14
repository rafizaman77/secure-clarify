# Novelty Matrix — Security-Aware Clarification for Agents

**Deliverable:** Jul 12. **Owner:** Student A (benchmark lead) drafts, both authors sign off.

The matrix records, for each closely related paper, whether it does the seven things this
project does. A `Y` means the paper does it; `n` means it does not; `~` means partial.
The point of the matrix is the **column of `n`s that only our row fills in**. If any single
prior paper earns `Y` on all seven, the contribution collapses to "secure question-format
and channel selection" and must be renarrated.

## The seven axes

1. **Ask?** — decides *whether* to ask vs. act (a real ask/act decision, not always-ask).
2. **What?** — chooses the *question* (format and/or content), not just a fixed template.
3. **Where?** — models *multiple channels* the answer can come from.
4. **Adv?** — permits *adversarial* clarification responses (not only benign/noisy).
5. **Util?** — assigns a *task-utility* function to the final action.
6. **Loss?** — assigns a *channel-dependent security loss* to the decision.
7. **Exec?** — evaluates *executable* outcomes (automatic verification, not LLM-judge-only).

## Matrix

| Work | Ask? | What? | Where? | Adv? | Util? | Loss? | Exec? | Closest contribution / gap |
|---|---|---|---|---|---|---|---|---|
| **VoI for Human-Agent Comm.** (Dong et al., 2601.06407) | Y | Y | n | n | Y | n | ~ | Utility vs. user cost; **no channel-dependent adversarial loss** |
| **ASPI** (Sehwag et al., 2605.17324) | ~ | n | ~ | Y | n | ~ | Y | Shows clarification *amplifies* injection; **diagnostic only, no prospective policy** |
| **SAGE-Agent / Structured Uncertainty** (Suri et al., 2511.08798) | Y | Y | ~ | n | Y | n | Y | POMDP + EVPI question selection; **cooperative-response assumption** |
| **Ask or Assume?** (2603.26233) | Y | ~ | n | n | Y | n | Y | Decouples underspec-detection from execution on SWE-bench; **no security dimension** |
| **Info-Gain Clarification** (2606.03135) | Y | Y | n | n | Y | n | ~ | Bayesian belief-update info-gain reward; **trusted answers assumed** |
| **CLAM** (Kuhn et al., 2212.07769) | Y | n | n | n | n | n | n | Foundational selective clarification; **single-turn QA, no agent/tools** |
| **ClarQ-LLM** (Gan et al., 2409.06097) | Y | Y | n | n | ~ | n | n | Clarification benchmark for task dialog; **no executable security consequence** |
| **Learning to Ask** (2409.00557) | Y | ~ | n | n | ~ | n | Y | Tool agents self-classify question relevance; **no channel/attacker model** |
| **InjecAgent** (Zhan et al., 2403.02691) | n | n | Y | Y | n | ~ | Y | Injection benchmark (direct-harm + exfil); **no clarification decision** |
| **AgentDojo** (Debenedetti et al., 2406.13352) | n | n | Y | Y | Y | ~ | Y | Dynamic tool-agent security env; **attacks are ambient, not clarification-induced** |
| **ToolEmu** (Ruan et al., 2309.15817) | n | n | ~ | ~ | n | Y | ~ | Emulated sandbox + risk eval for *underspecified* instructions; **LM-judge, no ask/channel policy** |
| **Instruction Hierarchy** (Wallace et al., 2404.13208) | n | n | Y | Y | n | ~ | n | Privilege ordering over instruction sources; **training-time, not a per-query ask decision** |
| **CaMeL** (Debenedetti et al., 2503.18813) | n | n | Y | Y | Y | Y | Y | Provable IFC/capabilities defense; **blocks flows, does not decide whether to acquire info** |
| **Agent-SafetyBench** (Zhang et al., 2412.14470) | n | n | ~ | Y | n | ~ | Y | Behavioral agent-safety benchmark; **not focused on clarification decisions** |
| **→ THIS WORK (SecureVoI)** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | Prospective *whether/what/where* decision under channel-dependent adversarial risk + response acceptance |

## Reading of the matrix

- The VoI / clarification cluster (rows 1–8) is strong on **Ask/What/Util** and empty on
  **Where/Loss** — they assume the answer arrives from one trusted counterpart.
- The security cluster (rows 9–14) is strong on **Where/Adv/Exec** and empty on **Ask/What** —
  they treat injection as ambient contamination of tool output, not as a consequence the agent
  *chose* by deciding to ask a particular question on a particular channel.
- **CaMeL is the sharpest foil.** It also has channels, attacks, utility, loss, and execution —
  but it is a *defense that constrains data flow after information is acquired*. It never
  decides whether acquiring the information was worth the exposure. That "acquire-decision"
  is our cell. Say this explicitly in related work so a reviewer does not file us under
  "weaker CaMeL."
- **ASPI is the sharpest priority claim.** It reports the phenomenon (clarification amplifies
  injection) but stops at measurement. Our H1/H2 reproduce their effect as a *sanity check*,
  then H3/H4 go past it with a prospective policy. Cite ASPI as the motivating observation,
  not as something we beat on their axis.

## Working novelty statement (freeze this wording)

> Prior work either optimizes clarification under cooperative-response assumptions or evaluates
> security consequences after clarification. We study the prospective decision problem of
> *whether, what, and where* to ask when channels differ in information quality, interaction
> cost, and adversarial risk, and we pair the pre-inquiry decision with a response-acceptance
> stage so that the policy is not a final-output guardrail.

## Falsification test for the novelty (run before writing the intro)

Search the eight query strings in the plan (§2 "search using"). If a returned paper earns `Y`
on all of {Ask, What, Where, Adv}, the general framing is taken — narrow to *secure
question-format + channel selection* and re-run this matrix on that narrower claim.
