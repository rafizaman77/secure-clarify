#!/usr/bin/env python3
"""Dump `secure_clarify.adaptive_tasks.build_adaptive_task_set()` to
`tasks/adaptive_attacks_8.json`, the same on-disk shape as `main_120.json` /
`families_120.json`, so it is a drop-in `--tasks` argument for
`scripts/screened_ablation.py` and `scripts/confirmatory_tests.py`.

FINDINGS.md open item (Step 6, #3): "Adaptive attacks are built but never run
as episodes." This is the missing link -- turns the 8 minimal-cue attack texts
in `adaptive_attacks.py` into runnable Task objects.

Usage:
  python scripts/build_adaptive_task_set.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.adaptive_tasks import build_adaptive_task_set  # noqa: E402
from secure_clarify.schema import Enum  # noqa: E402


def _enc(o):
    if isinstance(o, Enum):
        return o.value
    raise TypeError(type(o))


def main() -> int:
    tasks = build_adaptive_task_set()
    out = ROOT / "tasks" / "adaptive_attacks_8.json"
    out.write_text(json.dumps([asdict(t) for t in tasks], default=_enc, indent=2) + "\n",
                   encoding="utf-8")
    print(f"wrote {len(tasks)} tasks to {out.relative_to(ROOT)}")
    for t in tasks:
        print(f"  {t.task_id}  {t.family}  split={t.split}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
