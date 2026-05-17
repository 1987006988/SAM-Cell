#!/usr/bin/env bash
set -euo pipefail

RUN_KIND="${RUN_KIND:?Set RUN_KIND to iid or pannuke}"
GPU_DEVICE="${GPU_DEVICE:-0}"
ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501}"
STARDIST_ENV="${STARDIST_ENV:-/backup/taotao_work/venvs/stardist}"
PYTHON="$STARDIST_ENV/bin/python"
N_EPOCHS="${N_EPOCHS:-500}"
BATCH_SIZE="${BATCH_SIZE:-8}"
PATCH_SIZE="${PATCH_SIZE:-256}"

cd "$ROOT"
mkdir -p "$EXP_ROOT/logs" "$EXP_ROOT/configs" "$EXP_ROOT/checkpoints" "$EXP_ROOT/predictions" "$EXP_ROOT/metrics" "$EXP_ROOT/overlays" "$EXP_ROOT/run_manifests"

if [ "$RUN_KIND" = "iid" ]; then
  TRAIN_SPLIT="iid_train"
  VAL_SPLIT="iid_val"
  TEST_SPLITS=("iid_val")
  RUN_NAME="stardist_iid"
elif [ "$RUN_KIND" = "pannuke" ]; then
  TRAIN_SPLIT="pannuke_train"
  VAL_SPLIT="pannuke_core_test"
  TEST_SPLITS=("pannuke_core_test" "far_ood_test")
  RUN_NAME="stardist_pannuke"
else
  echo "Unsupported RUN_KIND=$RUN_KIND" >&2
  exit 2
fi

if [ ! -x "$PYTHON" ]; then
  bash scripts/setup_server_stardist_env.sh
fi

export CUDA_VISIBLE_DEVICES="$GPU_DEVICE"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
export TF_CPP_MIN_LOG_LEVEL="${TF_CPP_MIN_LOG_LEVEL:-1}"

MODEL_ROOT="$EXP_ROOT/checkpoints/stardist"
MODEL_DIR="$MODEL_ROOT/$RUN_NAME"
TRAIN_LOG="$EXP_ROOT/logs/${RUN_NAME}_train.log"

if [ ! -f "$MODEL_DIR/weights_best.h5" ]; then
  "$PYTHON" scripts/train_stardist_manifest.py \
    --train_csv "$EXP_ROOT/manifests/$TRAIN_SPLIT.csv" \
    --val_csv "$EXP_ROOT/manifests/$VAL_SPLIT.csv" \
    --model_dir "$MODEL_ROOT" \
    --model_name "$RUN_NAME" \
    --epochs "$N_EPOCHS" \
    --batch_size "$BATCH_SIZE" \
    --patch_size "$PATCH_SIZE" \
    2>&1 | tee "$TRAIN_LOG"
else
  echo "using existing StarDist model $MODEL_DIR"
fi

for SPLIT in "${TEST_SPLITS[@]}"; do
  MANIFEST="$EXP_ROOT/manifests/$SPLIT.csv"
  PRED_DIR="$EXP_ROOT/predictions/$RUN_NAME/$SPLIT"
  METRIC_DIR="$EXP_ROOT/metrics/$RUN_NAME/$SPLIT"
  OVERLAY_DIR="$EXP_ROOT/overlays/$RUN_NAME/$SPLIT"
  "$PYTHON" scripts/run_stardist_manifest.py \
    --manifest_csv "$MANIFEST" \
    --model_dir "$MODEL_ROOT" \
    --model_name "$RUN_NAME" \
    --out_dir "$PRED_DIR"
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

TEST_SPLITS_STR="${TEST_SPLITS[*]}"
"$PYTHON" - <<PY
import json
from pathlib import Path

payload = {
    "run_name": "$RUN_NAME",
    "run_kind": "$RUN_KIND",
    "gpu_device": "$GPU_DEVICE",
    "train_split": "$TRAIN_SPLIT",
    "val_split": "$VAL_SPLIT",
    "test_splits": "$TEST_SPLITS_STR".split(),
    "model_dir": "$MODEL_DIR",
    "train_log": "$TRAIN_LOG",
    "n_epochs": "$N_EPOCHS",
    "batch_size": "$BATCH_SIZE",
    "patch_size": "$PATCH_SIZE",
}
out = Path("$EXP_ROOT/run_manifests/${RUN_NAME}.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY
