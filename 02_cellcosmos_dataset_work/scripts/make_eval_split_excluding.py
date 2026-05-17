from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def _read_index(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_excluded(paths: list[str]) -> set[str]:
    excluded = set()
    for item in paths:
        if not item:
            continue
        with Path(item).open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                excluded.add(Path(row["image_path"]).name)
    return excluded


def _name(row: dict[str, str]) -> str:
    if "Image_Name" in row:
        return row["Image_Name"]
    return Path(row["Image_Path"]).name


def _source(row: dict[str, str]) -> str:
    return row.get("Source") or row.get("Source_Dataset") or _name(row).split("_", 1)[0]


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "image_path", "mask_path"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a stratified evaluation split excluding existing CSV rows.")
    parser.add_argument("--index_csv", default="/mnt/d/cell data/CellCosmos_Benchmark/CellCosmos_Core_3500/dataset_index.csv")
    parser.add_argument("--image_root", default="/mnt/d/cell data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/mnt/d/cell data/CellCosmos_Benchmark/masks")
    parser.add_argument("--exclude_csv", nargs="*", default=[])
    parser.add_argument("--per_source", type=int, default=50)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--out_csv", default="outputs/benchmark_splits_large/eval.csv")
    args = parser.parse_args()

    excluded = _read_excluded(args.exclude_csv)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_index(Path(args.index_csv)):
        name = _name(row)
        if name in excluded:
            continue
        image_path = Path(args.image_root) / name
        mask_path = Path(args.mask_root) / name
        if image_path.exists() and mask_path.exists():
            source = _source(row)
            grouped[source].append({"source": source, "image_path": str(image_path), "mask_path": str(mask_path)})

    rng = random.Random(args.seed)
    selected = []
    for source in sorted(grouped):
        rows = grouped[source][:]
        rng.shuffle(rows)
        selected.extend(rows[: args.per_source])
    _write(Path(args.out_csv), selected)
    print(f"wrote {len(selected)} rows to {args.out_csv}; excluded {len(excluded)} names")


if __name__ == "__main__":
    main()
