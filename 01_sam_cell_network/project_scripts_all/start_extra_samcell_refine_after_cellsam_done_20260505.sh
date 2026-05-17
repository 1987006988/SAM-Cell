#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
HELPER_MANIFEST="${HELPER_MANIFEST:-$FULL_ROOT/manifests/full_tail_from_12500_for_samcell_refine_extra_after_cellsam.csv}"
OUT_DIR="${OUT_DIR:-$FULL_ROOT/samcell_refine_final}"
SESSION_NAME="${SESSION_NAME:-full_samcell_refine_extra_after_cellsam}"
START_INDEX="${START_INDEX:-12500}"
POLL_SECONDS="${POLL_SECONDS:-300}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
CONFIG="${CONFIG:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
LOG_DIR="$FULL_ROOT/logs"
LOG="$LOG_DIR/start_extra_samcell_refine_after_cellsam_done.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

count_files() {
  local dir="$1"
  local pattern="$2"
  if [ ! -d "$dir" ]; then
    echo 0
    return
  fi
  find "$dir" -maxdepth 1 -type f -name "$pattern" 2>/dev/null | wc -l | tr -d ' '
}

session_alive() {
  tmux has-session -t "$1" 2>/dev/null
}

cd "$PROJECT"
date
echo "waiting for CellSAM sessions to finish before starting extra SAM-Cell refine helper"
echo "target session: $SESSION_NAME"
echo "target GPU: $CUDA_VISIBLE_DEVICES"

while session_alive full_cellsam_prestart || session_alive full_cellsam_tail_helper; do
  cellsam_labels="$(count_files "$FULL_ROOT/cellsam_generalist/predictions/labels" "*_cellsam.tif")"
  samcell_labels="$(count_files "$OUT_DIR/labels" "*.tif")"
  echo "$(date '+%F %T %Z') CellSAM still active; cellsam=$cellsam_labels/16777 samcell_refine=$samcell_labels/16777"
  sleep "$POLL_SECONDS"
done

if [ -s "$OUT_DIR/summary.csv" ]; then
  echo "final SAM-Cell refine metrics already complete: $OUT_DIR/summary.csv"
  date
  exit 0
fi

samcell_labels="$(count_files "$OUT_DIR/labels" "*.tif")"
if [ "$samcell_labels" -ge 16777 ]; then
  echo "final SAM-Cell refine labels already complete: $samcell_labels/16777; not starting helper"
  date
  exit 0
fi

if session_alive "$SESSION_NAME"; then
  echo "$SESSION_NAME already exists; not starting duplicate"
  date
  exit 0
fi

if [ ! -s "$CONFIG" ]; then
  echo "missing config: $CONFIG"
  exit 1
fi
if [ ! -s "$FULL_MANIFEST" ]; then
  echo "missing full manifest: $FULL_MANIFEST"
  exit 1
fi

"$NNUNET_PYTHON" - <<PY
import csv
from pathlib import Path

src = Path("$FULL_MANIFEST")
dst = Path("$HELPER_MANIFEST")
start = int("$START_INDEX")
with src.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit("empty manifest")
fieldnames = list(rows[0].keys())
tail = rows[start:]
dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(tail)
print(dst)
print("rows", len(tail), "start_index", start, "total", len(rows))
PY

RUN_SCRIPT="$FULL_ROOT/run_full_samcell_refine_extra_after_cellsam.sh"
cat > "$RUN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
export CUDA_VISIBLE_DEVICES="\${CUDA_VISIBLE_DEVICES:-$CUDA_VISIBLE_DEVICES}"
LOG="$LOG_DIR/full_samcell_refine_extra_after_cellsam.log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "\$LOG") 2>&1
date
PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_devset.py \\
  --config "$CONFIG" \\
  --devset_csv "$HELPER_MANIFEST" \\
  --out_dir "$OUT_DIR" \\
  --save_outputs \\
  --use_cache \\
  --no_summary
date
EOF
chmod +x "$RUN_SCRIPT"

tmux new-session -d -s "$SESSION_NAME" "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES bash '$RUN_SCRIPT'"
echo "started $SESSION_NAME on GPU$CUDA_VISIBLE_DEVICES"
tmux ls | grep -E "$SESSION_NAME|full_samcell_refine_final|full_samcell_refine_tail_helper|full_cellsam" || true
date
