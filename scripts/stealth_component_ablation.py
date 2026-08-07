#!/usr/bin/env python3
"""Which response_risk component actually detects a STEALTH attack?

Step 27 originally ran the full ablation grid on Mistral-Nemo-12B and concluded
the learned classifier "contributes nothing". That conclusion was an artifact:
Mistral's screen rejects 0/20 stealth attacks no matter what, so no change to
response_risk can move any outcome there.

This restricts the ablation to the cases that can actually discriminate -- the
tasks where SecureVoI asks DIRECTLY on the attacked channel, so the benign and
adversarial answers differ only in text -- and runs it per model. On gpt-oss-20b,
whose screen does fire on stealth, the answer reverses: the learned term is the
entire mechanism (16/20; 0/20 without it) and the prior and lexical cues are
redundant.

Cheap by construction: every model call it needs is already in the disk cache
from scripts/attacked_channel_audit.py, so this runs in seconds with zero
inference.

Usage:
  SECURE_CLARIFY_CACHE=.cache/agent python3 scripts/stealth_component_ablation.py \
      --model gpt-oss-20b-cloud --backend ollama \
      --backend-model gpt-oss:20b-cloud --host https://ollama.com
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, Channel, load_task  # noqa: E402
from secure_clarify.agent import CachingAgent  # noqa: E402
from secure_clarify.policies import SecureVoI  # noqa: E402
from secure_clarify.runner import find_response  # noqa: E402
from secure_clarify import estimators as E  # noqa: E402
from scripts.model_backends import build_agent  # noqa: E402

ALL = {"prior", "learned", "cue", "off_schema"}
ABLATIONS = [("full", None, False),
             ("no_learned", ALL - {"learned"}, True),
             ("no_cue", ALL - {"cue"}, True),
             ("no_prior", ALL - {"prior"}, True),
             ("learned_only", {"learned"}, True),
             ("cue_only", {"cue"}, True)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--backend-model", default="mistral-nemo:12b")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--cache", default=".cache/agent")
    ap.add_argument("--out", default="results/stealth_component_ablation.json")
    args = ap.parse_args()

    calib = json.loads((ROOT / f"results/models/{args.model}/dev_calibration.json")
                       .read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    priors = {Channel(c): p for c, p in calib["fitted_channel_priors"].items()}

    agent = CachingAgent(build_agent(args.backend, args.backend_model,
                                     args.base_url, args.api_key_env, args.host),
                         disk_cache_dir=args.cache or None)
    pol = SecureVoI(lam=lam)
    tasks = [t for t in (load_task(d) for d in
                         json.loads((ROOT / args.tasks).read_text(encoding="utf-8")))
             if t.split == "test"]

    E.set_priors(priors)
    E.set_risk_components()
    cases = []
    for t in tasks:
        d = pol.decide(t, agent)
        if not (d.ask and d.question is not None and d.channel is not None):
            continue
        r = find_response(t, d.question, d.channel, Condition.ADVERSARIAL_STEALTH)
        if r is None or not r.carries_attack:
            continue
        rb = find_response(t, d.question, d.channel, Condition.BENIGN)
        cases.append((t, d.question, d.channel, r, rb))

    rows = {}
    for label, comps, renorm in ABLATIONS:
        E.set_priors(priors)
        E.set_risk_components(comps, renorm)
        rej = sum(1 for t, q, c, r, _ in cases
                  if not pol.accept(t, q, c, r.text, agent))
        ben = sum(1 for t, q, c, _, rb in cases
                  if rb is not None and pol.accept(t, q, c, rb.text, agent))
        rows[label] = {"attack_rejected": rej, "benign_accepted": ben,
                       "n": len(cases),
                       "reject_rate": round(rej / len(cases), 4) if cases else None}
    E.set_risk_components()

    dest = ROOT / args.out
    existing = {}
    if dest.exists():
        try:
            existing = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing[args.model] = {"lambda": lam, "n_cases": len(cases), "ablations": rows}
    dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    print(f"\n{args.model} (lambda={lam}) -- {len(cases)} attacked-channel STEALTH cases")
    print(f"  {'ablation':14s} {'attack rejected':>16s} {'benign accepted':>16s}")
    for label, _, _ in ABLATIONS:
        s = rows[label]
        print(f"  {label:14s} {s['attack_rejected']:>13d}/{s['n']:<2d} "
              f"{s['benign_accepted']:>13d}/{s['n']:<2d}")
    st = agent.disk_stats()
    if st:
        print(f"  cache: {st['hits']} hits / {st['misses']} misses")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
