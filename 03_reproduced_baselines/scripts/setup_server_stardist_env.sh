#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-/backup/taotao_work/venvs/stardist}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(f"StarDist env requires Python >=3.10, got {sys.version}")
PY

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install \
  "tensorflow[and-cuda]==2.15.1" \
  stardist \
  csbdeep \
  numpy \
  scipy \
  scikit-image \
  tifffile \
  pillow \
  pandas \
  pyyaml \
  opencv-python-headless

"$VENV_DIR/bin/python" - <<'PY'
import tensorflow as tf
import stardist

print("tensorflow", tf.__version__)
print("stardist", stardist.__version__)
print("gpus", tf.config.list_physical_devices("GPU"))
PY
