#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/backup/taotao_work/sam_cell}"
BASE_PYTHON="${BASE_PYTHON:-/backup/taotao_work/venvs/nnunet/bin/python}"
VENV="${VENV:-/backup/taotao_work/venvs/hovernet311_shared}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-/backup/taotao_work/pip_cache}"
TIATOOLBOX_VERSION="${TIATOOLBOX_VERSION:-2.0.1}"

mkdir -p "$PIP_CACHE_DIR"

if [ ! -x "$VENV/bin/python" ]; then
  "$BASE_PYTHON" -m venv "$VENV"
fi

NNUNET_SITE="$("$BASE_PYTHON" - <<'PY'
import site
print(site.getsitepackages()[0])
PY
)"
HOVERNET_SITE="$("$VENV/bin/python" - <<'PY'
import site
print(site.getsitepackages()[0])
PY
)"
echo "$NNUNET_SITE" > "$HOVERNET_SITE/nnunet_site_packages.pth"

"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install "tiatoolbox==${TIATOOLBOX_VERSION}"

cd "$PROJECT"
"$VENV/bin/python" - <<'PY'
import tiatoolbox
from tiatoolbox.models.engine.nucleus_instance_segmentor import NucleusInstanceSegmentor
import torch
print("tiatoolbox", getattr(tiatoolbox, "__version__", "unknown"))
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("segmentor", NucleusInstanceSegmentor.__name__)
PY
