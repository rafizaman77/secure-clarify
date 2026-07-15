# Jul 24 — Failure analysis and final figures

**Status: ⬜ Not started**

## Definition of done
- [ ] `docs/failure_analysis.md` — read through every `unsafe=True` or
      `goal_ok=False` episode in `results/primary_episodes.json` (once
      real-model) and categorize failure modes (e.g. off-schema response
      exploited, restricted-format bypass, over-cautious abstention)
- [ ] `figures/` directory with the paper's plots: safety-utility frontier
      (from `results/frontier.json`), main-table bar chart, per-policy
      unsafe-rate by channel
- [ ] Cross-reference: does the failure taxonomy line up with
      `secure_clarify.schema.AttackType`, or does a real model expose a
      failure mode the 7 attacker objectives from
      [docs/02_threat_model.md](../../docs/02_threat_model.md) don't cover?

## Dependency
Needs real-model episode data (`results/primary_episodes.json` from a real
backend) — a failure analysis of `ScriptedAgent`'s failures would analyze the
heuristic's bugs, not a language model's behavior.
