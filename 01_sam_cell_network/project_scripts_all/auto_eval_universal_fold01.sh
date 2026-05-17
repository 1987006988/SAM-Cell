#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${REMOTE:-taotao@10.181.10.20}"
SSH_OPTS="${SSH_OPTS:--T -o BatchMode=yes -o GSSAPIAuthentication=no -o ConnectTimeout=5}"
POLL_SECONDS="${POLL_SECONDS:-600}"
REMOTE_MODEL_DIR="${REMOTE_MODEL_DIR:-/backup/taotao_work/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d}"
LOCAL_MODEL_DIR="${LOCAL_MODEL_DIR:-/home/taotao/nnUNet/nnUNetFrame/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d}"
DEVSET_CSV="${DEVSET_CSV:-outputs/benchmark_splits_large/eval_25_balanced.csv}"
CELLPOSE_DIR="${CELLPOSE_DIR:-outputs/benchmark_splits_large/cellpose_cyto}"
OUT_ROOT="${OUT_ROOT:-outputs/auto_eval_universal_fold01}"
LOG_FILE="$ROOT/$OUT_ROOT/auto_eval.log"
LOCK_FILE="$ROOT/$OUT_ROOT/auto_eval.lock"

mkdir -p "$ROOT/$OUT_ROOT"
exec > >(tee -a "$LOG_FILE") 2>&1

if [[ -e "$LOCK_FILE" ]]; then
  old_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "another auto-eval is already running: pid=$old_pid"
    exit 0
  fi
fi
echo "$$" > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

cd "$ROOT"

echo "started_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "remote=$REMOTE"
echo "poll_seconds=$POLL_SECONDS"
echo "remote_model_dir=$REMOTE_MODEL_DIR"
echo "local_model_dir=$LOCAL_MODEL_DIR"

ensure_eval_csv() {
  if [[ -f "$DEVSET_CSV" ]]; then
    return
  fi
  python - <<'PY'
import csv
from collections import defaultdict
from pathlib import Path

src = Path("outputs/benchmark_splits_large/eval_250.csv")
out = Path("outputs/benchmark_splits_large/eval_25_balanced.csv")
rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
seen = defaultdict(int)
picked = []
for row in rows:
    source = row.get("source") or Path(row["image_path"]).name.split("_", 1)[0]
    if seen[source] < 5:
        picked.append(row)
        seen[source] += 1
    if len(seen) >= 5 and all(v >= 5 for v in seen.values()):
        break
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(picked)
print(f"wrote {len(picked)} rows to {out}")
PY
}

remote_ready() {
  timeout 120 ssh $SSH_OPTS "$REMOTE" "
    test -s '$REMOTE_MODEL_DIR/fold_0/checkpoint_final.pth' &&
    test -s '$REMOTE_MODEL_DIR/fold_1/checkpoint_final.pth' &&
    grep -q 'Training done' '$REMOTE_MODEL_DIR/fold_0'/training_log_*.txt &&
    grep -q 'Training done' '$REMOTE_MODEL_DIR/fold_1'/training_log_*.txt
  " >/dev/null 2>&1
}

print_remote_status() {
  timeout 120 ssh $SSH_OPTS "$REMOTE" "
    date
    for f in 0 1; do
      echo fold\$f
      log=\$(ls -t '$REMOTE_MODEL_DIR'/fold_\${f}/training_log_*.txt 2>/dev/null | head -1 || true)
      if [ -n \"\$log\" ]; then
        grep -E 'Epoch |Pseudo dice|Training done' \"\$log\" | tail -n 6
      else
        echo no_log
      fi
      find '$REMOTE_MODEL_DIR'/fold_\${f} -maxdepth 1 -type f \( -name 'checkpoint_best.pth' -o -name 'checkpoint_final.pth' -o -name 'checkpoint_latest.pth' \) -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort
    done
  " || true
}

echo "waiting_for_fold01_final=1"
while ! remote_ready; do
  print_remote_status
  echo "not_ready_sleeping_${POLL_SECONDS}s"
  sleep "$POLL_SECONDS"
done
echo "fold01_final_detected_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
print_remote_status

echo "syncing fold0/fold1 checkpoints"
mkdir -p "$LOCAL_MODEL_DIR"
rsync -av -e "ssh $SSH_OPTS" \
  --include='/dataset.json' \
  --include='/dataset_fingerprint.json' \
  --include='/plans.json' \
  --include='/fold_0/' \
  --include='/fold_0/checkpoint_best.pth' \
  --include='/fold_0/checkpoint_final.pth' \
  --include='/fold_0/training_log_*.txt' \
  --include='/fold_0/debug.json' \
  --include='/fold_1/' \
  --include='/fold_1/checkpoint_best.pth' \
  --include='/fold_1/checkpoint_final.pth' \
  --include='/fold_1/training_log_*.txt' \
  --include='/fold_1/debug.json' \
  --exclude='*' \
  "$REMOTE:$REMOTE_MODEL_DIR/" \
  "$LOCAL_MODEL_DIR/"

ensure_eval_csv

BEST_OUT="$OUT_ROOT/sam_universal_fold01_best_eval25"
FINAL_OUT="$OUT_ROOT/sam_universal_fold01_final_eval25"
BEST_COMPARE="$OUT_ROOT/compare_universal_fold01_best_eval25"
FINAL_COMPARE="$OUT_ROOT/compare_universal_fold01_final_eval25"
REPORT="$OUT_ROOT/report.md"
REPORT_JSON="$OUT_ROOT/report.json"

echo "running best checkpoint eval"
rm -rf "$BEST_OUT" "$BEST_COMPARE"
PYTHONPATH="$ROOT" conda run -n SAM-Cell python scripts/eval_devset.py \
  --config configs/sam_cell_universal_boundary_fold01_best.yaml \
  --devset_csv "$DEVSET_CSV" \
  --out_dir "$BEST_OUT" \
  --save_outputs
PYTHONPATH="$ROOT" conda run -n SAM-Cell python scripts/compare_methods.py \
  --devset_csv "$DEVSET_CSV" \
  --sam_labels_dir "$BEST_OUT/labels" \
  --cellpose_dir "$CELLPOSE_DIR" \
  --out_dir "$BEST_COMPARE"

echo "running final checkpoint eval"
rm -rf "$FINAL_OUT" "$FINAL_COMPARE"
PYTHONPATH="$ROOT" conda run -n SAM-Cell python scripts/eval_devset.py \
  --config configs/sam_cell_universal_boundary_fold01_final.yaml \
  --devset_csv "$DEVSET_CSV" \
  --out_dir "$FINAL_OUT" \
  --save_outputs
PYTHONPATH="$ROOT" conda run -n SAM-Cell python scripts/compare_methods.py \
  --devset_csv "$DEVSET_CSV" \
  --sam_labels_dir "$FINAL_OUT/labels" \
  --cellpose_dir "$CELLPOSE_DIR" \
  --out_dir "$FINAL_COMPARE"

echo "writing report"
PYTHONPATH="$ROOT" conda run -n SAM-Cell python scripts/summarize_universal_fold01_eval.py \
  --primary_summary "$BEST_COMPARE/summary_by_source.csv" \
  --final_summary "$FINAL_COMPARE/summary_by_source.csv" \
  --out_md "$REPORT" \
  --out_json "$REPORT_JSON"

echo "finished_at=$(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "report=$ROOT/$REPORT"
