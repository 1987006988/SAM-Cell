from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    lo, hi = np.percentile(arr, (1, 99))
    if hi <= lo:
        lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint8)
    arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    return (arr * 255.0 + 0.5).astype(np.uint8)


def _read_image(path: Path, grayscale_mode: str) -> np.ndarray:
    arr = np.asarray(Image.open(path))
    if arr.ndim == 2:
        ch = _normalize_to_uint8(arr) if arr.dtype != np.uint8 else arr
        if grayscale_mode == "repeat":
            return np.repeat(ch[:, :, None], 3, axis=2)
        out = np.zeros((*ch.shape, 3), dtype=np.uint8)
        channel = {"red": 0, "green": 1, "blue": 2}[grayscale_mode]
        out[:, :, channel] = ch
        return out
    if arr.ndim != 3:
        raise ValueError(f"Unsupported image shape for {path}: {arr.shape}")
    if arr.shape[2] == 1:
        return _read_image(path, grayscale_mode)
    if arr.shape[2] >= 4:
        arr = arr[:, :, :3]
    if arr.shape[2] != 3:
        raise ValueError(f"Expected 3 image channels after conversion for {path}, got {arr.shape}")
    if arr.dtype == np.uint8:
        return np.ascontiguousarray(arr)
    channels = [_normalize_to_uint8(arr[:, :, c]) for c in range(3)]
    return np.ascontiguousarray(np.stack(channels, axis=2))


def _stem(row: dict[str, str]) -> str:
    image_name = row.get("image_name") or Path(row["image_path"]).name
    return Path(image_name).stem


def _empty_labels_for_image(image: np.ndarray) -> np.ndarray:
    if image.ndim < 2:
        raise ValueError(f"Expected at least 2D image for empty CellSAM label map, got {image.shape}")
    return np.zeros(image.shape[:2], dtype=np.int32)


def _is_blank_image(image: np.ndarray) -> bool:
    arr = np.asarray(image)
    if arr.size == 0:
        return True
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return True
    return float(finite.max()) <= float(finite.min())


def _is_empty_prediction_failure(exc: BaseException) -> bool:
    text = str(exc)
    return ("NoneType" in text) or ("not a sequence" in text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official CellSAM inference on a manifest CSV.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--suffix", default="_cellsam.tif")
    parser.add_argument("--bbox_threshold", type=float, default=0.4)
    parser.add_argument("--use_wsi", action="store_true")
    parser.add_argument("--low_contrast_enhancement", action="store_true")
    parser.add_argument("--gauge_cell_size", action="store_true")
    parser.add_argument("--block_size", type=int, default=400)
    parser.add_argument("--overlap", type=int, default=56)
    parser.add_argument("--iou_depth", type=int, default=56)
    parser.add_argument("--iou_threshold", type=float, default=0.5)
    parser.add_argument("--chunks", type=int, default=256)
    parser.add_argument("--model_path")
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--grayscale_mode", choices=["repeat", "red", "green", "blue"], default="repeat")
    args = parser.parse_args()

    from cellSAM import cellsam_pipeline

    rows = _read_rows(Path(args.manifest_csv), args.limit)
    out_dir = Path(args.out_dir)
    label_dir = out_dir / "labels"
    label_dir.mkdir(parents=True, exist_ok=True)
    records = []
    started = time.time()
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        stem = _stem(row)
        pred_path = label_dir / f"{stem}{args.suffix}"
        print(f"[{idx}/{len(rows)}] CellSAM {image_path.name}", flush=True)
        if args.skip_existing and pred_path.exists():
            records.append({"image": image_path.name, "prediction_path": str(pred_path), "status": "skipped"})
            continue
        image = _read_image(image_path, args.grayscale_mode)
        status = "done"
        if _is_blank_image(image):
            labels = _empty_labels_for_image(image)
            status = "empty_from_blank_image"
            tifffile.imwrite(pred_path, labels.astype(np.int32, copy=False))
            records.append({"image": image_path.name, "prediction_path": str(pred_path), "status": status})
            print(f"  blank image; wrote empty label map for {image_path.name}", flush=True)
            continue
        try:
            labels = cellsam_pipeline(
                image,
                chunks=int(args.chunks),
                model_path=args.model_path,
                bbox_threshold=float(args.bbox_threshold),
                low_contrast_enhancement=bool(args.low_contrast_enhancement),
                use_wsi=bool(args.use_wsi),
                gauge_cell_size=bool(args.gauge_cell_size),
                block_size=int(args.block_size),
                overlap=int(args.overlap),
                iou_depth=int(args.iou_depth),
                iou_threshold=float(args.iou_threshold),
            )
        except (AttributeError, TypeError) as exc:
            if not _is_empty_prediction_failure(exc):
                raise
            labels = _empty_labels_for_image(image)
            status = "empty_from_cellsam_none"
            print(f"  CellSAM failed with empty-output error; wrote empty label map for {image_path.name}", flush=True)
        if labels is None:
            labels = _empty_labels_for_image(image)
            status = "empty_from_cellsam_none"
            print(f"  CellSAM returned None; wrote empty label map for {image_path.name}", flush=True)
        tifffile.imwrite(pred_path, np.asarray(labels).astype(np.int32, copy=False))
        records.append({"image": image_path.name, "prediction_path": str(pred_path), "status": status})

    manifest = {
        "manifest_csv": args.manifest_csv,
        "out_dir": str(out_dir),
        "n_images": len(rows),
        "suffix": args.suffix,
        "bbox_threshold": args.bbox_threshold,
        "use_wsi": args.use_wsi,
        "low_contrast_enhancement": args.low_contrast_enhancement,
        "gauge_cell_size": args.gauge_cell_size,
        "grayscale_mode": args.grayscale_mode,
        "elapsed_sec": time.time() - started,
        "records": records,
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote labels to {label_dir}")


if __name__ == "__main__":
    main()
