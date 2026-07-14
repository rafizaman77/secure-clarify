#!/usr/bin/env python3
"""Regenerate the README.md 'Schedule & progress' table from real repo state.

Usage:
  python scripts/update_progress.py          # print table; exit 1 if README differs
  python scripts/update_progress.py --write  # rewrite the table in README.md

Do not hand-edit the schedule table. If a status looks wrong, fix row() here.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows consoles default to cp1252, which can't encode the emoji status
# markers; force UTF-8 stdout so --write doesn't crash on the summary print.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
HEADING = "## 📅 Schedule & progress"
STATE_PATH = ROOT / "results" / "progress_state.json"

DONE = "✅ Done"
PARTIAL = "🟡 Partial"
NOT_STARTED = "⬜ Not started"


def _exists(*relpaths: str) -> bool:
    return all((ROOT / p).exists() for p in relpaths)


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def _load_tasks() -> list[dict]:
    tasks: list[dict] = []
    for path in sorted((ROOT / "tasks").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            tasks.extend(data)
        elif isinstance(data, dict):
            tasks.append(data)
    return tasks


def _n_tasks() -> int:
    return len(_load_tasks())


def _splits_assigned() -> bool:
    tasks = _load_tasks()
    if not tasks:
        return False
    return all(t.get("split") in {"dev", "test"} for t in tasks)


def _split_counts() -> tuple[int, int, int]:
    tasks = _load_tasks()
    dev = sum(1 for t in tasks if t.get("split") == "dev")
    test = sum(1 for t in tasks if t.get("split") == "test")
    other = len(tasks) - dev - test
    return dev, test, other


def _open_model_methods_implemented() -> bool:
    """True iff OpenModelAgent's three methods no longer raise NotImplementedError."""
    src = _read("secure_clarify/agent.py")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "OpenModelAgent":
            needed = {"sample_intents", "classify_malice", "act"}
            found: set[str] = set()
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if item.name not in needed:
                    continue
                raises_ni = any(
                    isinstance(stmt, ast.Raise)
                    and isinstance(stmt.exc, ast.Call)
                    and isinstance(stmt.exc.func, ast.Name)
                    and stmt.exc.func.id == "NotImplementedError"
                    for stmt in item.body
                )
                if raises_ni:
                    return False
                found.add(item.name)
            return found == needed
    return False


