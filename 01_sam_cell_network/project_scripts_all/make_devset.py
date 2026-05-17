from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def _read_index(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _image_name(row: dict[str, str]) -> str:
    if "Image_Name" in row:
        return row["Image_Name"]
    if "Image_Path" in row:
        return Path(row["Image_Path"]).name
    raise KeyError(f"Cannot find image name column in {row.keys()}")


def _source(row: dict[str, str]) -> str:
    if "Source" in row:
        return row["Source"]
    if "Source_Dataset" in row:
        return row["Source_Dataset"]
    return _image_name(row).split("_", 1)[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a stratified CellCosmos mini development set")
    parser.add_argument("--index_csv", default="/mnt/d/cell data/CellCosmos_Benchmark/CellCosmos_Core_3500/dataset_index.csv")
    parser.add_argument("--image_root", default="/mnt/d/cell data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/mnt/d/cell data/CellCosmos_Benchmark/masks")
    parser.add_argument("--per_source", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out_csv", default="outputs/dev_eval/devset_25.csv")
    args = parser.parse_args()

    rows = _read_index(Path(args.index_csv))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[_source(row)].append(row)

    rng = random.Random(args.seed)
    out_rows = []
    for source in sorted(grouped):
        candidates = grouped[source][:]
        rng.shuffle(candidates)
        for row in candidates[: args.per_source]:
            name = _image_name(row)
            image_path = Path(args.image_root) / name
            mask_path = Path(args.mask_root) / name
            if image_path.exists() and mask_path.exists():
                out_rows.append({"source": source, "image_path": str(image_path), "mask_path": str(mask_path)})

    out_path = Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "image_path", "mask_path"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"wrote {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

