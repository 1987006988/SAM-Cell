#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

required=(
  "$PACKAGE_ROOT/README.md"
  "$PACKAGE_ROOT/environment.yml"
  "$PACKAGE_ROOT/requirements.txt"
  "$PACKAGE_ROOT/01_sam_cell_network/sam_cell/pipeline.py"
  "$PACKAGE_ROOT/01_sam_cell_network/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml"
  "$PACKAGE_ROOT/01_sam_cell_network/configs/sam_cell_final_packaged.yaml"
  "$PACKAGE_ROOT/02_cellcosmos_dataset_work/README.md"
  "$PACKAGE_ROOT/03_reproduced_baselines/README.md"
  "$PACKAGE_ROOT/docs/experiment_protocol.md"
  "$PACKAGE_ROOT/docs/runtime_environment_lock.md"
  "$PACKAGE_ROOT/artifacts/summary_tables/final_full16777_key_metrics.csv"
  "$PACKAGE_ROOT/artifacts/path_index/large_file_manifest.csv"
  "$PACKAGE_ROOT/artifacts/weights/WEIGHTS_MANIFEST.md"
  "$PACKAGE_ROOT/artifacts/weights/proposal_ranker_dual/proposal_ranker.joblib"
  "$PACKAGE_ROOT/artifacts/weights/sam2/checkpoints/sam2_hiera_large.pt"
  "$PACKAGE_ROOT/artifacts/weights/nnunet/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_final.pth"
  "$PACKAGE_ROOT/artifacts/weights/nnunet/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_final.pth"
  "$PACKAGE_ROOT/artifacts/third_party/segment-anything-2/sam2"
  "$PACKAGE_ROOT/artifacts/third_party/nnUNet/nnunetv2"
  "$PACKAGE_ROOT/artifacts/smoke_data/manifest.csv"
  "$PACKAGE_ROOT/artifacts/datasets/CellCosmos_Benchmark/full_manifest_packaged.csv"
)

for path in "${required[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "MISSING $path" >&2
    exit 1
  fi
done

while IFS= read -r script; do
  bash -n "$script"
done < <(find "$PACKAGE_ROOT/scripts" -type f -name '*.sh' | sort)

python - "$PACKAGE_ROOT" <<'PY'
import csv
import sys
from pathlib import Path

root = Path(sys.argv[1])
metrics = root / "artifacts" / "summary_tables" / "final_full16777_key_metrics.csv"
rows = list(csv.DictReader(metrics.open(newline="", encoding="utf-8")))
if len(rows) != 3:
    raise SystemExit(f"expected 3 final metric rows, got {len(rows)}")
names = {row["method"] for row in rows}
if "SAM-Cell refine final" not in names:
    raise SystemExit("SAM-Cell refine final row missing")
for row in rows:
    for key in ("f1", "pq", "aji", "dice"):
        value = float(row[key])
        if not (0.0 <= value <= 1.0):
            raise SystemExit(f"metric out of range: {row['method']} {key}={value}")
print("CSV sanity checks passed")

portable_config = root / "01_sam_cell_network" / "configs" / "sam_cell_final_packaged.yaml"
text = portable_config.read_text(encoding="utf-8")
for forbidden in ["/backup/taotao_work", "/backup/taotao_data", "/mnt/d/", "D:\\"]:
    if forbidden in text:
        raise SystemExit(f"portable config contains non-portable path marker: {forbidden}")

manifest = root / "artifacts" / "datasets" / "CellCosmos_Benchmark" / "full_manifest_packaged.csv"
manifest_rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
if len(manifest_rows) != 16777:
    raise SystemExit(f"expected 16777 packaged CellCosmos manifest rows, got {len(manifest_rows)}")
for rel in [
    "artifacts/datasets/CellCosmos_Benchmark/images",
    "artifacts/datasets/CellCosmos_Benchmark/masks",
]:
    count = sum(1 for p in (root / rel).iterdir() if p.is_file())
    if count != 16777:
        raise SystemExit(f"expected 16777 files in {rel}, got {count}")
print("packaged config and dataset checks passed")
PY

if grep -RInE --binary-files=without-match --exclude='verify_package.sh' --exclude='build_thesis_experiment_package_20260512.py' --exclude-dir='weights' --exclude-dir='datasets' --exclude-dir='third_party' '\bsk-[A-Za-z0-9_-]{20,}|BEGIN (RSA|OPENSSH|PRIVATE) KEY|deepcell.*token|api[_-]?key' "$PACKAGE_ROOT" >/tmp/samcell_pkg_secret_scan.txt 2>/dev/null; then
  echo "Potential secret-like string found:" >&2
  cat /tmp/samcell_pkg_secret_scan.txt >&2
  exit 1
fi

echo "verify_package: OK"
