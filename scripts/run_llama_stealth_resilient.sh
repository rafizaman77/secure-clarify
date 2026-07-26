#!/bin/bash
# Wrapper for llama-3.3-70b's stealth run: restarts run_primary.py as a FRESH
# PROCESS after every single task instead of one long-lived run.
#
# WHY A FRESH PROCESS PER TASK: model_backends._urlopen_hard_timeout's own
# docstring documents the root cause directly -- roughly 1-in-10-20 Groq calls
# hang with no exception, no data, indefinitely (confirmed via a prior 9h47m
# hang + `lsof` showing 19 leaked CLOSE_WAIT sockets). Python cannot forcibly
# kill a blocked socket read, so every hang permanently strands one thread and
# its OS resources for the life of the PROCESS. A single run_primary
# invocation makes many raw HTTP calls across a large task backlog, so leaked
# threads/sockets accumulate over the run's lifetime -- healthy for the first
# ~60 tasks, then degrading. Restarting the whole PYTHON PROCESS is a full
# OS-level reset, extending the codebase's own "fresh executor per call bounds
# a stuck call's blast radius" principle one level up.
#
# WHY NOT `| tail`: a stranded worker thread from run_primary's own per-task
# ThreadPoolExecutor is NON-DAEMON, so even after main() finishes cleanly
# (prints its summary, writes its files) the PROCESS cannot exit while that
# thread is still blocked on its socket read -- confirmed directly: a run
# whose logic completed in ~90s (its own PER_TASK_TIMEOUT) still showed up in
# `ps` alive 130s later, and a piped `tail` never printed a single line in
# that window because tail only flushes at the upstream fd's EOF, which
# doesn't arrive until the WHOLE process exits. Piping through tail therefore
# doesn't just delay output, it can wedge this wrapper's own loop forever.
# Fix: redirect straight to a file (real-time readable) and poll for either
# the episode COUNT increasing or a hard wall-clock cap, then SIGKILL the
# process tree outright rather than waiting for a graceful exit that a zombie
# thread may permanently block.
#
# Usage: GROQ_API_KEY=... bash scripts/run_llama_stealth_resilient.sh
set -uo pipefail
cd "$(dirname "$0")/.."

EPISODES=results/stealth/llama-3.3-70b_episodes.json
SUMMARY=results/stealth/llama-3.3-70b_summary.json
CALIB=results/models/llama-3.3-70b/dev_calibration.json
LOG=${LLAMA_STEALTH_LOG:-/tmp/llama_stealth_task.log}
export PER_TASK_TIMEOUT=600   # matches model_backends' own documented worst case
# (max_retries=8 x hard_timeout~70s + backoff ~= 600s -- this is the retry
# logic's LEGITIMATE worst case when a task's several raw calls each hit an
# unlucky patch, not a sign it's stuck. Verified directly: cal_039 reproduced
# outside the wrapper with >80s and no output, then the OS-level exit note
# below showed the underlying issue is real hangs needing genuine retries, not
# zombie-thread accumulation from prior tasks -- a shorter wall cap here was
# SIGKILLing the process before its own correct retry logic ever got to
# finish, 3 times in a row on the identical task.)
WALL_CAP=650

count_done() {
  python3 -c "
import json
try:
    eps=json.load(open('$EPISODES'))
    print(len({e['task_id'] for e in eps}))
except FileNotFoundError:
    print(0)
"
}

n_test=$(python3 -c "
import json
from secure_clarify.schema import load_task
print(sum(1 for t in (load_task(d) for d in json.load(open('tasks/main_120.json'))) if t.split=='test'))
")
echo "test split has $n_test tasks"

limit=$(( $(count_done) + 1 ))
while [ "$limit" -le "$n_test" ]; do
  before=$(count_done)
  if [ "$before" -ge "$n_test" ]; then
    echo "all $n_test tasks done -- stopping"
    break
  fi
  echo "--- limit=$limit (done so far: $before/$n_test) ---"
  python3 -u scripts/run_primary.py \
    --tasks tasks/main_120.json --calibration "$CALIB" \
    --policies mainplus --conditions adversarial_stealth --resume --limit "$limit" \
    --backend openai --model llama-3.3-70b-versatile --api-key-env GROQ_API_KEY \
    --out "$SUMMARY" --episodes-out "$EPISODES" > "$LOG" 2>&1 &
  pid=$!

  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 2
    waited=$((waited + 2))
    if [ "$waited" -ge "$WALL_CAP" ]; then
      echo "  pid $pid past ${WALL_CAP}s wall cap -- SIGKILL (likely a zombie leaked-thread exit, not still working: logic itself is bounded by PER_TASK_TIMEOUT=$PER_TASK_TIMEOUT)"
      kill -9 "$pid" 2>/dev/null
      pkill -9 -P "$pid" 2>/dev/null   # any child threads/procs it spawned
      break
    fi
  done
  wait "$pid" 2>/dev/null   # reap; ignore exit code, we judge success by episode count below

  after=$(count_done)
  tail -2 "$LOG"
  if [ "$after" -gt "$before" ]; then
    echo "  -> task landed ($before -> $after)"
  else
    echo "  -> task did not land (stayed at $after), retrying same slice next"
  fi
  limit=$((after + 1))
done

echo "=== FINAL: $(count_done)/$n_test tasks complete ==="
