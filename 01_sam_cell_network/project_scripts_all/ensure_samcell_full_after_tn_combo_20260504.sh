#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
SEARCH_ROOT="${SEARCH_ROOT:-$PROJECT/outputs/tissuenet_local_combo_search_20260504}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
FULL_MANIFEST="${FULL_MANIFEST:-$FULL_ROOT/manifests/full.csv}"
FALLBACK_CONFIG="${FALLBACK_CONFIG:-$PROJECT/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml}"
POLL_SECONDS="${POLL_SECONDS:-300}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
export CUDA_VISIBLE_DEVICES

LOG_DIR="$FULL_ROOT/logs"
LOG="$LOG_DIR/ensure_samcell_after_tn_combo.log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

cd "$PROJECT"
date
echo "waiting for $SEARCH_ROOT/decision.json"
while [ ! -s "$SEARCH_ROOT/decision.json" ]; do
  sleep "$POLL_SECONDS"
done

ACCEPTED="$("$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
decision = json.loads(Path("$SEARCH_ROOT/decision.json").read_text(encoding="utf-8"))
print("true" if decision.get("accepted") else "false")
PY
)"

FINAL_CONFIG="$("$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
decision = json.loads(Path("$SEARCH_ROOT/decision.json").read_text(encoding="utf-8"))
if decision.get("accepted"):
    print(decision.get("copied_best_config") or decision.get("best_config") or "")
else:
    print(decision.get("baseline_config") or "$FALLBACK_CONFIG")
PY
)"
if [ "$ACCEPTED" = "true" ]; then
  echo "TissueNet combo search accepted a new config; launching SAM-Cell full inference with it."
else
  echo "TissueNet combo search did not accept a new config; launching SAM-Cell full inference with fallback current strongest config."
  cat "$SEARCH_ROOT/decision.json"
fi
if [ ! -s "$FINAL_CONFIG" ]; then
  echo "accepted config missing: $FINAL_CONFIG"
  exit 1
fi

if [ ! -s "$FULL_MANIFEST" ]; then
  echo "full manifest missing: $FULL_MANIFEST"
  exit 1
fi

RUN_SCRIPT="$FULL_ROOT/run_full_samcell_tn_combo.sh"
cat > "$RUN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
export CUDA_VISIBLE_DEVICES="\${CUDA_VISIBLE_DEVICES:-1}"
LOG="$LOG_DIR/full_samcell_tn_combo.log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "\$LOG") 2>&1
date
PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_devset.py \\
  --config "$FINAL_CONFIG" \\
  --devset_csv "$FULL_MANIFEST" \\
  --out_dir "$FULL_ROOT/samcell_final" \\
  --save_outputs \\
  --use_cache
date
EOF
chmod +x "$RUN_SCRIPT"

"$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
payload = {
    "search_decision": "$SEARCH_ROOT/decision.json",
    "search_accepted": "$ACCEPTED",
    "final_config": "$FINAL_CONFIG",
    "fallback_config": "$FALLBACK_CONFIG",
    "full_manifest": "$FULL_MANIFEST",
    "run_script": "$RUN_SCRIPT",
    "out_dir": "$FULL_ROOT/samcell_final",
}
out = Path("$FULL_ROOT/run_manifest_samcell_tn_combo.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY

if tmux has-session -t full_samcell_final 2>/dev/null; then
  echo "full_samcell_final already exists; not starting duplicate"
else
  tmux new-session -d -s full_samcell_final "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES bash '$RUN_SCRIPT'"
  echo "started full_samcell_final"
fi
tmux ls | grep -E "full_samcell_final|tn_combo_search_20260504|full_cellsam_prestart" || true
date
