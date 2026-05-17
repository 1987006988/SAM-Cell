from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.proposals.regions import proposals_to_label_map


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _str_to_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value, got {value!r}")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _ids(label_map: np.ndarray) -> list[int]:
    return [int(item) for item in np.unique(label_map) if int(item) != 0]


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


def _iou_matrix_for_proposals(proposals: list, gt: np.ndarray, gt_ids: list[int]) -> np.ndarray:
    mat = np.zeros((len(proposals), len(gt_ids)), dtype=np.float32)
    if not proposals or not gt_ids:
        return mat
    gt_areas = {gt_id: int((gt == gt_id).sum()) for gt_id in gt_ids}
    gt_id_to_col = {gt_id: idx for idx, gt_id in enumerate(gt_ids)}
    for row, proposal in enumerate(proposals):
        x1, y1, x2, y2 = proposal.bbox_xyxy
        local_mask = proposal.mask[y1:y2, x1:x2]
        local_gt = gt[y1:y2, x1:x2]
        values, counts = np.unique(local_gt[local_mask], return_counts=True)
        for value, inter in zip(values.tolist(), counts.tolist(), strict=True):
            gt_id = int(value)
            if gt_id == 0:
                continue
            col = gt_id_to_col.get(gt_id)
            if col is None:
                continue
            union = int(proposal.area) + gt_areas[gt_id] - int(inter)
            mat[row, col] = float(inter) / float(max(1, union))
    return mat


def _oracle_metrics(proposals: list, gt: np.ndarray, iou_threshold: float) -> dict[str, float | int]:
    gt_ids = _ids(gt)
    mat = _iou_matrix_for_proposals(proposals, gt, gt_ids)
    matches: list[tuple[int, int, float]] = []
    if mat.size:
        rows, cols = linear_sum_assignment(-mat)
        matches = [(int(r), int(c), float(mat[r, c])) for r, c in zip(rows, cols) if mat[r, c] >= iou_threshold]

    tp = len(matches)
    fp = len(proposals) - tp
    fn = len(gt_ids) - tp
    sq = sum(item[2] for item in matches) / tp if tp else 0.0
    rq = tp / (tp + 0.5 * fp + 0.5 * fn) if (tp + fp + fn) else 1.0
    pq = sq * rq
    no_fp_rq = tp / (tp + 0.5 * fn) if (tp + fn) else 1.0
    no_fp_pq = sq * no_fp_rq

    gt_best = mat.max(axis=0) if mat.shape[1] else np.asarray([], dtype=np.float32)
    prop_best = mat.max(axis=1) if mat.shape[0] else np.asarray([], dtype=np.float32)
    gt_recall = float(np.mean(gt_best >= iou_threshold)) if gt_best.size else 1.0
    prop_precision = float(np.mean(prop_best >= iou_threshold)) if prop_best.size else 1.0
    return {
        "proposal_n": len(proposals),
        "gt_n": len(gt_ids),
        "oracle_tp": tp,
        "oracle_fp": fp,
        "oracle_fn": fn,
        "oracle_sq": sq,
        "oracle_rq": rq,
        "oracle_pq": pq,
        "oracle_no_fp_pq": no_fp_pq,
        "gt_recall_at_iou": gt_recall,
        "proposal_precision_at_iou": prop_precision,
        "mean_best_gt_iou": float(gt_best.mean()) if gt_best.size else 1.0,
        "median_best_gt_iou": float(np.median(gt_best)) if gt_best.size else 1.0,
        "min_best_gt_iou": float(gt_best.min()) if gt_best.size else 1.0,
        "mean_best_proposal_iou": float(prop_best.mean()) if prop_best.size else 1.0,
    }


