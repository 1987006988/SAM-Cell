#!/usr/bin/env bash
set -euo pipefail

GPU_DEVICE="${GPU_DEVICE:-0}"
ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501}"
PYTHON_ENV="${PYTHON_ENV:-/backup/taotao_work/venvs/nnunet}"
PYTHON="$PYTHON_ENV/bin/python"
SAM2_REPO="${SAM2_REPO:-/backup/taotao_work/segment-anything-2}"
SAM2_CHECKPOINT="${SAM2_CHECKPOINT:-/backup/taotao_work/segment-anything-2/checkpoints/sam2_hiera_large.pt}"
RUN_NAME="sam2_automatic_dense"

if [ "$#" -gt 0 ]; then
  SPLITS=("$@")
else
  SPLITS=("iid_val" "pannuke_core_test" "far_ood_test")
fi

cd "$ROOT"
mkdir -p "$EXP_ROOT/logs" "$EXP_ROOT/predictions" "$EXP_ROOT/metrics" "$EXP_ROOT/overlays" "$EXP_ROOT/run_manifests"

if [ ! -x "$PYTHON" ]; then
  echo "Python env not found: $PYTHON" >&2
  exit 2
fi
if [ ! -d "$SAM2_REPO" ]; then
  echo "SAM2 repo not found: $SAM2_REPO" >&2
  exit 2
fi
if [ ! -f "$SAM2_CHECKPOINT" ]; then
  echo "SAM2 checkpoint not found: $SAM2_CHECKPOINT" >&2
  exit 2
fi

export CUDA_VISIBLE_DEVICES="$GPU_DEVICE"
export PYTHONPATH="$ROOT:$SAM2_REPO:${PYTHONPATH:-}"

for SPLIT in "${SPLITS[@]}"; do
  MANIFEST="$EXP_ROOT/manifests/$SPLIT.csv"
  PRED_DIR="$EXP_ROOT/predictions/$RUN_NAME/$SPLIT"
  METRIC_DIR="$EXP_ROOT/metrics/$RUN_NAME/$SPLIT"
  OVERLAY_DIR="$EXP_ROOT/overlays/$RUN_NAME/$SPLIT"
  "$PYTHON" scripts/run_sam2_automatic_manifest.py \
    --manifest_csv "$MANIFEST" \
    --out_dir "$PRED_DIR" \
    --sam2_repo "$SAM2_REPO" \
    --checkpoint "$SAM2_CHECKPOINT" \
    --device cuda \
    --points_per_side 64 \
    --points_per_batch 128 \
    --pred_iou_thresh 0.7 \
    --stability_score_thresh 0.9 \
    --crop_n_layers 1 \
    --crop_n_points_downscale_factor 2 \
    --min_mask_region_area 0 \
    --label_min_area 10
  "$PYTHON" scripts/eval_label_dir.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_DIR" \
    --out_dir "$METRIC_DIR" \
    --pred_pattern "{stem}.tif" \
    --method_name "$RUN_NAME"
  "$PYTHON" scripts/render_instance_overlays.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_DIR" \
    --out_dir "$OVERLAY_DIR" \
    --pred_pattern "{stem}.tif" \
    --method_name "$RUN_NAME"
done

"$PYTHON" - <<PY
import json
from pathlib import Path

payload = {
    "run_name": "$RUN_NAME",
    "gpu_device": "$GPU_DEVICE",
    "sam2_repo": "$SAM2_REPO",
    "checkpoint": "$SAM2_CHECKPOINT",
    "splits": "${SPLITS[*]}".split(),
    "points_per_side": 64,
    "pred_iou_thresh": 0.7,
    "stability_score_thresh": 0.9,
    "crop_n_layers": 1,
    "min_mask_region_area": 0,
    "label_min_area": 10,
}
out = Path("$EXP_ROOT/run_manifests/${RUN_NAME}.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY
