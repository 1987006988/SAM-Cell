#!/usr/bin/env bash
set -euo pipefail

ENV_ROOT="${ENV_ROOT:-/backup/taotao_work/venvs/cellpose311}"
PYTHON_BIN="${PYTHON_BIN:-/backup/taotao_work/venvs/nnunet/bin/python}"

if [ ! -x "$ENV_ROOT/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$ENV_ROOT"
fi

"$ENV_ROOT/bin/python" -m pip install --upgrade pip setuptools wheel
"$ENV_ROOT/bin/python" -m pip install --no-cache-dir \
  --index-url https://download.pytorch.org/whl/cu121 \
  torch==2.5.1 torchvision==0.20.1
"$ENV_ROOT/bin/python" -m pip install --no-cache-dir \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  cellpose==3.1.1.1 scikit-image tifffile pillow pandas pyyaml opencv-python-headless

"$ENV_ROOT/bin/python" - <<'PY'
import importlib.util
import torch

print("python environment ready")
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), "gpus", torch.cuda.device_count())
for name in ["cellpose", "skimage", "tifffile", "PIL"]:
    if importlib.util.find_spec(name) is None:
        raise SystemExit(f"missing package: {name}")
    print(name, "ok")
PY
