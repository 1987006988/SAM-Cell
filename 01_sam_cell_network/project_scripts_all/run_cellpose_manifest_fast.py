from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
import tifffile


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _read_image(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3 and arr.shape[-1] >= 4:
        arr = arr[..., :3]
    return np.ascontiguousarray(arr)


def _stem(row: dict[str, str]) -> str:
    image_name = row.get("image_name") or Path(row["image_path"]).name
    return Path(image_name).stem


def _as_mask(result):
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, list):
        if len(result) != 1:
            raise ValueError(f"Expected one Cellpose mask, got {len(result)}")
        result = result[0]
    arr = np.asarray(result)
    if arr.ndim == 3:
        arr = arr[..., 0]
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D Cellpose mask, got shape {arr.shape}")
    return arr.astype(np.int32, copy=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cellpose inference with one persistent model over a manifest.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--pretrained_model", default="cyto3")
    parser.add_argument("--diameter", type=float, default=0.0)
    parser.add_argument("--chan", type=int, default=0)
    parser.add_argument("--chan2", type=int, default=0)
    parser.add_argument("--gpu_device", default="0")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--suffix", default="_cp_masks.tif")
    args = parser.parse_args()

    # Cellpose's Python API does not expose the CLI's gpu_device argument directly.
    # Use CUDA_VISIBLE_DEVICES before torch/cellpose import so gpu=True maps to the selected card.
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", str(args.gpu_device))
    from cellpose import models

    rows = _read_rows(Path(args.manifest_csv), args.limit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    model = models.CellposeModel(gpu=True, pretrained_model=args.pretrained_model)
    channels = [int(args.chan), int(args.chan2)]
    completed = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        pred_path = out_dir / f"{_stem(row)}{args.suffix}"
        if pred_path.exists() and (args.skip_existing or not args.overwrite):
            print(f"[{idx}/{len(rows)}] cached {pred_path.name}", flush=True)
            completed.append({"image": image_path.name, "prediction_path": str(pred_path), "status": "skipped"})
            continue
        print(f"[{idx}/{len(rows)}] cellpose-fast {image_path.name}", flush=True)
        image = _read_image(image_path)
        diameter = None if float(args.diameter) == 0.0 else float(args.diameter)
        result = model.eval(
            image,
            channels=channels,
            diameter=diameter,
            batch_size=int(args.batch_size),
        )
        mask = _as_mask(result)
        tifffile.imwrite(pred_path, mask)
        completed.append({"image": image_path.name, "prediction_path": str(pred_path), "status": "done"})

    manifest = {
        "manifest_csv": args.manifest_csv,
        "out_dir": str(out_dir),
        "pretrained_model": args.pretrained_model,
        "diameter": args.diameter,
        "channels": channels,
        "gpu_device": args.gpu_device,
        "batch_size": args.batch_size,
        "n_images": len(rows),
        "elapsed_sec": time.time() - started,
        "python": sys.executable,
        "outputs": completed,
    }
    (out_dir / "inference_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
