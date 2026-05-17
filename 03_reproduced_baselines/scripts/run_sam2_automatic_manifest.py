from __future__ import annotations

import argparse
import csv
import json
from contextlib import nullcontext
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


def _insert_path(path: str | None) -> None:
    if path and path not in sys.path:
        sys.path.insert(0, path)
    if path:
        config_init = Path(path) / "sam2_configs" / "__init__.py"
        if config_init.parent.exists() and not config_init.exists():
            config_init.write_text("", encoding="utf-8")


def _mask_sort_key(record: dict, mode: str) -> tuple:
    area = int(record.get("area", 0))
    predicted_iou = float(record.get("predicted_iou", 0.0))
    stability = float(record.get("stability_score", 0.0))
    if mode == "area_asc":
        return (-area,)
    if mode == "area_desc":
        return (area,)
    if mode == "score_area_desc":
        return (predicted_iou, stability, area)
    if mode == "score_area_asc":
        return (predicted_iou, stability, -area)
    raise ValueError(f"Unsupported sort mode: {mode}")


def _to_label_map(records: list[dict], shape: tuple[int, int], min_area: int, sort_by: str, max_masks: int | None) -> np.ndarray:
    label = np.zeros(shape, dtype=np.int32)
    kept = 0
    ordered = sorted(records, key=lambda record: _mask_sort_key(record, sort_by), reverse=True)
    for record in ordered:
        mask = np.asarray(record["segmentation"], dtype=bool)
        area = int(mask.sum())
        if area < min_area:
            continue
        fill = mask & (label == 0)
        if int(fill.sum()) < min_area:
            continue
        kept += 1
        label[fill] = kept
        if max_masks is not None and kept >= max_masks:
            break
    return label


def _metadata(records: list[dict]) -> list[dict]:
    output = []
    for idx, record in enumerate(records, start=1):
        item = {"id": idx}
        for key in ["area", "bbox", "predicted_iou", "stability_score", "point_coords", "crop_box"]:
            value = record.get(key)
            if isinstance(value, np.ndarray):
                value = value.tolist()
            item[key] = value
        output.append(item)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run native SAM2 automatic mask generation over a manifest CSV.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--sam2_repo", default="/home/taotao/segment-anything-2")
    parser.add_argument("--checkpoint", default="/home/taotao/segment-anything-2/checkpoints/sam2_hiera_large.pt")
    parser.add_argument("--config", default="sam2_hiera_l.yaml")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--autocast_dtype", default="bfloat16", choices=["none", "float16", "bfloat16"])
    parser.add_argument("--points_per_side", type=int, default=64)
    parser.add_argument("--points_per_batch", type=int, default=128)
    parser.add_argument("--pred_iou_thresh", type=float, default=0.7)
    parser.add_argument("--stability_score_thresh", type=float, default=0.9)
    parser.add_argument("--box_nms_thresh", type=float, default=0.7)
    parser.add_argument("--crop_n_layers", type=int, default=1)
    parser.add_argument("--crop_nms_thresh", type=float, default=0.7)
    parser.add_argument("--crop_n_points_downscale_factor", type=int, default=2)
    parser.add_argument("--min_mask_region_area", type=int, default=10)
    parser.add_argument("--label_min_area", type=int, default=10)
    parser.add_argument("--apply_postprocessing", action="store_true")
    parser.add_argument("--max_masks", type=int)
    parser.add_argument(
        "--sort_by",
        default="score_area_asc",
        choices=["score_area_asc", "score_area_desc", "area_asc", "area_desc"],
    )
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    _insert_path(args.sam2_repo)
    import torch
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
    from sam2.build_sam import build_sam2

    rows = _read_rows(Path(args.manifest_csv), args.limit)
    out_dir = Path(args.out_dir)
    labels_dir = out_dir
    metadata_dir = out_dir / "metadata"
    labels_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    model = build_sam2(args.config, args.checkpoint, device=args.device, apply_postprocessing=args.apply_postprocessing)
    for param in model.parameters():
        param.requires_grad_(False)
    model.eval()
    generator = SAM2AutomaticMaskGenerator(
        model,
        points_per_side=args.points_per_side,
        points_per_batch=args.points_per_batch,
        pred_iou_thresh=args.pred_iou_thresh,
        stability_score_thresh=args.stability_score_thresh,
        box_nms_thresh=args.box_nms_thresh,
        crop_n_layers=args.crop_n_layers,
        crop_nms_thresh=args.crop_nms_thresh,
        crop_n_points_downscale_factor=args.crop_n_points_downscale_factor,
        min_mask_region_area=args.min_mask_region_area,
        output_mode="binary_mask",
    )
    dtype = None
    if args.autocast_dtype == "float16":
        dtype = torch.float16
    elif args.autocast_dtype == "bfloat16":
        dtype = torch.bfloat16
    autocast = torch.autocast(args.device, dtype=dtype) if args.device == "cuda" and dtype is not None else nullcontext()

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        stem = image_path.stem
        print(f"[{idx}/{len(rows)}] SAM2 automatic {image_path.name}")
        image = load_image(image_path, normalize_mode="none")
        with torch.inference_mode(), autocast:
            records = generator.generate(image)
        label = _to_label_map(records, image.shape[:2], args.label_min_area, args.sort_by, args.max_masks)
        tifffile.imwrite(labels_dir / f"{stem}.tif", label.astype(np.int32, copy=False))
        (metadata_dir / f"{stem}.json").write_text(
            json.dumps(_metadata(records), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "manifest_csv": args.manifest_csv,
        "out_dir": str(out_dir),
        "sam2_repo": args.sam2_repo,
        "checkpoint": args.checkpoint,
        "config": args.config,
        "device": args.device,
        "points_per_side": args.points_per_side,
        "points_per_batch": args.points_per_batch,
        "pred_iou_thresh": args.pred_iou_thresh,
        "stability_score_thresh": args.stability_score_thresh,
        "box_nms_thresh": args.box_nms_thresh,
        "crop_n_layers": args.crop_n_layers,
        "crop_nms_thresh": args.crop_nms_thresh,
        "crop_n_points_downscale_factor": args.crop_n_points_downscale_factor,
        "min_mask_region_area": args.min_mask_region_area,
        "label_min_area": args.label_min_area,
        "apply_postprocessing": args.apply_postprocessing,
        "sort_by": args.sort_by,
        "limit": args.limit,
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
