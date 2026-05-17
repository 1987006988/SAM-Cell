from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.proposals.regions import proposals_to_label_map
from scripts.eval_devset import _read_rows, _write_csv
from scripts.proposal_oracle_diagnosis import _filter_rows_by_compare, _oracle_metrics


def _parse_float_list(text: str) -> list[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def _parse_threshold_sets(text: str) -> list[list[float]]:
    return [_parse_float_list(item) for item in text.split(";") if item.strip()]


def _apply_nested_overrides(obj, values: dict) -> dict:
    previous = {}
    for key, value in values.items():
        if "." in key:
            head, tail = key.split(".", 1)
            previous[key] = _apply_nested_overrides(getattr(obj, head), {tail: value})[tail]
            continue
        old = getattr(obj, key)
        previous[key] = deepcopy(old)
        if isinstance(value, dict) and hasattr(old, "__dataclass_fields__"):
            previous[key] = _apply_nested_overrides(old, value)
        else:
            setattr(obj, key, value)
    return previous


def _restore_nested_overrides(obj, values: dict) -> None:
    for key, value in values.items():
        if "." in key:
            head, tail = key.split(".", 1)
            _restore_nested_overrides(getattr(obj, head), {tail: value})
            continue
        current = getattr(obj, key)
        if isinstance(value, dict) and hasattr(current, "__dataclass_fields__"):
            _restore_nested_overrides(current, value)
        else:
            setattr(obj, key, value)


def _set_expert_thresholds(pipeline: SAMCellPipeline, source_name: str, thresholds: list[float]) -> None:
    for expert in pipeline.cfg.semantic_experts:
        expert_source = pipeline._expert_source(expert)
        if expert.name == source_name or expert_source == source_name:
            expert.proposal_thresholds = thresholds


def _summaries(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (
            row["setting_id"],
            row["cellpose_thresholds"],
            row["ranker_threshold"],
            row["duplicate_iou"],
            row["boundary_weight"],
            row["source"],
        )
        grouped[key].append(row)
    output = []
    for key, group in sorted(grouped.items()):
        setting_id, thresholds, ranker_threshold, duplicate_iou, boundary_weight, source = key
        item = {
            "setting_id": setting_id,
            "cellpose_thresholds": thresholds,
            "ranker_threshold": ranker_threshold,
            "duplicate_iou": duplicate_iou,
            "boundary_weight": boundary_weight,
            "source": source,
            "n": len(group),
        }
        item.update(summarize_metrics(group))
        output.append(item)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep SAM-Cell proposal generation parameters using cached semantics.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--devset_csv", default="outputs/benchmark_splits_large/eval_250.csv")
    parser.add_argument("--compare_csv")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--source", default="cellpose")
    parser.add_argument("--worst_k", type=int, default=50)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--expert_source", default="cellpose_style")
    parser.add_argument(
        "--threshold_sets",
        default="0.45,0.5,0.55;0.35,0.45,0.55;0.3,0.4,0.5;0.35,0.5,0.65;0.5",
    )
    parser.add_argument("--ranker_thresholds", default="0.4,0.45,0.5,0.55,0.6")
    parser.add_argument("--duplicate_ious", default="0.7,0.75,0.8")
    parser.add_argument("--boundary_weights", default="0.7")
    parser.add_argument("--include_oracle", action="store_true")
    args = parser.parse_args()

    all_rows = _read_rows(Path(args.devset_csv), args.limit)
    rows = _filter_rows_by_compare(
        all_rows,
        Path(args.compare_csv) if args.compare_csv else None,
        args.source,
        args.worst_k,
    )
    if not rows:
        raise ValueError("No rows selected for proposal parameter sweep")

    threshold_sets = _parse_threshold_sets(args.threshold_sets)
    ranker_thresholds = _parse_float_list(args.ranker_thresholds)
    duplicate_ious = _parse_float_list(args.duplicate_ious)
    boundary_weights = _parse_float_list(args.boundary_weights)
    settings = list(product(threshold_sets, ranker_thresholds, duplicate_ious, boundary_weights))

    cfg = load_config(args.config)
    cfg.sam2.enabled = False
    pipeline = SAMCellPipeline(cfg)
    out_dir = Path(args.out_dir)
    per_image = []

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        source = row.get("source", image_path.stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] proposal param sweep {source} {image_path.name}")
        gt = load_label_map(row["mask_path"])
        previous = _apply_nested_overrides(pipeline.cfg, pipeline.cfg.source_overrides.get(source, {}))
        try:
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            semantic_maps = pipeline._predict_all_semantics(image, image_id=image_path.stem)
            for setting_idx, (thresholds, ranker_threshold, duplicate_iou, boundary_weight) in enumerate(settings):
                _set_expert_thresholds(pipeline, args.expert_source, list(thresholds))
                pipeline.cfg.proposal_ranker.keep_threshold = float(ranker_threshold)
                pipeline.cfg.watershed.proposal_duplicate_iou_threshold = float(duplicate_iou)
                pipeline.cfg.watershed.boundary_suppression_weight = float(boundary_weight)

                *_debug, proposals, _fg_prob_by_source, _combined_fg_mask, _proposal_diag = pipeline._generate_multi_expert_proposals(
                    semantic_maps,
                    image_id=image_path.stem,
                    image=image,
                )
                label_map = proposals_to_label_map(proposals, gt.shape)
                metrics = instance_metrics(label_map, gt)
                oracle = _oracle_metrics(proposals, gt, 0.5) if args.include_oracle else {}
                per_image.append(
                    {
                        "setting_id": setting_idx,
                        "source": source,
                        "image": image_path.name,
                        "cellpose_thresholds": ",".join(f"{item:g}" for item in thresholds),
                        "ranker_threshold": float(ranker_threshold),
                        "duplicate_iou": float(duplicate_iou),
                        "boundary_weight": float(boundary_weight),
                        "proposal_n": len(proposals),
                        **metrics,
                        **{f"oracle_{key}": value for key, value in oracle.items()},
                    }
                )
        finally:
            _restore_nested_overrides(pipeline.cfg, previous)
        _write_csv(out_dir / "per_image.partial.csv", per_image)

    _write_csv(out_dir / "per_image.csv", per_image)
    summary = _summaries(per_image)
    _write_csv(out_dir / "summary_by_setting.csv", summary)
    best = sorted(summary, key=lambda row: float(row.get("pq", 0.0)), reverse=True)[:10]
    _write_csv(out_dir / "top10_by_pq.csv", best)
    print(f"wrote {out_dir / 'summary_by_setting.csv'}")


if __name__ == "__main__":
    main()
