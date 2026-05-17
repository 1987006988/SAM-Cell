#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
PROJECT_ROOT="${PROJECT_ROOT:-$WORK_ROOT/sam_cell}"
ENV_FILE="${ENV_FILE:-$WORK_ROOT/env_nnunet.sh}"
PYTHON_ENV="${PYTHON_ENV:-$WORK_ROOT/venvs/nnunet}"
PYTHON="${PYTHON:-$PYTHON_ENV/bin/python}"

DATA_ROOT="${DATA_ROOT:-/backup/taotao_data/CellCosmos_Benchmark}"
CONFIG="${CONFIG:-$PROJECT_ROOT/configs/sam_cell_multi_expert_cellpose_gate_dataset622_workstation2.yaml}"
TRAIN_CSV="${TRAIN_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_selector20/dev_tune.csv}"
VAL_CSV="${VAL_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_selector20/dev_holdout.csv}"
SERVER_TRAIN_CSV="${SERVER_TRAIN_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_selector20/dev_tune_cellpose_server_paths.csv}"
SERVER_VAL_CSV="${SERVER_VAL_CSV:-$PROJECT_ROOT/outputs/benchmark_splits_selector20/dev_holdout_cellpose_server_paths.csv}"
OUT_DIR="${OUT_DIR:-$PROJECT_ROOT/outputs/proposal_ranker_cellpose_gate_dataset622_cellposeonly}"
SOURCE_FILTER="${SOURCE_FILTER:-cellpose}"
THRESHOLD="${THRESHOLD:-0.5}"
FEATURE_VERSION="${FEATURE_VERSION:-1}"
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
mkdir -p "$(dirname "$SERVER_TRAIN_CSV")" "$(dirname "$SERVER_VAL_CSV")" "$OUT_DIR"

rewrite_csv() {
  local src="$1"
  local dst="$2"
  "$PYTHON" - "$src" "$dst" "$DATA_ROOT" "$SOURCE_FILTER" <<'PY'
import csv
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
data_root = sys.argv[3].rstrip("/")
source_filter = sys.argv[4]
old_prefixes = [
    "/mnt/d/cell data/CellCosmos_Benchmark",
    "D:/cell data/CellCosmos_Benchmark",
    "D:\\cell data\\CellCosmos_Benchmark",
]

with src.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys()) if rows else ["source", "image_path", "mask_path"]
out = []
for row in rows:
    source = row.get("source") or Path(row.get("image_path", "")).stem.split("_", 1)[0]
    if source_filter and source != source_filter:
        continue
    for key in ("image_path", "mask_path"):
        value = row.get(key, "")
        normalized = value.replace("\\", "/")
        for old in old_prefixes:
            old_norm = old.replace("\\", "/").rstrip("/")
            if normalized.startswith(old_norm):
                normalized = data_root + normalized[len(old_norm):]
                break
        row[key] = normalized
    out.append(row)

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(out)
print(f"wrote {dst} rows={len(out)} source_filter={source_filter or 'none'}")
PY
}

rewrite_csv "$TRAIN_CSV" "$SERVER_TRAIN_CSV"
rewrite_csv "$VAL_CSV" "$SERVER_VAL_CSV"

echo "project_root=$PROJECT_ROOT"
echo "config=$CONFIG"
echo "train=$SERVER_TRAIN_CSV"
echo "val=$SERVER_VAL_CSV"
echo "out_dir=$OUT_DIR"
echo "source_filter=${SOURCE_FILTER:-none} threshold=$THRESHOLD feature_version=$FEATURE_VERSION"
date

export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export CUDA_VISIBLE_DEVICES
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore::FutureWarning}"
"$PYTHON" scripts/train_proposal_ranker.py \
  --config "$CONFIG" \
  --train_csv "$SERVER_TRAIN_CSV" \
  --val_csv "$SERVER_VAL_CSV" \
  --out_dir "$OUT_DIR" \
  --threshold "$THRESHOLD" \
  --feature_version "$FEATURE_VERSION"
date
