#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

CHECK_ONLY=0
if [[ "${1:-}" == "--check-only" ]]; then
  CHECK_ONLY=1
  shift
elif [[ "${1:-}" == "--run" ]]; then
  DRY_RUN=0
  shift
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /home/taotao/anaconda3/envs/SAM-Cell/bin/python ]]; then
    PYTHON_BIN=/home/taotao/anaconda3/envs/SAM-Cell/bin/python
  else
    PYTHON_BIN=python
  fi
fi

DRY_RUN="${DRY_RUN:-1}"
IMAGE="${IMAGE:-$PACKAGE_ROOT/artifacts/smoke_data/images/cellpose_434.png}"
IMAGE_DIR="${IMAGE_DIR:-}"
LIMIT="${LIMIT:-1}"
DEVICE="${DEVICE:-auto}"
CONFIG="${CONFIG:-$PACKAGE_ROOT/01_sam_cell_network/configs/sam_cell_final_packaged.yaml}"
OUT_DIR="${OUT_DIR:-$PACKAGE_ROOT/artifacts/smoke_outputs/samcell_inference}"
CHECK_IMPORTS="${CHECK_IMPORTS:-1}"

required_files=(
  "$CONFIG"
  "$PACKAGE_ROOT/artifacts/weights/proposal_ranker_dual/proposal_ranker.joblib"
  "$PACKAGE_ROOT/artifacts/weights/sam2/checkpoints/sam2_hiera_large.pt"
  "$PACKAGE_ROOT/artifacts/weights/nnunet/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d/plans.json"
  "$PACKAGE_ROOT/artifacts/weights/nnunet/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_final.pth"
  "$PACKAGE_ROOT/artifacts/weights/nnunet/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d/plans.json"
  "$PACKAGE_ROOT/artifacts/weights/nnunet/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_final.pth"
)

for path in "${required_files[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "Missing required SAM-Cell artifact: $path" >&2
    echo "If this is a trimmed copy, restore artifacts/weights/ from the package source or run the documented sync command." >&2
    exit 1
  fi
done

if [[ ! -d "$PACKAGE_ROOT/artifacts/third_party/segment-anything-2/sam2" ]]; then
  echo "Missing packaged SAM2 source: artifacts/third_party/segment-anything-2/sam2" >&2
  exit 1
fi
if [[ ! -d "$PACKAGE_ROOT/artifacts/third_party/nnUNet/nnunetv2" ]]; then
  echo "Missing packaged nnU-Net source: artifacts/third_party/nnUNet/nnunetv2" >&2
  exit 1
fi

if [[ -n "$IMAGE_DIR" ]]; then
  if [[ ! -d "$IMAGE_DIR" ]]; then
    echo "Missing IMAGE_DIR: $IMAGE_DIR" >&2
    exit 1
  fi
else
  if [[ ! -f "$IMAGE" ]]; then
    echo "Missing IMAGE: $IMAGE" >&2
    exit 1
  fi
fi

export PYTHONPATH="$PACKAGE_ROOT/01_sam_cell_network:$PACKAGE_ROOT/artifacts/third_party/segment-anything-2:$PACKAGE_ROOT/artifacts/third_party/nnUNet:${PYTHONPATH:-}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$PACKAGE_ROOT/artifacts/cache/matplotlib}"
mkdir -p "$MPLCONFIGDIR"

if [[ "$CHECK_IMPORTS" == "1" ]]; then
  "$PYTHON_BIN" - <<'PY'
import importlib

checks = [
    ("numpy", None),
    ("PIL", None),
    ("tifffile", None),
    ("yaml", None),
    ("torch", None),
    ("joblib", None),
    ("sam_cell.config", "load_config"),
    ("nnunetv2.inference.predict_from_raw_data", "nnUNetPredictor"),
    ("sam2.build_sam", "build_sam2"),
]
missing = []
for module, attr in checks:
    try:
        obj = importlib.import_module(module)
        if attr is not None:
            getattr(obj, attr)
    except Exception as exc:
        missing.append(f"{module}: {type(exc).__name__}: {exc}")
if missing:
    raise SystemExit("Runtime import check failed:\n" + "\n".join(missing))
print("runtime import check: OK")
PY
fi

if [[ "$DEVICE" == "auto" ]]; then
  DEVICE_RESOLVED="$("$PYTHON_BIN" - <<'PY'
import torch
print("cuda" if torch.cuda.is_available() else "cpu")
PY
)"
else
  DEVICE_RESOLVED="$DEVICE"
fi

cmd=("$PYTHON_BIN" "$PACKAGE_ROOT/01_sam_cell_network/project_scripts_all/infer.py" --config "$CONFIG" --out_dir "$OUT_DIR" --limit "$LIMIT" --device "$DEVICE_RESOLVED")
if [[ -n "$IMAGE_DIR" ]]; then
  cmd+=(--image_dir "$IMAGE_DIR")
else
  cmd+=(--image "$IMAGE")
fi

if [[ "$CHECK_ONLY" == "1" || "$DRY_RUN" != "0" ]]; then
  echo "SAM-Cell packaged inference preflight: OK"
  echo "Set DRY_RUN=0 or pass --run to execute. DEVICE=$DEVICE resolved to $DEVICE_RESOLVED."
  printf 'Command template: '
  printf '%q ' "${cmd[@]}"
  printf '\n'
  exit 0
fi

cd "$PACKAGE_ROOT"
"${cmd[@]}"
