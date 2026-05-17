#!/usr/bin/env bash
set -euo pipefail

GPU_DEVICE="${GPU_DEVICE:-0}"
ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501}"
CELLPOSE_ENV="${CELLPOSE_ENV:-/backup/taotao_work/venvs/cellpose311}"
PYTHON="$CELLPOSE_ENV/bin/python"
RUN_NAME="cellpose_official_cyto3"
if [ "$#" -gt 0 ]; then
  SPLITS=("$@")
else
  SPLITS=("iid_val" "pannuke_core_test" "far_ood_test")
fi

cd "$ROOT"
mkdir -p "$EXP_ROOT/logs" "$EXP_ROOT/predictions" "$EXP_ROOT/metrics" "$EXP_ROOT/overlays" "$EXP_ROOT/run_manifests"

if [ ! -x "$PYTHON" ]; then
  bash scripts/setup_server_cellpose_env.sh
fi

for SPLIT in "${SPLITS[@]}"; do
  MANIFEST="$EXP_ROOT/manifests/$SPLIT.csv"
  PRED_DIR="$EXP_ROOT/predictions/$RUN_NAME/$SPLIT"
  METRIC_DIR="$EXP_ROOT/metrics/$RUN_NAME/$SPLIT"
  OVERLAY_DIR="$EXP_ROOT/overlays/$RUN_NAME/$SPLIT"
  "$PYTHON" scripts/run_cellpose_manifest.py \
    --manifest_csv "$MANIFEST" \
    --out_dir "$PRED_DIR" \
    --pretrained_model cyto3 \
    --gpu_device "$GPU_DEVICE"
  "$PYTHON" scripts/eval_label_dir.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_DIR" \
    --out_dir "$METRIC_DIR" \
    --pred_pattern "{stem}_cp_masks.tif" \
    --method_name "$RUN_NAME"
  "$PYTHON" scripts/render_instance_overlays.py \
    --manifest_csv "$MANIFEST" \
    --pred_dir "$PRED_DIR" \
    --out_dir "$OVERLAY_DIR" \
    --pred_pattern "{stem}_cp_masks.tif" \
    --method_name "$RUN_NAME"
done

"$PYTHON" - <<PY
import json
from pathlib import Path

payload = {
    "run_name": "$RUN_NAME",
    "gpu_device": "$GPU_DEVICE",
    "pretrained_model": "cyto3",
    "splits": "${SPLITS[*]}".split(),
}
out = Path("$EXP_ROOT/run_manifests/${RUN_NAME}.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY
