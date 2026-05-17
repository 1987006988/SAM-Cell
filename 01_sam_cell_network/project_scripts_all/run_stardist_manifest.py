from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.io import load_image


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a trained StarDist2D model over a manifest CSV.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--model_name", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--prob_thresh", type=float)
    parser.add_argument("--nms_thresh", type=float)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    from csbdeep.utils import normalize
    from stardist.models import StarDist2D

    rows = _read_rows(Path(args.manifest_csv), args.limit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = StarDist2D(None, name=args.model_name, basedir=args.model_dir)
    metadata = []

    predict_kwargs = {}
    if args.prob_thresh is not None:
        predict_kwargs["prob_thresh"] = args.prob_thresh
    if args.nms_thresh is not None:
        predict_kwargs["nms_thresh"] = args.nms_thresh

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        stem = image_path.stem
        print(f"[{idx}/{len(rows)}] StarDist predict {image_path.name}")
        image = load_image(image_path, normalize_mode="none")
        x = normalize(image, 1, 99.8, axis=(0, 1)).astype(np.float32, copy=False)
        label, details = model.predict_instances(x, **predict_kwargs)
        tifffile.imwrite(out_dir / f"{stem}.tif", label.astype(np.int32, copy=False))
        metadata.append(
            {
                "image": image_path.name,
                "n_instances": int(label.max()),
                "prob_thresh": args.prob_thresh,
                "nms_thresh": args.nms_thresh,
                "points": int(len(details.get("points", []))) if isinstance(details, dict) else None,
            }
        )

    (out_dir / "prediction_manifest.json").write_text(
        json.dumps(
            {
                "manifest_csv": args.manifest_csv,
                "model_dir": args.model_dir,
                "model_name": args.model_name,
                "out_dir": str(out_dir),
                "prob_thresh": args.prob_thresh,
                "nms_thresh": args.nms_thresh,
                "limit": args.limit,
                "images": metadata,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
