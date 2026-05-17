#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

exec bash "$PACKAGE_ROOT/scripts/run_packaged_samcell_inference.sh" "$@"
