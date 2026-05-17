#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
REFINE_ROOT="${REFINE_ROOT:-$PROJECT/outputs/tissuenet_refine_combo_search_20260504}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
OUT_DIR="${OUT_DIR:-$FULL_ROOT/samcell_refine_final}"
SESSION_NAME="${SESSION_NAME:-full_samcell_refine_final}"
POLL_SECONDS="${POLL_SECONDS:-300}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
export CUDA_VISIBLE_DEVICES

LOG_DIR="$FULL_ROOT/logs"
LOG="$LOG_DIR/ensure_samcell_after_tn_refine.log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

cd "$PROJECT"
date
echo "waiting for $REFINE_ROOT/decision.json"
while [ ! -s "$REFINE_ROOT/decision.json" ]; do
  sleep "$POLL_SECONDS"
done

ACCEPTED="$("$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
decision = json.loads(Path("$REFINE_ROOT/decision.json").read_text(encoding="utf-8"))
print("true" if decision.get("accepted") else "false")
PY
)"

if [ "$ACCEPTED" != "true" ]; then
  echo "TissueNet refine decision rejected; not launching a second SAM-Cell full run."
  cat "$REFINE_ROOT/decision.json"
  date
  exit 0
fi

FINAL_CONFIG="$("$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
decision = json.loads(Path("$REFINE_ROOT/decision.json").read_text(encoding="utf-8"))
print(decision.get("copied_best_config") or decision.get("best_config") or "")
PY
)"

if [ ! -s "$FINAL_CONFIG" ]; then
  echo "accepted refine config missing: $FINAL_CONFIG"
  exit 1
fi
if [ ! -s "$FULL_MANIFEST" ]; then
  echo "full manifest missing: $FULL_MANIFEST"
  exit 1
fi

RUN_SCRIPT="$FULL_ROOT/run_full_samcell_tn_refine.sh"
cat > "$RUN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
export CUDA_VISIBLE_DEVICES="\${CUDA_VISIBLE_DEVICES:-1}"
LOG="$LOG_DIR/full_samcell_tn_refine.log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "\$LOG") 2>&1
date
PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_devset.py \\
  --config "$FINAL_CONFIG" \\
  --devset_csv "$FULL_MANIFEST" \\
  --out_dir "$OUT_DIR" \\
  --save_outputs \\
  --use_cache
date
EOF
chmod +x "$RUN_SCRIPT"

"$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
payload = {
    "refine_decision": "$REFINE_ROOT/decision.json",
    "search_accepted": "$ACCEPTED",
    "final_config": "$FINAL_CONFIG",
    "full_manifest": "$FULL_MANIFEST",
    "run_script": "$RUN_SCRIPT",
    "out_dir": "$OUT_DIR",
    "session": "$SESSION_NAME",
}
out = Path("$FULL_ROOT/run_manifest_samcell_tn_refine.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY

if [ -s "$OUT_DIR/summary.csv" ]; then
  echo "refine full output already has summary: $OUT_DIR/summary.csv"
  date
  exit 0
fi

while tmux has-session -t full_samcell_final 2>/dev/null; do
  echo "$(date '+%F %T %Z') full_samcell_final is still running; waiting before starting $SESSION_NAME to avoid GPU contention"
  sleep "$POLL_SECONDS"
done

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "$SESSION_NAME already exists; not starting duplicate"
else
  tmux new-session -d -s "$SESSION_NAME" "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES bash '$RUN_SCRIPT'"
  echo "started $SESSION_NAME"
fi
tmux ls | grep -E "$SESSION_NAME|full_samcell_final|full_cellsam_prestart" || true
date
