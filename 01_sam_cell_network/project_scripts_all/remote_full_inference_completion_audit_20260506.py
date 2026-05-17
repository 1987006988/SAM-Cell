#!/usr/bin/env python3
"""Completion audit for the full CellCosmos CellSAM/SAM-Cell inference goal."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")
EXPECTED_N = 16777


def count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob(pattern))


def nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not nonempty(path):
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def first_value(row: dict[str, str], *keys: str) -> str | None:
    lowered = {k.lower(): v for k, v in row.items()}
    for key in keys:
        if key in row:
            return row[key]
        if key.lower() in lowered:
            return lowered[key.lower()]
    return None


def has_all_n(rows: list[dict[str, str]], expected: int, fallback_count: int | None = None) -> bool:
    for row in rows:
        source = first_value(row, "source", "dataset", "name")
        n_value = first_value(row, "n", "count", "num_images")
        if source == "ALL" and n_value is not None:
            try:
                return int(float(n_value)) == expected
            except ValueError:
                return False
        if source == "ALL" and n_value is None and fallback_count is not None:
            return fallback_count == expected
    return False


def audit() -> dict[str, object]:
    cellsam_summary = ROOT / "cellsam_generalist" / "metrics" / "summary_by_source.csv"
    samcell = ROOT / "samcell_refine_final"
    samcell_summary = samcell / "summary.csv"
    samcell_per_image = samcell / "per_image.csv"

    cellsam_rows = csv_rows(cellsam_summary)
    samcell_summary_rows = csv_rows(samcell_summary)
    samcell_per_image_rows = csv_rows(samcell_per_image)

    checks = [
        {
            "requirement": "CellSAM full labels complete",
            "evidence": "cellsam_generalist/predictions/labels/*_cellsam.tif",
            "value": count_files(ROOT / "cellsam_generalist" / "predictions" / "labels", "*_cellsam.tif"),
            "expected": EXPECTED_N,
        },
        {
            "requirement": "CellSAM full summary has ALL n=16777",
            "evidence": "cellsam_generalist/metrics/summary_by_source.csv",
            "value": has_all_n(cellsam_rows, EXPECTED_N),
            "expected": True,
        },
        {
            "requirement": "SAM-Cell refine full labels complete",
            "evidence": "samcell_refine_final/labels/*.tif",
            "value": count_files(samcell / "labels", "*.tif"),
            "expected": EXPECTED_N,
        },
        {
            "requirement": "SAM-Cell refine per-image metrics complete",
            "evidence": "samcell_refine_final/per_image.csv",
            "value": len(samcell_per_image_rows),
            "expected": EXPECTED_N,
        },
        {
            "requirement": "SAM-Cell refine summary has ALL row and per-image n=16777",
            "evidence": "samcell_refine_final/summary.csv",
            "value": has_all_n(samcell_summary_rows, EXPECTED_N, fallback_count=len(samcell_per_image_rows)),
            "expected": True,
        },
    ]
    for check in checks:
        check["ok"] = check["value"] == check["expected"]

    return {
        "objective": (
            "Monitor full CellSAM and accepted SAM-Cell refine inference on the "
            "16777-image CellCosmos full manifest until both have complete labels "
            "and full metric summaries."
        ),
        "root": str(ROOT),
        "checks": checks,
        "complete": all(bool(check["ok"]) for check in checks),
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
