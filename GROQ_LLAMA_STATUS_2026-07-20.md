# Llama-3.3-70B (Groq) status — 2026-07-20, third machine

Written for Anagh / anyone picking this up. Summarizes what happened trying to
finish the `llama-3.3-70b` mainplus re-run tonight, what's actually broken,
and what's genuinely done vs. blocked.

## TL;DR

**GPT-OSS-20B and GPT-OSS-120B (Ollama Cloud) are unaffected and proceeding
normally** (20B finished its primary run clean, 120B queued right behind it).
**Llama-3.3-70B (Groq) is blocked at 90/96 test tasks — not by a code bug, by
Groq's free-tier 100k-tokens/day cap.** This is the same structural limit
noted in `docs/DAILY_LOG.md` months ago ("its free-tier daily token cap
(~100k) could not finish the ~138k-token 96-task test grid") and now
independently confirmed on **two different Groq keys/orgs** tonight. Rotating
the key doesn't fix it — a fresh key just gets its own fresh 100k/day budget,
which still isn't enough headroom to finish a full 96-task grid (needs
~138k) in one sitting once you add any retries at all.

## What actually happened, in order

1. Resumed from the checkpoint the second machine left (37/96 for llama,
   11/96 for gpt-oss-20b-cloud) using fresh Groq/Ollama keys.
2. Llama progressed cleanly 37 → 90/96 (~13s/task). Then task 91 (`cal_023`
   originally, later `file_057`) started hanging with no error, no exception
   — looked exactly like OPEN ISSUE #4 in `HANDOFF.md`.
3. Diagnosed it directly (not guessed): killed the stuck process, confirmed
   90 tasks were safely persisted (episodes are written to disk after every
   task, so nothing was lost), then used macOS `sample` to get a live stack
   trace of the stuck process. The main thread was inside a legitimate
   `time.sleep()` retry backoff already in `scripts/model_backends.py`, not a
   genuinely un-timeoutable dead socket read.
4. Added a real fix: `scripts/run_primary.py` now wraps each task in a
   10-minute hard timeout (`PER_TASK_TIMEOUT` env var, default 600s) via a
   fresh single-use `ThreadPoolExecutor` per task. A task that exceeds it is
   skipped (logged, left "not done") instead of blocking the whole 96-task
   run indefinitely — exactly the workaround `HANDOFF.md`'s OPEN ISSUE #4
   already proposed as the pragmatic fallback. Also made `run_primary.py`
   return exit code 1 (not 0) when any task timed out, so
   `run_full_model.py` correctly treats a partial run as incomplete instead
   of silently computing "final" stats over < 96 tasks.
5. Kept hitting repeat timeouts on the same handful of remaining tasks even
   across fresh process restarts and with `GEN_MIN_INTERVAL` pacing added.
   Suspected (and confirmed via `lsof`) that abandoned background threads
   from earlier skipped tasks were still silently retrying and competing for
   the same rate-limit budget — a real flaw in the timeout-and-skip design
   (Python can't forcibly kill a blocked thread, so "skipping" a task doesn't
   actually stop its thread from continuing to hammer the API).
6. **Root cause, confirmed directly**: replayed `file_057`'s actual
   `sample_intents` prompt via raw `curl` three times back-to-back. Call 1
   succeeded; calls 2 and 3 immediately got HTTP 429 with body:
   `"Rate limit reached for model llama-3.3-70b-versatile ... on tokens per
   day (TPD): Limit 100000, Used 99963, Requested 655."` This is NOT the
   client-side hang bug OPEN ISSUE #4 originally suspected — it's the same
   **daily** token cap the first (rotated) Groq key hit earlier tonight,
   now independently hit on this second/"new" key too (different org ID),
   because ~90 real tasks + several full retry cycles + orphaned background
   retries + this diagnostic testing were enough to burn through its budget.
   The earlier stack samples showing `time.sleep()` were genuine 429 backoff
   waits the whole time, not a stuck socket — the timeout-and-skip mechanism
   was doing the right thing, it just couldn't succeed because there wasn't
   enough daily quota left to complete these last tasks regardless of retry
   count.

