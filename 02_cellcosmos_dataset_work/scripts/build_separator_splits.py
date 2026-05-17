from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def _read_excluded(paths: list[str]) -> set[str]:
    excluded: set[str] = set()
    for item in paths:
        if not item:
            continue
        with Path(item).open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("image_path"):
                    excluded.add(Path(row["image_path"]).name)
                elif row.get("image"):
                    excluded.add(Path(row["image"]).name)
    return excluded


def _parse_quotas(text: str) -> dict[str, int]:
    out = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        key, value = part.split(":", 1)
        out[key.strip()] = int(value)
    return out


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "image_path", "mask_path"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build balanced train/val splits for separator proposal training.")
    parser.add_argument("--image_root", default="/backup/taotao_data/CellCosmos_Benchmark/images")
    parser.add_argument("--mask_root", default="/backup/taotao_data/CellCosmos_Benchmark/masks")
    parser.add_argument("--exclude_csv", nargs="*", default=["outputs/benchmark_splits_large/eval_250_server_paths.csv"])
    parser.add_argument("--train_quotas", default="cellpose:440,dsb2018:500,livecell:500,pannuke:500,tissuenet:500")
    parser.add_argument("--val_quotas", default="cellpose:50,dsb2018:50,livecell:50,pannuke:50,tissuenet:50")
    parser.add_argument("--seed", type=int, default=2050301)
    parser.add_argument("--out_dir", default="outputs/samcell_optimization_20260503_cellpose_v2/separator_splits_v1")
    args = parser.parse_args()

    image_root = Path(args.image_root)
    mask_root = Path(args.mask_root)
    excluded = _read_excluded(args.exclude_csv)
    train_quotas = _parse_quotas(args.train_quotas)
    val_quotas = _parse_quotas(args.val_quotas)

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for image_path in sorted(image_root.glob("*.png")):
        name = image_path.name
        if name in excluded:
            continue
        mask_path = mask_root / name
        if not mask_path.exists():
            continue
        source = name.split("_", 1)[0]
        if source not in train_quotas and source not in val_quotas:
            continue
        grouped[source].append({"source": source, "image_path": str(image_path), "mask_path": str(mask_path)})

    rng = random.Random(args.seed)
    train_rows: list[dict[str, str]] = []
    val_rows: list[dict[str, str]] = []
    manifest = {
        "seed": args.seed,
        "image_root": str(image_root),
        "mask_root": str(mask_root),
        "excluded_count": len(excluded),
        "train_quotas": train_quotas,
        "val_quotas": val_quotas,
        "available_by_source": {},
        "selected_train_by_source": {},
        "selected_val_by_source": {},
    }
    for source in sorted(set(train_quotas) | set(val_quotas)):
        rows = grouped.get(source, [])[:]
        rng.shuffle(rows)
        val_n = min(int(val_quotas.get(source, 0)), len(rows))
        train_n = min(int(train_quotas.get(source, 0)), max(0, len(rows) - val_n))
        val_part = rows[:val_n]
        train_part = rows[val_n : val_n + train_n]
        val_rows.extend(val_part)
        train_rows.extend(train_part)
        manifest["available_by_source"][source] = len(rows)
        manifest["selected_train_by_source"][source] = len(train_part)
        manifest["selected_val_by_source"][source] = len(val_part)

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)
    out_dir = Path(args.out_dir)
    _write_csv(out_dir / "train.csv", train_rows)
    _write_csv(out_dir / "val.csv", val_rows)
    manifest["train_count"] = len(train_rows)
    manifest["val_count"] = len(val_rows)
    manifest["train_source_counts"] = dict(Counter(row["source"] for row in train_rows))
    manifest["val_source_counts"] = dict(Counter(row["source"] for row in val_rows))
    (out_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
