#!/usr/bin/env python3
"""Sanity check: run ONE task end-to-end through a REAL model backend before
trusting it for the full tune_dev.py / run_primary.py runs. This is the
"confirm one task runs end-to-end with a real model" step from
docs/03_gonogo_memo.md's Jul 16 next-steps list.

Prints the full trace (question asked, channel, raw model output at each of
the three OpenModelAgent calls, resolved intent, tool plan, goal/safety
outcome) so a human can eyeball whether the model is doing something sane
before spending the API budget / CPU time on the full grid.

Usage (hosted API, e.g. Groq -- fast, recommended if no local GPU):
  export GROQ_API_KEY=...
  python scripts/smoke_real_model.py --backend openai \
      --base-url https://api.groq.com/openai/v1/chat/completions \
      --api-key-env GROQ_API_KEY --model llama-3.1-8b-instant

Usage (local, free, requires `ollama serve` + `ollama pull llama3.1:8b`):
  python scripts/smoke_real_model.py --backend ollama --model llama3.1:8b
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, load_task  # noqa: E402
from secure_clarify.agent import OpenModelAgent  # noqa: E402
from secure_clarify.policies import SecureVoI  # noqa: E402
from secure_clarify.runner import run_episode  # noqa: E402
from scripts.model_backends import openai_compatible_generate_fn, ollama_generate_fn  # noqa: E402


def build_agent(args) -> OpenModelAgent:
    if args.backend == "openai":
        api_key = os.environ.get(args.api_key_env, "")
        if not api_key:
            raise SystemExit(
                f"Set {args.api_key_env} in your environment first "
                f"(export {args.api_key_env}=... / $env:{args.api_key_env}='...')."
            )
        gen = openai_compatible_generate_fn(base_url=args.base_url, api_key=api_key,
                                            model=args.model)
    elif args.backend == "ollama":
        gen = ollama_generate_fn(model=args.model, host=args.host)
    else:
        raise SystemExit(f"Unknown --backend {args.backend!r}")
    return OpenModelAgent(model_id=args.model, generate_fn=gen)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["openai", "ollama"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="https://api.groq.com/openai/v1/chat/completions")
    ap.add_argument("--api-key-env", default="GROQ_API_KEY")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--tasks", default="tasks/pilot_40.json")
    ap.add_argument("--task-id", default=None, help="default: first task in the file")
    ap.add_argument("--condition", choices=["benign", "adversarial"], default="adversarial")
    args = ap.parse_args()

    agent = build_agent(args)
    data = json.loads((ROOT / args.tasks).read_text(encoding="utf-8"))
    tasks = [load_task(d) for d in data]
    task = tasks[0] if args.task_id is None else next(
        t for t in tasks if t.task_id == args.task_id)

    print(f"Task: {task.task_id} ({task.domain}/{task.family}, stakes={task.stakes})")
    print(f"Request: {task.initial_request}")
    print(f"Ambiguities: {task.ambiguities}")
    print(f"Condition: {args.condition}\n")

    print("--- calling sample_intents (used by every policy's info-gain estimate) ---")
    hyps = agent.sample_intents(task, k=3)
    print(json.dumps(hyps, indent=2))

    print("\n--- running one SecureVoI episode ---")
    condition = Condition(args.condition)
    ep = run_episode(task, condition, SecureVoI(lam=1.0), agent)
    print(f"asked={ep.asked} channel={ep.channel} qformat={ep.qformat} accepted={ep.accepted}")
    print(f"goal_ok={ep.goal_ok} unsafe={ep.unsafe} attack_success={ep.attack_success} "
          f"utility={ep.utility}")
    if ep.reasons:
        print(f"safety_verifier reasons: {ep.reasons}")

    print("\nIf this looks sane (a real question, a plausible tool plan, no crash), "
          "the backend is ready for scripts/tune_dev.py and scripts/run_primary.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
