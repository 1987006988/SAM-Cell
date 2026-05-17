#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
OUT_DIR="${OUT_DIR:-$FULL_ROOT/samcell_refine_final}"
CONFIG="${CONFIG:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
SESSION_NAME="${SESSION_NAME:-full_samcell_refine_late_tail_14500_end}"
START_INDEX="${START_INDEX:-14500}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
LOG_DIR="$FULL_ROOT/logs"
LOG="$LOG_DIR/start_samcell_refine_late_tail_helper_20260506.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

session_alive() {
  tmux has-session -t "$1" 2>/dev/null
}

count_labels() {
  if [ ! -d "$OUT_DIR/labels" ]; then
    echo 0
    return
  fi
  find "$OUT_DIR/labels" -maxdepth 1 -type f -name "*.tif" 2>/dev/null | wc -l | tr -d " "
}

cd "$PROJECT"
date
echo "starting late-tail SAM-Cell refine helper if needed"
echo "out_dir: $OUT_DIR"
echo "start_index: $START_INDEX"
echo "gpu: $CUDA_VISIBLE_DEVICES"

if [ -s "$OUT_DIR/summary.csv" ]; then
  echo "summary already exists; no helper needed"
  exit 0
fi

labels="$(count_labels)"
echo "current labels: $labels/16777"
if [ "$labels" -ge 16777 ]; then
  echo "labels already complete; no helper needed"
  exit 0
fi

if session_alive "$SESSION_NAME"; then
  echo "$SESSION_NAME already alive; not starting duplicate"
  exit 0
fi

if [ ! -s "$CONFIG" ]; then
  echo "missing config: $CONFIG" >&2
  exit 1
fi
if [ ! -s "$FULL_MANIFEST" ]; then
  echo "missing manifest: $FULL_MANIFEST" >&2
  exit 1
fi

HELPER_MANIFEST="$FULL_ROOT/manifests/full_tail_from_${START_INDEX}_for_${SESSION_NAME}.csv"
"$NNUNET_PYTHON" - "$FULL_MANIFEST" "$HELPER_MANIFEST" "$START_INDEX" <<'PY'
import csv
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
start = int(sys.argv[3])

with src.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit(f"empty manifest: {src}")
if start < 0 or start >= len(rows):
    raise SystemExit(f"invalid start {start} for {len(rows)} rows")

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows[start:])

print(f"{dst} rows={len(rows) - start} start={start} total={len(rows)}")
PY

RUN_SCRIPT="$FULL_ROOT/run_${SESSION_NAME}.sh"
RUN_LOG="$LOG_DIR/${SESSION_NAME}.log"
cat > "$RUN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
export CUDA_VISIBLE_DEVICES="\${CUDA_VISIBLE_DEVICES:-$CUDA_VISIBLE_DEVICES}"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$RUN_LOG") 2>&1
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
tmux ls | grep -E "$SESSION_NAME|full_samcell_refine" || true
date
