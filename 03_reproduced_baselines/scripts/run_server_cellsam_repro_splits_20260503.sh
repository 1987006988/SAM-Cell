#!/usr/bin/env bash
set -euo pipefail

PROJECT=/backup/taotao_work/sam_cell
VENV=/backup/taotao_work/venvs/cellsam311_shared
EXP=$PROJECT/experiments/cellcosmos_repro_20260501/baseline_cellsam_generalist
LOG=$EXP/logs/repro_splits.log

mkdir -p "$EXP/logs" "$EXP/predictions" "$EXP/metrics" "$EXP/overlays"
exec > >(tee -a "$LOG") 2>&1

cd "$PROJECT"
date
"$VENV/bin/python" - <<'PY'
import torch, torchvision, cellSAM
print("torch", torch.__version__)
print("torchvision", torchvision.__version__)
print("cellSAM", getattr(cellSAM, "__version__", "unknown"))
PY

run_split() {
  local split="$1"
  local manifest="experiments/cellcosmos_repro_20260501/manifests/${split}.csv"
  local pred_root="$EXP/predictions/${split}"
  local metrics_root="$EXP/metrics/${split}"
  local overlay_root="$EXP/overlays/${split}"

  echo "=== CellSAM split: ${split} ==="
  date
  PYTHONPATH=. "$VENV/bin/python" scripts/run_cellsam_manifest.py \
    --manifest_csv "$manifest" \
    --out_dir "$pred_root" \
    --suffix _cellsam.tif \
    --bbox_threshold 0.4 \
    --grayscale_mode repeat \
    --skip_existing

  PYTHONPATH=. "$VENV/bin/python" scripts/eval_label_dir.py \
    --manifest_csv "$manifest" \
    --pred_dir "$pred_root/labels" \
    --out_dir "$metrics_root" \
    --pred_pattern "{stem}_cellsam.tif" \
    --method_name cellsam_generalist

  PYTHONPATH=. "$VENV/bin/python" scripts/render_instance_overlays.py \
    --manifest_csv "$manifest" \
    --pred_dir "$pred_root/labels" \
    --out_dir "$overlay_root" \
    --pred_pattern "{stem}_cellsam.tif" \
    --method_name cellsam_generalist

  cat "$metrics_root/summary_by_source.csv"
  date
}

run_split iid_val
run_split pannuke_core_test
run_split far_ood_test

echo "=== CellSAM repro splits complete ==="
date
