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

export PYTHONPATH="$PACKAGE_ROOT/01_sam_cell_network:$PACKAGE_ROOT/artifacts/third_party/segment-anything-2:$PACKAGE_ROOT/artifacts/third_party/nnUNet:${PYTHONPATH:-}"
"$PYTHON_BIN" - <<'PY'
import importlib
import sys

print("python", sys.version.replace("\n", " "))
for module in [
    "torch",
    "numpy",
    "scipy",
    "skimage",
    "PIL",
    "tifffile",
    "yaml",
    "pandas",
    "sklearn",
    "joblib",
    "sam_cell.config",
    "nnunetv2.inference.predict_from_raw_data",
    "sam2.build_sam",
]:
    obj = importlib.import_module(module)
    print(module, getattr(obj, "__version__", "OK"))
PY
