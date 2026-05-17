from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.metrics.instance import instance_metrics, summarize_metrics


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.int32, copy=False)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _prediction_path(pred_dir: Path, stem: str, pattern: str) -> Path:
    return pred_dir / pattern.format(stem=stem)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an instance label directory against a CellCosmos manifest.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--pred_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--pred_pattern", default="{stem}_cp_masks.tif")
    parser.add_argument("--method_name", required=True)
    parser.add_argument("--missing_ok", action="store_true")
    args = parser.parse_args()

    rows = _read_rows(Path(args.manifest_csv))
    pred_dir = Path(args.pred_dir)
    out_dir = Path(args.out_dir)
    per_image = []
    missing = []
    for row in rows:
        image_name = row.get("image_name") or Path(row["image_path"]).name
        stem = Path(image_name).stem
        pred_path = _prediction_path(pred_dir, stem, args.pred_pattern)
        if not pred_path.exists():
            missing.append(str(pred_path))
            if args.missing_ok:
                continue
            raise FileNotFoundError(pred_path)
        gt = _read_label(Path(row["mask_path"]))
        pred = _read_label(pred_path)
        if pred.shape != gt.shape:
            raise ValueError(f"Shape mismatch for {image_name}: pred={pred.shape}, gt={gt.shape}")
        metrics = instance_metrics(pred, gt)
        per_image.append(
            {
                "method": args.method_name,
                "source": row.get("source", stem.split("_", 1)[0]),
                "image": image_name,
                "prediction_path": str(pred_path),
                **metrics,
            }
        )

    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in per_image:
        by_source[row["source"]].append(row)
    summary = []
    for source, source_rows in [("ALL", per_image), *sorted(by_source.items())]:
        source_summary = summarize_metrics(source_rows)
        summary.append({"method": args.method_name, "source": source, "n": len(source_rows), **source_summary})
    source_only = [row for row in summary if row["source"] != "ALL"]
    macro = {}
    for key in ["pq", "aji", "f1", "dice", "binary_iou", "precision", "recall"]:
        values = [float(row[key]) for row in source_only if key in row]
        if values:
            macro[key] = float(np.mean(values))
    summary.append({"method": args.method_name, "source": "SOURCE_MACRO", "n": len(source_only), **macro})

    _write_csv(out_dir / "per_image.csv", per_image)
    _write_csv(out_dir / "summary_by_source.csv", summary)
    (out_dir / "eval_manifest.json").write_text(
        json.dumps(
            {
                "method_name": args.method_name,
                "manifest_csv": args.manifest_csv,
                "pred_dir": args.pred_dir,
                "pred_pattern": args.pred_pattern,
                "evaluated": len(per_image),
                "missing": missing,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"evaluated {len(per_image)} images; wrote {out_dir}")


if __name__ == "__main__":
    main()
