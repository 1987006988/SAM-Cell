from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from skimage.morphology import binary_dilation, disk
from skimage.segmentation import find_boundaries, relabel_sequential
import tifffile
from PIL import Image


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _name(row: dict[str, str]) -> str:
    if "Image_Name" in row:
        return row["Image_Name"]
    if "image_path" in row:
        return Path(row["image_path"]).name
    return Path(row["Image_Path"]).name


def _source(row: dict[str, str]) -> str:
    return row.get("Source") or row.get("Source_Dataset") or row.get("source") or _name(row).split("_", 1)[0]


def _excluded_names(paths: list[str]) -> set[str]:
    excluded = set()
    for item in paths:
        if not item:
            continue
        for row in _read_rows(Path(item)):
            excluded.add(_name(row))
    return excluded


def _load_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    arr = relabel_sequential(arr.astype(np.int64, copy=False))[0]
    return arr.astype(np.int32, copy=False)


def _copy_image(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("L").save(dst)


def _make_boundary_label(instance_map: np.ndarray, boundary_radius: int) -> np.ndarray:
    foreground = instance_map > 0
    boundary = find_boundaries(instance_map, mode="inner")
    if boundary_radius > 0:
        boundary = binary_dilation(boundary, footprint=disk(boundary_radius)) & foreground
    label = np.zeros(instance_map.shape, dtype=np.uint8)
    label[foreground & ~boundary] = 1
    label[boundary] = 2
    return label


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a multi-source CellCosmos boundary/interior nnU-Net dataset.")
    parser.add_argument("--index_csv", default="/mnt/d/cell data/CellCosmos_Benchmark/CellCosmos_Core_3500/dataset_index.csv")
    parser.add_argument("--image_root", default="/mnt/d/cell data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/mnt/d/cell data/CellCosmos_Benchmark/masks")
    parser.add_argument("--nnunet_raw", default="/home/taotao/nnUNet/nnUNetFrame/nnUNet_raw")
    parser.add_argument("--dataset_id", type=int, default=620)
    parser.add_argument("--dataset_name", default="CellCosmosBoundary")
    parser.add_argument("--exclude_csv", nargs="*", default=["outputs/benchmark_splits_large/eval_250.csv"])
    parser.add_argument("--boundary_radius", type=int, default=1)
    parser.add_argument("--limit_per_source", type=int)
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
    source_seen: Counter[str] = Counter()
    source_written: Counter[str] = Counter()
    mapping_rows = []
    index_rows = _read_rows(Path(args.index_csv))
    for row in index_rows:
        name = _name(row)
        if name in excluded:
            continue
        source = _source(row)
        source_seen[source] += 1
        if args.limit_per_source is not None and source_written[source] >= args.limit_per_source:
            continue
        image_path = Path(args.image_root) / name
        mask_path = Path(args.mask_root) / name
        if not image_path.exists() or not mask_path.exists():
            continue
        case_id = f"cellcosmos_{len(mapping_rows):04d}_{source}"
        image_out = images_tr / f"{case_id}_0000.png"
        label_out = labels_tr / f"{case_id}.png"
        _copy_image(image_path, image_out)
        instance_map = _load_label(mask_path)
        label = _make_boundary_label(instance_map, args.boundary_radius)
        Image.fromarray(label).save(label_out)
        source_written[source] += 1
        mapping_rows.append(
            {
                "case_id": case_id,
                "source": source,
                "image_name": name,
                "image_path": str(image_path),
                "mask_path": str(mask_path),
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
        writer = csv.DictWriter(f, fieldnames=["case_id", "source", "image_name", "image_path", "mask_path"])
        writer.writeheader()
        writer.writerows(mapping_rows)

    print(f"wrote {len(mapping_rows)} cases to {dataset_dir}")
    print(f"excluded {len(excluded)} names")
    print(f"source_seen={dict(source_seen)}")
    print(f"source_written={dict(source_written)}")


if __name__ == "__main__":
    main()
