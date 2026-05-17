#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-7200}"
TRAIN_SESSION="${TRAIN_SESSION:-cellcosmos_train}"
MONITOR_DIR="${MONITOR_DIR:-$WORK_ROOT/logs/training_monitor}"
STATUS_FILE="${STATUS_FILE:-$MONITOR_DIR/latest_status.txt}"
HISTORY_FILE="${HISTORY_FILE:-$MONITOR_DIR/history.log}"
MAX_IDLE_AFTER_FINISH="${MAX_IDLE_AFTER_FINISH:-2}"
DATASET_ID="${DATASET_ID:-620}"
DATASET_NAME="${DATASET_NAME:-CellCosmosBoundary}"
RUN_GLOB="${RUN_GLOB:-cellcosmos_boundary_*}"

printf -v DATASET_DIR "Dataset%03d_%s" "$DATASET_ID" "$DATASET_NAME"
RESULT_ROOT="$WORK_ROOT/nnUNet_results/$DATASET_DIR/nnUNetTrainer__nnUNetPlans__2d"

mkdir -p "$MONITOR_DIR"

find_latest_run_dir() {
  find "$WORK_ROOT/logs" -maxdepth 1 -type d -name "$RUN_GLOB" -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | awk 'NR==1 {print $2}'
}

summarize_fold_log() {
  local fold="$1"
  local run_dir="$2"
  local result_log
  result_log="$(ls -t "$RESULT_ROOT/fold_${fold}"/training_log_*.txt 2>/dev/null | head -1 || true)"
  local log="${result_log:-$run_dir/fold${fold}.log}"
  if [[ ! -s "$log" ]]; then
    printf 'fold%s: no log yet\n' "$fold"
    return
  fi
  local epoch dice train_loss val_loss epoch_time best
  epoch="$(grep -E 'Epoch [0-9]+' "$log" | tail -1 | sed -E 's/.*Epoch ([0-9]+).*/\1/' || true)"
  train_loss="$(grep -E 'train_loss' "$log" | tail -1 | sed -E 's/.*train_loss[[:space:]]+//g' || true)"
  val_loss="$(grep -E 'val_loss' "$log" | tail -1 | sed -E 's/.*val_loss[[:space:]]+//g' || true)"
  dice="$(grep -E 'Pseudo dice' "$log" | tail -1 | sed -E 's/.*Pseudo dice //g' || true)"
  epoch_time="$(grep -E 'Epoch time' "$log" | tail -1 | sed -E 's/.*Epoch time:[[:space:]]+//g' || true)"
  best="$(grep -E 'New best EMA pseudo Dice' "$log" | tail -1 | sed -E 's/.*New best EMA pseudo Dice:[[:space:]]+//g' || true)"
  printf 'fold%s: epoch=%s train_loss=%s val_loss=%s pseudo_dice=%s epoch_time=%s best_ema=%s\n' \
    "$fold" "${epoch:-NA}" "${train_loss:-NA}" "${val_loss:-NA}" "${dice:-NA}" "${epoch_time:-NA}" "${best:-NA}"
  printf 'fold%s_log=%s\n' "$fold" "$log"
}

write_status() {
  local run_dir="$1"
  {
    echo "timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "host=$(hostname)"
    echo "work_root=$WORK_ROOT"
    echo "dataset=$DATASET_DIR"
    echo "result_root=$RESULT_ROOT"
    echo "train_session=$TRAIN_SESSION"
    if tmux has-session -t "$TRAIN_SESSION" 2>/dev/null; then
      echo "train_session_status=running"
    else
      echo "train_session_status=not_running"
    fi
    echo "latest_run_dir=${run_dir:-NA}"
    echo
    echo "[gpu]"
    nvidia-smi --query-gpu=index,name,memory.used,memory.free,utilization.gpu --format=csv,noheader || true
    echo
    echo "[processes]"
    pgrep -af 'nnUNetv2_train|nnUNetv2_plan_and_preprocess' || true
    echo
    echo "[disk]"
    df -hT "$WORK_ROOT" || true
    echo
    echo "[fold_logs]"
    if [[ -n "$run_dir" && -d "$run_dir" ]]; then
      for fold in 0 1 2 3 4; do
        summarize_fold_log "$fold" "$run_dir"
      done
    else
      echo "no run dir found"
    fi
    echo
    echo "[checkpoints]"
    find "$RESULT_ROOT" \
      -maxdepth 2 -type f \( -name 'checkpoint_best.pth' -o -name 'checkpoint_final.pth' -o -name 'checkpoint_latest.pth' \) \
      -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort || true
  } > "$STATUS_FILE"

  {
    echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    cat "$STATUS_FILE"
    echo
  } >> "$HISTORY_FILE"
}

idle_after_finish=0
while true; do
  run_dir="$(find_latest_run_dir || true)"
  write_status "$run_dir"

  if tmux has-session -t "$TRAIN_SESSION" 2>/dev/null || pgrep -f 'nnUNetv2_train|nnUNetv2_plan_and_preprocess' >/dev/null 2>&1; then
    idle_after_finish=0
  else
    idle_after_finish=$((idle_after_finish + 1))
    if (( idle_after_finish >= MAX_IDLE_AFTER_FINISH )); then
      break
    fi
  fi

  sleep "$INTERVAL_SECONDS"
done

write_status "$(find_latest_run_dir || true)"
echo "monitor_finished_at=$(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$STATUS_FILE"
