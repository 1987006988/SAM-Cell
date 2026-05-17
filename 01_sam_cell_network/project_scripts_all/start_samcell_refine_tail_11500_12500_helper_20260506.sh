#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-$ROOT/experiments/cellcosmos_full_16777_20260503}"
CONFIG="${CONFIG:-$ROOT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
FULL_MANIFEST="${FULL_MANIFEST:-$EXP_ROOT/manifests/full.csv}"
OUT_DIR="${OUT_DIR:-$EXP_ROOT/samcell_refine_final}"
SESSION="${SESSION:-full_samcell_refine_tail_11500_12500}"
MANIFEST="${MANIFEST:-$EXP_ROOT/manifests/full_tail_11500_12500_for_${SESSION}.csv}"
GPU="${GPU:-0}"
START_INDEX="${START_INDEX:-11500}"
END_INDEX="${END_INDEX:-12500}"
LOG="${LOG:-$EXP_ROOT/logs/start_samcell_refine_tail_11500_12500_helper_20260506.log}"

mkdir -p "$(dirname "$LOG")" "$(dirname "$MANIFEST")"

now() {
  date "+%F %T %Z"
}

log() {
  echo "$(now) $*" | tee -a "$LOG"
}

label_count() {
  find "$OUT_DIR/labels" -maxdepth 1 -type f -name '*.tif' 2>/dev/null | wc -l
}

if [[ -s "$OUT_DIR/summary.csv" ]]; then
  log "Final summary already exists; not starting $SESSION."
  exit 0
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  log "$SESSION already exists; not starting duplicate."
  exit 0
fi

"$ROOT"/../venvs/nnunet/bin/python - "$FULL_MANIFEST" "$MANIFEST" "$START_INDEX" "$END_INDEX" <<'PY'
import csv
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
start = int(sys.argv[3])
end = int(sys.argv[4])

with src.open(newline="") as f:
    rows = list(csv.DictReader(f))
    fieldnames = rows[0].keys()

part = rows[start:end]
dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(part)
PY

RUN_SCRIPT="$EXP_ROOT/run_${SESSION}.sh"
cat > "$RUN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
export CUDA_VISIBLE_DEVICES="$GPU"
PYTHONWARNINGS=ignore::FutureWarning nice -n 10 "$ROOT/../venvs/nnunet/bin/python" scripts/eval_devset.py \\
  --config "$CONFIG" \\
  --devset_csv "$MANIFEST" \\
  --out_dir "$OUT_DIR" \\
  --save_outputs \\
  --use_cache \\
  --no_summary
EOF
chmod +x "$RUN_SCRIPT"

tmux new-session -d -s "$SESSION" "bash '$RUN_SCRIPT'"
log "Started $SESSION on GPU=$GPU labels=$(label_count)/16777 manifest=$MANIFEST run_script=$RUN_SCRIPT."
