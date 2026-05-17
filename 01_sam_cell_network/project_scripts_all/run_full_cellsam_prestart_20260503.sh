#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
CELLSAM_PYTHON="${CELLSAM_PYTHON:-/backup/taotao_work/venvs/cellsam311_shared/bin/python}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export CUDA_VISIBLE_DEVICES

LOG_DIR="$FULL_ROOT/logs"
PRED_ROOT="$FULL_ROOT/cellsam_generalist/predictions"
METRIC_DIR="$FULL_ROOT/cellsam_generalist/metrics"
OVERLAY_DIR="$FULL_ROOT/cellsam_generalist/overlays"

mkdir -p "$LOG_DIR" "$PRED_ROOT" "$METRIC_DIR" "$OVERLAY_DIR"
exec > >(tee -a "$LOG_DIR/full_cellsam_prestart.log") 2>&1

cd "$PROJECT"
date
PYTHONPATH=. "$CELLSAM_PYTHON" scripts/run_cellsam_manifest_fast.py \
  --manifest_csv "$FULL_MANIFEST" \
  --out_dir "$PRED_ROOT" \
  --suffix _cellsam.tif \
  --bbox_threshold 0.4 \
  --grayscale_mode repeat \
  --skip_existing

PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_label_dir.py \
  --manifest_csv "$FULL_MANIFEST" \
  --pred_dir "$PRED_ROOT/labels" \
  --out_dir "$METRIC_DIR" \
  --pred_pattern "{stem}_cellsam.tif" \
  --method_name cellsam_generalist

PYTHONPATH=. "$NNUNET_PYTHON" scripts/render_instance_overlays.py \
  --manifest_csv "$FULL_MANIFEST" \
  --pred_dir "$PRED_ROOT/labels" \
  --out_dir "$OVERLAY_DIR" \
  --pred_pattern "{stem}_cellsam.tif" \
  --method_name cellsam_generalist

date
