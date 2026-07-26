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
# thread is still blocked on its socket read. Piping through tail doesn't just
# delay output, it can wedge this wrapper's own loop forever (tail only
# flushes at the upstream fd's EOF, which doesn't arrive until the WHOLE
# zombie process is gone). Fix: redirect straight to a file and poll for
# either the episode COUNT increasing or a hard wall-clock cap, then SIGKILL
# the process tree outright rather than waiting for a graceful exit a zombie
# thread may permanently block.
#
# WHY A PER-TASK RETRY CAP: some tasks are not transient bad luck but a
# reproducible poison interaction with ONE backend's infrastructure
# specifically. Confirmed directly for cal_039: it hung on EVERY attempt
# across process restarts and two different wall-clock budgets (150s, then a
# corrected 650s matching the backend's own documented worst-case retry
# budget), while completing fine and fast on three OTHER backends entirely
# (mistral/ollama, gpt-oss-20b/120b/ollama) -- ruling out task content as an
# absolute cause and pointing at something specific to this content x this
# backend's edge/infra. Retrying such a task forever would starve every task
# after it of a chance to even be attempted. After MAX_RETRIES failures on the
# SAME task, it is excluded via --skip-task-ids and the run proceeds; this is
# a documented coverage gap, not a fix, and must be reported as one.
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
# unlucky patch, not a sign it's stuck.)
WALL_CAP=650
MAX_RETRIES=3   # attempts on the SAME task before it's excluded, not skipped-and-revisited

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

next_task_id() {
  # The earliest test-split task_id not yet in EPISODES and not in SKIP_IDS.
  python3 -c "
import json
from secure_clarify.schema import load_task
all_tasks = [load_task(d) for d in json.load(open('tasks/main_120.json'))]
test_tasks = [t for t in all_tasks if t.split == 'test']
skip = set('$SKIP_IDS'.split(',')) if '$SKIP_IDS' else set()
try:
    done = {e['task_id'] for e in json.load(open('$EPISODES'))}
except FileNotFoundError:
    done = set()
remaining = [t.task_id for t in test_tasks if t.task_id not in done and t.task_id not in skip]
print(remaining[0] if remaining else '')
"
}

n_test=$(python3 -c "
import json
from secure_clarify.schema import load_task
print(sum(1 for t in (load_task(d) for d in json.load(open('tasks/main_120.json'))) if t.split=='test'))
")
echo "test split has $n_test tasks"

SKIP_IDS=""
cur_task=""
cur_fails=0

while true; do
  done=$(count_done)
  n_skipped=$( [ -z "$SKIP_IDS" ] && echo 0 || echo "$SKIP_IDS" | tr ',' '\n' | grep -c . )
  if [ "$((done + n_skipped))" -ge "$n_test" ]; then
    echo "all $n_test tasks accounted for ($done done, $n_skipped skipped) -- stopping"
    break
  fi

  target=$(next_task_id)
  if [ -z "$target" ]; then
    echo "no remaining task found but done+skipped < n_test -- stopping to avoid an infinite loop"
    break
  fi
  if [ "$target" != "$cur_task" ]; then
    cur_task="$target"
    cur_fails=0
  fi

  # --limit needs a count, not a task_id: since --skip-task-ids has already
  # removed excluded tasks from the ordered list, "how many tasks in are we"
  # is exactly done+1 within the filtered set.
  limit=$((done + 1))
  echo "--- target=$cur_task (attempt $((cur_fails+1))/$MAX_RETRIES), done so far: $done/$n_test, skipped: $n_skipped ---"
  python3 -u scripts/run_primary.py \
    --tasks tasks/main_120.json --calibration "$CALIB" \
    --policies mainplus --conditions adversarial_stealth --resume --limit "$limit" \
    --skip-task-ids "$SKIP_IDS" \
    --backend openai --model llama-3.3-70b-versatile --api-key-env GROQ_API_KEY \
    --out "$SUMMARY" --episodes-out "$EPISODES" > "$LOG" 2>&1 &
  pid=$!

  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 2
    waited=$((waited + 2))
    if [ "$waited" -ge "$WALL_CAP" ]; then
      echo "  pid $pid past ${WALL_CAP}s wall cap -- SIGKILL (script logic is bounded by "
      echo "  PER_TASK_TIMEOUT=$PER_TASK_TIMEOUT; a longer OS-level lifetime past that is a "
      echo "  zombie non-daemon thread from an exhausted retry, not still-useful work)"
      kill -9 "$pid" 2>/dev/null
      pkill -9 -P "$pid" 2>/dev/null
      break
    fi
  done
  wait "$pid" 2>/dev/null

  after=$(count_done)
  tail -2 "$LOG"
  if [ "$after" -gt "$done" ]; then
    echo "  -> $cur_task landed ($done -> $after)"
    cur_task=""
    cur_fails=0
  else
    cur_fails=$((cur_fails + 1))
    echo "  -> $cur_task did not land (attempt $cur_fails/$MAX_RETRIES)"
    if [ "$cur_fails" -ge "$MAX_RETRIES" ]; then
      echo "  -> $cur_task EXCLUDED after $MAX_RETRIES failed attempts -- documented coverage gap, not a fix"
      SKIP_IDS="${SKIP_IDS:+$SKIP_IDS,}$cur_task"
      cur_task=""
      cur_fails=0
    fi
  fi
done

echo "=== FINAL: $(count_done)/$n_test tasks complete. Excluded: ${SKIP_IDS:-none} ==="
