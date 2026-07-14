#!/usr/bin/env python3
"""Regenerate a frozen task-set JSON from task_factory.build_pilot() and freeze
the dev/test split with a checksum (plan section 11: "freeze and checksum the
test file before tuning").

build_pilot() is deterministic (fixed random.seed in task_factory.py, no other
randomness), so re-running this after a task_factory change is how a frozen
JSON snapshot is kept in sync with the live generator -- it is never hand-edited.

Usage:
  python scripts/freeze_tasks.py
      # pilot scale (default): 40 tasks -> tasks/pilot_40.json (Jul 14-16)

  python scripts/freeze_tasks.py --n-per-domain 60 \
      --tasks-out tasks/main_120.json --manifest-out results/main120_manifest.json
      # main-experiment scale: 120 tasks, 24 dev / 96 test (Jul 17-19)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.task_factory import build_pilot  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-domain", type=int, default=20,
                    help="tasks per domain; 20 -> 40 total (pilot), 60 -> 120 total (main)")
    ap.add_argument("--tasks-out", default="tasks/pilot_40.json")
    ap.add_argument("--manifest-out", default="results/split_manifest.json")
    args = ap.parse_args()

    tasks = build_pilot(n_per_domain=args.n_per_domain)
    for t in tasks:
        t.validate()

    payload = [json.loads(t.to_json()) for t in tasks]
    tasks_path = ROOT / args.tasks_out
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    dev = sorted(t.task_id for t in tasks if t.split == "dev")
    test = sorted(t.task_id for t in tasks if t.split == "test")
    other = sorted(t.task_id for t in tasks if t.split not in {"dev", "test"})

    def checksum(task_ids: list[str]) -> str:
        h = hashlib.sha256()
        by_id = {t.task_id: t for t in tasks}
        for tid in task_ids:
            h.update(by_id[tid].to_json().encode("utf-8"))
        return h.hexdigest()

    manifest = {
        "n_tasks": len(tasks),
        "n_per_domain": args.n_per_domain,
        "tasks_file": args.tasks_out,
        "dev": {"n": len(dev), "task_ids": dev, "sha256": checksum(dev)},
        "test": {"n": len(test), "task_ids": test, "sha256": checksum(test)},
        "unassigned": other,
        "note": (
            "Frozen from build_pilot(); development-only choices (lambda, "
            "channel priors, prompt wording) must be tuned on the dev split "
            "only -- see scripts/tune_dev.py and results/dev_calibration.json."
        ),
    }
    manifest_path = ROOT / args.manifest_out
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {tasks_path.relative_to(ROOT)} ({len(tasks)} tasks: "
          f"{len(dev)} dev, {len(test)} test, {len(other)} unassigned)")
    print(f"Wrote {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
