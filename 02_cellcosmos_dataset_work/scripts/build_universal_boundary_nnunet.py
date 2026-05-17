from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.morphology import binary_dilation, disk
from skimage.segmentation import find_boundaries, relabel_sequential
import tifffile


IMAGE_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg"}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _name(row: dict[str, str]) -> str:
    if "Image_Name" in row:
        return row["Image_Name"]
    if "image_path" in row:
        return Path(row["image_path"]).name
    if "Image_Path" in row:
        return Path(row["Image_Path"]).name
    return ""


def _excluded_names(paths: list[str]) -> set[str]:
    excluded = set()
    for item in paths:
        if not item:
            continue
        path = Path(item)
        if not path.exists():
            continue
        for row in _read_rows(path):
            name = _name(row)
            if name:
                excluded.add(name)
    return excluded


def _source_from_name(name: str) -> str:
    return name.split("_", 1)[0].lower()


def _safe_id(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()


def _parse_source_quotas(values: list[str]) -> dict[str, int]:
    quotas = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected source=n, got {item}")
        key, value = item.split("=", 1)
        quotas[key.lower()] = int(value)
    return quotas


def _load_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    elif path.suffix.lower() == ".npy":
        arr = np.load(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    arr = relabel_sequential(arr.astype(np.int64, copy=False))[0]
    return arr.astype(np.int32, copy=False)


def _to_uint8(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        image = image[..., 0]
    image = image.astype(np.float32, copy=False)
    finite = np.isfinite(image)
    if not finite.any():
        return np.zeros(image.shape, dtype=np.uint8)
    lo, hi = np.percentile(image[finite], (0.5, 99.5))
    if hi <= lo:
        hi = float(image[finite].max())
        lo = float(image[finite].min())
    if hi <= lo:
        return np.zeros(image.shape, dtype=np.uint8)
    image = np.clip((image - lo) / (hi - lo), 0.0, 1.0)
    return (image * 255.0 + 0.5).astype(np.uint8)


def _copy_image(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in {".tif", ".tiff"}:
        Image.fromarray(_to_uint8(tifffile.imread(src))).save(dst)
    else:
        Image.open(src).convert("L").save(dst)


def _write_uint8_image(arr: np.ndarray, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(_to_uint8(arr)).save(dst)


def _make_boundary_label(instance_map: np.ndarray, boundary_radius: int) -> np.ndarray:
    foreground = instance_map > 0
    boundary = find_boundaries(instance_map, mode="inner")
    if boundary_radius > 0:
        boundary = binary_dilation(boundary, footprint=disk(boundary_radius)) & foreground
    label = np.zeros(instance_map.shape, dtype=np.uint8)
    label[foreground & ~boundary] = 1
    label[boundary] = 2
    return label


def _write_label(instance_path: Path, label_out: Path, boundary_radius: int) -> None:
    instance_map = _load_label(instance_path)
    label = _make_boundary_label(instance_map, boundary_radius)
    Image.fromarray(label).save(label_out)


def _cellcosmos_records(image_root: Path, mask_root: Path, excluded: set[str]) -> list[dict[str, str]]:
    images = {p.name: p for p in image_root.iterdir() if p.suffix.lower() in IMAGE_EXTS}
    masks = {p.name: p for p in mask_root.iterdir() if p.suffix.lower() in IMAGE_EXTS}
    records = []
    for name in sorted(set(images) & set(masks)):
        if name in excluded:
            continue
        source = _source_from_name(name)
        records.append(
            {
                "source": source,
                "target_type": "whole_cell" if source in {"cellpose", "livecell", "tissuenet"} else "nucleus",
                "modality": {
                    "cellpose": "mixed_microscopy",
                    "livecell": "phase_contrast",
                    "tissuenet": "multiplex_tissue",
                    "pannuke": "histology",
                    "dsb2018": "fluorescence_mixed",
                }.get(source, "unknown"),
                "image_name": name,
                "image_path": str(images[name]),
                "mask_path": str(masks[name]),
            }
        )
    return records


def _yeastnet_records(root: Path, limit: int | None) -> list[dict[str, str]]:
    if not root.exists():
        return []
    records = []
    for idx in range(50):
        image_path = root / "Z1" / f"im{idx:03d}.tif"
        mask_path = root / "Masks" / f"mask{idx:03d}.npy"
        if not image_path.exists() or not mask_path.exists():
            continue
        records.append(
            {
                "source": "yeastnet",
                "target_type": "yeast",
                "modality": "fluorescence_yeast",
                "image_name": f"yeastnet_z1_{idx:03d}.png",
                "image_path": str(image_path),
                "mask_path": str(mask_path),
            }
        )
    return records[:limit] if limit is not None else records


def _sample_records(records: list[dict[str, str]], quotas: dict[str, int], seed: int) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        grouped[record["source"]].append(record)
    rng = random.Random(seed)
    sampled = []
    for source in sorted(grouped):
        source_records = grouped[source][:]
        rng.shuffle(source_records)
        quota = quotas.get(source, len(source_records))
        sampled.extend(source_records[:quota])
    sampled.sort(key=lambda r: (r["source"], r["image_name"]))
    return sampled


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a source-balanced universal boundary/interior nnU-Net dataset.")
    parser.add_argument("--image_root", default="/mnt/d/cell data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/mnt/d/cell data/CellCosmos_Benchmark/masks")
    parser.add_argument("--yeastnet_root", default="/mnt/d/cell data/YeastNet")
    parser.add_argument("--include_yeastnet", action="store_true")
    parser.add_argument("--yeastnet_limit", type=int, default=50)
    parser.add_argument("--nnunet_raw", default="/home/taotao/nnUNet/nnUNetFrame/nnUNet_raw")
    parser.add_argument("--dataset_id", type=int, default=621)
    parser.add_argument("--dataset_name", default="SAMCellUniversalBoundary")
    parser.add_argument("--exclude_csv", nargs="*", default=["outputs/benchmark_splits_large/eval_250.csv"])
    parser.add_argument("--boundary_radius", type=int, default=1)
    parser.add_argument("--source_quota", nargs="*", default=["cellpose=500", "dsb2018=500", "livecell=500", "pannuke=500", "tissuenet=500", "yeastnet=50"])
    parser.add_argument("--seed", type=int, default=621)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.nnunet_raw) / f"Dataset{args.dataset_id:03d}_{args.dataset_name}"
    if dataset_dir.exists() and args.overwrite:
        shutil.rmtree(dataset_dir)
    images_tr = dataset_dir / "imagesTr"
    labels_tr = dataset_dir / "labelsTr"
    images_tr.mkdir(parents=True, exist_ok=True)
    labels_tr.mkdir(parents=True, exist_ok=True)

    excluded = _excluded_names(args.exclude_csv)
    quotas = _parse_source_quotas(args.source_quota)
    records = _cellcosmos_records(Path(args.image_root), Path(args.mask_root), excluded)
    if args.include_yeastnet:
        records.extend(_yeastnet_records(Path(args.yeastnet_root), args.yeastnet_limit))
    source_available = Counter(r["source"] for r in records)
    records = _sample_records(records, quotas, args.seed)

    mapping_rows = []
    for idx, record in enumerate(records):
        source = _safe_id(record["source"])
        case_id = f"universal_{idx:04d}_{source}"
        image_out = images_tr / f"{case_id}_0000.png"
        label_out = labels_tr / f"{case_id}.png"
        image_path = Path(record["image_path"])
        if image_path.suffix.lower() in {".tif", ".tiff"}:
            _write_uint8_image(tifffile.imread(image_path), image_out)
        else:
            _copy_image(image_path, image_out)
        _write_label(Path(record["mask_path"]), label_out, args.boundary_radius)
        mapping_rows.append(
            {
                "case_id": case_id,
                "source": record["source"],
                "target_type": record["target_type"],
                "modality": record["modality"],
                "image_name": record["image_name"],
                "image_path": record["image_path"],
                "mask_path": record["mask_path"],
            }
        )

    dataset_json = {
        "channel_names": {"0": "CellImage"},
        "labels": {
            "background": 0,
            "cell_interior": 1,
            "cell_boundary": 2,
        },
        "numTraining": len(mapping_rows),
        "file_ending": ".png",
        "overwrite_image_reader_writer": "NaturalImage2DIO",
    }
    with (dataset_dir / "dataset.json").open("w", encoding="utf-8") as f:
        json.dump(dataset_json, f, ensure_ascii=False, indent=2)
    with (dataset_dir / "case_mapping.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["case_id", "source", "target_type", "modality", "image_name", "image_path", "mask_path"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping_rows)

    source_written = Counter(row["source"] for row in mapping_rows)
    print(f"wrote {len(mapping_rows)} cases to {dataset_dir}")
    print(f"excluded {len(excluded)} names")
    print(f"source_available={dict(source_available)}")
    print(f"source_written={dict(source_written)}")
    print(f"quotas={quotas}")


if __name__ == "__main__":
    main()
