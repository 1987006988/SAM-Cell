#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/backup/taotao_work/sam_cell}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_ROOT="${FULL_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503}"
REPRO_ROOT="${REPRO_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501}"
OUT_DIR="${OUT_DIR:-/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
export CUDA_VISIBLE_DEVICES

CONFIG="${CONFIG:-$PROJECT_ROOT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
MANIFEST="${MANIFEST:-$REPRO_ROOT/manifests/far_ood_test.csv}"
FULL_LABEL_DIR="${FULL_LABEL_DIR:-$FULL_ROOT/samcell_refine_final/labels}"
CELLPOSE_FAROOD_SUMMARY="${CELLPOSE_FAROOD_SUMMARY:-$REPRO_ROOT/metrics/cellpose_official_cyto3/far_ood_test/summary_by_source.csv}"
LOG_DIR="${LOG_DIR:-$FULL_ROOT/logs/farood_module_attribution_20260507}"
mkdir -p "$LOG_DIR" "$OUT_DIR"

LIMIT_ARG=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARG=(--limit "$LIMIT")
fi

OVERLAY_ARG=()
if [[ "${SAVE_OVERLAYS:-0}" == "1" ]]; then
  OVERLAY_ARG=(--save_overlays)
fi

cd "$PROJECT_ROOT"
{
  date '+%Y-%m-%d %H:%M:%S %Z'
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo "CONFIG=$CONFIG"
  echo "MANIFEST=$MANIFEST"
  echo "OUT_DIR=$OUT_DIR"
  echo "FULL_LABEL_DIR=$FULL_LABEL_DIR"
  echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
} | tee "$LOG_DIR/run_header.txt"

"$PYTHON_BIN" scripts/farood_module_attribution_20260507.py \
  --config "$CONFIG" \
  --manifest_csv "$MANIFEST" \
  --out_dir "$OUT_DIR" \
  --full_samcell_label_dir "$FULL_LABEL_DIR" \
  --cellpose_farood_summary "$CELLPOSE_FAROOD_SUMMARY" \
  --skip_existing \
  "${LIMIT_ARG[@]}" \
  "${OVERLAY_ARG[@]}" \
  2>&1 | tee "$LOG_DIR/run.log"
