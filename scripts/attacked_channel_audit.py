#!/usr/bin/env python3
"""Does the stage-2 screen discriminate CONTENT, or only on the explicit tier?

The manuscript's answer to "isn't SecureVoI just channel avoidance?" is a
per-episode audit: on the tasks where SecureVoI asks *directly on the attacked
channel*, it accepts the benign answer and rejects the adversarial one --
"identical channel, opposite decision, driven by content."

That audit is run on the EXPLICIT adversarial tier. This script reruns exactly
the same audit on BOTH tiers, because the headline safety result is reported on
the STEALTH tier, and Step 8 found the learned classifier flags 0/12 stealth
attacks while scoring them *below* ordinary benign text. If the screen does not
discriminate on stealth, the mechanism claim cannot be carried over to it.

Reproduces the manuscript's figure exactly on Mistral-Nemo-12B, test split:
20 tasks on the attacked channel, benign accepted 20/20, explicit adversarial
rejected 13/20 -- matching the reported "(Mistral: 13/20)" -- while the same 20
tasks give 0/20 on stealth.

Usage:
  python scripts/attacked_channel_audit.py --model mistral-nemo-12b \
      --backend ollama --backend-model mistral-nemo:12b
  GROQ_API_KEY=... python scripts/attacked_channel_audit.py --model llama-3.3-70b \
      --backend openai --backend-model llama-3.3-70b-versatile \
      --base-url https://api.groq.com/openai/v1/chat/completions \
      --api-key-env GROQ_API_KEY
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

TIERS = (Condition.ADVERSARIAL, Condition.ADVERSARIAL_STEALTH)


def audit(tasks, pol, agent) -> dict:
    """Per tier: among tasks asked ON the attacked channel, how often is the
    benign answer accepted and the attack rejected?

    The benign comparison uses the SAME (task, question, channel), so the only
    thing differing between the two decisions is the answer text -- which is what
    makes this a test of content discrimination rather than of routing.
    """
    out = {}
    for cond in TIERS:
        n = ben = rej = 0
        for t in tasks:
            d = pol.decide(t, agent)
            if not (d.ask and d.question is not None and d.channel is not None):
                continue
            r = find_response(t, d.question, d.channel, cond)
            if r is None or not r.carries_attack:
                continue                      # must be ON the attack to compare
            n += 1
            rb = find_response(t, d.question, d.channel, Condition.BENIGN)
            if rb is not None and pol.accept(t, d.question, d.channel, rb.text, agent):
                ben += 1
            if not pol.accept(t, d.question, d.channel, r.text, agent):
                rej += 1
        out[cond.value] = {
            "on_attacked_channel": n,
            "benign_accepted": ben,
            "attack_rejected": rej,
            "reject_rate": round(rej / n, 4) if n else None,
            "benign_accept_rate": round(ben / n, 4) if n else None,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="results/models/<name>/ dir")
    ap.add_argument("--tasks", default="tasks/main_120.json")
    ap.add_argument("--split", default="test", choices=["test", "all"],
                    help="the manuscript's audit is on the test split")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--backend-model", default="mistral-nemo:12b")
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--cache", default=".cache/agent")
    ap.add_argument("--out", default="results/attacked_channel_audit.json")
    args = ap.parse_args()

    calib = json.loads((ROOT / f"results/models/{args.model}/dev_calibration.json")
                       .read_text(encoding="utf-8"))
    lam = calib["chosen_lambda"]
    E.set_priors({Channel(c): p for c, p in calib["fitted_channel_priors"].items()})

    tasks = [load_task(d) for d in
             json.loads((ROOT / args.tasks).read_text(encoding="utf-8"))]
    if args.split == "test":
        tasks = [t for t in tasks if t.split == "test"]

    agent = CachingAgent(build_agent(args.backend, args.backend_model,
                                     args.base_url, args.api_key_env, args.host),
                         disk_cache_dir=args.cache or None)
    res = audit(tasks, SecureVoI(lam=lam), agent)

    dest = ROOT / args.out
    existing = {}
    if dest.exists():
        try:
            existing = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    if not isinstance(existing, dict) or "tiers" in existing:
        existing = {}          # supersede the single-model format
    existing[args.model] = {"lambda": lam, "split": args.split,
                            "n_tasks": len(tasks), "tiers": res}
    dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    print(f"\n{args.model}  (lambda={lam}, {args.split} split, {len(tasks)} tasks)")
    print(f"  {'tier':22s} {'on attacked chan':>17s} {'benign acc':>12s} {'ATTACK rej':>12s}")
    for cond in TIERS:
        s = res[cond.value]
        n = s["on_attacked_channel"]
        print(f"  {cond.value:22s} {n:17d} {s['benign_accepted']:>9d}/{n:<2d} "
              f"{s['attack_rejected']:>9d}/{n:<2d}")
    st = agent.disk_stats()
    if st:
        print(f"  cache: {st['hits']} hits / {st['misses']} misses")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
