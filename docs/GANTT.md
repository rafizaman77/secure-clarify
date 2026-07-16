# AAAI-27 Project Timeline (Gantt)

GitHub renders the chart below natively (Mermaid). Status bars reflect real
repo state as of this writing — cross-check against the auto-generated
[PROGRESS.md](../PROGRESS.md) table, which is the source of truth; this chart
is a visual project-management view of the same facts, not an independent
tracker. Days are per-task-item, not strictly calendar days — Jul 17-19 in
particular ran as one continuous engineering push (see
[docs/DAILY_LOG.md](DAILY_LOG.md)), shown here on its planned calendar slots.

```mermaid
gantt
    title Security-Aware Clarification for Agents -- AAAI-27
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d
    todayMarker off

    section Foundations (done)
    Novelty matrix + threat model        :done, f1, 2026-07-12, 1d
    Simulators + verifiers                :done, f2, 2026-07-13, 1d
    Policies + estimators + pilot tasks   :done, f3, 2026-07-14, 1d

    section Pilot (done)
    Pilot run + unsafe-trajectory audit   :done, p1, 2026-07-15, 1d
    Go/no-go (GO) + freeze + split        :done, p2, 2026-07-16, 1d

    section Main experiment (done)
    Scale to 120 tasks (24 dev/96 test)   :done, m1, 2026-07-17, 1d
    Dev-only lambda + prior calibration   :done, m2, 2026-07-17, 1d
    Primary test-split run                :done, m3, 2026-07-18, 1d
    Real open-weight model backend        :done, m4, 2026-07-18, 2d
    Bootstrap stats + main table          :done, m5, 2026-07-19, 1d
    Real abstract numbers                 :done, m6, 2026-07-20, 1d

    section Writing & submission (abstract done; rest not started)
    Abstract submission                   :milestone, done, w1, 2026-07-21, 0d
    Third model + 2 more policies         :active, w2, 2026-07-22, 2d
    Oracle-vs-learned-risk ablation       :w3, 2026-07-22, 2d
    Stochastic-repetition robustness      :w4, 2026-07-22, 2d
    Failure analysis + figures            :w5, 2026-07-24, 1d
    Seven-page paper draft                :w6, 2026-07-25, 2d
    Revision + reproducibility + citations :w7, 2026-07-27, 1d
    Full submission                       :milestone, w8, 2026-07-28, 0d
```

## What the critical path actually was (now closed)

**Wiring a real open-weight model into `OpenModelAgent`** was the one
dependency every downstream box (m6 through w1) sat behind — closed Jul 18-19
using `ollama:mistral-nemo:12b` locally (no rate limits, deterministic),
after a hosted Groq route hit a free-tier daily token cap mid-run on the test
grid (validated on dev only — `results/models/llama-3.3-70b/`). Held-out
verdict: **GO**, both central comparisons significant at p<0.001. Full
account of the eight bugs that surfaced only once a real model touched the
pipeline: [days/jul17-18/README.md](../days/jul17-18/README.md).

**The new critical path is Jul 22-23**: a second/third *test-split-complete*
model and the two unimplemented baselines (confidence-threshold, post-hoc
guardrail) are what Jul 25-26's paper draft and Jul 27's revision now sit
behind.

```mermaid
flowchart LR
    A["Real model backend\n(ollama:mistral-nemo:12b)"] --> B["tune_dev.py\n(dev calibration, lambda=0.75)"]
    B --> C["run_primary.py\n(test-split run, verdict GO)"]
    C --> D["compute_stats.py\n(bootstrap CIs, p<0.001)"]
    D --> E["make_main_table.py"]
    E --> F["abstract.md filled"]
    F --> G["Jul 21: abstract submitted"]
    C --> H["Jul 24: failure analysis\n(needs real episodes -- have them now)"]
    A --> I["Jul 22-23: 2nd/3rd test-split model +\n2 more policies + ablations"]
    G --> J["Jul 25-26: paper draft"]
    H --> J
    I --> J
    J --> K["Jul 27: revision + repro"]
    K --> L["Jul 28: submission"]

    style A fill:#6c6,stroke:#060,stroke-width:2px
    style I fill:#f66,stroke:#900,stroke-width:2px
```

## Status legend
- ✅ **Done** — built, tested, and (where applicable) statistically verified.
- 🟡 **Partial** — the pipeline/infrastructure exists and runs correctly, but
  is still exercising `ScriptedAgent` rather than a real model.
- ⬜ **Not started** — no code/doc artifact exists yet.

See [PROGRESS.md](../PROGRESS.md) for the auto-generated, always-current
version of this status (never hand-edited), and
[docs/DAILY_LOG.md](DAILY_LOG.md) for the full narrative behind each box.
