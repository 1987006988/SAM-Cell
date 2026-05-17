#!/usr/bin/env bash
set -euo pipefail

DATASET_ID="${DATASET_ID:-620}"
CONFIGURATION="${CONFIGURATION:-2d}"
FOLDS="${FOLDS:-0 1 2 3 4}"
NPFP="${NPFP:-8}"
NP="${NP:-8}"
TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---npz}"
WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
ENV_FILE="${ENV_FILE:-$WORK_ROOT/env_nnunet.sh}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

: "${nnUNet_raw:?Set nnUNet_raw before running this script}"
: "${nnUNet_preprocessed:?Set nnUNet_preprocessed before running this script}"
: "${nnUNet_results:?Set nnUNet_results before running this script}"

nnUNetv2_plan_and_preprocess \
  -d "$DATASET_ID" \
  -c "$CONFIGURATION" \
  --verify_dataset_integrity \
  -npfp "$NPFP" \
  -np "$NP"

for fold in $FOLDS; do
  nnUNetv2_train "$DATASET_ID" "$CONFIGURATION" "$fold" $TRAIN_EXTRA_ARGS
done