def _label_metrics(label_map: np.ndarray, gt: np.ndarray) -> dict[str, float | int]:
    metrics = instance_metrics(label_map, gt)
    return {
        "proposal_n": int(metrics["pred_n"]),
        "gt_n": int(metrics["gt_n"]),
        "oracle_tp": int(metrics["tp"]),
        "oracle_fp": int(metrics["fp"]),
        "oracle_fn": int(metrics["fn"]),
        "oracle_sq": float(metrics["sq"]),
        "oracle_rq": float(metrics["rq"]),
        "oracle_pq": float(metrics["pq"]),
        "oracle_no_fp_pq": float(metrics["pq"]),
        "gt_recall_at_iou": float(metrics["recall"]),
        "proposal_precision_at_iou": float(metrics["precision"]),
        "mean_best_gt_iou": 0.0,
        "median_best_gt_iou": 0.0,
        "min_best_gt_iou": 0.0,
        "mean_best_proposal_iou": 0.0,
        "aji": float(metrics["aji"]),
        "f1": float(metrics["f1"]),
    }


def _generate_raw_expert_proposals(
    pipeline: SAMCellPipeline,
    semantic_maps_by_source: dict[str, dict[str, np.ndarray | None]],
    image_id: str,
) -> tuple[list, dict[str, np.ndarray], np.ndarray]:
    all_proposals = []
    fg_prob_by_source: dict[str, np.ndarray] = {}
    combined_fg_mask = None
    for expert in pipeline._active_semantic_experts(image_id):
        source_name = pipeline._expert_source(expert)
        maps = semantic_maps_by_source[source_name]
        fg_prob = maps["fg_prob"]
        if fg_prob is None:
            continue
        fg_prob = fg_prob.astype(np.float32, copy=False)
        boundary_prob = maps.get("boundary_prob")
        fg_prob_by_source[source_name] = fg_prob
        fg_mask, *_unused, proposals = pipeline._generate_proposals(
            fg_prob,
            image_id=image_id,
            boundary_prob=None if boundary_prob is None else boundary_prob.astype(np.float32, copy=False),
            semantic_cfg=expert,
            source=source_name,
            include_external=False,
        )
        all_proposals.extend(proposals)
        combined_fg_mask = fg_mask if combined_fg_mask is None else (combined_fg_mask | fg_mask)
    default_fg_prob = pipeline._combined_fg_prob(fg_prob_by_source)
    return all_proposals, fg_prob_by_source, combined_fg_mask if combined_fg_mask is not None else default_fg_prob > 0


def _stage_rows(
    row_prefix: dict,
    stage: str,
    proposals: list,
    gt: np.ndarray,
    iou_threshold: float,
    include_source_breakdown: bool,
) -> tuple[dict, list[dict]]:
    all_row = {
        **row_prefix,
        "stage": stage,
        "proposal_source": "ALL",
        **_oracle_metrics(proposals, gt, iou_threshold),
    }
    source_rows: list[dict] = []
    if include_source_breakdown:
        by_source: dict[str, list] = defaultdict(list)
        for proposal in proposals:
            by_source[str(proposal.source)].append(proposal)
        for proposal_source, source_proposals in sorted(by_source.items()):
            source_rows.append(
                {
                    **row_prefix,
                    "stage": stage,
                    "proposal_source": proposal_source,
                    **_oracle_metrics(source_proposals, gt, iou_threshold),
                }
            )
    return all_row, source_rows


def _summarize(rows: list[dict], group_keys: list[str]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in group_keys)].append(row)
    output = []
    for key, group_rows in sorted(grouped.items()):
        item = {name: value for name, value in zip(group_keys, key, strict=True)}
        item["n_images"] = len(group_rows)
        item.update(summarize_metrics(group_rows))
        output.append(item)
    return output


