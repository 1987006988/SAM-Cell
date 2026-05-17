#!/usr/bin/env python3
"""Build Chapter 2.6.3 qualitative visualization panel from full inference artifacts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tifffile


DEFAULT_EXPERIMENT_ROOT = Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")
DEFAULT_OUT_DIR = Path("outputs/chapter2_qualitative_2_6_3_20260512")

SAMPLES = [
    {
        "source": "pannuke",
        "image": "pannuke_fold3_1370.png",
        "title": "PanNuke",
        "challenge": "dense H&E nuclei",
    },
    {
        "source": "tissuenet",
        "image": "tissuenet_val_279.png",
        "title": "TissueNet",
        "challenge": "adherent tissue cells",
    },
    {
        "source": "dsb2018",
        "image": "dsb2018_adc315bd40d699fd4e4effbcce81cd7162851007f485d754ad3b0472f73a86df.png",
        "title": "DSB2018",
        "challenge": "low-SNR fluorescence",
    },
    {
        "source": "livecell",
        "image": "livecell_A172_Phase_D7_2_00d04h00m_1.png",
        "title": "LIVECell",
        "challenge": "phase-contrast domain shift",
    },
    {
        "source": "cellpose",
        "image": "cellpose_201.png",
        "title": "Cellpose",
        "challenge": "cell-culture morphology",
    },
]

COLUMN_SPECS = [
    ("image", "Raw image"),
    ("gt", "Ground truth"),
    ("cellpose", "Cellpose cyto3"),
    ("cellsam", "CellSAM"),
    ("samcell", "SAM-Cell"),
]

METHOD_PATHS = {
    "cellpose": ("cellpose_official_cyto3", "predictions", "{stem}_cp_masks.tif"),
    "cellsam": ("cellsam_generalist", "predictions/labels", "{stem}_cellsam.tif"),
    "samcell": ("samcell_refine_final", "labels", "{stem}.tif"),
}

METHOD_METRIC_PATHS = {
    "cellpose": ("cellpose_official_cyto3", "metrics", "per_image.csv"),
    "cellsam": ("cellsam_generalist", "metrics", "per_image.csv"),
    "samcell": ("samcell_refine_final", "", "per_image.csv"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.int32, copy=False)


def read_image(path: Path) -> np.ndarray:
    arr = np.asarray(Image.open(path))
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.shape[-1] > 3:
        arr = arr[..., :3]
    arr = arr.astype(np.float32)
    lo, hi = np.percentile(arr, [1, 99])
    if hi <= lo:
        lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        return np.zeros((*arr.shape[:2], 3), dtype=np.uint8)
    arr = np.clip((arr - lo) / (hi - lo), 0, 1)
    return (arr * 255).astype(np.uint8)


def boundary_mask(label: np.ndarray) -> np.ndarray:
    label = np.asarray(label)
    fg = label > 0
    if not fg.any():
        return fg
    b = np.zeros_like(fg, dtype=bool)
    b[:-1, :] |= label[:-1, :] != label[1:, :]
    b[1:, :] |= label[1:, :] != label[:-1, :]
    b[:, :-1] |= label[:, :-1] != label[:, 1:]
    b[:, 1:] |= label[:, 1:] != label[:, :-1]
    return b & fg


def label_colors(labels: np.ndarray) -> np.ndarray:
    ids = np.unique(labels)
    ids = ids[ids > 0]
    colors = np.zeros((*labels.shape, 3), dtype=np.float32)
    for obj_id in ids:
        rng = np.random.default_rng(int(obj_id) * 104729 + 17)
        color = np.array(
            [
                0.32 + 0.60 * rng.random(),
                0.32 + 0.60 * rng.random(),
                0.32 + 0.60 * rng.random(),
            ],
            dtype=np.float32,
        )
        colors[labels == obj_id] = color
    return colors


def overlay_instances(image: np.ndarray, label: np.ndarray, alpha: float = 0.48) -> np.ndarray:
    base = image.astype(np.float32) / 255.0
    label = np.asarray(label)
    if label.shape != image.shape[:2]:
        label_img = Image.fromarray(label.astype(np.int32), mode="I")
        label = np.asarray(label_img.resize((image.shape[1], image.shape[0]), Image.Resampling.NEAREST))
    fg = label > 0
    colors = label_colors(label)
    out = base.copy()
    out[fg] = (1 - alpha) * out[fg] + alpha * colors[fg]
    boundary = boundary_mask(label)
    out[boundary] = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    return np.clip(out * 255, 0, 255).astype(np.uint8)


def resize_square(arr: np.ndarray, size: int) -> Image.Image:
    img = Image.fromarray(arr)
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (248, 248, 244))
    x = (size - img.width) // 2
    y = (size - img.height) // 2
    canvas.paste(img.convert("RGB"), (x, y))
    return canvas


def metric_value(row: dict[str, str], metric: str) -> float:
    value = row.get(metric)
    if value in (None, ""):
        value = row.get(f"final_{metric}", "")
    return float(value) if value not in (None, "") else float("nan")


def method_pred_path(root: Path, method: str, image_name: str) -> Path:
    subdir, pred_dir, pattern = METHOD_PATHS[method]
    stem = Path(image_name).stem
    return root / subdir / pred_dir / pattern.format(stem=stem)


def metrics_by_image(root: Path) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for method, (subdir, metric_dir, filename) in METHOD_METRIC_PATHS.items():
        path = root / subdir / metric_dir / filename if metric_dir else root / subdir / filename
        out[method] = {row["image"]: row for row in read_csv(path)}
    return out


def find_crop(label: np.ndarray, margin: int = 18) -> tuple[slice, slice]:
    fg = label > 0
    if not fg.any():
        return slice(0, label.shape[0]), slice(0, label.shape[1])
    ys, xs = np.where(fg)
    y0, y1 = max(0, int(ys.min()) - margin), min(label.shape[0], int(ys.max()) + margin)
    x0, x1 = max(0, int(xs.min()) - margin), min(label.shape[1], int(xs.max()) + margin)
    height = max(y1 - y0, 1)
    width = max(x1 - x0, 1)
    side = max(height, width)
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    y0 = max(0, cy - side // 2)
    x0 = max(0, cx - side // 2)
    y1 = min(label.shape[0], y0 + side)
    x1 = min(label.shape[1], x0 + side)
    y0 = max(0, y1 - side)
    x0 = max(0, x1 - side)
    return slice(y0, y1), slice(x0, x1)


def make_panel(root: Path, out_dir: Path, tile_size: int = 220) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {row["image_name"]: row for row in read_csv(root / "manifests" / "full.csv")}
    metrics = metrics_by_image(root)

    gap = 18
    row_label_w = 230
    header_h = 64
    caption_h = 34
    n_rows = len(SAMPLES)
    n_cols = len(COLUMN_SPECS)
    width = row_label_w + n_cols * tile_size + (n_cols + 1) * gap
    height = header_h + n_rows * (tile_size + caption_h) + (n_rows + 1) * gap
    canvas = Image.new("RGB", (width, height), (250, 249, 245))
    draw = ImageDraw.Draw(canvas)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        font_head = ImageFont.truetype("DejaVuSans-Bold.ttf", 17)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 14)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        font_title = font_head = font_body = font_small = ImageFont.load_default()

    draw.text((18, 16), "Qualitative segmentation and error correction across microscopy domains", fill=(35, 35, 35), font=font_title)
    for col, (_key, title) in enumerate(COLUMN_SPECS):
        x = row_label_w + gap + col * (tile_size + gap)
        draw.text((x + 6, header_h - 28), title, fill=(35, 35, 35), font=font_head)

    records: list[dict[str, str | float]] = []
    for row_idx, sample in enumerate(SAMPLES):
        image_name = sample["image"]
        manifest_row = manifest[image_name]
        raw = read_image(Path(manifest_row["image_path"]))
        gt = read_label(Path(manifest_row["mask_path"]))
        crop_y, crop_x = find_crop(gt)
        raw_crop = raw[crop_y, crop_x]
        gt_crop = gt[crop_y, crop_x]

        y = header_h + gap + row_idx * (tile_size + caption_h + gap)
        draw.text((18, y + 14), str(sample["title"]), fill=(30, 30, 30), font=font_head)
        draw.text((18, y + 43), str(sample["challenge"]), fill=(95, 95, 95), font=font_body)
        draw.text((18, y + 72), Path(image_name).stem[:27], fill=(110, 110, 110), font=font_small)

        tiles = {"image": raw_crop, "gt": overlay_instances(raw_crop, gt_crop)}
        metric_text: dict[str, str] = {"image": "", "gt": "manual annotation"}
        for method in ["cellpose", "cellsam", "samcell"]:
            pred = read_label(method_pred_path(root, method, image_name))[crop_y, crop_x]
            tiles[method] = overlay_instances(raw_crop, pred)
            row = metrics[method][image_name]
            metric_text[method] = f"PQ {metric_value(row, 'pq'):.2f}  Dice {metric_value(row, 'dice'):.2f}"
            records.append(
                {
                    "source": sample["source"],
                    "image": image_name,
                    "method": method,
                    "pq": metric_value(row, "pq"),
                    "aji": metric_value(row, "aji"),
                    "dice": metric_value(row, "dice"),
                    "f1": metric_value(row, "f1"),
                }
            )

        for col, (key, _title) in enumerate(COLUMN_SPECS):
            x = row_label_w + gap + col * (tile_size + gap)
            tile = resize_square(tiles[key], tile_size)
            canvas.paste(tile, (x, y))
            draw.rounded_rectangle((x, y, x + tile_size, y + tile_size), radius=5, outline=(216, 216, 210), width=1)
            text = metric_text[key]
            if text:
                tw = draw.textlength(text, font=font_small)
                draw.text((x + (tile_size - tw) / 2, y + tile_size + 9), text, fill=(80, 80, 80), font=font_small)

    out_png = out_dir / "fig_2_13_qualitative_error_correction_panel.png"
    out_pdf = out_dir / "fig_2_13_qualitative_error_correction_panel.pdf"
    canvas.save(out_png)
    canvas.save(out_pdf, "PDF", resolution=300)

    with (out_dir / "fig_2_13_selected_samples.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["source", "image", "method", "f1", "pq", "aji", "dice"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    write_notes(out_dir)
    print(out_png)
    print(out_pdf)


def write_notes(out_dir: Path) -> None:
    notes = """# Chapter 2.6.3 Qualitative Visualization

