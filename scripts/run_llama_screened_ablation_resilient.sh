#!/bin/bash
# Per-task-process-restart wrapper for scripts/screened_ablation.py's llama
# stealth-tier run, same design as scripts/run_llama_stealth_resilient.sh
# (Groq's ~1-in-10-20 silent hang + non-daemon-thread fd leak on long-lived
# processes -- see that script's docstring for the full root-cause writeup).
#
# Built 2026-07-28 after a single long-lived screened_ablation.py process hit
# 65 CLOSE_WAIT / 37 ESTABLISHED sockets simultaneously with ZERO progress
# over 3 hours -- screened_ablation.py didn't have --limit/--skip-task-ids
# until this session added them (mirroring run_primary.py's flags) so this
# per-task pattern could exist at all.
#
# Persists its exclusion list to /tmp so a poison task is never re-discovered
# from scratch if this script itself gets restarted (a real bug hit earlier:
# an in-memory-only skip list caused 6+ hours of zero progress re-excluding
# the same tasks every restart).
#
# Usage: GROQ_API_KEY=... bash scripts/run_llama_screened_ablation_resilient.sh
set -uo pipefail
cd "$(dirname "$0")/.."

EPISODES=results/models/llama-3.3-70b/screened_ablation_stealth_episodes.json
SUMMARY=results/models/llama-3.3-70b/screened_ablation_stealth.json
CALIB=results/models/llama-3.3-70b/dev_calibration.json
LOG=${LLAMA_ABLATION_LOG:-/tmp/llama_ablation_task.log}
export PER_TASK_TIMEOUT=300
WALL_CAP=350
MAX_RETRIES=3

SKIPFILE=${LLAMA_ABLATION_SKIPFILE:-/tmp/llama_ablation_skipped.txt}
touch "$SKIPFILE"
# file_037 through cal_048 (18 tasks) are confirmed poison for this backend
# as of 2026-07-28 -- seed the ones already confirmed if the file is fresh.
for t in file_037 cal_037 file_038 cal_038 file_039 cal_039 file_041 cal_041 \
         file_042 cal_042 file_043 cal_043 file_044 cal_044 file_046 cal_047 \
         file_048 cal_048; do
  grep -qx "$t" "$SKIPFILE" || echo "$t" >> "$SKIPFILE"
done

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

n_test=96
SKIP_IDS=$(paste -sd, "$SKIPFILE" 2>/dev/null)
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
    echo "no remaining task found but done+skipped < n_test -- stopping"
    break
  fi
  if [ "$target" != "$cur_task" ]; then
    cur_task="$target"
    cur_fails=0
  fi

  limit=$((done + 1))
  echo "--- target=$cur_task (attempt $((cur_fails+1))/$MAX_RETRIES), done: $done/$n_test, skipped: $n_skipped ---"
  python3 -u scripts/screened_ablation.py --tasks tasks/main_120.json \
    --calibration "$CALIB" --conditions adversarial_stealth --resume --limit "$limit" \
    --skip-task-ids "$SKIP_IDS" \
    --backend openai --model llama-3.3-70b-versatile --api-key-env GROQ_API_KEY \
    --out "$SUMMARY" --episodes-out "$EPISODES" > "$LOG" 2>&1 &
  pid=$!

  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 2
    waited=$((waited + 2))
    if [ "$waited" -ge "$WALL_CAP" ]; then
      echo "  pid $pid past ${WALL_CAP}s wall cap -- SIGKILL"
      kill -9 "$pid" 2>/dev/null
      pkill -9 -P "$pid" 2>/dev/null
      break
    fi
  done
  wait "$pid" 2>/dev/null

  after=$(count_done)
  tail -3 "$LOG"

  if [ "$after" -gt "$done" ]; then
    echo "  -> $cur_task landed ($done -> $after)"
    cur_task=""
    cur_fails=0
  else
    cur_fails=$((cur_fails + 1))
    echo "  -> $cur_task did not land (attempt $cur_fails/$MAX_RETRIES)"
    if [ "$cur_fails" -ge "$MAX_RETRIES" ]; then
      echo "  -> $cur_task EXCLUDED after $MAX_RETRIES failed attempts"
      SKIP_IDS="${SKIP_IDS:+$SKIP_IDS,}$cur_task"
      echo "$cur_task" >> "$SKIPFILE"
      cur_task=""
      cur_fails=0
    fi
  fi
done

echo "=== FINAL: $(count_done)/$n_test tasks complete. Skipped: ${SKIP_IDS:-none} ==="
