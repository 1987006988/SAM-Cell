#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504}"
LOG_DIR="$EXP_ROOT/logs"

mkdir -p "$LOG_DIR"
cd "$PROJECT"

export SAM_CELL_ROOT="${SAM_CELL_ROOT:-$PROJECT}"
export NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
export CELLCOSMOS_DATA_ROOT="${CELLCOSMOS_DATA_ROOT:-/backup/taotao_data/CellCosmos_Benchmark}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore::FutureWarning}"

{
  date
  echo "PROJECT=$PROJECT"
  echo "EXP_ROOT=$EXP_ROOT"
  echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
  "$NNUNET_PYTHON" scripts/tissuenet_refine_combo_search_20260504.py \
    --top_proposal "${TOP_PROPOSAL:-10}" \
    --top_holdout "${TOP_HOLDOUT:-4}" \
    --top_eval250 "${TOP_EVAL250:-3}"
  date
} 2>&1 | tee -a "$LOG_DIR/tissuenet_refine_combo_search_20260504.log"
