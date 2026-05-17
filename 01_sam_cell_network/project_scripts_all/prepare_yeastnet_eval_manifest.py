from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image
import tifffile


def to_uint8(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        image = image[..., 0]
    image = image.astype(np.float32, copy=False)
    finite = np.isfinite(image)
    if not finite.any():
        return np.zeros(image.shape, dtype=np.uint8)
    lo, hi = np.percentile(image[finite], (0.5, 99.5))
    if hi <= lo:
        lo, hi = float(image[finite].min()), float(image[finite].max())
    if hi <= lo:
        return np.zeros(image.shape, dtype=np.uint8)
    image = np.clip((image - lo) / (hi - lo), 0.0, 1.0)
    return (image * 255.0 + 0.5).astype(np.uint8)


def load_mask(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        mask = np.load(path)
    elif path.suffix.lower() in {".tif", ".tiff"}:
        mask = tifffile.imread(path)
    else:
        mask = np.asarray(Image.open(path))
    if mask.ndim == 3:
        mask = mask[..., 0]
    mask = mask.astype(np.int64, copy=False)
    labels = np.unique(mask)
    labels = labels[labels != 0]
    out = np.zeros(mask.shape, dtype=np.int32)
    for new_label, old_label in enumerate(labels, start=1):
        out[mask == old_label] = new_label
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a standard YeastNet eval manifest for SAM-Cell evaluation.")
    parser.add_argument("--yeastnet_root", default="/mnt/d/cell data/YeastNet")
    parser.add_argument("--out_dir", default="outputs/yeastnet_eval_50_20260504")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    root = Path(args.yeastnet_root)
    out_dir = Path(args.out_dir)
    image_dir = out_dir / "images"
    mask_dir = out_dir / "masks"
    image_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for idx in range(int(args.limit)):
        image_path = root / "Z1" / f"im{idx:03d}.tif"
        mask_path = root / "Masks" / f"mask{idx:03d}.npy"
        if not image_path.exists() or not mask_path.exists():
            continue
        name = f"yeastnet_z1_{idx:03d}"
        out_image = image_dir / f"{name}.png"
        out_mask = mask_dir / f"{name}.tif"
        Image.fromarray(to_uint8(tifffile.imread(image_path))).save(out_image)
        tifffile.imwrite(out_mask, load_mask(mask_path))
        rows.append(
            {
                "source": "yeastnet",
                "image_name": out_image.name,
                "image_path": str(out_image.resolve()),
                "mask_path": str(out_mask.resolve()),
                "split": "yeastnet_eval_50",
            }
        )

    manifest = out_dir / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "image_name", "image_path", "mask_path", "split"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {manifest}")


if __name__ == "__main__":
    main()
