#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
VENV="${VENV:-/backup/taotao_work/venvs/hovernet311_shared}"
NNUNET_PYTHON="${NNUNET_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
EXP_ROOT="${EXP_ROOT:-$PROJECT/experiments/cellcosmos_repro_20260501}"
SPLIT="${SPLIT:-core3500_all}"
RUN_NAME="${RUN_NAME:-hovernet_fast_pannuke}"
MANIFEST="${MANIFEST:-$EXP_ROOT/manifests/$SPLIT.csv}"
OUT_ROOT="${OUT_ROOT:-$EXP_ROOT/baseline_${RUN_NAME}}"
WEIGHTS_PATH="${WEIGHTS_PATH:-/backup/taotao_home/.tiatoolbox/models/hovernet_fast-pannuke.official.pth}"
TIATOOLBOX_HOME="${TIATOOLBOX_HOME:-/backup/taotao_home/.tiatoolbox}"
DEVICE="${DEVICE:-cuda}"
BATCH_SIZE="${BATCH_SIZE:-8}"
LIMIT="${LIMIT:-}"

LOG_DIR="$OUT_ROOT/logs"
PRED_ROOT="$OUT_ROOT/predictions/$SPLIT"
METRIC_ROOT="$OUT_ROOT/metrics/$SPLIT"
OVERLAY_ROOT="$OUT_ROOT/overlays/$SPLIT"
RUN_MANIFEST_DIR="$OUT_ROOT/run_manifests"
EVAL_MANIFEST="$MANIFEST"

mkdir -p "$LOG_DIR" "$PRED_ROOT" "$METRIC_ROOT" "$OVERLAY_ROOT" "$RUN_MANIFEST_DIR"
exec > >(tee -a "$LOG_DIR/${SPLIT}.log") 2>&1

cd "$PROJECT"
date

if [ -n "$LIMIT" ]; then
  mkdir -p "$OUT_ROOT/manifests"
  EVAL_MANIFEST="$OUT_ROOT/manifests/${SPLIT}_limit${LIMIT}.csv"
  "$NNUNET_PYTHON" - <<PY
import csv
from pathlib import Path
src = Path("$MANIFEST")
dst = Path("$EVAL_MANIFEST")
limit = int("$LIMIT")
with src.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))[:limit]
fieldnames = list(rows[0].keys()) if rows else []
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(dst)
PY
fi

if ! "$VENV/bin/python" -c "import tiatoolbox" >/dev/null 2>&1; then
  bash scripts/setup_server_hovernet_env.sh
fi

ARGS=()
if [ -n "$LIMIT" ]; then
  ARGS+=(--limit "$LIMIT")
fi

PYTHONPATH=. "$VENV/bin/python" scripts/run_hovernet_manifest.py \
  --manifest_csv "$EVAL_MANIFEST" \
  --out_dir "$PRED_ROOT" \
  --model hovernet_fast-pannuke \
  --weights_path "$WEIGHTS_PATH" \
  --tiatoolbox_home "$TIATOOLBOX_HOME" \
  --device "$DEVICE" \
  --batch_size "$BATCH_SIZE" \
  --skip_existing \
  "${ARGS[@]}"

PYTHONPATH=. "$NNUNET_PYTHON" scripts/eval_label_dir.py \
  --manifest_csv "$EVAL_MANIFEST" \
  --pred_dir "$PRED_ROOT/labels" \
  --out_dir "$METRIC_ROOT" \
  --pred_pattern "{stem}_hovernet.tif" \
  --method_name "$RUN_NAME"

PYTHONPATH=. "$NNUNET_PYTHON" scripts/render_instance_overlays.py \
  --manifest_csv "$EVAL_MANIFEST" \
  --pred_dir "$PRED_ROOT/labels" \
  --out_dir "$OVERLAY_ROOT" \
  --pred_pattern "{stem}_hovernet.tif" \
  --method_name "$RUN_NAME"

"$NNUNET_PYTHON" - <<PY
import json
from pathlib import Path
payload = {
    "run_name": "$RUN_NAME",
    "split": "$SPLIT",
    "manifest": "$EVAL_MANIFEST",
    "source_manifest": "$MANIFEST",
    "predictions": "$PRED_ROOT/labels",
    "metrics": "$METRIC_ROOT",
    "overlays": "$OVERLAY_ROOT",
    "weights_path": "$WEIGHTS_PATH",
    "tiatoolbox_home": "$TIATOOLBOX_HOME",
    "device": "$DEVICE",
    "batch_size": "$BATCH_SIZE",
    "limit": "$LIMIT" or None,
}
out = Path("$RUN_MANIFEST_DIR/${SPLIT}.json")
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(out)
PY

cat "$METRIC_ROOT/summary_by_source.csv"
date
