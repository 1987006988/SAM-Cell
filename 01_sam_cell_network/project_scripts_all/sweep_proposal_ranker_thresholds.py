from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
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
from sam_cell.proposals.internal_selector import proposal_features, selector_scores
from sam_cell.proposals.regions import merge_duplicate_proposals, proposals_to_label_map
from scripts.eval_devset import _read_rows, _write_csv
from scripts.proposal_oracle_diagnosis import _filter_rows_by_compare, _oracle_metrics


def _parse_thresholds(text: str) -> list[float]:
    return [float(item) for item in text.split(",") if item.strip()]


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


def _pre_ranker_proposals(
    pipeline: SAMCellPipeline,
    semantic_maps_by_source: dict[str, dict[str, np.ndarray | None]],
    image_id: str,
) -> tuple[list, dict[str, np.ndarray], np.ndarray]:
    proposals = []
    fg_prob_by_source: dict[str, np.ndarray] = {}
    for expert in pipeline._active_semantic_experts(image_id):
        source = pipeline._expert_source(expert)
        maps = semantic_maps_by_source[source]
        fg_prob = maps["fg_prob"]
        if fg_prob is None:
            continue
        fg_prob = fg_prob.astype(np.float32, copy=False)
        boundary_prob = maps.get("boundary_prob")
        fg_prob_by_source[source] = fg_prob
        *_debug, expert_proposals = pipeline._generate_proposals(
            fg_prob,
            image_id=image_id,
            boundary_prob=None if boundary_prob is None else boundary_prob.astype(np.float32, copy=False),
            semantic_cfg=expert,
            source=source,
            include_external=False,
        )
        proposals.extend(expert_proposals)

    default_fg_prob = pipeline._combined_fg_prob(fg_prob_by_source)
    external = pipeline._external_proposals(image_id, default_fg_prob)
    if pipeline.cfg.external_proposals.enabled and pipeline.cfg.external_proposals.mode == "replace":
        proposals = external
    else:
        proposals = pipeline._filter_internal_proposals(proposals, external, default_fg_prob, image_id)
        proposals.extend(external)
    return proposals, fg_prob_by_source, default_fg_prob


def _ranker_scores(
    pipeline: SAMCellPipeline,
    proposals: list,
    fg_prob_by_source: dict[str, np.ndarray],
    default_fg_prob: np.ndarray,
    image_id: str,
) -> np.ndarray:
    ranker = pipeline._load_proposal_ranker(image_id)
    if ranker is None or not proposals:
        return np.ones((len(proposals),), dtype=np.float32)
    features = []
    extended_features = int(ranker.get("feature_version", 1)) >= 2
    for proposal in proposals:
        fg_prob = pipeline._fg_prob_for_proposal(proposal, fg_prob_by_source, default_fg_prob)
        feature = proposal_features(proposal, [], fg_prob, image_id, extended=extended_features)
        feature["proposal_source"] = proposal.source
        features.append(feature)
    return selector_scores(ranker, features)


def _merge_for_threshold(pipeline: SAMCellPipeline, proposals: list, scores: np.ndarray, threshold: float) -> list:
    kept = []
    for proposal, score in zip(proposals, scores, strict=True):
        proposal.rank_score = float(score)
        if float(score) >= threshold:
            kept.append(proposal)
    kept.sort(key=lambda proposal: (proposal.rank_score, proposal.mean_fg_prob, -proposal.area), reverse=True)
    if pipeline.cfg.proposal_ranker.top_k is not None:
        kept = kept[: int(pipeline.cfg.proposal_ranker.top_k)]
    return merge_duplicate_proposals(
        kept,
        iou_threshold=(
            pipeline.cfg.external_proposals.duplicate_iou_threshold
            if pipeline.cfg.external_proposals.enabled
            else pipeline.cfg.watershed.proposal_duplicate_iou_threshold
        ),
    )


def _summaries(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[float, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(float(row["threshold"]), str(row["source"]))].append(row)
        grouped[(float(row["threshold"]), "ALL")].append(row)
    output = []
    for (threshold, source), source_rows in sorted(grouped.items()):
        output.append(
            {
                "threshold": threshold,
                "source": source,
                "n": len(source_rows),
                **summarize_metrics(source_rows),
            }
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep proposal ranker thresholds without rerunning SAM2.")
    parser.add_argument("--config", default="configs/sam_cell_multi_expert_cellpose_gate.yaml")
    parser.add_argument("--devset_csv", default="outputs/benchmark_splits_large/eval_250.csv")
    parser.add_argument("--compare_csv")
    parser.add_argument("--out_dir", default="outputs/samcell_optimization_20260501/proposal_ranker_threshold_sweep")
    parser.add_argument("--source", default="cellpose")
    parser.add_argument("--worst_k", type=int, default=50)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--thresholds", default="0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65")
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
        raise ValueError("No rows selected for proposal ranker threshold sweep")

    cfg = load_config(args.config)
    cfg.sam2.enabled = False
    pipeline = SAMCellPipeline(cfg)
    thresholds = _parse_thresholds(args.thresholds)
    out_dir = Path(args.out_dir)
    per_image = []

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        source = row.get("source", image_path.stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] sweep {source} {image_path.name}")
        gt = load_label_map(row["mask_path"])
        previous = _apply_nested_overrides(pipeline.cfg, pipeline.cfg.source_overrides.get(source, {}))
        try:
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            semantic_maps = pipeline._predict_all_semantics(image, image_id=image_path.stem)
            proposals, fg_prob_by_source, default_fg_prob = _pre_ranker_proposals(pipeline, semantic_maps, image_path.stem)
            scores = _ranker_scores(pipeline, proposals, fg_prob_by_source, default_fg_prob, image_path.stem)
            for threshold in thresholds:
                merged = _merge_for_threshold(pipeline, proposals, scores, threshold)
                label_map = proposals_to_label_map(merged, gt.shape)
                metrics = instance_metrics(label_map, gt)
                oracle = _oracle_metrics(merged, gt, 0.5) if args.include_oracle else {}
                per_image.append(
                    {
                        "threshold": float(threshold),
                        "source": source,
                        "image": image_path.name,
                        "pre_ranker_proposals": len(proposals),
                        "kept_before_merge": int(np.sum(scores >= threshold)),
                        "merged_proposals": len(merged),
                        **{f"proposal_{key}": value for key, value in metrics.items()},
                        **{f"oracle_{key}": value for key, value in oracle.items()},
                    }
                )
        finally:
            _restore_nested_overrides(pipeline.cfg, previous)
        _write_csv(out_dir / "per_image.partial.csv", per_image)

    _write_csv(out_dir / "per_image.csv", per_image)
    _write_csv(out_dir / "summary_by_source.csv", _summaries(per_image))
    print(f"wrote {out_dir / 'summary_by_source.csv'}")


if __name__ == "__main__":
    main()