def _class_names(relpath: str) -> set[str]:
    tree = ast.parse(_read(relpath))
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def _def_names(relpath: str) -> set[str]:
    tree = ast.parse(_read(relpath))
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _smoke_passes() -> bool:
    try:
        proc = subprocess.run(
            [sys.executable, "test_smoke.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.returncode == 0 and "ALL SMOKE TESTS PASSED" in (proc.stdout or "")
    except (OSError, subprocess.TimeoutExpired):
        return False


def _memo_has_go() -> bool:
    path = ROOT / "docs" / "03_gonogo_memo.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"(?i)\b(decision:\s*go|verdict:\s*go|\*\*GO\*\*)\b", text))


def _abstract_has_placeholders() -> bool:
    path = ROOT / "abstract.md"
    if not path.exists():
        return True
    return bool(re.search(r"\[[A-Z]\]", path.read_text(encoding="utf-8")))


def row(date: str, deliverable: str) -> tuple[str, str]:
    """Return (status, evidence) for one schedule row from real repo state."""
    n = _n_tasks()
    classes_agent = _class_names("secure_clarify/agent.py") if _exists("secure_clarify/agent.py") else set()
    classes_pol = _class_names("secure_clarify/policies.py") if _exists("secure_clarify/policies.py") else set()
    defs_sim = _def_names("secure_clarify/simulators.py") if _exists("secure_clarify/simulators.py") else set()
    # simulators use classes FileEnv/CalendarEnv
    sim_classes = _class_names("secure_clarify/simulators.py") if _exists("secure_clarify/simulators.py") else set()
    defs_ver = _def_names("secure_clarify/verifiers.py") if _exists("secure_clarify/verifiers.py") else set()
    open_ok = _open_model_methods_implemented()
    splits_ok = _splits_assigned()
    dev_n, test_n, other_n = _split_counts()
    smoke = _smoke_passes()

    if date == "Jul 12":
        bits = [
            _exists("docs/01_novelty_matrix.md"),
            _exists("docs/02_threat_model.md"),
            _exists("secure_clarify/schema.py"),
            n >= 10,
        ]
        if all(bits):
            return DONE, f"docs/01–02, schema.py, {n} tasks"
        if any(bits):
            missing = []
            if not bits[0]:
                missing.append("novelty matrix")
            if not bits[1]:
                missing.append("threat model")
            if not bits[2]:
                missing.append("schema")
            if not bits[3]:
                missing.append(f"tasks={n}<10")
            return PARTIAL, "missing: " + ", ".join(missing)
        return NOT_STARTED, "—"

    if date == "Jul 13":
        bits = [
            "FileEnv" in sim_classes,
            "CalendarEnv" in sim_classes,
            "goal_verifier" in defs_ver,
            "safety_verifier" in defs_ver,
            n >= 20,
        ]
        if all(bits):
            return DONE, f"FileEnv/CalendarEnv, both verifiers, {n} tasks"
        if any(bits):
            return PARTIAL, f"sims={ {c for c in ('FileEnv','CalendarEnv') if c in sim_classes} }, verifs={ {d for d in ('goal_verifier','safety_verifier') if d in defs_ver} }, tasks={n}"
        return NOT_STARTED, "—"

    if date == "Jul 14":
        needed = {"NeverAsk", "ConventionalVoI", "TrustedOnly", "SecureVoI"}
        have = needed & classes_pol
        bits = [
            have == needed,
            _exists("secure_clarify/estimators.py"),
            n >= 40,
            "ScriptedAgent" in classes_agent,
        ]
        if all(bits):
            return DONE, f"4 policies, estimators, ScriptedAgent, {n} tasks"
        if any(bits) or have:
            return PARTIAL, f"policies={sorted(have)}, tasks={n}"
        return NOT_STARTED, "—"

    if date == "Jul 15":
        bits = [
            _exists("run_pilot.py"),
            _exists("results/pilot_summary.json"),
            _exists("docs/03_gonogo_memo.md"),
            smoke,
        ]
        # "Two-model pilot" requires OpenModelAgent to be real, not NotImplemented.
        if all(bits) and open_ok:
            return DONE, "pilot results + OpenModelAgent + smoke pass"
        if all(bits):
            return PARTIAL, "scripted pilot+audit+smoke OK; OpenModelAgent still NotImplemented"
        if any(bits):
            return PARTIAL, f"run_pilot={bits[0]}, summary={bits[1]}, memo={bits[2]}, smoke={bits[3]}"
        return NOT_STARTED, "—"

    if date == "Jul 16":
        go = _memo_has_go()
        freeze_bits = _exists(
            "secure_clarify/schema.py",
            "secure_clarify/simulators.py",
            "secure_clarify/verifiers.py",
            "docs/01_novelty_matrix.md",
            "docs/02_threat_model.md",
        )
        if go and freeze_bits and splits_ok and smoke:
            return DONE, f"GO + freeze artifacts + split assigned (dev={dev_n}, test={test_n})"
        if go or freeze_bits or n > 0:
            return PARTIAL, (
                f"GO={go}, freeze_files={freeze_bits}, "
                f"splits assigned={splits_ok} (dev={dev_n}, test={test_n}, other={other_n})"
            )
        return NOT_STARTED, "—"

    if date == "Jul 17-18":
        bits = [n >= 120, open_ok, splits_ok]
        if all(bits):
            return DONE, f"{n} tasks, OpenModelAgent live, splits set"
        if any(bits) or n >= 40:
            return PARTIAL, f"tasks={n}/120, open_model={open_ok}, splits={splits_ok}"
        return NOT_STARTED, "—"

    if date == "Jul 19":
        has_primary = _exists("results/primary_summary.json") or any(
            (ROOT / "results").glob("primary*.json")
        ) if (ROOT / "results").exists() else False
        if splits_ok and open_ok and has_primary:
            return DONE, "splits frozen + primary results present"
        if splits_ok or open_ok or has_primary:
            return PARTIAL, f"splits={splits_ok}, open_model={open_ok}, primary={has_primary}"
        return NOT_STARTED, "—"

    if date == "Jul 20":
        has_stats = _exists("results/stats.json") or _exists("results/main_table.json")
        abstract_ok = _exists("abstract.md") and not _abstract_has_placeholders()
        if has_stats and abstract_ok and _exists("results/frontier.json"):
            return DONE, "stats + filled abstract + frontier"
        if has_stats or _exists("abstract.md") or _exists("results/frontier.json"):
            return PARTIAL, (
                f"frontier={_exists('results/frontier.json')}, "
                f"abstract placeholders={_abstract_has_placeholders() if _exists('abstract.md') else 'missing'}, "
                f"stats={has_stats}"
            )
        return NOT_STARTED, "—"

    if date == "Jul 21":
        if _exists("abstract.md") and not _abstract_has_placeholders():
            return DONE, "abstract.md filled with real numbers"
        if _exists("abstract.md"):
            return PARTIAL, "abstract.md present but still has [N]/X]-style placeholders"
        return NOT_STARTED, "—"

    if date == "Jul 22-23":
        has_ablation = any((ROOT / "results").glob("*ablation*")) if (ROOT / "results").exists() else False
        if open_ok and has_ablation:
            return DONE, "ablation results present"
        if open_ok or has_ablation:
            return PARTIAL, f"open_model={open_ok}, ablation_files={has_ablation}"
        return NOT_STARTED, "—"

    if date == "Jul 24":
        if _exists("docs/failure_analysis.md") and any(
            (ROOT / "figures").glob("*") if (ROOT / "figures").exists() else []
        ):
            return DONE, "failure analysis + figures/"
        if _exists("docs/failure_analysis.md") or (ROOT / "figures").exists():
            return PARTIAL, "partial failure-analysis/figures artifacts"
        return NOT_STARTED, "—"

    if date == "Jul 25-26":
        paper = list(ROOT.glob("paper*.tex")) + list(ROOT.glob("**/main.tex"))
        if paper:
            return DONE, str(paper[0].relative_to(ROOT))
        if _exists("abstract.md"):
            return PARTIAL, "abstract only; no paper*.tex yet"
        return NOT_STARTED, "—"

    if date == "Jul 27":
        if _exists("REPRODUCIBILITY.md") and _exists("CITATIONS.md"):
            return DONE, "REPRODUCIBILITY.md + CITATIONS.md"
        if _exists("REPRODUCIBILITY.md") or _exists("CITATIONS.md") or _exists("docs/04_references.md"):
            return PARTIAL, "refs present; repro/citation audit artifacts incomplete"
        return NOT_STARTED, "—"

    if date == "Jul 28":
        if _exists("SUBMISSION.md") or _exists("camera_ready"):
            return DONE, "submission marker present"
        return NOT_STARTED, "—"

    return NOT_STARTED, f"unknown date key: {date}"


SCHEDULE: list[tuple[str, str]] = [
    ("Jul 12", "Novelty matrix, threat model, schemas, 10 seed tasks"),
    ("Jul 13", "File/calendar simulators, verifiers, 20 tasks"),
    ("Jul 14", "Four policies, 40 pilot tasks, matched responses"),
    ("Jul 15", "Two-model pilot and full unsafe-trajectory audit"),
    ("Jul 16", "Go/no-go, freeze method, split tasks"),
    ("Jul 17-18", "120 tasks, development runs, tune lambda and priors"),
    ("Jul 19", "Freeze development choices; primary test runs"),
    ("Jul 20", "Statistics, main table, frontier, real abstract"),
    ("Jul 21", "Abstract submission"),
    ("Jul 22-23", "Third model, ablations, robustness subset"),
    ("Jul 24", "Failure analysis and final figures"),
    ("Jul 25-26", "Write full seven-page paper"),
    ("Jul 27", "Revision, anonymity, reproduction, citation audit"),
    ("Jul 28", "Full paper and supplement submission"),
]


def build_table() -> str:
    lines = [
        "| Date | Deliverable | Status | Evidence |",
        "|---|---|---|---|",
    ]
    for date, deliverable in SCHEDULE:
        status, evidence = row(date, deliverable)
        # keep evidence compact for the table
        evidence = evidence.replace("|", "/")
        lines.append(f"| {date} | {deliverable} | {status} | {evidence} |")
    lines.append("")
    lines.append(
        "_This table is auto-generated by `scripts/update_progress.py` from repo state. "
        "Do not hand-edit. Fix `row()` if a status is wrong._"
    )
    lines.append("")
    return "\n".join(lines)


def _extract_section_span(text: str, heading: str) -> tuple[int, int] | None:
    """Return [start, end) character span of content AFTER heading until next ##."""
    idx = text.find(heading)
    if idx < 0:
        return None
    content_start = idx + len(heading)
    # skip a single newline after the heading
    if content_start < len(text) and text[content_start] == "\n":
        content_start += 1
    rest = text[content_start:]
    m = re.search(r"^## ", rest, flags=re.MULTILINE)
    content_end = content_start + (m.start() if m else len(rest))
    return content_start, content_end


def render_progress_block() -> str:
    return build_table()


def read_current_table_from_readme() -> str | None:
    text = README.read_text(encoding="utf-8")
    span = _extract_section_span(text, HEADING)
    if span is None:
        return None
    start, end = span
    return text[start:end]


def write_table(table: str) -> None:
    text = README.read_text(encoding="utf-8")
    span = _extract_section_span(text, HEADING)
    if span is None:
        raise SystemExit(
            f"README.md missing heading {HEADING!r}. Add it before running --write."
        )
    start, end = span
    new_text = text[:start] + table + text[end:]
    README.write_text(new_text, encoding="utf-8")


def load_prev_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(statuses: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(statuses, indent=2) + "\n", encoding="utf-8")


def collect_statuses() -> dict[str, str]:
    return {date: row(date, deliverable)[0] for date, deliverable in SCHEDULE}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write",
        action="store_true",
        help="Rewrite the Schedule & progress table in README.md",
    )
    args = ap.parse_args()

    table = render_progress_block()
    statuses = collect_statuses()
    prev = load_prev_state()

    changed = []
    for date, status in statuses.items():
        old = prev.get(date)
        if old is not None and old != status:
            changed.append(f"{date}: {old} -> {status}")
        elif old is None:
            changed.append(f"{date}: (new) -> {status}")

    if args.write:
        write_table(table)
        save_state(statuses)
        print("Wrote schedule table to README.md")
        if changed:
            print("Status changes:")
            for c in changed:
                print(" ", c)
        return 0

    # dry-run / check mode
    print(table)
    current = read_current_table_from_readme()
    if current is None:
        print("README missing schedule heading.", file=sys.stderr)
        return 1
    # Normalize trailing whitespace for comparison
    if current.strip() != table.strip():
        print(
            "README schedule table differs from regenerated output.",
            file=sys.stderr,
        )
        return 1
    print("README schedule table matches regenerated output.")
    if changed and prev:
        print("Note: statuses changed since last --write, but README already matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
