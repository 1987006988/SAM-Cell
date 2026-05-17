#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-$ROOT/experiments/cellcosmos_full_16777_20260503}"
FINAL_SUMMARY="${FINAL_SUMMARY:-$EXP_ROOT/samcell_refine_final/summary.csv}"
LOG="${LOG:-$EXP_ROOT/logs/pause_old_samcell_until_refine_done_20260506.log}"
POLL_SECONDS="${POLL_SECONDS:-300}"

mkdir -p "$(dirname "$LOG")"

now() {
  date "+%F %T %Z"
}

log() {
  echo "$(now) $*" | tee -a "$LOG"
}

find_old_pid() {
  pgrep -af "eval_devset.py .*tissuenet_local_combo_search_20260504.*samcell_final" \
    | awk 'NR==1 {print $1}'
}

OLD_PID="${OLD_PID:-$(find_old_pid || true)}"

if [[ -z "${OLD_PID}" ]]; then
  log "No old non-final samcell_final eval_devset.py process found; nothing to pause."
  exit 0
fi

if ! kill -0 "$OLD_PID" 2>/dev/null; then
  log "Old non-final process PID=$OLD_PID is not alive; nothing to pause."
  exit 0
fi

state="$(ps -o stat= -p "$OLD_PID" | awk '{print $1}')"
log "Old non-final PID=$OLD_PID current_state=$state final_summary=$FINAL_SUMMARY"

if [[ -s "$FINAL_SUMMARY" ]]; then
  log "Final summary already exists; leaving old process running."
  exit 0
fi

if [[ "$state" != T* ]]; then
  kill -STOP "$OLD_PID"
  log "Paused old non-final PID=$OLD_PID with SIGSTOP to prioritize final samcell_refine_final."
else
  log "Old non-final PID=$OLD_PID is already stopped."
fi

while true; do
  if [[ -s "$FINAL_SUMMARY" ]]; then
    if kill -0 "$OLD_PID" 2>/dev/null; then
      kill -CONT "$OLD_PID" || true
      log "Final summary exists; resumed old non-final PID=$OLD_PID with SIGCONT."
    else
      log "Final summary exists; old non-final PID=$OLD_PID is no longer alive."
    fi
    exit 0
  fi
  if ! kill -0 "$OLD_PID" 2>/dev/null; then
    log "Old non-final PID=$OLD_PID exited while final summary is still pending."
    exit 0
  fi
  count="$(find "$EXP_ROOT/samcell_refine_final/labels" -maxdepth 1 -type f -name '*.tif' 2>/dev/null | wc -l)"
  log "Waiting for final summary; samcell_refine_final labels=$count/16777; old PID=$OLD_PID remains paused."
  sleep "$POLL_SECONDS"
done
