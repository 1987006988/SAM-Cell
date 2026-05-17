#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
ENV_FILE="${ENV_FILE:-$WORK_ROOT/env_nnunet.sh}"
DATASET_ID="${DATASET_ID:-620}"
CONFIGURATION="${CONFIGURATION:-2d}"
NPFP="${NPFP:-8}"
NP="${NP:-8}"
SKIP_PREPROCESS="${SKIP_PREPROCESS:-0}"
TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---npz}"
LOG_DIR="${LOG_DIR:-$WORK_ROOT/logs/cellcosmos_boundary_$(date +%Y%m%d_%H%M%S)}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

mkdir -p "$LOG_DIR"

echo "work_root=$WORK_ROOT"
echo "log_dir=$LOG_DIR"
echo "nnUNet_raw=$nnUNet_raw"
echo "nnUNet_preprocessed=$nnUNet_preprocessed"
echo "nnUNet_results=$nnUNet_results"
echo "dataset=$DATASET_ID configuration=$CONFIGURATION"
echo "train_extra_args=$TRAIN_EXTRA_ARGS"
date

if [[ "$SKIP_PREPROCESS" != "1" ]]; then
  echo "Starting plan_and_preprocess"
  nnUNetv2_plan_and_preprocess \
    -d "$DATASET_ID" \
    -c "$CONFIGURATION" \
    --verify_dataset_integrity \
    -npfp "$NPFP" \
    -np "$NP" \
    2>&1 | tee "$LOG_DIR/preprocess.log"
  echo "Finished plan_and_preprocess"
fi

run_fold() {
  local gpu="$1"
  local fold="$2"
  local pid_var="$3"
  local log="$LOG_DIR/fold${fold}.log"
  echo "Starting fold $fold on GPU $gpu, log=$log" >&2
  CUDA_VISIBLE_DEVICES="$gpu" nnUNetv2_train "$DATASET_ID" "$CONFIGURATION" "$fold" $TRAIN_EXTRA_ARGS > "$log" 2>&1 &
  printf -v "$pid_var" "%s" "$!"
}

wait_pair() {
  local status=0
  local pid
  for pid in "$@"; do
    if ! wait "$pid"; then
      status=1
    fi
  done
  return "$status"
}

run_fold 0 0 pid0
run_fold 1 1 pid1
wait_pair "$pid0" "$pid1"

run_fold 0 2 pid2
run_fold 1 3 pid3
wait_pair "$pid2" "$pid3"

run_fold 0 4 pid4
wait_pair "$pid4"

echo "All folds finished"
date
