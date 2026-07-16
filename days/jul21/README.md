# Jul 21 — Abstract submission

**Status: ✅ Done** (tracked automatically — see [PROGRESS.md](../../PROGRESS.md);
`_abstract_has_placeholders()` found zero bracketed placeholders left in
`abstract.md` as of the Jul 20 real-number fill)

## What "Done" means here, precisely
`scripts/update_progress.py` can only verify the *artifact* — that
`abstract.md` has no `[X]`-style placeholders and the numbers in it trace to
a real `agent_backend`. It cannot verify the actual submission action.

## Definition of done
- [x] `abstract.md` has 0 bracketed placeholders
- [x] Numbers in the abstract match `results/main_table.md` exactly (verified
      manually: 100pp benign lift, 0%→50% unsafe range, 100% benign recovery,
      83% unsafe reduction — all trace to `results/stats.json`)
- [ ] **Submitted through the AAAI-27 portal** — this is the one remaining
      human action item; nothing in the repo can verify it.

## Dependency
Was 100% downstream of [jul20](../jul20/README.md) — now unblocked.
