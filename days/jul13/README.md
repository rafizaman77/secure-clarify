# Jul 13 — File/calendar simulators, verifiers, 20 tasks

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md))

## Goal
Build the executable environments and the automatic, non-LLM outcome checks
the whole benchmark depends on (the "Exec" axis from Jul 12's novelty matrix).

## Deliverables produced
| Artifact | What it is |
|---|---|
| `secure_clarify/simulators.py` | `FileEnv` / `CalendarEnv`, backed by an **immutable, append-only** action log |
| `secure_clarify/verifiers.py` | `goal_verifier` (final-state check) + `safety_verifier` (log-scan for prohibited actions) — both plain Python, no LLM judge |
| 20 tasks (10 file + 10 calendar) | Validated end-to-end |

## Key decision
The action log is append-only and immutable (`Action` is a frozen dataclass)
specifically so "unsafe = trajectory property" (from the Jul 12 threat model)
is actually enforceable: a `delete_file` on a protected file is logged even if
something later restores it. This is the concrete implementation of the
threat model's rule 5 ("reverting a bad `share_file` does not un-leak the
file").

## Definition of done
- [x] `FileEnv` + `CalendarEnv` implemented with an immutable log
- [x] `goal_verifier` + `safety_verifier` implemented, both non-LLM
- [x] ≥20 tasks validate

## Full narrative
See [docs/DAILY_LOG.md](../../docs/DAILY_LOG.md#jul-13--filecalendar-simulators-verifiers-20-tasks).
