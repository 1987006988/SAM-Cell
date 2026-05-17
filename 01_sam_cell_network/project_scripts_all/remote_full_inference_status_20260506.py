#!/usr/bin/env python3
"""Report full CellCosmos inference status on the workstation."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


ROOT = Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")


def shell(cmd: str) -> str:
    return subprocess.getoutput(cmd)


def count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob(pattern))


def nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def interval_status(rows: list[dict[str, str]], labels_dir: Path) -> list[dict[str, int | str | None]]:
    intervals = [
        (0, 2500, "main_0_2500"),
        (2500, 5000, "gap_2500_5000"),
        (5000, 8000, "gap_5000_8000"),
        (8000, 10000, "tail_8000_10000"),
        (10000, 12500, "tail_10000_12500"),
        (12500, 13500, "midtail_12500_13500"),
        (13500, 14500, "midtail_13500_14500"),
        (14500, len(rows), "late_14500_end"),
    ]
    result: list[dict[str, int | str | None]] = []
    for start, end, name in intervals:
        done = 0
        first_missing = None
        for idx, row in enumerate(rows[start:end], start=start):
            image_path = (
                row.get("image_path")
                or row.get("image")
                or row.get("image_file")
                or row.get("img_path")
                or ""
            )
            label_path = labels_dir / f"{Path(image_path).stem}.tif"
            if label_path.exists():
                done += 1
            elif first_missing is None:
                first_missing = idx
        result.append(
            {
                "name": name,
                "done": done,
                "total": end - start,
                "first_missing": first_missing,
            }
        )
    return result


def main() -> None:
    manifest = ROOT / "manifests" / "full.csv"
    rows = list(csv.DictReader(manifest.open(newline=""))) if manifest.exists() else []
    refine = ROOT / "samcell_refine_final"
    cellsam_labels = ROOT / "cellsam_generalist" / "predictions" / "labels"
    refine_labels = refine / "labels"

    report = {
        "time": shell("date '+%F %T %Z'"),
        "manifest_rows": len(rows),
        "cellsam_labels": count_files(cellsam_labels, "*_cellsam.tif"),
        "cellsam_summary_present": nonempty(ROOT / "cellsam_generalist" / "metrics" / "summary_by_source.csv"),
        "samcell_refine_labels": count_files(refine_labels, "*.tif"),
        "samcell_refine_summary_present": nonempty(refine / "summary.csv"),
        "samcell_refine_per_image_present": nonempty(refine / "per_image.csv"),
        "samcell_refine_intervals": interval_status(rows, refine_labels),
        "eval_processes": shell("pgrep -af 'eval_devset.py.*samcell_refine_final' | wc -l"),
        "gpu": shell("nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader"),
        "load": shell("uptime"),
        "sessions": shell("tmux ls 2>/dev/null | grep -E 'samcell_refine|full_samcell_final|hourly_full' || true"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
