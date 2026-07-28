#!/bin/bash
# Self-healing supervisor for any per-model screened_ablation / run_primary pass.
#
# WHY THIS EXISTS (2026-07-28): a long hosted-backend run degrades in a way a
# single process cannot recover from. `_urlopen_hard_timeout` in
# scripts/model_backends.py bounds each call with a hard wall-clock timeout,
# but Python cannot kill a thread blocked on an OS-level socket read -- so
# every hang ABANDONS a worker thread that still holds its fd. Those pile up
# as CLOSE_WAIT sockets. Observed live on llama-3.3-70b: 18 CLOSE_WAIT / 0
# ESTABLISHED, at which point every remaining task burned its full per-task
# timeout and made zero progress. A FRESH PROCESS is the only fix, because
# the leaked fds die with the process. This loop supplies that.
#
# It is a wrapper, not a change to the pipeline: it just re-invokes the same
# command with --resume until the episodes file reaches full coverage.
#
# Usage:
#   MAX_ATTEMPTS=12 PER_TASK_TIMEOUT=300 \
#   scripts/supervise_run.sh <model-dir-name> <command...>
#
# Example:
#   OLLAMA_API_KEY=... PER_TASK_TIMEOUT=300 \
#   scripts/supervise_run.sh gpt-oss-120b-cloud \
#     python3 scripts/screened_ablation.py --tasks tasks/main_120.json \
#       --calibration results/models/gpt-oss-120b-cloud/dev_calibration.json \
#       --out results/models/gpt-oss-120b-cloud/screened_ablation.json \
#       --episodes-out results/models/gpt-oss-120b-cloud/screened_ablation_episodes.json \
#       --backend ollama --model gpt-oss:120b-cloud --host https://ollama.com --resume
#
# NOTE: the command MUST end in --resume, or each attempt restarts from zero.
set -uo pipefail

NAME="${1:?usage: supervise_run.sh <model-dir-name> <command...>}"; shift
EPS="${EPISODES_FILE:-results/models/${NAME}/screened_ablation_episodes.json}"
TARGET="${TARGET_TASKS:-96}"
MAX="${MAX_ATTEMPTS:-12}"

coverage() {
  python3 -c "
import json
try:
    d = json.load(open('$EPS'))
    print(len({e['task_id'] for e in d}))
except Exception:
    print(0)
" 2>/dev/null || echo 0
}

for i in $(seq 1 "$MAX"); do
  n=$(coverage)
  if [ "$n" -ge "$TARGET" ]; then
    echo "SUPERVISOR[$NAME]: COMPLETE at ${n}/${TARGET} after $((i-1)) attempt(s)"
    exit 0
  fi
  echo "SUPERVISOR[$NAME]: attempt ${i}/${MAX}, currently ${n}/${TARGET}"
  "$@"
  sleep 10
done

n=$(coverage)
echo "SUPERVISOR[$NAME]: EXHAUSTED ${MAX} attempts, final coverage ${n}/${TARGET}"
[ "$n" -ge "$TARGET" ] && exit 0 || exit 1
