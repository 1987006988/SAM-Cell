#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"
POLL_SECONDS="${POLL_SECONDS:-600}"
RUN_ONCE="${RUN_ONCE:-0}"

MONITOR_DIR="$EXP_ROOT/logs/refine_monitor_20260504"
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

csv_rows() {
  local path="$1"
  if [ ! -s "$path" ]; then
    echo 0
    return
  fi
  local rows
  rows="$(wc -l < "$path" | tr -d ' ')"
  if [ "$rows" -gt 0 ]; then
    echo $((rows - 1))
  else
    echo 0
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

best_csv_row() {
  local path="$1"
  local value_col="$2"
  if [ ! -s "$path" ]; then
    echo "pending"
    return
  fi
  "$PYTHON_BIN" - "$path" "$value_col" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
value_col = sys.argv[2]
rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
if not rows:
    print("empty")
    raise SystemExit
rows.sort(key=lambda r: float(r.get(value_col) or r.get("objective") or 0.0), reverse=True)
row = rows[0]
name = row.get("candidate", "unknown")
value = row.get(value_col) or row.get("objective") or ""
delta = row.get("tissuenet_delta") or row.get("ALL_delta") or ""
print(f"{name} {value_col}={value} delta={delta}")
PY
}

decision_state() {
  local path="$EXP_ROOT/decision.json"
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

append_history_header() {
  if [ ! -s "$HISTORY" ]; then
    printf "epoch\ttimestamp\tcellsam_labels\tsamcell_labels\ttune_rows\tholdout_rows\teval250_rows\tallsource_rows\tdecision\n" > "$HISTORY"
  fi
}

write_snapshot() {
  append_history_header
  local epoch timestamp cellsam_count samcell_count tune_rows holdout_rows eval250_rows allsource_rows decision
  epoch="$(date +%s)"
  timestamp="$(date '+%F %T %Z')"
  cellsam_count="$(count_files "$FULL_ROOT/cellsam_generalist/predictions/labels" "*_cellsam.tif")"
  samcell_count="$(count_files "$FULL_ROOT/samcell_final/labels" "*.tif")"
  tune_rows="$(csv_rows "$EXP_ROOT/tune_summary.csv")"
  holdout_rows="$(csv_rows "$EXP_ROOT/holdout_summary.partial.csv")"
  if [ -s "$EXP_ROOT/holdout_summary.csv" ]; then
    holdout_rows="$(csv_rows "$EXP_ROOT/holdout_summary.csv")"
  fi
  eval250_rows="$(csv_rows "$EXP_ROOT/eval250_tissuenet_summary.partial.csv")"
  if [ -s "$EXP_ROOT/eval250_tissuenet_summary.csv" ]; then
    eval250_rows="$(csv_rows "$EXP_ROOT/eval250_tissuenet_summary.csv")"
  fi
  allsource_rows="$(csv_rows "$EXP_ROOT/eval250_all_summary.csv")"
  decision="$(decision_state)"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$epoch" "$timestamp" "$cellsam_count" "$samcell_count" "$tune_rows" "$holdout_rows" "$eval250_rows" "$allsource_rows" "$decision" >> "$HISTORY"

  {
    echo "timestamp: $timestamp"
    echo "project: $PROJECT"
    echo "exp_root: $EXP_ROOT"
    echo "full_root: $FULL_ROOT"
    echo
    echo "sessions:"
    echo "  tn_refine_combo_search_20260504: $(session_state tn_refine_combo_search_20260504)"
    echo "  full_cellsam_prestart: $(session_state full_cellsam_prestart)"
    echo "  full_samcell_final: $(session_state full_samcell_final)"
    echo
    echo "full_inference_counts:"
    echo "  cellsam_labels: $cellsam_count/16777"
    echo "  samcell_labels: $samcell_count/16777"
    echo
    echo "refine_search:"
    echo "  tune_rows: $tune_rows"
    echo "  holdout_rows: $holdout_rows"
    echo "  eval250_tissuenet_rows: $eval250_rows"
    echo "  eval250_all_rows: $allsource_rows"
    echo "  decision: $decision"
    echo "  best_tune: $(best_csv_row "$EXP_ROOT/tune_summary.csv" tissuenet_proposal_pq)"
    echo "  best_holdout: $(best_csv_row "$EXP_ROOT/holdout_summary.partial.csv" tissuenet_final_pq)"
    echo "  best_eval250: $(best_csv_row "$EXP_ROOT/eval250_tissuenet_summary.partial.csv" tissuenet_final_pq)"
    echo "  best_allsource: $(best_csv_row "$EXP_ROOT/eval250_all_summary.csv" ALL_final_pq)"
    echo
    echo "gpu:"
    nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true
    echo
    echo "active_processes:"
    pgrep -af "tissuenet_refine_combo_search_20260504|run_cellsam_manifest_fast.py|eval_devset.py" || true
  } > "$LATEST.tmp"
  mv "$LATEST.tmp" "$LATEST"

  echo "[$timestamp] cs=$cellsam_count/16777 sam=$samcell_count/16777 tune=$tune_rows holdout=$holdout_rows eval250=$eval250_rows all=$allsource_rows decision=$decision" >> "$MONITOR_LOG"

  if [ "$decision" != "pending" ]; then
    echo "[$timestamp] refine decision complete; monitor exiting" >> "$MONITOR_LOG"
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
