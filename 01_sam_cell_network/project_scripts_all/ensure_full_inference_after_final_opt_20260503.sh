#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
CELLPOSE_PYTHON="${CELLPOSE_PYTHON:-/backup/taotao_work/venvs/cellpose311/bin/python}"
CELLSAM_PYTHON="${CELLSAM_PYTHON:-/backup/taotao_work/venvs/cellsam311_shared/bin/python}"
OPT_ROOT="${OPT_ROOT:-$PROJECT/outputs/final_optimization_20260503}"
FULL_ROOT="${FULL_ROOT:-$PROJECT/experiments/cellcosmos_full_16777_20260503}"
BASE_CONFIG="${BASE_CONFIG:-$PROJECT/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml}"
POLL_SECONDS="${POLL_SECONDS:-300}"

LOG_DIR="$FULL_ROOT/logs"
mkdir -p "$LOG_DIR" "$FULL_ROOT/manifests"
LOG="$LOG_DIR/ensure_full_inference.log"
exec > >(tee -a "$LOG") 2>&1

cd "$PROJECT"
date
echo "waiting for $OPT_ROOT/final_decision.json"
while [ ! -s "$OPT_ROOT/final_decision.json" ]; do
  sleep "$POLL_SECONDS"
done

FULL_MANIFEST="$FULL_ROOT/manifests/full.csv"
if [ ! -s "$FULL_MANIFEST" ]; then
  echo "full manifest missing; rebuilding"
  "$NNUNET_PYTHON" - <<'PY'
import csv
from pathlib import Path

data_root = Path("/backup/taotao_data/CellCosmos_Benchmark")
out = Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv")
rows = []
for image_path in sorted((data_root / "images").iterdir()):
    if not image_path.is_file():
        continue
    mask_path = data_root / "masks" / image_path.name
    if not mask_path.exists():
        raise FileNotFoundError(mask_path)
    source = image_path.name.split("_", 1)[0]
    rows.append({
        "source": source,
        "image_name": image_path.name,
        "image_path": str(image_path),
        "mask_path": str(mask_path),
        "split": "full_16777",
    })
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "image_name", "image_path", "mask_path", "split"])
    writer.writeheader()
    writer.writerows(rows)
print(out, len(rows))
PY
fi

FINAL_CONFIG="$OPT_ROOT/sam_cell_final_config.yaml"
FINAL_NAME="$("$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
decision = json.loads(Path("$OPT_ROOT/final_decision.json").read_text(encoding="utf-8"))
print(decision.get("final_name", "v3_baseline"))
PY
)"
ACCEPTED="$("$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
decision = json.loads(Path("$OPT_ROOT/final_decision.json").read_text(encoding="utf-8"))
print("true" if decision.get("accepted") else "false")
PY
)"
if [ "$ACCEPTED" != "true" ] || [ ! -s "$FINAL_CONFIG" ]; then
  FINAL_NAME="v3_baseline_fallback"
  cp "$BASE_CONFIG" "$FINAL_CONFIG"
fi

SAMCELL_SCRIPT="$FULL_ROOT/run_full_samcell.sh"
BASELINE_SCRIPT="$FULL_ROOT/run_full_cellpose_cellsam.sh"

cat > "$SAMCELL_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
LOG="$LOG_DIR/full_samcell.log"
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

cat > "$BASELINE_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT"
LOG="$LOG_DIR/full_cellpose_cellsam.log"
mkdir -p "$LOG_DIR"
exec > >(tee -a "\$LOG") 2>&1
date
PYTHONPATH=. "$CELLPOSE_PYTHON" scripts/run_cellpose_manifest.py \\
  --manifest_csv "$FULL_MANIFEST" \\
  --out_dir "$FULL_ROOT/cellpose_official_cyto3/predictions" \\
  --pretrained_model cyto3 \\
  --gpu_device 1
