"""Persistent memoization of the agent's model calls.

WHY. `CachingAgent` memoizes in-process only, so every fresh process re-pays the
full cost of identical work: a single 81-task pass costs ~12 minutes of local
inference on `sample_intents` alone, and that tax lands on every diagnostic,
every ablation, and every re-run of an analysis whose inputs never changed. The
calls are pure functions at temperature 0, so recomputing them buys nothing.

SAFETY. Reusing a cached model call across processes is only sound if the key
captures *everything* that could change the answer. Three hazards, all handled:

1. TASK IDENTITY IS NOT TASK CONTENT. The in-process cache keys `sample_intents`
   on `(task_id, k)`. That is fine within one run but wrong across task files:
   `main_120.json` and `diversity_180.json` share all 120 of `file_*`/`cal_*`
   ids. They happen to be byte-identical today (verified), so nothing is
   currently broken -- but a disk cache would turn any future divergence into
   silent cross-contamination. Keys here hash the task's full JSON, so identity
   plays no part.

2. MODEL IDENTITY. A cached answer from one model must never be served to
   another. `model_id` is in the key.

3. STALE PROMPTS. If a prompt in `OpenModelAgent` is edited, previously cached
   answers correspond to a prompt that no longer exists. The key includes a
   fingerprint of the *source* of the agent's prompt-building methods, so any
   edit to them invalidates the cache automatically rather than silently serving
   answers to a question that is no longer asked.

OPT-IN. Disabled unless `SECURE_CLARIFY_CACHE` names a directory, so the default
code path is byte-identical to before and no published result can move by
accident. Enable with:

    SECURE_CLARIFY_CACHE=.cache/agent python3 scripts/whatever.py
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import threading
from pathlib import Path

_FINGERPRINT_METHODS = ("sample_intents", "classify_malice", "act",
                        "_gen", "_generate")


def agent_fingerprint(inner) -> str:
    """Identity of the model AND of the prompts used to query it."""
    parts = [type(inner).__name__, str(getattr(inner, "model_id", "?"))]
    for name in _FINGERPRINT_METHODS:
        fn = getattr(type(inner), name, None)
        if fn is None:
            continue
        try:
            parts.append(inspect.getsource(fn))
        except (OSError, TypeError):
            # a C function or a dynamically built callable: fall back to its
            # qualified name rather than pretending we fingerprinted it
            parts.append(f"<unsourceable {name}>")
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


class DiskCache:
    """Append-only JSONL store, loaded once per process and written through.

    JSONL rather than one file per entry: entries are small and numerous, and a
    single sequential read at startup beats thousands of stats. Append-only means
    a crash mid-write can lose at most the last line, which is then simply
    recomputed -- no corrupt state.
    """

    def __init__(self, directory: str | os.PathLike, fingerprint: str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{fingerprint}.jsonl"
        self._mem: dict[str, object] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    self._mem[rec["k"]] = rec["v"]
                except (json.JSONDecodeError, KeyError):
                    continue          # torn final line: recompute, don't crash

    def get(self, key: str, default=None):
        if key in self._mem:
            self.hits += 1
            return self._mem[key]
        self.misses += 1
        return default

    def __contains__(self, key: str) -> bool:
        return key in self._mem

    def put(self, key: str, value) -> None:
        with self._lock:
            self._mem[key] = value
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"k": key, "v": value},
                                    sort_keys=True, default=str) + "\n")

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"entries": len(self._mem), "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / total, 4) if total else None,
                "path": str(self.path)}


def make_key(method: str, *parts: str) -> str:
    h = hashlib.sha256()
    h.update(method.encode("utf-8"))
    for p in parts:
        h.update(b"\x00")
        h.update(str(p).encode("utf-8"))
    return h.hexdigest()


def cache_dir_from_env() -> str | None:
    d = os.environ.get("SECURE_CLARIFY_CACHE", "").strip()
    return d or None
