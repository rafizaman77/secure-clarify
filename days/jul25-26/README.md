# Jul 25-26 — Write full seven-page paper

**Status: ⬜ Not started** (only `abstract.md` exists; no `paper*.tex`)

## Section-by-section source map (what to pull from where)
| Paper section | Source material already in this repo |
|---|---|
| Intro / motivation | `README.md`'s plain-English overview |
| Related work | `docs/04_references.md` (verified citations + "how each thread grounds this repo's design") |
| Novelty / positioning | `docs/01_novelty_matrix.md`'s working novelty statement |
| Threat model | `docs/02_threat_model.md` (paste near-verbatim, it's already written for this purpose) |
| Method (SecureVoI) | `secure_clarify/policies.py` + `secure_clarify/estimators.py` docstrings, `docs/03_gonogo_memo.md`'s bug-fix lessons |
| Experimental setup | `docs/DAILY_LOG.md`'s Jul 17-19 entries, `results/main120_manifest.json` |
| Results | `results/main_table.md`, `results/stats.json`, `results/frontier.json` |
| Limitations | `docs/02_threat_model.md` §6 (explicit non-goals) + `docs/DAILY_LOG.md`'s "known, deliberately-not-hidden limitation" (2 task templates) + the oracle-vs-learned-risk caveat |

## Dependency
Needs Jul 20-24 real numbers and figures to write Results/Limitations
honestly — the related-work and method sections could technically be
drafted now, but should wait so citations/framing don't need rewriting
against real-model results.
