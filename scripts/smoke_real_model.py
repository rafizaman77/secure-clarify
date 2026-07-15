#!/usr/bin/env python3
"""Sanity check: run ONE task end-to-end through a REAL model backend before
trusting it for the full tune_dev.py / run_primary.py runs. This is the
"confirm one task runs end-to-end with a real model" step from
docs/03_gonogo_memo.md's Jul 16 next-steps list.

Prints the full trace (raw model output at each of the three OpenModelAgent
calls, the question/channel/plan chosen, goal/safety outcome) so a human can
eyeball whether the model is doing something sane before spending the API
budget / CPU time on the full grid.

Usage (hosted API, e.g. Groq -- fast, recommended if no local GPU):
  export GROQ_API_KEY=...
  python scripts/smoke_real_model.py --backend openai \
      --base-url https://api.groq.com/openai/v1/chat/completions \
      --api-key-env GROQ_API_KEY --model llama-3.1-8b-instant

Usage (local, free, requires `ollama serve` + `ollama pull llama3.1:8b`):
  python scripts/smoke_real_model.py --backend ollama --model llama3.1:8b

Usage (local, free, no Ollama -- just transformers + a small model; this repo
uses .venv_model/ for this since the system Python's numpy/sklearn is broken):
  python scripts/smoke_real_model.py --backend hf_local --model Qwen/Qwen2.5-0.5B-Instruct
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.schema import Condition, load_task  # noqa: E402
from secure_clarify.policies import SecureVoI  # noqa: E402
from secure_clarify.runner import run_episode  # noqa: E402
from scripts.model_backends import build_agent, add_backend_args  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    add_backend_args(ap)
    ap.add_argument("--tasks", default="tasks/pilot_40.json")
    ap.add_argument("--task-id", default=None, help="default: first task in the file")
    ap.add_argument("--condition", choices=["benign", "adversarial"], default="adversarial")
    args = ap.parse_args()

    agent = build_agent(args.backend, args.model, args.base_url,
                        args.api_key_env, args.host)
    data = json.loads((ROOT / args.tasks).read_text(encoding="utf-8"))
    tasks = [load_task(d) for d in data]
    task = tasks[0] if args.task_id is None else next(
        t for t in tasks if t.task_id == args.task_id)

    print(f"Backend: {args.backend}:{args.model}")
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
