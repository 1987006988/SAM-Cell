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


SETTING_FIELDS = [
    "setting_id",
    "source",
    "cellpose_thresholds",
    "marker_method",
    "h_maxima_values",
    "min_distance_factor",
    "peak_threshold_rel",
    "ranker_threshold",
    "duplicate_iou",
    "boundary_weight",
    "boundary_additive_weight",
    "share_boundary",
    "selector_iou",
    "selector_containment",
    "selector_center_factor",
    "selector_margin",
    "marker_rescue_enabled",
    "marker_rescue_area_factor",
    "marker_rescue_min_distance_factor",
    "marker_rescue_peak_threshold_rel",
    "split_enabled",
    "split_keep_parent",
    "split_min_area_factor",
    "split_min_area_absolute",
    "split_max_compactness",
    "split_min_child_area_fraction",
    "split_min_child_mean_fg_prob",
    "split_min_child_parent_fg_delta",
    "split_min_child_compactness",
]


def _parse_float_list(text: str) -> list[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def _parse_int_list(text: str) -> list[int]:
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def _parse_str_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def _parse_bool_list(text: str) -> list[bool]:
    output = []
    for item in _parse_str_list(text):
        normalized = item.lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            output.append(True)
        elif normalized in {"0", "false", "no", "n", "off"}:
            output.append(False)
        else:
            raise argparse.ArgumentTypeError(f"Expected bool list item, got {item!r}")
    return output


def _parse_threshold_sets(text: str) -> list[list[float]]:
    return [_parse_float_list(item) for item in text.split(";") if item.strip()]


def _format_float_list(values: list[float]) -> str:
    return ",".join(f"{item:g}" for item in values)


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


def _setting_dict(setting_id: int, values: tuple) -> dict:
    (
        thresholds,
        marker_method,
        h_values,
        min_distance_factor,
        peak_threshold_rel,
        ranker_threshold,
        duplicate_iou,
        boundary_weight,
        boundary_additive_weight,
        share_boundary,
        selector_iou,
        selector_containment,
        selector_center_factor,
        selector_margin,
        marker_rescue_enabled,
        marker_rescue_area_factor,
        marker_rescue_min_distance_factor,
        marker_rescue_peak_threshold_rel,
        split_enabled,
        split_keep_parent,
        split_min_area_factor,
        split_min_area_absolute,
        split_max_compactness,
        split_min_child_area_fraction,
        split_min_child_mean_fg_prob,
        split_min_child_parent_fg_delta,
        split_min_child_compactness,
    ) = values
    return {
        "setting_id": setting_id,
        "cellpose_thresholds": _format_float_list(thresholds),
        "marker_method": marker_method,
        "h_maxima_values": _format_float_list(h_values),
        "min_distance_factor": float(min_distance_factor),
        "peak_threshold_rel": float(peak_threshold_rel),
        "ranker_threshold": float(ranker_threshold),
        "duplicate_iou": float(duplicate_iou),
        "boundary_weight": float(boundary_weight),
        "boundary_additive_weight": float(boundary_additive_weight),
        "share_boundary": bool(share_boundary),
        "selector_iou": float(selector_iou),
        "selector_containment": float(selector_containment),
        "selector_center_factor": float(selector_center_factor),
        "selector_margin": float(selector_margin),
        "marker_rescue_enabled": bool(marker_rescue_enabled),
        "marker_rescue_area_factor": float(marker_rescue_area_factor),
        "marker_rescue_min_distance_factor": float(marker_rescue_min_distance_factor),
        "marker_rescue_peak_threshold_rel": float(marker_rescue_peak_threshold_rel),
        "split_enabled": bool(split_enabled),
        "split_keep_parent": bool(split_keep_parent),
        "split_min_area_factor": float(split_min_area_factor),
        "split_min_area_absolute": int(split_min_area_absolute),
        "split_max_compactness": float(split_max_compactness),
        "split_min_child_area_fraction": float(split_min_child_area_fraction),
        "split_min_child_mean_fg_prob": float(split_min_child_mean_fg_prob),
        "split_min_child_parent_fg_delta": float(split_min_child_parent_fg_delta),
        "split_min_child_compactness": float(split_min_child_compactness),
    }


def _apply_setting(pipeline: SAMCellPipeline, setting: dict, expert_source: str) -> None:
    thresholds = [float(item) for item in str(setting["cellpose_thresholds"]).split(",") if item]
    h_values = [float(item) for item in str(setting["h_maxima_values"]).split(",") if item]
    _set_expert_thresholds(pipeline, expert_source, thresholds)
    pipeline.cfg.watershed.marker_method = str(setting["marker_method"])
    pipeline.cfg.watershed.h_maxima_values = h_values
    pipeline.cfg.watershed.min_distance_factor = float(setting["min_distance_factor"])
    pipeline.cfg.watershed.peak_threshold_rel = float(setting["peak_threshold_rel"])
    pipeline.cfg.watershed.proposal_duplicate_iou_threshold = float(setting["duplicate_iou"])
    pipeline.cfg.watershed.boundary_suppression_weight = float(setting["boundary_weight"])
    pipeline.cfg.watershed.boundary_additive_weight = float(setting["boundary_additive_weight"])
    pipeline.cfg.watershed.share_boundary_across_experts = bool(setting["share_boundary"])
    pipeline.cfg.watershed.marker_rescue_enabled = bool(setting["marker_rescue_enabled"])
    pipeline.cfg.watershed.marker_rescue_area_factor = float(setting["marker_rescue_area_factor"])
    pipeline.cfg.watershed.marker_rescue_min_distance_factor = float(setting["marker_rescue_min_distance_factor"])
    pipeline.cfg.watershed.marker_rescue_peak_threshold_rel = float(setting["marker_rescue_peak_threshold_rel"])
    pipeline.cfg.proposal_ranker.keep_threshold = float(setting["ranker_threshold"])
    pipeline.cfg.proposal_repair.enabled = True
    pipeline.cfg.proposal_repair.set_selector_enabled = True
    pipeline.cfg.proposal_repair.set_selector_iou_threshold = float(setting["selector_iou"])
    pipeline.cfg.proposal_repair.set_selector_containment_threshold = float(setting["selector_containment"])
    pipeline.cfg.proposal_repair.set_selector_center_distance_factor = float(setting["selector_center_factor"])
    pipeline.cfg.proposal_repair.set_selector_score_margin = float(setting["selector_margin"])
    pipeline.cfg.proposal_repair.split_enabled = bool(setting["split_enabled"])
    pipeline.cfg.proposal_repair.split_keep_parent = bool(setting["split_keep_parent"])
    pipeline.cfg.proposal_repair.split_min_area_factor = float(setting["split_min_area_factor"])
    pipeline.cfg.proposal_repair.split_min_area_absolute = int(setting["split_min_area_absolute"])
    pipeline.cfg.proposal_repair.split_max_compactness = float(setting["split_max_compactness"])
    pipeline.cfg.proposal_repair.split_min_child_area_fraction = float(setting["split_min_child_area_fraction"])
    pipeline.cfg.proposal_repair.split_min_child_mean_fg_prob = float(setting["split_min_child_mean_fg_prob"])
    pipeline.cfg.proposal_repair.split_min_child_parent_fg_delta = float(setting["split_min_child_parent_fg_delta"])
    pipeline.cfg.proposal_repair.split_min_child_compactness = float(setting["split_min_child_compactness"])


def _summaries(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in SETTING_FIELDS)].append(row)
    output = []
    for key, group_rows in sorted(grouped.items()):
        item = {field: value for field, value in zip(SETTING_FIELDS, key, strict=True)}
        item["n"] = len(group_rows)
        item.update(summarize_metrics(group_rows))
        output.append(item)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Cellpose-focused SAM-Cell proposal strategy sweep.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--devset_csv", default="outputs/benchmark_splits_large/eval_250.csv")
    parser.add_argument("--compare_csv")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--source", default="cellpose")
    parser.add_argument("--worst_k", type=int, default=50)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--expert_source", default="cellpose_style")
    parser.add_argument("--threshold_sets", default="0.4,0.5,0.6;0.35,0.45,0.55")
    parser.add_argument("--marker_methods", default="adaptive_hybrid")
    parser.add_argument("--h_maxima_sets", default="0.06,0.1,0.14;0.08,0.12,0.16")
    parser.add_argument("--min_distance_factors", default="0.35,0.4,0.45")
    parser.add_argument("--peak_threshold_rels", default="0.18")
    parser.add_argument("--ranker_thresholds", default="0.45,0.5,0.55")
    parser.add_argument("--duplicate_ious", default="0.7,0.75")
    parser.add_argument("--boundary_weights", default="0.7")
    parser.add_argument("--boundary_additive_weights", default="0.0")
    parser.add_argument("--share_boundary_values", default="false")
    parser.add_argument("--selector_ious", default="0.5,0.55")
    parser.add_argument("--selector_containments", default="0.75")
    parser.add_argument("--selector_center_factors", default="0.35")
    parser.add_argument("--selector_margins", default="0.01,0.02")
    parser.add_argument("--marker_rescue_enabled_values", default="false")
    parser.add_argument("--marker_rescue_area_factors", default="1.35")
    parser.add_argument("--marker_rescue_min_distance_factors", default="0.55")
    parser.add_argument("--marker_rescue_peak_threshold_rels", default="0.08")
    parser.add_argument("--split_enabled_values", default="false")
    parser.add_argument("--split_keep_parent_values", default="false")
    parser.add_argument("--split_min_area_factors", default="2.2")
    parser.add_argument("--split_min_area_absolutes", default="120")
    parser.add_argument("--split_max_compactness_values", default="0.65")
    parser.add_argument("--split_min_child_area_fractions", default="0.0")
    parser.add_argument("--split_min_child_mean_fg_probs", default="0.0")
    parser.add_argument("--split_min_child_parent_fg_deltas", default="-1.0")
    parser.add_argument("--split_min_child_compactness_values", default="0.0")
    parser.add_argument("--max_settings", type=int)
    parser.add_argument("--setting_offset", type=int, default=0)
    parser.add_argument("--include_oracle", action="store_true")
    args = parser.parse_args()

    all_rows = _read_rows(Path(args.devset_csv), args.limit)
    source = None if args.source.lower() in {"", "all", "*"} else args.source
    rows = _filter_rows_by_compare(
        all_rows,
        Path(args.compare_csv) if args.compare_csv else None,
        source,
        args.worst_k,
    )
    if not rows:
        raise ValueError("No rows selected for Cellpose proposal sweep")

    value_grid = list(
        product(
            _parse_threshold_sets(args.threshold_sets),
            _parse_str_list(args.marker_methods),
            _parse_threshold_sets(args.h_maxima_sets),
            _parse_float_list(args.min_distance_factors),
            _parse_float_list(args.peak_threshold_rels),
            _parse_float_list(args.ranker_thresholds),
            _parse_float_list(args.duplicate_ious),
            _parse_float_list(args.boundary_weights),
            _parse_float_list(args.boundary_additive_weights),
            _parse_bool_list(args.share_boundary_values),
            _parse_float_list(args.selector_ious),
            _parse_float_list(args.selector_containments),
            _parse_float_list(args.selector_center_factors),
            _parse_float_list(args.selector_margins),
            _parse_bool_list(args.marker_rescue_enabled_values),
            _parse_float_list(args.marker_rescue_area_factors),
            _parse_float_list(args.marker_rescue_min_distance_factors),
            _parse_float_list(args.marker_rescue_peak_threshold_rels),
            _parse_bool_list(args.split_enabled_values),
            _parse_bool_list(args.split_keep_parent_values),
            _parse_float_list(args.split_min_area_factors),
            _parse_int_list(args.split_min_area_absolutes),
            _parse_float_list(args.split_max_compactness_values),
            _parse_float_list(args.split_min_child_area_fractions),
            _parse_float_list(args.split_min_child_mean_fg_probs),
            _parse_float_list(args.split_min_child_parent_fg_deltas),
            _parse_float_list(args.split_min_child_compactness_values),
        )
    )
    settings = [_setting_dict(idx, values) for idx, values in enumerate(value_grid)]
    if args.setting_offset:
        settings = settings[args.setting_offset :]
    if args.max_settings is not None:
        settings = settings[: args.max_settings]
    if not settings:
        raise ValueError("No settings selected")

    cfg = load_config(args.config)
    cfg.sam2.enabled = False
    pipeline = SAMCellPipeline(cfg)
    out_dir = Path(args.out_dir)
    per_image = []

    print(f"selected_images={len(rows)} settings={len(settings)}")
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        row_source = row.get("source", image_path.stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] sweep {row_source} {image_path.name}")
        gt = load_label_map(row["mask_path"])
        previous = _apply_nested_overrides(pipeline.cfg, pipeline.cfg.source_overrides.get(row_source, {}))
        try:
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            semantic_maps = pipeline._predict_all_semantics(image, image_id=image_path.stem)
            for setting in settings:
                _apply_setting(pipeline, setting, args.expert_source)
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
                        **setting,
                        "source": row_source,
                        "image": image_path.name,
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
    _write_csv(out_dir / "top20_by_pq.csv", sorted(summary, key=lambda row: float(row.get("pq", 0.0)), reverse=True)[:20])
    _write_csv(
        out_dir / "top20_by_oracle_pq.csv",
        sorted(summary, key=lambda row: float(row.get("oracle_oracle_pq", 0.0)), reverse=True)[:20],
    )
    print(f"wrote {out_dir / 'summary_by_setting.csv'}")


if __name__ == "__main__":
    main()
