#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
CELLPOSE_PYTHON="${CELLPOSE_PYTHON:-/backup/taotao_work/venvs/cellpose311/bin/python}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
GPU_DEVICE="${GPU_DEVICE:-1}"

LOG_DIR="$FULL_ROOT/logs"
PRED_DIR="$FULL_ROOT/cellpose_official_cyto3/predictions"
METRIC_DIR="$FULL_ROOT/cellpose_official_cyto3/metrics"
OVERLAY_DIR="$FULL_ROOT/cellpose_official_cyto3/overlays"

mkdir -p "$LOG_DIR" "$PRED_DIR" "$METRIC_DIR" "$OVERLAY_DIR"
exec > >(tee -a "$LOG_DIR/full_cellpose_cyto3_prestart.log") 2>&1

cd "$PROJECT"
date
PYTHONPATH=. "$CELLPOSE_PYTHON" scripts/run_cellpose_manifest_cli_batch.py \
  --manifest_csv "$FULL_MANIFEST" \
  --out_dir "$PRED_DIR" \
  --pretrained_model cyto3 \
  --gpu_device "$GPU_DEVICE" \
  --skip_existing

PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_label_dir.py \
  --manifest_csv "$FULL_MANIFEST" \
  --pred_dir "$PRED_DIR" \
  --out_dir "$METRIC_DIR" \
  --pred_pattern "{stem}_cp_masks.tif" \
  --method_name cellpose_official_cyto3

PYTHONPATH=. "$NNUNET_PYTHON" scripts/render_instance_overlays.py \
  --manifest_csv "$FULL_MANIFEST" \
  --pred_dir "$PRED_DIR" \
  --out_dir "$OVERLAY_DIR" \
  --pred_pattern "{stem}_cp_masks.tif" \
  --method_name cellpose_official_cyto3

date
