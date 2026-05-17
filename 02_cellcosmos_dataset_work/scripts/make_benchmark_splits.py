from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def _read_index(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
    parser = argparse.ArgumentParser(description="Create stratified tune/holdout splits for SAM-Cell optimization")
    parser.add_argument("--index_csv", default="/mnt/d/cell data/CellCosmos_Benchmark/CellCosmos_Core_3500/dataset_index.csv")
    parser.add_argument("--image_root", default="/mnt/d/cell data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/mnt/d/cell data/CellCosmos_Benchmark/masks")
    parser.add_argument("--tune_per_source", type=int, default=25)
    parser.add_argument("--holdout_per_source", type=int, default=25)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--out_dir", default="outputs/benchmark_splits")
    args = parser.parse_args()

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_index(Path(args.index_csv)):
        name = _name(row)
        image_path = Path(args.image_root) / name
        mask_path = Path(args.mask_root) / name
        if image_path.exists() and mask_path.exists():
            grouped[_source(row)].append({"source": _source(row), "image_path": str(image_path), "mask_path": str(mask_path)})

    rng = random.Random(args.seed)
    tune = []
    holdout = []
    for source in sorted(grouped):
        rows = grouped[source][:]
        rng.shuffle(rows)
        tune.extend(rows[: args.tune_per_source])
        holdout.extend(rows[args.tune_per_source : args.tune_per_source + args.holdout_per_source])

    out_dir = Path(args.out_dir)
    _write(out_dir / "dev_tune.csv", tune)
    _write(out_dir / "dev_holdout.csv", holdout)
    print(f"wrote {len(tune)} tune and {len(holdout)} holdout rows to {out_dir}")


if __name__ == "__main__":
    main()
