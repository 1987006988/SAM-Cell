from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image
from sam_cell.pipeline import SAMCellPipeline


def _read_rows(paths: list[str], limit: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _cache_exists(pipeline: SAMCellPipeline, image_id: str, source: str) -> bool:
    for expert in pipeline._active_semantic_experts(image_id):
        cache_dir = expert.prob_cache_dir
        if not cache_dir:
            return False
        use_npz = expert.boundary_class_index is not None
        path = Path(cache_dir) / (f"{image_id}.npz" if use_npz else f"{image_id}.npy")
        if not path.exists():
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate SAM-Cell nnU-Net semantic caches for CSV rows.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--csv", nargs="+", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--out_manifest", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    pipeline = SAMCellPipeline(cfg)
    rows = _read_rows(args.csv, args.limit)
    counts = Counter()
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        image_id = image_path.stem
        source = row.get("source", image_id.split("_", 1)[0])
        if args.skip_existing and _cache_exists(pipeline, image_id, source):
            counts["skipped"] += 1
            continue
        print(f"[{idx}/{len(rows)}] cache {source} {image_path.name}", flush=True)
        image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
        pipeline._predict_all_semantics(image, image_id=image_id)
        counts["cached"] += 1
        counts[f"source_{source}"] += 1

    manifest = {"rows": len(rows), **dict(counts)}
    out_manifest = Path(args.out_manifest) if args.out_manifest else Path(args.csv[0]).parent / "semantic_cache_manifest.json"
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
