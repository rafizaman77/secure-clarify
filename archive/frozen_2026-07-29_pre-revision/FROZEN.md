# Frozen snapshot — 2026-07-29, pre-revision baseline

Everything committed after this point is a NEW EXPERIMENTAL REVISION per
RESEARCH_PLAN.md. This directory is the reference the revision is measured against.

- code commit: 83cc97ac483223e2483cd23c8e7a7787384e4f37
- models with complete primary results (96 test tasks, 7 policies, benign+adversarial):
    - mistral-nemo-12b (lambda=4.0)
    - gpt-oss-20b-cloud (lambda=3.0)
    - gpt-oss-120b-cloud (lambda=3.0)
    - llama-3.3-70b (lambda=3.0)
    - gpt-5.4-mini (lambda=3.0)
    - claude-sonnet-5 (lambda=2.0)
    - gemini-3.6-flash (lambda=3.0)
- decoding: greedy (temperature 0) except the 30-task sampling check (0.7)
- bootstrap: task-level paired, 2000 resamples, fixed seed
- raw episode trajectories: left in place under results/models/*/ (not duplicated
  here -- they are large and already immutable in git history at 83cc97ac483223e2483cd23c8e7a7787384e4f37)

Reconstruct exactly:  git checkout 83cc97ac483223e2483cd23c8e7a7787384e4f37
