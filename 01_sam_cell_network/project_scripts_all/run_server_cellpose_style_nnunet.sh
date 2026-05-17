#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
PROJECT_ROOT="${PROJECT_ROOT:-$WORK_ROOT/sam_cell}"
ENV_FILE="${ENV_FILE:-$WORK_ROOT/env_nnunet.sh}"
PYTHON_ENV="${PYTHON_ENV:-$WORK_ROOT/venvs/nnunet}"
PYTHON="${PYTHON:-$PYTHON_ENV/bin/python}"

DATASET_ID="${DATASET_ID:-622}"
DATASET_NAME="${DATASET_NAME:-SAMCellCellposeStyleBoundary}"
CONFIGURATION="${CONFIGURATION:-2d}"
FOLDS="${FOLDS:-0 1 2 3 4}"
NPFP="${NPFP:-8}"
NP="${NP:-8}"
TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---npz}"
LOG_DIR="${LOG_DIR:-$WORK_ROOT/logs/cellpose_style_boundary_$(date +%Y%m%d_%H%M%S)}"
WAIT_FOR_TMUX="${WAIT_FOR_TMUX-baseline_stardist_iid baseline_sam2_automatic}"

IMAGE_ROOT="${IMAGE_ROOT:-/backup/taotao_data/CellCosmos_Benchmark/images}"
MASK_ROOT="${MASK_ROOT:-/backup/taotao_data/CellCosmos_Benchmark/masks}"
MANIFEST_CSV="${MANIFEST_CSV:-}"
EXCLUDE_CSV="${EXCLUDE_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_large/eval_250.csv}"
SOURCE_QUOTA="${SOURCE_QUOTA:-cellpose=100000}"
BOUNDARY_RADIUS="${BOUNDARY_RADIUS:-1}"
OVERWRITE_DATASET="${OVERWRITE_DATASET:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"
SKIP_PREPROCESS="${SKIP_PREPROCESS:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python)"
fi

mkdir -p "$LOG_DIR"
cd "$PROJECT_ROOT"

echo "work_root=$WORK_ROOT"
echo "project_root=$PROJECT_ROOT"
echo "log_dir=$LOG_DIR"
echo "nnUNet_raw=$nnUNet_raw"
echo "nnUNet_preprocessed=$nnUNet_preprocessed"
echo "nnUNet_results=$nnUNet_results"
echo "dataset=${DATASET_ID}_${DATASET_NAME} configuration=$CONFIGURATION folds=$FOLDS"
echo "source_quota=$SOURCE_QUOTA"
echo "wait_for_tmux=$WAIT_FOR_TMUX"
date

if [[ "$SKIP_BUILD" != "1" ]]; then
  build_args=(
    --nnunet_raw "$nnUNet_raw"
    --dataset_id "$DATASET_ID"
    --dataset_name "$DATASET_NAME"
    --boundary_radius "$BOUNDARY_RADIUS"
    --exclude_csv "$EXCLUDE_CSV"
    --source_quota $SOURCE_QUOTA
  )
  if [[ -n "$MANIFEST_CSV" ]]; then
    build_args+=(--manifest_csv "$MANIFEST_CSV")
  else
    build_args+=(--image_root "$IMAGE_ROOT" --mask_root "$MASK_ROOT")
  fi
  if [[ "$OVERWRITE_DATASET" == "1" ]]; then
    build_args+=(--overwrite)
  fi
  "$PYTHON" scripts/build_cellpose_style_boundary_nnunet.py "${build_args[@]}" 2>&1 | tee "$LOG_DIR/build_dataset.log"
fi

if [[ "$SKIP_PREPROCESS" != "1" ]]; then
  nnUNetv2_plan_and_preprocess \
    -d "$DATASET_ID" \
    -c "$CONFIGURATION" \
    --verify_dataset_integrity \
    -npfp "$NPFP" \
    -np "$NP" \
    2>&1 | tee "$LOG_DIR/preprocess.log"
fi

for session in $WAIT_FOR_TMUX; do
  while tmux has-session -t "$session" 2>/dev/null; do
    echo "$(date '+%F %T') waiting for tmux session $session"
    sleep 300
  done
done

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

case " $FOLDS " in
  *" 0 "*)
    run_fold 0 0 pid0
    ;;
esac
case " $FOLDS " in
  *" 1 "*)
    run_fold 1 1 pid1
    ;;
esac
if [[ -n "${pid0:-}" || -n "${pid1:-}" ]]; then
  wait_pair ${pid0:-} ${pid1:-}
fi

case " $FOLDS " in
  *" 2 "*)
    run_fold 0 2 pid2
    ;;
esac
case " $FOLDS " in
  *" 3 "*)
    run_fold 1 3 pid3
    ;;
esac
if [[ -n "${pid2:-}" || -n "${pid3:-}" ]]; then
  wait_pair ${pid2:-} ${pid3:-}
fi

case " $FOLDS " in
  *" 4 "*)
    run_fold 0 4 pid4
    wait_pair "$pid4"
    ;;
esac

echo "All requested folds finished"
date
