#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
SEARCH_ROOT="${SEARCH_ROOT:-$PROJECT/outputs/tissuenet_local_combo_search_20260504}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"
POLL_SECONDS="${POLL_SECONDS:-1800}"
RUN_ONCE="${RUN_ONCE:-0}"

MANIFEST="$FULL_ROOT/manifests/full.csv"
MONITOR_DIR="$FULL_ROOT/logs/full_inference_tn_combo_monitor_20260504"
HISTORY="$MONITOR_DIR/history.tsv"
LATEST="$MONITOR_DIR/latest_status.txt"
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

metric_state() {
  local path="$1"
  if [ -s "$path" ]; then
    echo "done"
  else
    echo "pending"
  fi
}

append_history_header() {
  if [ ! -s "$HISTORY" ]; then
    printf "epoch\ttimestamp\tcellpose_labels\tcellsam_labels\tsamcell_labels\ttune_rows\tholdout_rows\teval250_tn_rows\teval250_all_rows\tdecision\n" > "$HISTORY"
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
  local path="$SEARCH_ROOT/decision.json"
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

write_snapshot() {
  append_history_header

  local total
  if [ -s "$MANIFEST" ]; then
    total=$(( $(wc -l < "$MANIFEST") - 1 ))
  else
    total=16777
  fi

  local epoch timestamp
  epoch="$(date +%s)"
  timestamp="$(date '+%F %T %Z')"

  local cp_count cs_count sam_count
  cp_count="$(count_files "$FULL_ROOT/cellpose_official_cyto3/predictions" "*_cp_masks.tif")"
  cs_count="$(count_files "$FULL_ROOT/cellsam_generalist/predictions/labels" "*_cellsam.tif")"
  sam_count="$(count_files "$FULL_ROOT/samcell_final/labels" "*.tif")"

  local tune_rows holdout_rows eval250_tn_rows eval250_all_rows decision
  tune_rows="$(csv_rows "$SEARCH_ROOT/tune_summary.csv")"
  holdout_rows="$(csv_rows "$SEARCH_ROOT/holdout_summary.partial.csv")"
  if [ -s "$SEARCH_ROOT/holdout_summary.csv" ]; then
    holdout_rows="$(csv_rows "$SEARCH_ROOT/holdout_summary.csv")"
  fi
  eval250_tn_rows="$(csv_rows "$SEARCH_ROOT/eval250_tissuenet_summary.partial.csv")"
  if [ -s "$SEARCH_ROOT/eval250_tissuenet_summary.csv" ]; then
    eval250_tn_rows="$(csv_rows "$SEARCH_ROOT/eval250_tissuenet_summary.csv")"
  fi
  eval250_all_rows="$(csv_rows "$SEARCH_ROOT/eval250_all_summary.partial.csv")"
  if [ -s "$SEARCH_ROOT/eval250_all_summary.csv" ]; then
    eval250_all_rows="$(csv_rows "$SEARCH_ROOT/eval250_all_summary.csv")"
  fi
  decision="$(decision_state)"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$epoch" "$timestamp" "$cp_count" "$cs_count" "$sam_count" \
    "$tune_rows" "$holdout_rows" "$eval250_tn_rows" "$eval250_all_rows" "$decision" >> "$HISTORY"

  {
    echo "timestamp: $timestamp"
    echo "project: $PROJECT"
    echo "full_root: $FULL_ROOT"
    echo "search_root: $SEARCH_ROOT"
    echo "manifest_total: $total"
    echo
    echo "sessions:"
    echo "  tn_combo_search_20260504: $(session_state tn_combo_search_20260504)"
    echo "  ensure_samcell_after_tn_combo: $(session_state ensure_samcell_after_tn_combo)"
    echo "  full_cellsam_prestart: $(session_state full_cellsam_prestart)"
    echo "  full_samcell_final: $(session_state full_samcell_final)"
    echo "  monitor_full_inference_tn_combo_20260504: $(session_state monitor_full_inference_tn_combo_20260504)"
    echo
    echo "full_inference_counts:"
    echo "  cellpose_labels: $cp_count/$total"
    echo "  cellsam_labels: $cs_count/$total"
    echo "  samcell_labels: $sam_count/$total"
    echo
    echo "metrics:"
    echo "  cellpose_official_cyto3: $(metric_state "$FULL_ROOT/cellpose_official_cyto3/metrics/summary_by_source.csv")"
    echo "  cellsam_generalist: $(metric_state "$FULL_ROOT/cellsam_generalist/metrics/summary_by_source.csv")"
    echo "  samcell_final: $(metric_state "$FULL_ROOT/samcell_final/summary.csv")"
    echo
    echo "tissuenet_combo:"
    echo "  tune_rows: $tune_rows"
    echo "  holdout_rows: $holdout_rows"
    echo "  eval250_tissuenet_rows: $eval250_tn_rows"
    echo "  eval250_all_rows: $eval250_all_rows"
    echo "  decision: $decision"
    echo "  best_tune: $(best_csv_row "$SEARCH_ROOT/tune_summary.csv" tissuenet_proposal_pq)"
    echo "  best_holdout: $(best_csv_row "$SEARCH_ROOT/holdout_summary.partial.csv" tissuenet_final_pq)"
    echo "  best_eval250_tissuenet: $(best_csv_row "$SEARCH_ROOT/eval250_tissuenet_summary.partial.csv" tissuenet_final_pq)"
    echo "  best_eval250_all: $(best_csv_row "$SEARCH_ROOT/eval250_all_summary.partial.csv" ALL_final_pq)"
    echo
    echo "disk:"
    df -h "$FULL_ROOT" 2>/dev/null || true
    echo
    echo "gpu:"
    nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true
    echo
    echo "active_processes:"
    pgrep -af "tissuenet_local_combo_search_20260504|eval_devset.py|run_cellsam_manifest_fast.py" || true
    echo
    echo "recent_tmux:"
    for name in tn_combo_search_20260504 ensure_samcell_after_tn_combo full_cellsam_prestart full_samcell_final; do
      if tmux has-session -t "$name" 2>/dev/null; then
        echo "----- tmux:$name -----"
        tmux capture-pane -pt "$name" -S -40 2>/dev/null || true
      fi
    done
  } > "$LATEST.tmp"
  mv "$LATEST.tmp" "$LATEST"

  echo "[$timestamp] cp=$cp_count/$total cs=$cs_count/$total sam=$sam_count/$total tune=$tune_rows holdout=$holdout_rows eval250_tn=$eval250_tn_rows eval250_all=$eval250_all_rows decision=$decision" >> "$MONITOR_LOG"

  if [ "$(metric_state "$FULL_ROOT/cellsam_generalist/metrics/summary_by_source.csv")" = "done" ] \
    && [ "$(metric_state "$FULL_ROOT/samcell_final/summary.csv")" = "done" ]; then
    echo "[$timestamp] CellSAM and SAM-Cell full metrics complete; monitor exiting" >> "$MONITOR_LOG"
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
