#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
OUT_DIR="${OUT_DIR:-$FULL_ROOT/samcell_refine_final}"
CONFIG="${CONFIG:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
LOG_DIR="$FULL_ROOT/logs"
LAUNCH_LOG="$LOG_DIR/start_samcell_refine_gap_helpers_20260506.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LAUNCH_LOG") 2>&1

count_labels() {
  if [ ! -d "$OUT_DIR/labels" ]; then
    echo 0
    return
  fi
  find "$OUT_DIR/labels" -maxdepth 1 -type f -name "*.tif" 2>/dev/null | wc -l | tr -d " "
}

session_alive() {
  tmux has-session -t "$1" 2>/dev/null
}

build_manifest() {
  local start="$1"
  local end="$2"
  local dst="$3"
  "$NNUNET_PYTHON" - "$FULL_MANIFEST" "$dst" "$start" "$end" <<'PY'
import csv
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
start = int(sys.argv[3])
end = int(sys.argv[4])

with src.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit(f"empty manifest: {src}")
if start < 0 or end <= start or end > len(rows):
    raise SystemExit(f"invalid slice {start}:{end} for {len(rows)} rows")

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows[start:end])

print(f"{dst} rows={end - start} start={start} end={end} total={len(rows)}")
PY
}

start_helper() {
  local session="$1"
  local gpu="$2"
  local start="$3"
  local end="$4"
  local manifest="$FULL_ROOT/manifests/full_gap_${start}_${end}_for_${session}.csv"
  local run_script="$FULL_ROOT/run_${session}.sh"
  local run_log="$LOG_DIR/${session}.log"

  if session_alive "$session"; then
    echo "$(date '+%F %T %Z') $session already alive; skip"
    return
  fi

  build_manifest "$start" "$end" "$manifest"

  cat > "$run_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
export CUDA_VISIBLE_DEVICES="\${CUDA_VISIBLE_DEVICES:-$gpu}"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$run_log") 2>&1
date
PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_devset.py \\
  --config "$CONFIG" \\
  --devset_csv "$manifest" \\
  --out_dir "$OUT_DIR" \\
  --save_outputs \\
  --use_cache \\
  --no_summary
date
EOF
  chmod +x "$run_script"

  tmux new-session -d -s "$session" "CUDA_VISIBLE_DEVICES=$gpu bash '$run_script'"
  echo "$(date '+%F %T %Z') started $session on GPU$gpu for rows $start:$end"
}

cd "$PROJECT"
date
echo "output: $OUT_DIR"

if [ -s "$OUT_DIR/summary.csv" ]; then
  echo "final SAM-Cell refine summary already exists; no gap helpers needed"
  exit 0
fi

label_count="$(count_labels)"
echo "current labels: $label_count/16777"
if [ "$label_count" -ge 16777 ]; then
  echo "labels already complete; no gap helpers needed"
  exit 0
fi

if [ ! -s "$CONFIG" ]; then
  echo "missing config: $CONFIG" >&2
  exit 1
fi
if [ ! -s "$FULL_MANIFEST" ]; then
  echo "missing full manifest: $FULL_MANIFEST" >&2
  exit 1
fi

# Current long-running refine coverage is main 0+, tail 8000+, and extra 12500+.
# These helpers cover the large middle gap without writing summary files.
start_helper full_samcell_refine_gap_2500_5000 0 2500 5000
start_helper full_samcell_refine_gap_5000_8000 1 5000 8000

tmux ls | grep -E "full_samcell_refine_(final|tail_helper|extra_after_cellsam|gap_2500_5000|gap_5000_8000)" || true
date
