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

    section Main experiment (in progress)
    Scale to 120 tasks (24 dev/96 test)   :done, m1, 2026-07-17, 1d
    Dev-only lambda + prior calibration   :done, m2, 2026-07-17, 1d
    Primary test-split run                :done, m3, 2026-07-18, 1d
    Real open-weight model backend        :active, crit, m4, 2026-07-18, 2d
    Bootstrap stats + main table          :done, m5, 2026-07-19, 1d
    Real abstract numbers                 :m6, after m4, 1d

    section Writing & submission (not started)
    Abstract submission                   :milestone, w1, 2026-07-21, 0d
    Third model + 2 more policies         :w2, 2026-07-22, 2d
    Oracle-vs-learned-risk ablation       :w3, 2026-07-22, 2d
    Stochastic-repetition robustness      :w4, 2026-07-22, 2d
    Failure analysis + figures            :w5, 2026-07-24, 1d
    Seven-page paper draft                :w6, 2026-07-25, 2d
    Revision + reproducibility + citations :w7, 2026-07-27, 1d
    Full submission                       :milestone, w8, 2026-07-28, 0d
```

## What the critical path actually is

The single item marked `crit` above — **wiring a real open-weight model into
`OpenModelAgent`** — is the one dependency every downstream box (m6 through
w8) sits behind. Everything to its left is genuinely done; everything to its
right is either blocked on it directly or (Jul 22-23's two extra policies,
the ablation, the robustness subset) is new engineering that hasn't started
because there was no point building it against ScriptedAgent placeholder data.

```mermaid
flowchart LR
    A["Real model backend\n(scripts/model_backends.py)"] --> B["tune_dev.py\n(dev calibration)"]
    B --> C["run_primary.py\n(test-split run)"]
    C --> D["compute_stats.py\n(bootstrap CIs)"]
    D --> E["make_main_table.py"]
    E --> F["abstract.md filled"]
    F --> G["Jul 21: submit abstract"]
    C --> H["Jul 24: failure analysis\n(needs real episodes)"]
    A --> I["Jul 22-23: 3rd model +\n2 more policies + ablations"]
    G --> J["Jul 25-26: paper draft"]
    H --> J
    I --> J
    J --> K["Jul 27: revision + repro"]
    K --> L["Jul 28: submission"]

    style A fill:#f66,stroke:#900,stroke-width:2px
```

## Status legend
- ✅ **Done** — built, tested, and (where applicable) statistically verified.
- 🟡 **Partial** — the pipeline/infrastructure exists and runs correctly, but
  is still exercising `ScriptedAgent` rather than a real model.
- ⬜ **Not started** — no code/doc artifact exists yet.

See [PROGRESS.md](../PROGRESS.md) for the auto-generated, always-current
version of this status (never hand-edited), and
[docs/DAILY_LOG.md](DAILY_LOG.md) for the full narrative behind each box.
