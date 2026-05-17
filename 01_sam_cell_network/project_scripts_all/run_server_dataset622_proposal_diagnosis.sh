#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
PROJECT_ROOT="${PROJECT_ROOT:-$WORK_ROOT/sam_cell}"
ENV_FILE="${ENV_FILE:-$WORK_ROOT/env_nnunet.sh}"
PYTHON_ENV="${PYTHON_ENV:-$WORK_ROOT/venvs/nnunet}"
PYTHON="${PYTHON:-$PYTHON_ENV/bin/python}"

DATA_ROOT="${DATA_ROOT:-/backup/taotao_data/CellCosmos_Benchmark}"
CONFIG="${CONFIG:-$PROJECT_ROOT/configs/sam_cell_multi_expert_cellpose_gate_dataset622_workstation2.yaml}"
DEVSET_CSV="${DEVSET_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_large/eval_250.csv}"
SERVER_DEVSET_CSV="${SERVER_DEVSET_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_large/eval_250_server_paths.csv}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/samcell_optimization_20260501/proposal_oracle_dataset622_cellpose50_unranked}"
SOURCE="${SOURCE:-cellpose}"
WORST_K="${WORST_K:-50}"
LIMIT="${LIMIT:-}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python)"
fi

cd "$PROJECT_ROOT"
mkdir -p "$(dirname "$SERVER_DEVSET_CSV")" "$OUT_DIR"

"$PYTHON" - "$DEVSET_CSV" "$SERVER_DEVSET_CSV" "$DATA_ROOT" <<'PY'
import csv
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
data_root = sys.argv[3].rstrip("/")
old_prefixes = [
    "/mnt/d/cell data/CellCosmos_Benchmark",
    "D:/cell data/CellCosmos_Benchmark",
    "D:\\cell data\\CellCosmos_Benchmark",
]

with src.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys()) if rows else ["source", "image_path", "mask_path"]
for row in rows:
    for key in ("image_path", "mask_path"):
        value = row.get(key, "")
        normalized = value.replace("\\", "/")
        for old in old_prefixes:
            old_norm = old.replace("\\", "/").rstrip("/")
            if normalized.startswith(old_norm):
                normalized = data_root + normalized[len(old_norm):]
                break
        row[key] = normalized

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {dst} rows={len(rows)}")
PY

args=(
  scripts/proposal_oracle_diagnosis.py
  --config "$CONFIG"
  --devset_csv "$SERVER_DEVSET_CSV"
  --out_dir "$OUT_DIR"
  --source "$SOURCE"
  --worst_k "$WORST_K"
  --include_source_breakdown
)
if [[ -n "$LIMIT" ]]; then
  args+=(--limit "$LIMIT")
fi

echo "project_root=$PROJECT_ROOT"
echo "config=$CONFIG"
echo "devset=$SERVER_DEVSET_CSV"
echo "out_dir=$OUT_DIR"
echo "source=$SOURCE worst_k=$WORST_K limit=${LIMIT:-none}"
date

export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export CUDA_VISIBLE_DEVICES
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore::FutureWarning}"
"$PYTHON" "${args[@]}"
date
