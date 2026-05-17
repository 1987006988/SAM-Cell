#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
OPT_ROOT="${OPT_ROOT:-$PROJECT/outputs/final_optimization_20260503}"
POLL_SECONDS="${POLL_SECONDS:-1800}"
RUN_ONCE="${RUN_ONCE:-0}"

MANIFEST="$FULL_ROOT/manifests/full.csv"
LOG_DIR="$FULL_ROOT/logs"
MONITOR_DIR="$LOG_DIR/full_inference_monitor_20260503"
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

calc_rate_eta() {
  local current="$1"
  local previous="$2"
  local dt="$3"
  local total="$4"
  awk -v current="$current" -v previous="$previous" -v dt="$dt" -v total="$total" '
    BEGIN {
      delta = current - previous
      remaining = total - current
      if (dt > 0 && delta > 0) {
        rate = delta / dt * 3600.0
        eta = remaining / rate
        printf "%.1f img/h, ETA %.1f h", rate, eta
      } else {
        printf "n/a"
      }
    }'
}

append_history_header() {
  if [ ! -s "$HISTORY" ]; then
    printf "epoch\ttimestamp\tcellpose_labels\tcellsam_labels\tsamcell_labels\tcellpose_overlays\tcellsam_overlays\tsamcell_overlays\n" > "$HISTORY"
  fi
}

