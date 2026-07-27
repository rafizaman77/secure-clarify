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
      and verified the same way. **Deliberately excluded from `references.bib`
      as of 2026-07-27** rather than cited on unconfirmed grounds — none of
      them were needed by the current in-text citation set, so this is safe
      to leave open unless a future revision adds a claim that needs one.
- [x] BibTeX entries cross-checked against the final in-text citation list
      (2026-07-27, commit `0edd300`) — `references.bib` has exactly the 10
      ✅-verified entries `paper.tex` actually cites (`\citep{}` x16, 10
      unique keys), wired via `\bibliography{references}`. Compiled through
      the full pdflatex→bibtex→pdflatex→pdflatex cycle: 0 errors, 0 undefined
      citations, bibtex raised no warnings. No entry is present in the .bib
      without being cited, and no citation in the text lacks a matching entry.
- [x] Venue-specific citation style applied: `aaai2027.sty` auto-sets
      `\bibliographystyle{aaai2027}` when natbib is loaded (confirmed by
      reading the .sty source, not assumed) — `aaai2027.bst` renders all 10
      entries correctly (author lists, titles, years, venue where noted).
      **Still open:** AAAI-27's actual page limit is not verified anywhere in
      this repo. Adding the bibliography moved the compiled paper from 6 to 7
      pages (a References section is real content, not free) — check against
      the actual AAAI-27 call for papers before submission, not assumed to
      fit.

## Anonymity note (if double-blind)

`docs/04_references.md` and this file do not currently name this project's
authors in a way that would need redaction. Check `README.md`, `PROGRESS.md`,
and git commit history/author metadata separately before an anonymous
submission — those DO currently contain author names (Rafi Zaman, Anagh
Sangavarapu) and are out of scope for this file's audit.
