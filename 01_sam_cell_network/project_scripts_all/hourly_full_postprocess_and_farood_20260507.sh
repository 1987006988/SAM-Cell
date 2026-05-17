#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/backup/taotao_work/sam_cell}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_ROOT="${FULL_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503}"
EXPECTED_N="${EXPECTED_N:-16777}"
SLEEP_SECONDS="${SLEEP_SECONDS:-3600}"
FAROOD_SESSION="${FAROOD_SESSION:-farood_module_attribution_20260507}"
SUMMARY_SESSION="${SUMMARY_SESSION:-full_samcell_refine_cached_summary_eval}"
CACHED_SUMMARY_WATCHER_SESSION="${CACHED_SUMMARY_WATCHER_SESSION:-samcell_refine_cached_summary_watcher_20260506}"
LOG_DIR="${LOG_DIR:-$FULL_ROOT/logs/hourly_full_postprocess_and_farood_20260507}"
LOG_FILE="$LOG_DIR/watch.log"
mkdir -p "$LOG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

FULL_MANIFEST="$FULL_ROOT/manifests/full.csv"
SAMCELL_DIR="$FULL_ROOT/samcell_refine_final"
SAMCELL_LABEL_DIR="$SAMCELL_DIR/labels"
SAMCELL_SUMMARY="$SAMCELL_DIR/summary.csv"
SAMCELL_PER_IMAGE="$SAMCELL_DIR/per_image.csv"
CELLPOSE_METRICS="$FULL_ROOT/cellpose_official_cyto3/metrics"
CELLSAM_METRICS="$FULL_ROOT/cellsam_generalist/metrics"
COMPARISON_MD="$FULL_ROOT/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.md"
FAROOD_OUT="${FAROOD_OUT:-/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507}"
AUDIT_JSON="${AUDIT_JSON:-$FULL_ROOT/metrics/active_goal_audit_20260507.json}"
AUDIT_MD="${AUDIT_MD:-$FULL_ROOT/metrics/active_goal_audit_20260507.md}"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S %Z'
}

count_tifs() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo 0
    return
  fi
  find "$dir" -maxdepth 1 -type f -name '*.tif' | wc -l
}

csv_data_rows() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo 0
    return
  fi
  local lines
  lines=$(wc -l < "$path")
  if (( lines <= 0 )); then
    echo 0
  else
    echo $((lines - 1))
  fi
}

session_exists() {
  tmux has-session -t "$1" 2>/dev/null
}

ensure_cellpose_metrics() {
  if [[ -s "$CELLPOSE_METRICS/summary_by_source.csv" && -s "$CELLPOSE_METRICS/per_image.csv" ]]; then
    return
  fi
  echo "[$(timestamp)] Cellpose metrics missing; running eval_label_dir.py"
  "$PYTHON_BIN" scripts/eval_label_dir.py \
    --manifest_csv "$FULL_MANIFEST" \
    --pred_dir "$FULL_ROOT/cellpose_official_cyto3/predictions" \
    --out_dir "$CELLPOSE_METRICS" \
    --pred_pattern '{stem}_cp_masks.tif' \
    --method_name cellpose_official_cyto3
}

ensure_cellsam_metrics() {
  if [[ -s "$CELLSAM_METRICS/summary_by_source.csv" && -s "$CELLSAM_METRICS/per_image.csv" ]]; then
    return
  fi
  echo "[$(timestamp)] CellSAM metrics missing; running eval_label_dir.py"
  "$PYTHON_BIN" scripts/eval_label_dir.py \
    --manifest_csv "$FULL_MANIFEST" \
    --pred_dir "$FULL_ROOT/cellsam_generalist/predictions/labels" \
    --out_dir "$CELLSAM_METRICS" \
    --pred_pattern '{stem}_cellsam.tif' \
    --method_name cellsam_generalist
}

