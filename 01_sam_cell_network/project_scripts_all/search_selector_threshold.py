from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from scripts.compare_methods import _read_label
from scripts.eval_devset import _read_rows, _write_csv, evaluate_rows


def _parse_thresholds(text: str) -> list[float]:
    return [float(item) for item in text.split(",") if item.strip()]


def _cellpose_metrics(rows: list[dict[str, str]], cellpose_dir: Path) -> dict[str, dict[str, float | int]]:
    metrics = {}
    for row in rows:
        image_path = Path(row["image_path"])
        gt = load_label_map(row["mask_path"])
        cp = _read_label(cellpose_dir / f"{image_path.stem}_cp_masks.tif")
        metrics[image_path.name] = instance_metrics(cp, gt)
    return metrics


def _comparison_rows(sam_rows: list[dict], cp_metrics: dict[str, dict[str, float | int]], threshold: float) -> list[dict]:
    rows = []
    for row in sam_rows:
        cp = cp_metrics[str(row["image"])]
        output = {
            "threshold": threshold,
            "source": row["source"],
            "image": row["image"],
            "watershed_selected": row.get("watershed_selected", 0),
            "sam_pq": float(row["final_pq"]),
            "cellpose_pq": float(cp["pq"]),
            "delta_pq": float(row["final_pq"]) - float(cp["pq"]),
            "sam_aji": float(row["final_aji"]),
            "cellpose_aji": float(cp["aji"]),
            "delta_aji": float(row["final_aji"]) - float(cp["aji"]),
            "sam_f1": float(row["final_f1"]),
            "cellpose_f1": float(cp["f1"]),
            "delta_f1": float(row["final_f1"]) - float(cp["f1"]),
            "sam_wins_pq": int(float(row["final_pq"]) > float(cp["pq"])),
        }
        rows.append(output)
    return rows


def _summaries(rows: list[dict]) -> list[dict]:
    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_source[str(row["source"])].append(row)
    output = []
    for source, source_rows in [("ALL", rows), *sorted(by_source.items())]:
        summary = summarize_metrics(source_rows)
        wins = sum(int(row["sam_wins_pq"]) for row in source_rows)
        output.append(
            {
                "threshold": float(source_rows[0]["threshold"]) if source_rows else np.nan,
                "source": source,
                "n": len(source_rows),
                "sam_win_rate": wins / len(source_rows) if source_rows else 0.0,
                "source_beats_cellpose": int(float(summary.get("delta_pq", 0.0)) > 0),
                **summary,
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Search internal selector thresholds using instance metrics.")
    parser.add_argument("--config", default="configs/sam_cell_fusion_selector.yaml")
    parser.add_argument("--devset_csv", default="outputs/benchmark_splits_smoke/dev_tune.csv")
    parser.add_argument("--cellpose_dir", default="outputs/benchmark_splits_smoke/cellpose_cyto")
    parser.add_argument("--out_dir", default="outputs/selector_threshold_search")
    parser.add_argument("--thresholds", default="0.15,0.25,0.35,0.45,0.55,0.65")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = _read_rows(Path(args.devset_csv), args.limit)
    cfg = load_config(args.config)
    pipeline = SAMCellPipeline(cfg)
    cp_metrics = _cellpose_metrics(rows, Path(args.cellpose_dir))
    all_per_image = []
    all_summary = []
    for threshold in _parse_thresholds(args.thresholds):
        print(f"threshold={threshold}")
        pipeline.cfg.external_proposals.internal_selector_threshold = threshold
        sam_rows = evaluate_rows(pipeline, rows)
        comparison = _comparison_rows(sam_rows, cp_metrics, threshold)
        all_per_image.extend(comparison)
        all_summary.extend(_summaries(comparison))
    out_dir = Path(args.out_dir)
    _write_csv(out_dir / "per_image.csv", all_per_image)
    _write_csv(out_dir / "summary_by_source.csv", all_summary)
    print(f"wrote {out_dir / 'summary_by_source.csv'}")


if __name__ == "__main__":
    main()
