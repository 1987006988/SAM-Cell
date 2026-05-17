#!/usr/bin/env bash
set -euo pipefail

RUN_KIND="${RUN_KIND:?Set RUN_KIND to iid or pannuke}"
GPU_DEVICE="${GPU_DEVICE:-0}"
ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501}"
CELLPOSE_ENV="${CELLPOSE_ENV:-/backup/taotao_work/venvs/cellpose311}"
PYTHON="$CELLPOSE_ENV/bin/python"
SAVE_EVERY="${SAVE_EVERY:-25}"
N_EPOCHS="${N_EPOCHS:-500}"
BATCH_SIZE="${BATCH_SIZE:-8}"

cd "$ROOT"
mkdir -p "$EXP_ROOT/logs" "$EXP_ROOT/configs" "$EXP_ROOT/checkpoints" "$EXP_ROOT/predictions" "$EXP_ROOT/metrics" "$EXP_ROOT/overlays" "$EXP_ROOT/run_manifests"

if [ "$RUN_KIND" = "iid" ]; then
  TRAIN_SPLIT="iid_train"
  TRAIN_TEST_SPLIT="iid_val"
  TEST_SPLITS=("iid_val")
  RUN_NAME="cellpose_iid_finetune_cyto3"
elif [ "$RUN_KIND" = "pannuke" ]; then
  TRAIN_SPLIT="pannuke_train"
  TRAIN_TEST_SPLIT="pannuke_core_test"
  TEST_SPLITS=("pannuke_core_test" "far_ood_test")
  RUN_NAME="cellpose_pannuke_finetune_cyto3"
else
  echo "Unsupported RUN_KIND=$RUN_KIND" >&2
  exit 2
fi

TRAIN_DIR="$EXP_ROOT/data/cellpose/$TRAIN_SPLIT"
TRAIN_TEST_DIR="$EXP_ROOT/data/cellpose/$TRAIN_TEST_SPLIT"
MODEL_NAME="$RUN_NAME"
MODEL_PATH="$TRAIN_DIR/models/$MODEL_NAME"
TRAIN_LOG="$EXP_ROOT/logs/${RUN_NAME}_train.log"

if [ ! -x "$PYTHON" ]; then
  bash scripts/setup_server_cellpose_env.sh
fi

if [ ! -f "$EXP_ROOT/manifests/split_summary.json" ]; then
  "$PYTHON" scripts/cellcosmos_repro_prepare.py \
    --index_csv "$EXP_ROOT/manifests/core3500_index.csv" \
    --image_root /backup/taotao_data/CellCosmos_Benchmark/images \
    --mask_root /backup/taotao_data/CellCosmos_Benchmark/masks \
    --out_root "$EXP_ROOT"
fi

if [ ! -f "$MODEL_PATH" ]; then
  echo "training $RUN_NAME on GPU $GPU_DEVICE"
  "$PYTHON" -m cellpose \
    --train \
    --dir "$TRAIN_DIR" \
    --test_dir "$TRAIN_TEST_DIR" \
    --pretrained_model cyto3 \
    --chan 0 \
    --chan2 0 \
    --diameter 0 \
    --use_gpu \
    --gpu_device "$GPU_DEVICE" \
    --n_epochs "$N_EPOCHS" \
    --batch_size "$BATCH_SIZE" \
    --save_every "$SAVE_EVERY" \
    --model_name_out "$MODEL_NAME" \
    --verbose 2>&1 | tee "$TRAIN_LOG"
else
  echo "using existing model $MODEL_PATH"
fi

mkdir -p "$EXP_ROOT/checkpoints/$RUN_NAME"
if [ -d "$TRAIN_DIR/models" ]; then
  cp -av "$TRAIN_DIR/models/." "$EXP_ROOT/checkpoints/$RUN_NAME/" || true
fi

for SPLIT in "${TEST_SPLITS[@]}"; do
  MANIFEST="$EXP_ROOT/manifests/$SPLIT.csv"
  PRED_DIR="$EXP_ROOT/predictions/$RUN_NAME/$SPLIT"
  METRIC_DIR="$EXP_ROOT/metrics/$RUN_NAME/$SPLIT"
  OVERLAY_DIR="$EXP_ROOT/overlays/$RUN_NAME/$SPLIT"
  "$PYTHON" scripts/run_cellpose_manifest.py \
    --manifest_csv "$MANIFEST" \
    --out_dir "$PRED_DIR" \
    --pretrained_model "$MODEL_PATH" \
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

TEST_SPLITS_STR="${TEST_SPLITS[*]}"
"$PYTHON" - <<PY
import json
from pathlib import Path

payload = {
    "run_name": "$RUN_NAME",
    "run_kind": "$RUN_KIND",
    "gpu_device": "$GPU_DEVICE",
    "train_split": "$TRAIN_SPLIT",
    "test_splits": "$TEST_SPLITS_STR".split(),
    "model_path": "$MODEL_PATH",
    "train_log": "$TRAIN_LOG",
    "n_epochs": "$N_EPOCHS",
    "save_every": "$SAVE_EVERY",
    "batch_size": "$BATCH_SIZE",
}
out = Path("$EXP_ROOT/run_manifests/${RUN_NAME}.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY
