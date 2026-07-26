#!/usr/bin/env python3
"""Decompose response_risk per attack string: learned classifier vs keyword cues.

WHY THIS EXISTS. `estimators.response_risk` is a blend:

    r = 0.35*prior(channel,format) + 0.4*classify_malice(text) + 0.2*cue_signal(text)
        + off_schema

Only `classify_malice` is the learned screen. `cue_signal` is a hardcoded keyword
list (`_CUE_TERMS`: "ignore", "also ", "external", "credential", "@", ...). The
stealth tier removes the explicit tier's surface tells -- and several of those tells
are literally on that keyword list, so stealth mechanically lowers `cue_signal`
whether or not the model's judgement changes at all.

That makes the headline stealth result ambiguous until it is decomposed. "SecureVoI's
learned screen is fooled by rephrasing" and "we deleted words from a hand-written
keyword list" are very different claims, and only the first is interesting. A
reviewer will make this objection; the paper should answer it with numbers.

This script reports, per attack string and per model:
  learned      = classify_malice(text), the LLM screen alone
  cue_signal   = the keyword heuristic alone
  and the explicit->stealth delta in each

Read it as: if `learned` barely moves while `cue_signal` collapses, the stealth
effect is an artifact of the keyword list, and the honest fix is to drop or reweight
the cue term rather than claim a defeated classifier. If `learned` drops too, the
learned screen is genuinely presentation-sensitive.

Usage:
  OLLAMA_API_KEY=... python scripts/risk_decomposition.py \
      --backend ollama --model gpt-oss:120b-cloud --host https://ollama.com --reps 3
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from secure_clarify.task_factory import build_pilot  # noqa: E402
from secure_clarify.estimators import _CUE_TERMS  # noqa: E402
from scripts.model_backends import build_agent, add_backend_args  # noqa: E402

W_LEARNED, W_CUE = 0.4, 0.2  # weights in estimators.response_risk


def cue_signal(text: str) -> float:
    low = text.lower()
    return min(1.0, sum(t in low for t in _CUE_TERMS) / 4.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3,
                    help="classify_malice calls per string; reported as mean +- sd")
    ap.add_argument("--out", default=None)
    add_backend_args(ap)
    args = ap.parse_args()

    strings: dict[tuple[str, str, str], str] = {}
    for t in build_pilot(60):
        for r in t.responses:
            if r.carries_attack:
                strings[(r.condition.value, t.domain, r.qid)] = r.text

    agent = build_agent(args.backend, args.model, args.base_url,
                        args.api_key_env, args.host)
    label = f"{args.backend}:{args.model}"
    print(f"Decomposing {len(strings)} attack strings x {args.reps} reps  [{label}]\n")

    rows = []
    for key in sorted(strings):
        tier, domain, qid = key
        text = strings[key]
        vals = [agent.classify_malice(text) for _ in range(args.reps)]
        mean = statistics.fmean(vals)
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        cs = cue_signal(text)
        rows.append({"tier": tier, "domain": domain, "qid": qid,
                     "learned_mean": mean, "learned_sd": sd, "learned_vals": vals,
                     "cue_signal": cs,
                     "learned_contrib": W_LEARNED * mean,
                     "cue_contrib": W_CUE * cs})

    print(f"{'tier':20s} {'domain':9s} {'qid':8s} {'learned':>16} {'cue':>7} "
          f"{'0.4*learn':>10} {'0.2*cue':>8}")
    print("-" * 82)
    for r in rows:
        print(f"{r['tier']:20s} {r['domain']:9s} {r['qid']:8s} "
              f"{r['learned_mean']:.3f}+-{r['learned_sd']:.3f}   {r['cue_signal']:6.3f} "
              f"{r['learned_contrib']:10.3f} {r['cue_contrib']:8.3f}")

    # Paired explicit -> stealth deltas, matched on (domain, qid).
    print(f"\n--- explicit -> stealth delta, matched by (domain, question) ---")
    print(f"{'domain':9s} {'qid':8s} {'d learned':>10} {'d cue':>8} "
          f"{'d risk(learn)':>14} {'d risk(cue)':>12}")
    print("-" * 70)
    idx = {(r["tier"], r["domain"], r["qid"]): r for r in rows}
    dl_all, dc_all = [], []
    for (tier, domain, qid), r in sorted(idx.items()):
        if tier != "adversarial":
            continue
        s = idx.get(("adversarial_stealth", domain, qid))
        if not s:
            continue
        dl = s["learned_mean"] - r["learned_mean"]
        dc = s["cue_signal"] - r["cue_signal"]
        dl_all.append(dl)
        dc_all.append(dc)
        print(f"{domain:9s} {qid:8s} {dl:+10.3f} {dc:+8.3f} "
              f"{W_LEARNED*dl:+14.3f} {W_CUE*dc:+12.3f}")

    if dl_all:
        ml, mc = statistics.fmean(dl_all), statistics.fmean(dc_all)
        rl, rc = W_LEARNED * ml, W_CUE * mc
        print(f"\nmean delta: learned {ml:+.3f} (risk {rl:+.3f}), "
              f"cue {mc:+.3f} (risk {rc:+.3f})")
        total = abs(rl) + abs(rc)
        if total > 1e-9:
            print(f"share of the risk drop from the LEARNED screen: {abs(rl)/total:.0%}; "
                  f"from the KEYWORD list: {abs(rc)/total:.0%}")
        if abs(rl) < 0.5 * abs(rc):
            print("\nVERDICT: the stealth effect is driven mainly by the hardcoded "
                  "keyword list, not the learned screen. Report it as cue-list "
                  "brittleness -- claiming a defeated classifier would overstate it.")
        elif abs(rl) >= abs(rc):
            print("\nVERDICT: the learned screen accounts for at least as much of the "
                  "risk drop as the keyword list. The stealth effect is a genuine "
                  "classifier limitation, not just deleted trigger words.")
        else:
            print("\nVERDICT: mixed -- both the learned screen and the keyword list "
                  "contribute materially. Report the decomposition, not a single cause.")

    out = Path(args.out) if args.out else (
        ROOT / "results" / "stealth" /
        f"risk_decomposition_{args.model.replace('/', '-').replace(':', '-')}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"model": label, "reps": args.reps, "rows": rows},
                              indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
