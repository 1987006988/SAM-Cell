#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /home/taotao/anaconda3/envs/SAM-Cell/bin/python ]]; then
    PYTHON_BIN=/home/taotao/anaconda3/envs/SAM-Cell/bin/python
  else
    PYTHON_BIN=python
  fi
fi
DRY_RUN="${DRY_RUN:-0}"
MANIFEST_CSV="${MANIFEST_CSV:-$PACKAGE_ROOT/artifacts/smoke_data/manifest.csv}"
PRED_DIR="${PRED_DIR:-$PACKAGE_ROOT/artifacts/smoke_data/predictions/gt_as_prediction}"
PRED_PATTERN="${PRED_PATTERN:-}"
if [[ -z "$PRED_PATTERN" ]]; then
  PRED_PATTERN='{stem}.png'
fi
METHOD_NAME="${METHOD_NAME:-gt_as_prediction_fixture}"
OUT_DIR="${OUT_DIR:-$PACKAGE_ROOT/artifacts/smoke_outputs/baseline_eval}"

export PYTHONPATH="$PACKAGE_ROOT/01_sam_cell_network:${PYTHONPATH:-}"
cmd=("$PYTHON_BIN" "$PACKAGE_ROOT/03_reproduced_baselines/scripts/eval_label_dir.py" --manifest_csv "$MANIFEST_CSV" --pred_dir "$PRED_DIR" --out_dir "$OUT_DIR" --pred_pattern "$PRED_PATTERN" --method_name "$METHOD_NAME")

if [[ ! -f "$MANIFEST_CSV" ]]; then
  echo "Missing manifest: $MANIFEST_CSV" >&2
  exit 1
fi
if [[ ! -d "$PRED_DIR" ]]; then
  echo "Missing prediction directory: $PRED_DIR" >&2
  exit 1
fi

if [[ "$DRY_RUN" != "0" ]]; then
  echo "DRY_RUN=1; command not executed:"
  printf 'Command template: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
  exit 0
fi

cd "$PACKAGE_ROOT"
"${cmd[@]}"