capture_session() {
  local name="$1"
  if tmux has-session -t "$name" 2>/dev/null; then
    echo "----- tmux:$name -----"
    tmux capture-pane -pt "$name" -S -60 2>/dev/null || true
  fi
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

  local cp_count cs_count sam_count cp_overlay cs_overlay sam_overlay
  cp_count="$(count_files "$FULL_ROOT/cellpose_official_cyto3/predictions" "*_cp_masks.tif")"
  cs_count="$(count_files "$FULL_ROOT/cellsam_generalist/predictions/labels" "*_cellsam.tif")"
  sam_count="$(count_files "$FULL_ROOT/samcell_final/labels" "*.tif")"
  cp_overlay="$(count_files "$FULL_ROOT/cellpose_official_cyto3/overlays" "*.png")"
  cs_overlay="$(count_files "$FULL_ROOT/cellsam_generalist/overlays" "*.png")"
  sam_overlay="$(count_files "$FULL_ROOT/samcell_final/overlays" "*.png")"

  local prev_line prev_epoch prev_cp prev_cs prev_sam dt cp_rate cs_rate sam_rate
  prev_line="$(tail -n 1 "$HISTORY" 2>/dev/null || true)"
  prev_epoch=0
  prev_cp="$cp_count"
  prev_cs="$cs_count"
  prev_sam="$sam_count"
  if [ -n "$prev_line" ] && [[ "$prev_line" != epoch$'\t'* ]]; then
    prev_epoch="$(printf '%s\n' "$prev_line" | awk -F '\t' '{print $1}')"
    if [[ "$prev_epoch" =~ ^[0-9]+$ ]]; then
      prev_cp="$(printf '%s\n' "$prev_line" | awk -F '\t' '{print $3}')"
      prev_cs="$(printf '%s\n' "$prev_line" | awk -F '\t' '{print $4}')"
      prev_sam="$(printf '%s\n' "$prev_line" | awk -F '\t' '{print $5}')"
    else
      prev_epoch="$epoch"
    fi
  else
    prev_epoch="$epoch"
  fi
  dt=$(( epoch - prev_epoch ))
  cp_rate="$(calc_rate_eta "$cp_count" "$prev_cp" "$dt" "$total")"
  cs_rate="$(calc_rate_eta "$cs_count" "$prev_cs" "$dt" "$total")"
  sam_rate="$(calc_rate_eta "$sam_count" "$prev_sam" "$dt" "$total")"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$epoch" "$timestamp" "$cp_count" "$cs_count" "$sam_count" "$cp_overlay" "$cs_overlay" "$sam_overlay" >> "$HISTORY"

  local opt_state
  if [ -s "$OPT_ROOT/final_decision.json" ]; then
    opt_state="final_decision_present"
  else
    opt_state="waiting_for_final_decision"
  fi

  local cp_metric cs_metric sam_metric
  cp_metric="$(metric_state "$FULL_ROOT/cellpose_official_cyto3/metrics/summary_by_source.csv")"
  cs_metric="$(metric_state "$FULL_ROOT/cellsam_generalist/metrics/summary_by_source.csv")"
  sam_metric="$(metric_state "$FULL_ROOT/samcell_final/summary.csv")"

  {
    echo "timestamp: $timestamp"
    echo "project: $PROJECT"
    echo "full_root: $FULL_ROOT"
    echo "manifest_total: $total"
    echo
    echo "optimization: $opt_state"
    echo "sessions:"
    echo "  final_samcell_opt_20260503: $(session_state final_samcell_opt_20260503)"
    echo "  ensure_full_after_opt_20260503: $(session_state ensure_full_after_opt_20260503)"
    echo "  full_cellpose_cyto3_prestart: $(session_state full_cellpose_cyto3_prestart)"
    echo "  full_cellsam_prestart: $(session_state full_cellsam_prestart)"
    echo "  full_samcell_final: $(session_state full_samcell_final)"
    echo
    echo "counts:"
    echo "  cellpose_labels: $cp_count/$total"
    echo "  cellsam_labels: $cs_count/$total"
    echo "  samcell_labels: $sam_count/$total"
    echo "  cellpose_overlays: $cp_overlay/$total"
    echo "  cellsam_overlays: $cs_overlay/$total"
    echo "  samcell_overlays: $sam_overlay/$total"
    echo
    echo "rates_since_last_poll:"
    echo "  cellpose: $cp_rate"
    echo "  cellsam: $cs_rate"
    echo "  samcell: $sam_rate"
    echo
    echo "metrics:"
    echo "  cellpose_official_cyto3: $cp_metric"
    echo "  cellsam_generalist: $cs_metric"
    echo "  samcell_final: $sam_metric"
    echo
    echo "disk:"
    df -h "$FULL_ROOT" 2>/dev/null || true
    echo
    echo "gpu:"
    nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader 2>/dev/null || true
    echo
    echo "warnings:"
    if [ "$(session_state full_cellpose_cyto3_prestart)" = "dead" ] && [ "$cp_metric" != "done" ]; then
      echo "  cellpose prestart session is dead before metrics are done"
    fi
    if [ "$(session_state full_cellsam_prestart)" = "dead" ] && [ "$cs_metric" != "done" ]; then
      echo "  cellsam prestart session is dead before metrics are done"
    fi
    if [ "$opt_state" = "final_decision_present" ] && [ "$(session_state full_samcell_final)" = "dead" ] && [ "$sam_metric" != "done" ]; then
      echo "  final decision exists but full_samcell_final is not running and metrics are not done"
    fi
    echo
    echo "recent_logs:"
    for log in \
      "$LOG_DIR/full_cellpose_cyto3_prestart.log" \
      "$LOG_DIR/full_cellsam_prestart.log" \
      "$LOG_DIR/full_samcell.log" \
      "$LOG_DIR/ensure_full_inference.log"; do
      if [ -s "$log" ]; then
        echo "----- $log -----"
        tail -n 30 "$log" || true
      fi
    done
    capture_session final_samcell_opt_20260503
    capture_session full_cellpose_cyto3_prestart
    capture_session full_cellsam_prestart
    capture_session full_samcell_final
  } > "$LATEST.tmp"
  mv "$LATEST.tmp" "$LATEST"

  {
    echo "[$timestamp] cp=$cp_count/$total cs=$cs_count/$total sam=$sam_count/$total cp_metric=$cp_metric cs_metric=$cs_metric sam_metric=$sam_metric"
    echo "  rates: cp=[$cp_rate] cs=[$cs_rate] sam=[$sam_rate]"
  } >> "$MONITOR_LOG"

  if [ "$cp_metric" = "done" ] && [ "$cs_metric" = "done" ] && [ "$sam_metric" = "done" ]; then
    echo "[$timestamp] all full-corpus metrics are complete; monitor exiting" >> "$MONITOR_LOG"
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
