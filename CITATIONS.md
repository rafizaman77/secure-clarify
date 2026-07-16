# Citations

Full citation list, verification status, and per-thread grounding notes live
in **[docs/04_references.md](docs/04_references.md)** — this file is the
Jul 27 audit checkpoint, not a duplicate bibliography.

## Verification status summary

| Status | Count | Meaning |
|---|---|---|
| ✅ verified | 22 | Fetched and confirmed directly against the arXiv abstract page (title/authors/claims), not recalled from training data. Session date 2026-07-14/16. |
| 📄 from your list | 3 | Carried from the curated source list; not yet independently fetched against arXiv. |
| ⚠️ check id | 2 | Plausible paper, arXiv id still needs verification before camera-ready. |

(Counts as of the last `docs/04_references.md` update — recount if that file
changes before submission.)

## Audit checklist before camera-ready

- [x] Every "✅ verified" entry checked directly against its arXiv abstract
      page this session (not memory-recalled) — see `docs/04_references.md`'s
      per-entry notes.
- [x] Two mischaracterizations caught and corrected (SAGE-Agent's abstract
      does not itself claim a POMDP formulation; Ambig-DS is about
      data-science agents, not dialog systems).
- [ ] Remaining "📄 from your list" (3) and "⚠️ check id" (2) entries fetched
      and verified the same way.
- [ ] BibTeX entries in `docs/04_references.md` cross-checked against the
      final in-text citation list once `paper.tex` exists (Jul 25-26) — no
      cited-but-not-in-bibliography or vice versa.
- [ ] Venue-specific citation style/format applied (AAAI uses its own BibTeX
      style file — confirm before submission).

## Anonymity note (if double-blind)

`docs/04_references.md` and this file do not currently name this project's
authors in a way that would need redaction. Check `README.md`, `PROGRESS.md`,
and git commit history/author metadata separately before an anonymous
submission — those DO currently contain author names (Rafi Zaman, Anagh
Sangavarapu) and are out of scope for this file's audit.
