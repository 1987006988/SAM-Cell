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

from sam_cell.io import load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _read_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.array(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.int32, copy=False)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare SAM-Cell predictions with Cellpose baseline")
    parser.add_argument("--devset_csv", default="outputs/dev_eval/devset_25.csv")
    parser.add_argument("--sam_labels_dir", required=True)
    parser.add_argument("--cellpose_dir", required=True)
    parser.add_argument("--out_dir", default="outputs/dev_eval/compare")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = _read_rows(Path(args.devset_csv), args.limit)
    sam_dir = Path(args.sam_labels_dir)
    cellpose_dir = Path(args.cellpose_dir)
    out_dir = Path(args.out_dir)
    per_image = []

    for row in rows:
        image_path = Path(row["image_path"])
        stem = image_path.stem
        source = row.get("source", stem.split("_", 1)[0])
        gt = load_label_map(row["mask_path"])
        sam_path = sam_dir / f"{stem}.tif"
        cp_path = cellpose_dir / f"{stem}_cp_masks.tif"
        if not sam_path.exists():
            raise FileNotFoundError(sam_path)
        if not cp_path.exists():
            raise FileNotFoundError(cp_path)
        sam = instance_metrics(_read_label(sam_path), gt)
        cp = instance_metrics(_read_label(cp_path), gt)
        row_out = {
            "source": source,
            "image": image_path.name,
            **{f"sam_{k}": v for k, v in sam.items()},
            **{f"cellpose_{k}": v for k, v in cp.items()},
            "sam_wins_pq": int(float(sam["pq"]) > float(cp["pq"])),
            "delta_pq": float(sam["pq"]) - float(cp["pq"]),
            "delta_aji": float(sam["aji"]) - float(cp["aji"]),
            "delta_f1": float(sam["f1"]) - float(cp["f1"]),
        }
        per_image.append(row_out)

    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in per_image:
        by_source[row["source"]].append(row)

    summary = []
    for source, source_rows in [("ALL", per_image), *sorted(by_source.items())]:
        source_summary = summarize_metrics(source_rows)
        wins = sum(1 for r in source_rows if int(r["sam_wins_pq"]) == 1)
        count = len(source_rows)
        summary.append(
            {
                "source": source,
                "n": count,
                "sam_win_rate": wins / count if count else 0.0,
                "sam_beats_cellpose_by_mean_pq": int(source_summary.get("delta_pq", 0.0) > 0),
                **source_summary,
            }
        )
    _write_csv(out_dir / "per_image.csv", per_image)
    _write_csv(out_dir / "summary_by_source.csv", summary)
    print(f"wrote {out_dir / 'per_image.csv'} and {out_dir / 'summary_by_source.csv'}")


if __name__ == "__main__":
    main()

