#!/usr/bin/env python3
"""Regenerate tasks/pilot_40.json from task_factory.build_pilot() and freeze the
dev/test split with a checksum (plan section 11: "freeze and checksum the test
file before tuning").

build_pilot() is deterministic (fixed random.seed in task_factory.py, no other
randomness), so re-running this after a task_factory change is how the frozen
JSON snapshot is kept in sync with the live generator -- it is never hand-edited.

Usage:
  python scripts/freeze_tasks.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from secure_clarify.task_factory import build_pilot  # noqa: E402


def main() -> int:
    tasks = build_pilot(n_per_domain=20)
    for t in tasks:
        t.validate()

    payload = [json.loads(t.to_json()) for t in tasks]
    tasks_path = ROOT / "tasks" / "pilot_40.json"
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
        "dev": {"n": len(dev), "task_ids": dev, "sha256": checksum(dev)},
        "test": {"n": len(test), "task_ids": test, "sha256": checksum(test)},
        "unassigned": other,
        "note": (
            "Pilot-scale split (n=40, ~20%/80%), frozen from build_pilot(). "
            "Re-freeze at n=120 for the Jul 17-19 development/test split; "
            "development-only choices (lambda, channel priors, prompt wording) "
            "must be tuned on the dev split only."
        ),
    }
    manifest_path = ROOT / "results" / "split_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {tasks_path.relative_to(ROOT)} ({len(tasks)} tasks: "
          f"{len(dev)} dev, {len(test)} test, {len(other)} unassigned)")
    print(f"Wrote {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
