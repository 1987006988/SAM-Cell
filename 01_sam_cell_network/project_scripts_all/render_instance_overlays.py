from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from skimage.segmentation import find_boundaries
import tifffile


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        arr = arr[:, :, :3]
    elif arr.ndim == 3:
        arr = arr[:, :, 0]
    if arr.ndim == 2:
        arr = arr.astype(np.float32, copy=False)
        lo, hi = np.percentile(arr, (1, 99))
        if hi <= lo:
            hi = float(arr.max())
            lo = float(arr.min())
        if hi <= lo:
            arr = np.zeros(arr.shape, dtype=np.uint8)
        else:
            arr = np.clip((arr - lo) / (hi - lo), 0, 1)
            arr = (arr * 255 + 0.5).astype(np.uint8)
        return np.repeat(arr[:, :, None], 3, axis=2)
    if arr.dtype != np.uint8:
        arr = arr.astype(np.float32, copy=False)
        lo, hi = np.percentile(arr, (1, 99))
        arr = np.clip((arr - lo) / max(hi - lo, 1e-6), 0, 1)
        arr = (arr * 255 + 0.5).astype(np.uint8)
    return arr


def _read_image(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        return _to_uint8(tifffile.imread(path))
    return _to_uint8(np.asarray(Image.open(path)))


def _read_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.int32, copy=False)


def _color(label_id: int) -> np.ndarray:
    digest = hashlib.md5(str(label_id).encode("ascii")).digest()
    return np.asarray([digest[0], digest[1], digest[2]], dtype=np.uint8)


def _overlay(image: np.ndarray, labels: np.ndarray, title: str) -> Image.Image:
    out = image.copy().astype(np.float32)
    for label_id in np.unique(labels):
        if int(label_id) == 0:
            continue
        mask = labels == label_id
        color = _color(int(label_id)).astype(np.float32)
        out[mask] = 0.55 * out[mask] + 0.45 * color
    boundaries = find_boundaries(labels, mode="outer")
    out[boundaries] = np.asarray([255, 255, 0], dtype=np.float32)
    pil = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(pil)
    draw.rectangle([0, 0, min(360, pil.width), 24], fill=(0, 0, 0))
    draw.text((6, 5), title, fill=(255, 255, 255))
    return pil


def _tile(panels: list[Image.Image]) -> Image.Image:
    width = max(panel.width for panel in panels)
    height = max(panel.height for panel in panels)
    canvas = Image.new("RGB", (width * len(panels), height), (0, 0, 0))
    for idx, panel in enumerate(panels):
        canvas.paste(panel.convert("RGB"), (idx * width, 0))
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Render prediction and GT overlays for an evaluated label directory.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--pred_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--pred_pattern", default="{stem}_cp_masks.tif")
    parser.add_argument("--method_name", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = _read_rows(Path(args.manifest_csv))
    if args.limit:
        rows = rows[: args.limit]
    pred_dir = Path(args.pred_dir)
    out_dir = Path(args.out_dir)
    pred_overlay_dir = out_dir / "pred"
    gt_overlay_dir = out_dir / "gt"
    compare_dir = out_dir / "compare"
    pred_overlay_dir.mkdir(parents=True, exist_ok=True)
    gt_overlay_dir.mkdir(parents=True, exist_ok=True)
    compare_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        image_name = row.get("image_name") or Path(row["image_path"]).name
        stem = Path(image_name).stem
        pred_path = pred_dir / args.pred_pattern.format(stem=stem)
        if not pred_path.exists():
            raise FileNotFoundError(pred_path)
        image = _read_image(Path(row["image_path"]))
        gt = _read_label(Path(row["mask_path"]))
        pred = _read_label(pred_path)
        original = Image.fromarray(image)
        gt_overlay = _overlay(image, gt, f"GT {stem}")
        pred_overlay = _overlay(image, pred, f"{args.method_name} {stem}")
        gt_overlay.save(gt_overlay_dir / f"{stem}_gt_overlay.png")
        pred_overlay.save(pred_overlay_dir / f"{stem}_{args.method_name}_overlay.png")
        _tile([original, gt_overlay, pred_overlay]).save(compare_dir / f"{stem}_{args.method_name}_compare.png")
    print(f"wrote overlays for {len(rows)} images to {out_dir}")


if __name__ == "__main__":
    main()
