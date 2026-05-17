#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

bash "$PACKAGE_ROOT/scripts/verify_package.sh"
bash "$PACKAGE_ROOT/scripts/run_packaged_samcell_inference.sh" --check-only
DRY_RUN=0 bash "$PACKAGE_ROOT/scripts/run_baseline_eval_smoke.sh"

echo "run_all_smoke: OK"
