# Jul 27 — Revision, anonymity, reproduction, citation audit

**Status: 🟡 Partial** — citation-audit half has a running start.

## What's already done
`docs/04_references.md`'s verification pass (this session): every paper in
the curated list was fetched and checked directly against its arXiv abstract
page (not recalled from memory), two mischaracterizations were caught and
fixed (SAGE-Agent's POMDP claim, Ambig-DS's domain). This is most of a
citation audit already.

## What's not done
- [ ] `REPRODUCIBILITY.md` — should document: exact commands to regenerate
      every result file (`scripts/freeze_tasks.py` → `tune_dev.py` →
      `run_primary.py` → `compute_stats.py` → `make_main_table.py`), the
      checksum manifests that prove the test split was never touched during
      tuning, and the model/version pinned for the final run.
- [ ] `CITATIONS.md` / final BibTeX pass — `docs/04_references.md` has a
      BibTeX section for the already-verified entries; needs the remaining
      "📄 from your list" entries verified the same way before camera-ready.
- [ ] Anonymity pass — strip author-identifying paths/comments if the venue
      requires double-blind submission.
