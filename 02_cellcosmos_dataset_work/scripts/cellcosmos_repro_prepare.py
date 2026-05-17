from __future__ import annotations

import argparse
import csv
import json
import os
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["source", "image_name", "image_path", "mask_path", "split"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _source(row: dict[str, str]) -> str:
    return (row.get("Source") or row.get("source") or row["Image_Name"].split("_", 1)[0]).lower()


def _record(row: dict[str, str], image_root: Path, mask_root: Path, split: str) -> dict[str, str]:
    image_name = row["Image_Name"]
    return {
        "source": _source(row),
        "image_name": image_name,
        "image_path": str(image_root / image_name),
        "mask_path": str(mask_root / image_name),
        "split": split,
    }


def _stratified_split(rows: list[dict[str, str]], train_fraction: float, seed: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[_source(row)].append(row)
    rng = random.Random(seed)
    train: list[dict[str, str]] = []
    val: list[dict[str, str]] = []
    for source in sorted(grouped):
        source_rows = grouped[source][:]
        rng.shuffle(source_rows)
        n_train = int(len(source_rows) * train_fraction)
        train.extend(source_rows[:n_train])
        val.extend(source_rows[n_train:])
    train.sort(key=lambda r: (_source(r), r["Image_Name"]))
    val.sort(key=lambda r: (_source(r), r["Image_Name"]))
    return train, val


def _load_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.int32, copy=False)


def _link_or_copy(src: Path, dst: Path, overwrite: bool) -> None:
    if dst.exists() or dst.is_symlink():
        if not overwrite:
            return
        dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _write_cellpose_split(split_name: str, rows: list[dict[str, str]], out_dir: Path, overwrite: bool) -> None:
    split_dir = out_dir / split_name
    split_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        image_path = Path(row["image_path"])
        mask_path = Path(row["mask_path"])
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        if not mask_path.exists():
            raise FileNotFoundError(mask_path)
        stem = image_path.stem
        image_out = split_dir / image_path.name
        mask_out = split_dir / f"{stem}_masks.tif"
        _link_or_copy(image_path, image_out, overwrite=overwrite)
        if mask_out.exists() and not overwrite:
            continue
        tifffile.imwrite(mask_out, _load_label(mask_path), compression="zlib")


def _summaries(splits: dict[str, list[dict[str, str]]]) -> dict[str, dict[str, int]]:
    return {name: dict(Counter(row["source"] for row in rows)) for name, rows in splits.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare CellCosmos Core3500 reproducibility splits and Cellpose-format data.")
    parser.add_argument("--index_csv", default="/mnt/d/cell data/CellCosmos_Benchmark/CellCosmos_Core_3500/dataset_index.csv")
    parser.add_argument("--image_root", default="/backup/taotao_data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/backup/taotao_data/CellCosmos_Benchmark/masks")
    parser.add_argument("--out_root", default="/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train_fraction", type=float, default=0.8)
    parser.add_argument("--overwrite_data", action="store_true")
    args = parser.parse_args()

    index_csv = Path(args.index_csv)
    image_root = Path(args.image_root)
    mask_root = Path(args.mask_root)
    out_root = Path(args.out_root)
    manifests_dir = out_root / "manifests"
    cellpose_dir = out_root / "data" / "cellpose"
    rows = _read_rows(index_csv)
    rows = [row for row in rows if Path(row["Image_Name"]).suffix.lower() in IMAGE_EXTS]

    all_records = [_record(row, image_root, mask_root, "core3500_all") for row in rows]
    iid_train_raw, iid_val_raw = _stratified_split(rows, args.train_fraction, args.seed)
    pannuke_raw = [row for row in rows if _source(row) == "pannuke"]
    pannuke_train_raw, pannuke_test_raw = _stratified_split(pannuke_raw, args.train_fraction, args.seed)
    far_ood_raw = [row for row in rows if _source(row) != "pannuke"]

    splits = {
        "core3500_all": all_records,
        "iid_train": [_record(row, image_root, mask_root, "iid_train") for row in iid_train_raw],
        "iid_val": [_record(row, image_root, mask_root, "iid_val") for row in iid_val_raw],
        "pannuke_train": [_record(row, image_root, mask_root, "pannuke_train") for row in pannuke_train_raw],
        "pannuke_core_test": [_record(row, image_root, mask_root, "pannuke_core_test") for row in pannuke_test_raw],
        "far_ood_test": [_record(row, image_root, mask_root, "far_ood_test") for row in far_ood_raw],
    }

    for split_name, split_rows in splits.items():
        _write_rows(manifests_dir / f"{split_name}.csv", split_rows)
        _write_cellpose_split(split_name, split_rows, cellpose_dir, overwrite=args.overwrite_data)

    payload = {
        "index_csv": str(index_csv),
        "image_root": str(image_root),
        "mask_root": str(mask_root),
        "seed": args.seed,
        "train_fraction": args.train_fraction,
        "n_rows": len(rows),
        "splits": {name: len(split_rows) for name, split_rows in splits.items()},
        "source_counts": _summaries(splits),
    }
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / "split_summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