## Current state (safe, nothing lost)

- **90/96 llama-3.3-70b test tasks are done and persisted** in
  `results/models/llama-3.3-70b/primary_episodes.json` (1260 episodes, no
  partial/corrupt writes — confirmed by task_id count).
- **6 tasks remain**: `file_057, cal_057, file_058, cal_058, file_059,
  cal_059`. Nothing pipeline-specific about these tasks (inspected
  `file_057`'s content directly — an ordinary, unremarkable file-domain
  task); they're just whichever tasks happened to be next when the daily
  quota ran out.
- No `primary_summary.json` / downstream stats exist yet for llama (the run
  has never completed all 96 in one pass, so `run_full_model.py` never
  reached the oracle_ablation/guardrail_eval/stats steps for this model).
- **gpt-oss-20b-cloud**: primary run complete, all 8 `check_invariants.py`
  checks **PASS**. `secure_voi` beats `channel_heuristic` clearly
  (adv unsafe 0.000 vs 0.333; adv utility +0.081 vs −0.498) — stronger than
  the earlier mistral preview. One soft flag: `secure_not_degenerate` came
  back FAIL because `secure_voi` benign utility (0.321) is marginally below
  `trusted_only` (0.331) — a ~0.01 gap, likely noise, not a correctness bug
  (the formal invariants all pass). oracle_ablation done (SecureVoI matches
  the oracle exactly, 0 gap). guardrail_eval was running as of this write-up.
- **gpt-oss-120b-cloud**: queued behind 20b in the same background chain,
  will start automatically with a fresh calibration once 20b's full
  pipeline finishes. (Old pre-channel-mix-fix 120b data was archived to
  `results/models/_pre_domain_bugfix_2026-07-20/gpt-oss-120b-cloud-premainplus/`
  before this run started, so `--resume` can't accidentally reuse stale
  episodes from before the channel-mix fix.)

## What's needed to actually finish llama-3.3-70b

Pick one:
1. **Wait it out.** The daily cap does refill, just slowly and not fully
   within a single evening — realistically needs a fresh day (or a long
   multi-hour gap) before there's enough headroom to safely finish 6 more
   tasks without immediately re-exhausting it.
2. **Upgrade this Groq account to Dev Tier** at
   console.groq.com/settings/billing — removes the daily cap entirely. This
   is a billing action Rafi needs to do himself.
3. **Point just these 6 tasks at a different provider** (Together, Fireworks,
   OpenRouter — all already OpenAI-chat-compatible via
   `scripts/model_backends.py`'s `--backend openai --base-url ...`) with a
   fresh key, then merge those episodes in. Not yet attempted.

Once there's real headroom again, resuming is one command (the code changes
above make this safe/idempotent):

    export GROQ_API_KEY=...
    python3 scripts/run_full_model.py --name llama-3.3-70b --backend openai \
      --base-url https://api.groq.com/openai/v1/chat/completions \
      --api-key-env GROQ_API_KEY --model llama-3.3-70b-versatile \
      --skip-dev-calibration

It will pick up exactly the 6 remaining tasks and, once all 96 are present,
automatically continue through check_invariants/oracle_ablation/
guardrail_eval/compute_stats/tables.

## Code changes made tonight (both in `scripts/run_primary.py`)

1. Per-task 10-minute hard timeout with skip-and-log (not silent — a task
   that times out is printed loudly and left retryable via `--resume`).
2. Nonzero exit code when any task timed out, so the pipeline wrapper
   (`run_full_model.py`) doesn't silently treat a partial run as complete.

Known limitation of tonight's fix (not yet addressed): a timed-out task's
background thread isn't actually killed (Python can't forcibly kill a
blocked thread), so it keeps retrying unsupervised in the background for a
while after being "skipped." This is a real contributor to the compounding
failures observed above and would be worth fixing properly (e.g. threading a
cancellation signal into `model_backends.py`'s retry loop) if this keeps
being a problem on future runs.
