from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
import tifffile

from sam_cell.config import load_config
from sam_cell.io import load_image
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.visualize import overlay_instances


SUPPORTED_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp"}


def _iter_images(image: str | None, image_dir: str | None, limit: int | None) -> list[Path]:
    if image:
        return [Path(image)]
    if not image_dir:
        raise ValueError("Either --image or --image_dir is required")
    paths = sorted(p for p in Path(image_dir).iterdir() if p.suffix.lower() in SUPPORTED_EXTS)
    return paths[:limit] if limit else paths


def _save_debug(result: dict, stem: str, debug_dir: Path) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    fg_prob = np.clip(result["fg_prob"] * 255, 0, 255).astype(np.uint8)
    Image.fromarray(fg_prob).save(debug_dir / f"{stem}_fg_prob.png")
    if result.get("boundary_prob") is not None:
        boundary_prob = np.clip(result["boundary_prob"] * 255, 0, 255).astype(np.uint8)
        Image.fromarray(boundary_prob).save(debug_dir / f"{stem}_boundary_prob.png")
    Image.fromarray((result["fg_mask"].astype(np.uint8) * 255)).save(debug_dir / f"{stem}_fg_mask.png")
    tifffile.imwrite(debug_dir / f"{stem}_watershed.tif", result["proposal_label_map"].astype(np.int32))


def run(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    if args.device:
        cfg.runtime.device = args.device
    if args.save_debug:
        cfg.output.save_debug = True

    out_dir = Path(args.out_dir)
    labels_dir = out_dir / "labels"
    overlays_dir = out_dir / "overlays"
    instances_dir = out_dir / "instances"
    labels_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    instances_dir.mkdir(parents=True, exist_ok=True)

    pipeline = SAMCellPipeline(cfg)
    image_paths = _iter_images(args.image, args.image_dir, args.limit)
    for idx, image_path in enumerate(image_paths, start=1):
        print(f"[{idx}/{len(image_paths)}] {image_path}")
        image = load_image(
            image_path,
            normalize_mode=cfg.image.normalize_mode,
            lower_p=cfg.image.lower_percentile,
            upper_p=cfg.image.upper_percentile,
        )
        result = pipeline.infer(image, image_id=image_path.stem)
        stem = image_path.stem
        if cfg.output.save_label_map:
            tifffile.imwrite(labels_dir / f"{stem}.tif", result["instance_map"].astype(np.int32))
        if cfg.output.save_overlay:
            overlay = overlay_instances(image, result["instance_map"])
            Image.fromarray(overlay).save(overlays_dir / f"{stem}.png")
        if cfg.output.save_instance_json:
            with (instances_dir / f"{stem}.json").open("w", encoding="utf-8") as f:
                json.dump(result["instances"], f, ensure_ascii=False, indent=2)
        if cfg.output.save_debug:
            _save_debug(result, stem, out_dir / "debug")
        print(f"  proposals={len(result['proposals'])} refined={len(result['refined_instances'])} final={int(result['instance_map'].max())}")


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SAM-Cell inference")
    parser.add_argument("--config", default="configs/sam_cell_default.yaml")
    parser.add_argument("--image")
    parser.add_argument("--image_dir")
    parser.add_argument("--out_dir", default="outputs/sam_cell")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--device", choices=["cuda", "cpu"])
    parser.add_argument("--save_debug", action="store_true")
    return parser


def main() -> None:
    run(build_argparser().parse_args())


if __name__ == "__main__":
    main()
