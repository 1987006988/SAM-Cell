#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
REFINE_ROOT="${REFINE_ROOT:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"
POLL_SECONDS="${POLL_SECONDS:-3600}"
RUN_ONCE="${RUN_ONCE:-0}"

MONITOR_DIR="$FULL_ROOT/logs/hourly_full_inference_watch_20260504"
LATEST="$MONITOR_DIR/latest_status.txt"
HISTORY="$MONITOR_DIR/history.tsv"
MONITOR_LOG="$MONITOR_DIR/monitor.log"

mkdir -p "$MONITOR_DIR"

count_files() {
  local dir="$1"
  local pattern="$2"
  if [ ! -d "$dir" ]; then
    echo 0
    return
  fi
  find "$dir" -maxdepth 1 -type f -name "$pattern" 2>/dev/null | wc -l | tr -d ' '
}

metric_state() {
  local path="$1"
  if [ -s "$path" ]; then
    echo "done"
  else
    echo "pending"
  fi
}

session_state() {
  local name="$1"
  if tmux has-session -t "$name" 2>/dev/null; then
    echo "alive"
  else
    echo "dead"
  fi
}

refine_decision_state() {
  local path="$REFINE_ROOT/decision.json"
  if [ ! -s "$path" ]; then
    echo "pending"
    return
  fi
  "$PYTHON_BIN" - "$path" <<'PY'
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("accepted" if decision.get("accepted") else "rejected")
PY
}

active_samcell_dir() {
  local decision="$1"
  if [ "$decision" = "accepted" ]; then
    echo "$FULL_ROOT/samcell_refine_final"
  else
    echo "$FULL_ROOT/samcell_final"
  fi
}

append_history_header() {
  if [ ! -s "$HISTORY" ]; then
    printf "epoch\ttimestamp\trefine_decision\tcellsam_labels\tsamcell_labels\tsamcell_dir\tcellsam_metrics\tsamcell_metrics\n" > "$HISTORY"
  fi
}

write_snapshot() {
  append_history_header
  local epoch timestamp decision samcell_dir cellsam_labels samcell_labels cellsam_metrics samcell_metrics
  epoch="$(date +%s)"
  timestamp="$(date '+%F %T %Z')"
  decision="$(refine_decision_state)"
  samcell_dir="$(active_samcell_dir "$decision")"
  cellsam_labels="$(count_files "$FULL_ROOT/cellsam_generalist/predictions/labels" "*_cellsam.tif")"
  samcell_labels="$(count_files "$samcell_dir/labels" "*.tif")"
  cellsam_metrics="$(metric_state "$FULL_ROOT/cellsam_generalist/metrics/summary_by_source.csv")"
  samcell_metrics="$(metric_state "$samcell_dir/summary.csv")"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$epoch" "$timestamp" "$decision" "$cellsam_labels" "$samcell_labels" "$samcell_dir" "$cellsam_metrics" "$samcell_metrics" >> "$HISTORY"

  {
    echo "timestamp: $timestamp"
    echo "project: $PROJECT"
    echo "full_root: $FULL_ROOT"
    echo "refine_root: $REFINE_ROOT"
    echo "refine_decision: $decision"
    echo
    echo "tracked_outputs:"
    echo "  cellsam_dir: $FULL_ROOT/cellsam_generalist"
    echo "  samcell_dir: $samcell_dir"
    echo
    echo "counts:"
    echo "  cellsam_labels: $cellsam_labels/16777"
    echo "  samcell_labels: $samcell_labels/16777"
    echo
    echo "metrics:"
    echo "  cellsam: $cellsam_metrics"
    echo "  samcell: $samcell_metrics"
    echo
    echo "sessions:"
    echo "  full_cellsam_prestart: $(session_state full_cellsam_prestart)"
    echo "  full_samcell_final: $(session_state full_samcell_final)"
    echo "  full_samcell_refine_final: $(session_state full_samcell_refine_final)"
    echo "  tn_refine_combo_search_20260504: $(session_state tn_refine_combo_search_20260504)"
    echo "  ensure_samcell_after_tn_refine: $(session_state ensure_samcell_after_tn_refine)"
    echo
    echo "gpu:"
    nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true
    echo
    echo "disk:"
    df -h "$FULL_ROOT" 2>/dev/null || true
  } > "$LATEST.tmp"
  mv "$LATEST.tmp" "$LATEST"

  echo "[$timestamp] refine=$decision cellsam=$cellsam_labels/16777 samcell=$samcell_labels/16777 cellsam_metrics=$cellsam_metrics samcell_metrics=$samcell_metrics samcell_dir=$samcell_dir" >> "$MONITOR_LOG"

  if [ "$cellsam_metrics" = "done" ] && [ "$samcell_metrics" = "done" ]; then
    echo "[$timestamp] tracked CellSAM and SAM-Cell metrics complete; hourly watch exiting" >> "$MONITOR_LOG"
    return 10
  fi
  return 0
}

while true; do
  set +e
  write_snapshot
  code=$?
  set -e
  if [ "$code" = "10" ]; then
    exit 0
  fi
  if [ "$code" != "0" ]; then
    exit "$code"
  fi
  if [ "$RUN_ONCE" = "1" ]; then
    exit 0
  fi
  sleep "$POLL_SECONDS"
done
