#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
CELLPOSE_PYTHON="${CELLPOSE_PYTHON:-/backup/taotao_work/venvs/cellpose311/bin/python}"
CELLSAM_PYTHON="${CELLSAM_PYTHON:-/backup/taotao_work/venvs/cellsam311_shared/bin/python}"

MANIFEST="${MANIFEST:-$PROJECT/outputs/yeastnet_eval_50_20260504/manifest.csv}"
OUT_ROOT="${OUT_ROOT:-$PROJECT/experiments/yeastnet_eval_50_20260504}"
SAMCELL_CONFIG="${SAMCELL_CONFIG:-$PROJECT/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml}"
GPU_DEVICE="${GPU_DEVICE:-1}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-$GPU_DEVICE}"
RUN_SAMCELL="${RUN_SAMCELL:-1}"
RUN_CELLPOSE="${RUN_CELLPOSE:-1}"
RUN_CELLSAM="${RUN_CELLSAM:-1}"
LIMIT="${LIMIT:-}"
export CUDA_VISIBLE_DEVICES

LOG_DIR="$OUT_ROOT/logs"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/run_yeastnet_eval.log") 2>&1

cd "$PROJECT"
date
echo "manifest: $MANIFEST"
echo "out_root: $OUT_ROOT"
echo "samcell_config: $SAMCELL_CONFIG"
echo "run_samcell=$RUN_SAMCELL run_cellpose=$RUN_CELLPOSE run_cellsam=$RUN_CELLSAM"

if [ ! -s "$MANIFEST" ]; then
  echo "missing manifest: $MANIFEST"
  exit 1
fi

LIMIT_ARGS=()
if [ -n "$LIMIT" ]; then
  LIMIT_ARGS=(--limit "$LIMIT")
fi

if [ "$RUN_SAMCELL" = "1" ]; then
  echo "=== SAM-Cell YeastNet eval ==="
  PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_devset.py \
    --config "$SAMCELL_CONFIG" \
    --devset_csv "$MANIFEST" \
    --out_dir "$OUT_ROOT/samcell_v3" \
    --save_outputs \
    --use_cache \
    "${LIMIT_ARGS[@]}"
fi

if [ "$RUN_CELLPOSE" = "1" ]; then
  echo "=== Cellpose cyto3 YeastNet eval ==="
  PRED_DIR="$OUT_ROOT/cellpose_official_cyto3/predictions"
  METRIC_DIR="$OUT_ROOT/cellpose_official_cyto3/metrics"
  OVERLAY_DIR="$OUT_ROOT/cellpose_official_cyto3/overlays"
  mkdir -p "$PRED_DIR" "$METRIC_DIR" "$OVERLAY_DIR"
  PYTHONPATH=. "$CELLPOSE_PYTHON" scripts/run_cellpose_manifest_cli_batch.py \
    --manifest_csv "$MANIFEST" \
    --out_dir "$PRED_DIR" \
    --pretrained_model cyto3 \
    --gpu_device "$GPU_DEVICE" \
    --skip_existing \
    "${LIMIT_ARGS[@]}"
  PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_label_dir.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_DIR" \
    --out_dir "$METRIC_DIR" \
    --pred_pattern "{stem}_cp_masks.tif" \
    --method_name cellpose_official_cyto3
  PYTHONPATH=. "$NNUNET_PYTHON" scripts/render_instance_overlays.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_DIR" \
    --out_dir "$OVERLAY_DIR" \
    --pred_pattern "{stem}_cp_masks.tif" \
    --method_name cellpose_official_cyto3
fi

if [ "$RUN_CELLSAM" = "1" ]; then
  echo "=== CellSAM YeastNet eval ==="
  PRED_ROOT="$OUT_ROOT/cellsam_generalist/predictions"
  METRIC_DIR="$OUT_ROOT/cellsam_generalist/metrics"
  OVERLAY_DIR="$OUT_ROOT/cellsam_generalist/overlays"
  mkdir -p "$PRED_ROOT" "$METRIC_DIR" "$OVERLAY_DIR"
  PYTHONPATH=. "$CELLSAM_PYTHON" scripts/run_cellsam_manifest_fast.py \
    --manifest_csv "$MANIFEST" \
    --out_dir "$PRED_ROOT" \
    --suffix _cellsam.tif \
    --bbox_threshold 0.4 \
    --grayscale_mode repeat \
    --skip_existing \
    "${LIMIT_ARGS[@]}"
  PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_label_dir.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_ROOT/labels" \
    --out_dir "$METRIC_DIR" \
    --pred_pattern "{stem}_cellsam.tif" \
    --method_name cellsam_generalist
  PYTHONPATH=. "$NNUNET_PYTHON" scripts/render_instance_overlays.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_ROOT/labels" \
    --out_dir "$OVERLAY_DIR" \
    --pred_pattern "{stem}_cellsam.tif" \
    --method_name cellsam_generalist
fi

"$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
payload = {
    "manifest": "$MANIFEST",
    "out_root": "$OUT_ROOT",
    "samcell_config": "$SAMCELL_CONFIG",
    "run_samcell": "$RUN_SAMCELL",
    "run_cellpose": "$RUN_CELLPOSE",
    "run_cellsam": "$RUN_CELLSAM",
    "limit": "$LIMIT",
}
out = Path("$OUT_ROOT/run_manifest.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY

date
