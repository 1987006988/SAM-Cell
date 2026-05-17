#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
OUT_DIR="${OUT_DIR:-$FULL_ROOT/samcell_refine_final}"
CONFIG="${CONFIG:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml}"
WATCH_SESSION="${WATCH_SESSION:-samcell_refine_cached_summary_watcher_20260506}"
EVAL_SESSION="${EVAL_SESSION:-full_samcell_refine_cached_summary_eval}"
POLL_SECONDS="${POLL_SECONDS:-300}"
STABLE_SECONDS="${STABLE_SECONDS:-600}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
LOG_DIR="$FULL_ROOT/logs"
LOG="$LOG_DIR/start_samcell_refine_cached_summary_watcher_20260506.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

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

cd "$PROJECT"
date
echo "watching for complete cached SAM-Cell refine labels"
echo "out_dir: $OUT_DIR"
echo "poll_seconds: $POLL_SECONDS stable_seconds: $STABLE_SECONDS"

if [ ! -s "$CONFIG" ]; then
  echo "missing config: $CONFIG" >&2
  exit 1
fi
if [ ! -s "$FULL_MANIFEST" ]; then
  echo "missing full manifest: $FULL_MANIFEST" >&2
  exit 1
fi

while true; do
  if [ -s "$OUT_DIR/summary.csv" ]; then
    echo "$(date '+%F %T %Z') summary already exists: $OUT_DIR/summary.csv"
    exit 0
  fi

  labels="$(count_labels)"
  echo "$(date '+%F %T %Z') labels=$labels/16777"
  if [ "$labels" -lt 16777 ]; then
    sleep "$POLL_SECONDS"
    continue
  fi

  echo "$(date '+%F %T %Z') labels complete once; waiting for stability"
  sleep "$STABLE_SECONDS"
  if [ -s "$OUT_DIR/summary.csv" ]; then
    echo "$(date '+%F %T %Z') summary appeared during stability wait"
    exit 0
  fi
  labels_after="$(count_labels)"
  echo "$(date '+%F %T %Z') labels_after_stability=$labels_after/16777"
  if [ "$labels_after" -lt 16777 ]; then
    continue
  fi

  if session_alive "$EVAL_SESSION"; then
    echo "$(date '+%F %T %Z') $EVAL_SESSION already alive; exiting watcher"
    exit 0
  fi

  RUN_SCRIPT="$FULL_ROOT/run_samcell_refine_cached_summary_eval.sh"
  cat > "$RUN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
export CUDA_VISIBLE_DEVICES="\${CUDA_VISIBLE_DEVICES:-$CUDA_VISIBLE_DEVICES}"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_DIR/full_samcell_refine_cached_summary_eval.log") 2>&1
date
PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_devset.py \\
  --config "$CONFIG" \\
  --devset_csv "$FULL_MANIFEST" \\
  --out_dir "$OUT_DIR" \\
  --use_cache
date
EOF
  chmod +x "$RUN_SCRIPT"

  tmux new-session -d -s "$EVAL_SESSION" "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES bash '$RUN_SCRIPT'"
  echo "$(date '+%F %T %Z') started $EVAL_SESSION on GPU$CUDA_VISIBLE_DEVICES"
  tmux ls | grep -E "$EVAL_SESSION|$WATCH_SESSION" || true
  exit 0
done