def _filter_rows_by_compare(
    rows: list[dict[str, str]],
    compare_csv: Path | None,
    source: str | None,
    worst_k: int | None,
) -> list[dict[str, str]]:
    if compare_csv is None:
        filtered = rows
        if source:
            filtered = [row for row in filtered if row.get("source", Path(row["image_path"]).stem.split("_", 1)[0]) == source]
        return filtered[:worst_k] if worst_k else filtered

    compare_rows = _read_rows(compare_csv)
    if source:
        compare_rows = [row for row in compare_rows if row.get("source") == source]
    compare_rows = sorted(compare_rows, key=lambda row: float(row.get("delta_pq", 0.0)))
    if worst_k:
        compare_rows = compare_rows[:worst_k]
    wanted = {Path(row["image"]).stem for row in compare_rows}
    return [row for row in rows if Path(row["image_path"]).stem in wanted]


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose SAM-Cell proposal/ranker/final bottlenecks with GT oracle metrics.")
    parser.add_argument("--config", default="configs/sam_cell_multi_expert_cellpose_gate.yaml")
    parser.add_argument("--devset_csv", default="outputs/benchmark_splits_large/eval_250.csv")
    parser.add_argument("--compare_csv", help="Optional compare_methods per_image.csv used to select worst cases.")
    parser.add_argument("--out_dir", default="outputs/samcell_optimization_20260501/proposal_oracle")
    parser.add_argument("--source", default="cellpose")
    parser.add_argument("--worst_k", type=int, default=50)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--iou_threshold", type=float, default=0.5)
    parser.add_argument("--proposal_ranker_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_ranker_model_path")
    parser.add_argument("--proposal_ranker_keep_threshold", type=float)
    parser.add_argument("--watershed_marker_method", help="Diagnostic override for cfg.watershed.marker_method.")
    parser.add_argument("--proposal_repair_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_split_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_set_selector_enabled", type=_str_to_bool)
    parser.add_argument("--separator_enabled", type=_str_to_bool)
    parser.add_argument("--separator_model_path")
    parser.add_argument("--separator_mode", choices=["augment", "replace"])
    parser.add_argument("--final_labels_dir", help="Optional cached final SAM-Cell labels directory.")
    parser.add_argument("--include_source_breakdown", action="store_true")
    args = parser.parse_args()

    all_rows = _read_rows(Path(args.devset_csv), args.limit)
    rows = _filter_rows_by_compare(
        all_rows,
        Path(args.compare_csv) if args.compare_csv else None,
        args.source,
        args.worst_k,
    )
    if not rows:
        raise ValueError("No rows selected for oracle diagnosis")

    cfg = load_config(args.config)
    if args.proposal_ranker_enabled is not None:
        cfg.proposal_ranker.enabled = args.proposal_ranker_enabled
    if args.proposal_ranker_model_path:
        cfg.proposal_ranker.model_path = args.proposal_ranker_model_path
    if args.proposal_ranker_keep_threshold is not None:
        cfg.proposal_ranker.keep_threshold = float(args.proposal_ranker_keep_threshold)
    if args.watershed_marker_method:
        cfg.watershed.marker_method = args.watershed_marker_method
    if args.proposal_repair_enabled is not None:
        cfg.proposal_repair.enabled = args.proposal_repair_enabled
    if args.proposal_split_enabled is not None:
        cfg.proposal_repair.split_enabled = args.proposal_split_enabled
    if args.proposal_set_selector_enabled is not None:
        cfg.proposal_repair.set_selector_enabled = args.proposal_set_selector_enabled
    if args.separator_enabled is not None:
        cfg.separator_proposals.enabled = args.separator_enabled
    if args.separator_model_path:
        cfg.separator_proposals.model_path = args.separator_model_path
    if args.separator_mode:
        cfg.separator_proposals.mode = args.separator_mode
    cfg.sam2.enabled = False
    pipeline = SAMCellPipeline(cfg)

    out_dir = Path(args.out_dir)
    per_stage = []
    per_source = []
    final_labels_dir = Path(args.final_labels_dir) if args.final_labels_dir else None

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        mask_path = Path(row["mask_path"])
        source = row.get("source", image_path.stem.split("_", 1)[0])
        image_id = image_path.stem
        print(f"[{idx}/{len(rows)}] oracle diagnosis {source} {image_path.name}")
        gt = load_label_map(mask_path)
        previous = _apply_nested_overrides(pipeline.cfg, pipeline.cfg.source_overrides.get(source, {}))
        try:
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            semantic_maps = pipeline._predict_all_semantics(image, image_id=image_id)
            raw_proposals, fg_prob_by_source, combined_fg_mask = _generate_raw_expert_proposals(
                pipeline,
                semantic_maps,
                image_id,
            )
            default_fg_prob = pipeline._combined_fg_prob(fg_prob_by_source)
            separator_boundary = pipeline._shared_boundary_prob(semantic_maps)
            raw_separator = pipeline._separator_proposals(image, default_fg_prob, separator_boundary, image_id)

            ranker_enabled = pipeline.cfg.proposal_ranker.enabled
            pipeline.cfg.proposal_ranker.enabled = False
            try:
                (
                    _fg_mask_unranked,
                    _dist_unranked,
                    _markers_unranked,
                    _label_unranked,
                    unranked_proposals,
                    _fg_by_source,
                    _fg_mask,
                    _diag_unranked,
                ) = pipeline._generate_multi_expert_proposals(
                    semantic_maps,
                    image_id=image_id,
                    image=image,
                )
            finally:
                pipeline.cfg.proposal_ranker.enabled = ranker_enabled

            (
                _fg_mask_ranked,
                _dist_ranked,
                _markers_ranked,
                _label_ranked,
                ranked_proposals,
                _fg_by_source,
                _fg_mask,
                _diag_ranked,
            ) = pipeline._generate_multi_expert_proposals(
                semantic_maps,
                image_id=image_id,
                image=image,
            )
        finally:
            _restore_nested_overrides(pipeline.cfg, previous)

        row_prefix = {"source": source, "image": image_path.name}
        for stage, proposals in [
            ("raw_expert_unranked", raw_proposals),
            ("raw_separator", raw_separator),
            ("raw_expert_plus_separator", raw_proposals + raw_separator),
            ("merged_unranked", unranked_proposals),
            ("ranked_merged", ranked_proposals),
        ]:
            row_out, source_rows = _stage_rows(
                row_prefix,
                stage,
                proposals,
                gt,
                args.iou_threshold,
                args.include_source_breakdown,
            )
            per_stage.append(row_out)
            per_source.extend(source_rows)
            if stage == "ranked_merged":
                label_map = proposals_to_label_map(ranked_proposals, gt.shape)
                per_stage.append(
                    {
                        **row_prefix,
                        "stage": "ranked_label_map_nonoverlap",
                        "proposal_source": "ALL",
                        **_label_metrics(label_map, gt),
                    }
                )

        if final_labels_dir is not None:
            final_path = final_labels_dir / f"{image_id}.tif"
            if final_path.exists():
                final_label = load_label_map(final_path)
                per_stage.append(
                    {
                        **row_prefix,
                        "stage": "final_cached",
                        "proposal_source": "ALL",
                        **_label_metrics(final_label, gt),
                    }
                )

    _write_csv(out_dir / "per_image_stage.csv", per_stage)
    _write_csv(out_dir / "summary_by_stage.csv", _summarize(per_stage, ["stage", "proposal_source"]))
    if per_source:
        _write_csv(out_dir / "per_image_stage_by_source.csv", per_source)
        _write_csv(out_dir / "summary_by_stage_by_source.csv", _summarize(per_source, ["stage", "proposal_source"]))

    by_image_stage: dict[tuple[str, str], dict] = {(row["image"], row["stage"]): row for row in per_stage}
    gap_rows = []
    for row in rows:
        image_name = Path(row["image_path"]).name
        ranked = by_image_stage.get((image_name, "ranked_merged"))
        final = by_image_stage.get((image_name, "final_cached"))
        if not ranked or not final:
            continue
        gap_rows.append(
            {
                "source": ranked["source"],
                "image": image_name,
                "ranked_oracle_no_fp_pq": ranked["oracle_no_fp_pq"],
                "ranked_gt_recall_at_iou": ranked["gt_recall_at_iou"],
                "final_pq": final["oracle_pq"],
                "final_recall": final["gt_recall_at_iou"],
                "final_minus_oracle_no_fp_pq": float(final["oracle_pq"]) - float(ranked["oracle_no_fp_pq"]),
                "final_minus_ranked_recall": float(final["gt_recall_at_iou"]) - float(ranked["gt_recall_at_iou"]),
            }
        )
    if gap_rows:
        _write_csv(
            out_dir / "worst_final_vs_oracle_gap.csv",
            sorted(gap_rows, key=lambda row: float(row["final_minus_oracle_no_fp_pq"]))[:25],
        )

    print(f"wrote {out_dir / 'summary_by_stage.csv'}")


if __name__ == "__main__":
    main()
