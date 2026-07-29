#!/bin/bash
# Per-task-process-restart wrapper for run_primary.py against the
# task-family/attack-phrasing diversity set (tasks/diversity_180.json, 144
# test tasks, 3rd "messaging" domain), same Groq fd-leak rationale as
# scripts/run_llama_stealth_resilient.sh. Handles BOTH tiers via $1 (a label
# used only for naming output/log/skip files) and $CONDITIONS (empty = the
# explicit benign+adversarial pair; "adversarial_stealth" = stealth tier).
#
# WALL_CAP=1650 (raised from 1200, which itself was raised from 650): a
# direct foreground repro (2026-07-28) showed individual explicit-tier
# episodes on this task set legitimately taking 90s+ each on Groq for this
# model -- not a hang, just real per-call latency multiplied by 14 episodes
# (7 policies x 2 conditions) per task. 1200s wasn't enough either: 8 tasks
# across file/cal/messaging domains were wrongly excluded as "poison" over
# ~7 hours of the outer supervisor endlessly restarting on a 2-consecutive-
# exclusion circuit breaker with zero net progress. None of them were
# actually poisoned -- just under-timed. Also raised the circuit breaker
# from 2 to 3 to match run_llama_screened_ablation_resilient.sh, for the
# same reason.
#
# Persists its exclusion list to /tmp (see SKIPFILE) so poison tasks are
# never re-discovered from scratch across restarts.
#
# Usage:
#   GROQ_API_KEY=... bash scripts/run_llama_diversity_resilient.sh primary
#   CONDITIONS=adversarial_stealth GROQ_API_KEY=... \
#     bash scripts/run_llama_diversity_resilient.sh stealth
set -uo pipefail
cd "$(dirname "$0")/.."

LABEL="${1:-run}"
CONDITIONS="${CONDITIONS:-}"
DIR=results/models/llama-3.3-70b-diversity
mkdir -p "$DIR"
EPISODES="$DIR/${LABEL}_episodes.json"
SUMMARY="$DIR/${LABEL}_summary.json"
CALIB="$DIR/dev_calibration.json"
LOG=${LLAMA_DIVERSITY_LOG:-/tmp/llama_diversity_${LABEL}_task.log}
export PER_TASK_TIMEOUT=1500
WALL_CAP=1650
MAX_RETRIES=3

SKIPFILE=${LLAMA_DIVERSITY_SKIPFILE:-/tmp/llama_diversity_${LABEL}_skipped.txt}
touch "$SKIPFILE"
SKIP_IDS=$(paste -sd, "$SKIPFILE" 2>/dev/null)

COND_ARGS=()
if [ -n "$CONDITIONS" ]; then
  COND_ARGS=(--conditions "$CONDITIONS")
fi

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
all_tasks = [load_task(d) for d in json.load(open('tasks/diversity_180.json'))]
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
print(sum(1 for t in (load_task(d) for d in json.load(open('tasks/diversity_180.json'))) if t.split=='test'))
")
echo "[$LABEL] test split has $n_test tasks"

cur_task=""
cur_fails=0
consec_excluded=0

while true; do
  done=$(count_done)
  n_skipped=$( [ -z "$SKIP_IDS" ] && echo 0 || echo "$SKIP_IDS" | tr ',' '\n' | grep -c . )
  if [ "$((done + n_skipped))" -ge "$n_test" ]; then
    echo "[$LABEL] all $n_test tasks accounted for ($done done, $n_skipped skipped) -- stopping"
    break
  fi

  target=$(next_task_id)
  if [ -z "$target" ]; then
    echo "[$LABEL] no remaining task found but done+skipped < n_test -- stopping"
    break
  fi
  if [ "$target" != "$cur_task" ]; then
    cur_task="$target"
    cur_fails=0
  fi

  limit=$((done + 1))
  echo "[$LABEL] --- target=$cur_task (attempt $((cur_fails+1))/$MAX_RETRIES), done: $done/$n_test, skipped: $n_skipped ---"
  python3 -u scripts/run_primary.py \
    --tasks tasks/diversity_180.json --calibration "$CALIB" \
    --policies mainplus ${COND_ARGS[@]+"${COND_ARGS[@]}"} --resume --limit "$limit" \
    --skip-task-ids "$SKIP_IDS" \
    --backend openai --model llama-3.3-70b-versatile --api-key-env GROQ_API_KEY \
    --out "$SUMMARY" --episodes-out "$EPISODES" > "$LOG" 2>&1 &
  pid=$!

  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 2
    waited=$((waited + 2))
    if [ "$waited" -ge "$WALL_CAP" ]; then
      echo "[$LABEL] pid $pid past ${WALL_CAP}s wall cap -- SIGKILL"
      kill -9 "$pid" 2>/dev/null
      pkill -9 -P "$pid" 2>/dev/null
      break
    fi
  done
  wait "$pid" 2>/dev/null

  after=$(count_done)
  tail -2 "$LOG"

  if grep -qE "Access denied|HTTP Error 401|HTTP Error 403" "$LOG"; then
    echo "[$LABEL] !!! SYSTEMIC ACCESS FAILURE (401/403) -- stopping. done=$after/$n_test"
    exit 1
  fi

  if [ "$after" -gt "$done" ]; then
    echo "[$LABEL]  -> $cur_task landed ($done -> $after)"
    cur_task=""
    cur_fails=0
    consec_excluded=0
  else
    cur_fails=$((cur_fails + 1))
    echo "[$LABEL]  -> $cur_task did not land (attempt $cur_fails/$MAX_RETRIES)"
    if [ "$cur_fails" -ge "$MAX_RETRIES" ]; then
      echo "[$LABEL]  -> $cur_task EXCLUDED after $MAX_RETRIES failed attempts"
      SKIP_IDS="${SKIP_IDS:+$SKIP_IDS,}$cur_task"
      echo "$cur_task" >> "$SKIPFILE"
      cur_task=""
      cur_fails=0
      consec_excluded=$((consec_excluded + 1))
      if [ "$consec_excluded" -ge 3 ]; then
        echo "[$LABEL] !!! $consec_excluded clustered exclusions -- stopping to avoid excluding everything blindly. done=$after/$n_test, skipped=$SKIP_IDS"
        exit 1
      fi
    fi
  fi
done

echo "[$LABEL] === FINAL: $(count_done)/$n_test tasks complete. Excluded: ${SKIP_IDS:-none} ==="