PYTHONPATH=. "$CELLPOSE_PYTHON" scripts/eval_label_dir.py \\
  --manifest_csv "$FULL_MANIFEST" \\
  --pred_dir "$FULL_ROOT/cellpose_official_cyto3/predictions" \\
  --out_dir "$FULL_ROOT/cellpose_official_cyto3/metrics" \\
  --pred_pattern "{stem}_cp_masks.tif" \\
  --method_name cellpose_official_cyto3
PYTHONPATH=. "$CELLPOSE_PYTHON" scripts/render_instance_overlays.py \\
  --manifest_csv "$FULL_MANIFEST" \\
  --pred_dir "$FULL_ROOT/cellpose_official_cyto3/predictions" \\
  --out_dir "$FULL_ROOT/cellpose_official_cyto3/overlays" \\
  --pred_pattern "{stem}_cp_masks.tif" \\
  --method_name cellpose_official_cyto3
PYTHONPATH=. "$CELLSAM_PYTHON" scripts/run_cellsam_manifest.py \\
  --manifest_csv "$FULL_MANIFEST" \\
  --out_dir "$FULL_ROOT/cellsam_generalist/predictions" \\
  --suffix _cellsam.tif \\
  --bbox_threshold 0.4 \\
  --grayscale_mode repeat \\
  --skip_existing
PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_label_dir.py \\
  --manifest_csv "$FULL_MANIFEST" \\
  --pred_dir "$FULL_ROOT/cellsam_generalist/predictions/labels" \\
  --out_dir "$FULL_ROOT/cellsam_generalist/metrics" \\
  --pred_pattern "{stem}_cellsam.tif" \\
  --method_name cellsam_generalist
PYTHONPATH=. "$NNUNET_PYTHON" scripts/render_instance_overlays.py \\
  --manifest_csv "$FULL_MANIFEST" \\
  --pred_dir "$FULL_ROOT/cellsam_generalist/predictions/labels" \\
  --out_dir "$FULL_ROOT/cellsam_generalist/overlays" \\
  --pred_pattern "{stem}_cellsam.tif" \\
  --method_name cellsam_generalist
date
EOF

chmod +x "$SAMCELL_SCRIPT" "$BASELINE_SCRIPT"

"$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
payload = {
    "final_name": "$FINAL_NAME",
    "accepted_by_optimizer": "$ACCEPTED" == "true",
    "final_config": "$FINAL_CONFIG",
    "full_manifest": "$FULL_MANIFEST",
    "scripts": ["$SAMCELL_SCRIPT", "$BASELINE_SCRIPT"],
    "models": ["samcell_final", "cellpose_official_cyto3", "cellsam_generalist"],
}
out = Path("$FULL_ROOT/run_manifest.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY

if ! tmux has-session -t full_samcell_final 2>/dev/null; then
  tmux new-session -d -s full_samcell_final "bash '$SAMCELL_SCRIPT'"
fi
CELLPOSE_DONE="$FULL_ROOT/cellpose_official_cyto3/metrics/summary_by_source.csv"
CELLSAM_DONE="$FULL_ROOT/cellsam_generalist/metrics/summary_by_source.csv"
if [ -s "$CELLPOSE_DONE" ] && [ -s "$CELLSAM_DONE" ]; then
  echo "full Cellpose cyto3 and CellSAM outputs already complete; skip baseline launcher"
elif tmux has-session -t full_cellpose_cyto3_prestart 2>/dev/null || tmux has-session -t full_cellsam_prestart 2>/dev/null; then
  echo "prestarted full Cellpose/CellSAM sessions are still running; skip duplicate baseline launcher"
elif ! tmux has-session -t full_cellpose_cellsam 2>/dev/null; then
  tmux new-session -d -s full_cellpose_cellsam "bash '$BASELINE_SCRIPT'"
fi

tmux ls | grep -E "full_samcell_final|full_cellpose_cellsam|full_cellpose_cyto3_prestart|full_cellsam_prestart" || true
date
