#!/usr/bin/env bash
set -euo pipefail

WORK_ROOT="${WORK_ROOT:-/backup/taotao_work}"
PYTHON_BIN="${PYTHON_BIN:-/opt/software/python-3.11.12-r8/bin/python}"
VENV_DIR="${VENV_DIR:-$WORK_ROOT/venvs/nnunet}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu121}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"

mkdir -p "$WORK_ROOT"/{venvs,nnUNet_raw,nnUNet_preprocessed,nnUNet_results,logs,tmp}

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install --index-url "$TORCH_INDEX_URL" torch torchvision
"$VENV_DIR/bin/python" -m pip install \
  --index-url "$PIP_INDEX_URL" \
  --trusted-host "$PIP_TRUSTED_HOST" \
  nnunetv2 \
  scikit-image \
  pillow \
  tifffile \
  pandas \
  pyyaml \
  scipy \
  joblib \
  opencv-python-headless

cat > "$WORK_ROOT/env_nnunet.sh" <<EOF
export WORK_ROOT="$WORK_ROOT"
export nnUNet_raw="$WORK_ROOT/nnUNet_raw"
export nnUNet_preprocessed="$WORK_ROOT/nnUNet_preprocessed"
export nnUNet_results="$WORK_ROOT/nnUNet_results"
export TMPDIR="$WORK_ROOT/tmp"
export PATH="$VENV_DIR/bin:\$PATH"
EOF

chmod +x "$WORK_ROOT/env_nnunet.sh"

"$VENV_DIR/bin/python" - <<'PY'
import torch
import nnunetv2

print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "gpus", torch.cuda.device_count())
print("nnunetv2", nnunetv2.__file__)
PY
