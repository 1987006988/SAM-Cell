#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/backup/taotao_work/sam_cell}"
EXP_ROOT="${EXP_ROOT:-$ROOT/experiments/cellcosmos_full_16777_20260503}"
CONFIG="${CONFIG:-$ROOT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
FULL_MANIFEST="${FULL_MANIFEST:-$EXP_ROOT/manifests/full.csv}"
OUT_DIR="${OUT_DIR:-$EXP_ROOT/samcell_refine_final}"
LOG="${LOG:-$EXP_ROOT/logs/start_samcell_refine_midtail_when_safe_20260506.log}"
SESSION="${SESSION:-full_samcell_refine_midtail_13500_14500}"
MANIFEST="${MANIFEST:-$EXP_ROOT/manifests/full_midtail_13500_14500_for_${SESSION}.csv}"
GPU="${GPU:-1}"
START_INDEX="${START_INDEX:-13500}"
END_INDEX="${END_INDEX:-14500}"
LOAD_THRESHOLD="${LOAD_THRESHOLD:-160}"
POLL_SECONDS="${POLL_SECONDS:-300}"

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

load1_int() {
  awk '{printf "%d", $1}' /proc/loadavg
}

if [[ -s "$OUT_DIR/summary.csv" ]]; then
  log "Final summary already exists; not starting $SESSION."
  exit 0
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  log "$SESSION already exists; not starting duplicate."
  exit 0
fi

if [[ ! -s "$MANIFEST" ]]; then
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
  log "Wrote midtail manifest $MANIFEST rows=$((END_INDEX - START_INDEX))."
fi

while true; do
  if [[ -s "$OUT_DIR/summary.csv" ]]; then
    log "Final summary exists; not starting $SESSION."
    exit 0
  fi
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    log "$SESSION already exists; exiting watcher."
    exit 0
  fi
  current_load="$(load1_int)"
  current_labels="$(label_count)"
  if (( current_load <= LOAD_THRESHOLD )); then
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
    log "Started $SESSION on GPU=$GPU at load1=$current_load labels=$current_labels/16777 manifest=$MANIFEST."
    exit 0
  fi
  log "Waiting; load1=$current_load > threshold=$LOAD_THRESHOLD labels=$current_labels/16777."
  sleep "$POLL_SECONDS"
done
