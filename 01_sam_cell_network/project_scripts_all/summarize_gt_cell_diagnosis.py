#!/usr/bin/env python3
"""Summarize GT-cell-level SAM-Cell diagnosis CSV outputs."""

from __future__ import annotations

import argparse
import collections
import csv
from pathlib import Path


def _float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _mean(rows: list[dict[str, str]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(_float(row, key) for row in rows) / len(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnosis_dir", required=True, help="Directory with gt_cell_diagnosis.csv.")
    parser.add_argument(
        "--focus_images",
        default="cellpose_469.png,cellpose_280.png,cellpose_533.png,cellpose_528.png,cellpose_434.png,cellpose_389.png,cellpose_235.png,cellpose_367.png",
        help="Comma-separated image names for detailed summaries.",
    )
    args = parser.parse_args()

    root = Path(args.diagnosis_dir)
    rows = _read_csv(root / "gt_cell_diagnosis.csv")
    image_rows = _read_csv(root / "image_summary.csv")

    print(f"diagnosis_dir: {root}")
    print(f"total_gt_cells: {len(rows)}")

    counts = collections.Counter(row["failure_type"] for row in rows)
    print("\nfailure_type_counts_all:")
    for key, value in counts.most_common():
        print(f"{key},{value},{value / max(1, len(rows)):.6f}")

    miss = [row for row in rows if row["failure_type"] != "detected"]
    miss_counts = collections.Counter(row["failure_type"] for row in miss)
    print(f"\nmissed_or_low_iou_gt_cells: {len(miss)}")
    print("failure_type_counts_missed_only:")
    for key, value in miss_counts.most_common():
        print(f"{key},{value},{value / max(1, len(miss)):.6f}")

    metric_keys = [
        "combined_cov03",
        "combined_cov05",
        "cellpose_style_cov03",
        "cellpose_style_cov05",
        "universal_boundary_cov03",
        "universal_boundary_cov05",
        "universal_boundary_boundary_mean",
        "marker_count_inside_gt",
        "best_raw_iou",
        "best_unranked_iou",
        "best_ranked_iou",
        "best_final_iou",
        "best_raw_proposal_gt_count",
    ]
    print("\nmeans_all:")
    for key in metric_keys:
        print(f"{key},{_mean(rows, key):.6f}")

    print("\nmeans_missed_only:")
    for key in metric_keys:
        print(f"{key},{_mean(miss, key):.6f}")

    print("\nworst_images_by_detected_fraction:")
    image_rows = sorted(
        image_rows,
        key=lambda row: (
            _float(row, "detected") / max(1.0, _float(row, "gt_cells")),
            -int(float(row.get("gt_cells", 0) or 0)),
        ),
    )
    for row in image_rows[:12]:
        detected_frac = _float(row, "detected") / max(1.0, _float(row, "gt_cells"))
        compact = {
            "image": row.get("image", ""),
            "gt_cells": row.get("gt_cells", ""),
            "detected_frac": f"{detected_frac:.4f}",
            "foreground_miss": row.get("foreground_miss", "0"),
            "weak_foreground": row.get("weak_foreground", "0"),
            "marker_miss": row.get("marker_miss", "0"),
            "merge_under_split": row.get("merge_under_split", "0"),
            "ranker_filtered": row.get("ranker_filtered", "0"),
            "selector_or_merge_filtered": row.get("selector_or_merge_filtered", "0"),
            "final_merge_loss": row.get("final_merge_loss", "0"),
            "shape_low_iou": row.get("shape_low_iou", "0"),
        }
        print(",".join(f"{k}={v}" for k, v in compact.items()))

    print("\nfocus_images:")
    focus = [name.strip() for name in args.focus_images.split(",") if name.strip()]
    for image in focus:
        sub = [row for row in rows if row["image"] == image]
        if not sub:
            print(f"{image}: no_rows")
            continue
        c = collections.Counter(row["failure_type"] for row in sub)
        print(f"{image}: gt={len(sub)} counts={dict(c)}")
        print(
            "  means="
            + ",".join(
                f"{key}:{_mean(sub, key):.4f}"
                for key in [
                    "combined_cov03",
                    "combined_cov05",
                    "marker_count_inside_gt",
                    "best_raw_iou",
                    "best_ranked_iou",
                    "best_final_iou",
                    "best_raw_proposal_gt_count",
                ]
            )
        )


if __name__ == "__main__":
    main()