ensure_samcell_summary_if_labels_complete() {
  local labels
  labels=$(count_tifs "$SAMCELL_LABEL_DIR")
  if (( labels < EXPECTED_N )); then
    echo "[$(timestamp)] SAM-Cell labels $labels/$EXPECTED_N; summary wait."
    return
  fi
  if [[ -s "$SAMCELL_SUMMARY" && -s "$SAMCELL_PER_IMAGE" ]]; then
    echo "[$(timestamp)] SAM-Cell summary already present."
    return
  fi
  if session_exists "$CACHED_SUMMARY_WATCHER_SESSION"; then
    echo "[$(timestamp)] SAM-Cell labels complete; stable cached summary watcher is alive, so this watcher will not start a duplicate/early summary."
    return
  fi
  if session_exists "$SUMMARY_SESSION"; then
    echo "[$(timestamp)] SAM-Cell labels complete; cached summary session already running."
    return
  fi
  echo "[$(timestamp)] SAM-Cell labels complete; stable watcher is absent, starting fallback cached summary eval in tmux $SUMMARY_SESSION."
  tmux new-session -d -s "$SUMMARY_SESSION" \
    "cd '$PROJECT_ROOT' && CUDA_VISIBLE_DEVICES='${SUMMARY_CUDA_VISIBLE_DEVICES:-1}' '$PYTHON_BIN' scripts/eval_devset.py --config outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml --devset_csv '$FULL_MANIFEST' --out_dir '$SAMCELL_DIR' --use_cache"
}

try_build_comparison() {
  local rows
  rows=$(csv_data_rows "$SAMCELL_PER_IMAGE")
  if [[ ! -s "$SAMCELL_SUMMARY" || "$rows" -lt "$EXPECTED_N" ]]; then
    echo "[$(timestamp)] Full model comparison not ready; SAM-Cell per_image rows=$rows/$EXPECTED_N."
    return 1
  fi
  echo "[$(timestamp)] Building full model PQ/AJI/Dice comparison."
  "$PYTHON_BIN" scripts/build_full_model_metric_comparison_20260507.py --root "$FULL_ROOT" --expected_n "$EXPECTED_N"
}

maybe_start_farood() {
  if [[ ! -s "$COMPARISON_MD" ]]; then
    echo "[$(timestamp)] Far-OOD attribution wait: full comparison is not ready."
    return
  fi
  if [[ -s "$FAROOD_OUT/interpretation.md" && -s "$FAROOD_OUT/combined_summary.csv" ]]; then
    echo "[$(timestamp)] Far-OOD attribution already complete: $FAROOD_OUT"
    return
  fi
  if session_exists "$FAROOD_SESSION"; then
    echo "[$(timestamp)] Far-OOD attribution session already running: $FAROOD_SESSION"
    return
  fi
  echo "[$(timestamp)] Starting Far-OOD module attribution in tmux $FAROOD_SESSION."
  tmux new-session -d -s "$FAROOD_SESSION" \
    "cd '$PROJECT_ROOT' && CUDA_VISIBLE_DEVICES='${FAROOD_CUDA_VISIBLE_DEVICES:-1}' OUT_DIR='$FAROOD_OUT' bash scripts/run_farood_attribution_20260507.sh"
}

maybe_run_final_audit() {
  if [[ ! -s "$COMPARISON_MD" ]]; then
    echo "[$(timestamp)] Final audit wait: full comparison is not ready."
    return 1
  fi
  if [[ ! -s "$FAROOD_OUT/interpretation.md" || ! -s "$FAROOD_OUT/combined_summary.csv" ]]; then
    echo "[$(timestamp)] Final audit wait: Far-OOD attribution is not complete."
    return 1
  fi
  echo "[$(timestamp)] Running final active-goal audit."
  set +e
  "$PYTHON_BIN" scripts/audit_active_goal_20260507.py \
    --out_json "$AUDIT_JSON" \
    --out_md "$AUDIT_MD"
  local audit_status=$?
  set -e
  if (( audit_status == 0 )); then
    "$PYTHON_BIN" scripts/build_active_goal_final_report_20260507.py \
      --audit_json "$AUDIT_JSON" \
      --out_md "$FULL_ROOT/metrics/active_goal_final_report_20260507.md"
    echo "[$(timestamp)] Final active-goal audit complete=true. Watcher can stop."
    return 0
  fi
  echo "[$(timestamp)] Final active-goal audit still incomplete. Continuing hourly watch."
  return 1
}

one_pass() {
  echo "[$(timestamp)] hourly postprocess pass begin"
  cd "$PROJECT_ROOT"
  "$PYTHON_BIN" scripts/remote_full_inference_completion_audit_20260506.py || true
  ensure_cellpose_metrics
  ensure_cellsam_metrics
  ensure_samcell_summary_if_labels_complete
  if try_build_comparison; then
    maybe_start_farood
  fi
  maybe_run_final_audit && return 0
  echo "[$(timestamp)] hourly postprocess pass end"
  return 1
}

if [[ "${RUN_ONCE:-0}" == "1" ]]; then
  one_pass || true
else
  while true; do
    if one_pass; then
      break
    fi
    sleep "$SLEEP_SECONDS"
  done
fi