Recommended figure:

- Fig. 2-13: `fig_2_13_qualitative_error_correction_panel.png/.pdf`

One-line caption:

图 2-13 不同显微成像场景下 Cellpose、CellSAM 与 SAM-Cell 的实例分割可视化对比。

Text replacement:

图 2-13 展示了五类代表性显微图像场景下的定性分割结果，包括 H&E 染色病理图像、组织细胞图像、低信噪比荧光图像、相差显微图像以及常规细胞培养图像。每一行对应一个来源数据集，每一列分别给出原始图像、人工标注、Cellpose cyto3、CellSAM 和 SAM-Cell 的实例掩码叠加结果。可以看到，SAM-Cell 在密集细胞、低对比度边界和跨域成像风格下通常能够保持较连续的实例轮廓，并减少粘连区域中的漏分割和过度扩张现象。该结果从视觉层面说明，语义前景引导、局部区域重构、混合提示和候选筛选机制能够在不微调 SAM2 的条件下提升复杂显微场景中的实例边界质量。
"""
    (out_dir / "section_2_6_3_qualitative_notes.md").write_text(notes, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment_root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--tile_size", type=int, default=220)
    args = parser.parse_args()
    make_panel(args.experiment_root, args.out_dir, args.tile_size)


if __name__ == "__main__":
    main()
