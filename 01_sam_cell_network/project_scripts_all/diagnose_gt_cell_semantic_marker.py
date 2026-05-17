from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import sys

import numpy as np

try:
    import tifffile
except Exception:  # pragma: no cover - tifffile is optional for non-tiff labels
    tifffile = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.proposals.watershed import compute_distance, make_markers, suppress_distance_by_boundary


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


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


def _load_label_any(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"} and tifffile is not None:
        return np.asarray(tifffile.imread(path), dtype=np.int32)
    return load_label_map(path)


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


def _proposal_iou_with_mask(proposal, gt_mask: np.ndarray) -> float:
    x1, y1, x2, y2 = proposal.bbox_xyxy
    local_prop = proposal.mask[y1:y2, x1:x2]
    local_gt = gt_mask[y1:y2, x1:x2]
    inter = int(np.logical_and(local_prop, local_gt).sum())
    if inter <= 0:
        return 0.0
    union = int(proposal.area) + int(gt_mask.sum()) - inter
    return inter / float(max(1, union))


def _best_proposal_match(proposals: list, gt_mask: np.ndarray, gt: np.ndarray, gt_area_threshold: float) -> dict:
    best_iou = 0.0
    best_idx = -1
    best_gt_count = 0
    for idx, proposal in enumerate(proposals):
        iou = _proposal_iou_with_mask(proposal, gt_mask)
        if iou <= best_iou:
            continue
        x1, y1, x2, y2 = proposal.bbox_xyxy
        local_gt = gt[y1:y2, x1:x2]
        values, counts = np.unique(local_gt[proposal.mask[y1:y2, x1:x2]], return_counts=True)
        covered_gt = 0
        for value, inter in zip(values.tolist(), counts.tolist(), strict=True):
            gt_id = int(value)
            if gt_id == 0:
                continue
            gt_area = int((gt == gt_id).sum())
            if gt_area > 0 and int(inter) / float(gt_area) >= gt_area_threshold:
                covered_gt += 1
        best_iou = iou
        best_idx = idx
        best_gt_count = covered_gt
    if best_idx < 0:
        return {"iou": 0.0, "proposal_id": 0, "proposal_source": "", "proposal_area": 0, "proposal_gt_count": 0}
    proposal = proposals[best_idx]
    return {
        "iou": best_iou,
        "proposal_id": int(getattr(proposal, "id", best_idx + 1)),
        "proposal_source": str(getattr(proposal, "source", "")),
        "proposal_area": int(getattr(proposal, "area", 0)),
        "proposal_gt_count": int(best_gt_count),
    }


def _best_label_match(label_map: np.ndarray | None, gt_mask: np.ndarray) -> dict:
    if label_map is None:
        return {"iou": 0.0, "label_id": 0}
    gt_area = int(gt_mask.sum())
    values, counts = np.unique(label_map[gt_mask], return_counts=True)
    best_iou = 0.0
    best_id = 0
    for value, inter in zip(values.tolist(), counts.tolist(), strict=True):
        label_id = int(value)
        if label_id == 0:
            continue
        pred_area = int((label_map == label_id).sum())
        union = gt_area + pred_area - int(inter)
        iou = int(inter) / float(max(1, union))
        if iou > best_iou:
            best_iou = iou
            best_id = label_id
    return {"iou": best_iou, "label_id": best_id}


def _marker_count_inside(markers_by_source: dict[str, list[np.ndarray]], gt_mask: np.ndarray) -> tuple[int, str]:
    total = 0
    parts = []
    for source, marker_maps in sorted(markers_by_source.items()):
        source_count = 0
        for marker_map in marker_maps:
            ids = [int(item) for item in np.unique(marker_map[gt_mask]) if int(item) != 0]
            source_count += len(ids)
        total += source_count
        parts.append(f"{source}:{source_count}")
    return total, ";".join(parts)


def _coverage_stats(prob: np.ndarray | None, gt_mask: np.ndarray, thresholds: tuple[float, float]) -> dict:
    if prob is None:
        return {"mean": 0.0, f"cov{thresholds[0]:g}": 0.0, f"cov{thresholds[1]:g}": 0.0}
    values = prob[gt_mask]
    if values.size == 0:
        return {"mean": 0.0, f"cov{thresholds[0]:g}": 0.0, f"cov{thresholds[1]:g}": 0.0}
    return {
        "mean": float(values.mean()),
        f"cov{thresholds[0]:g}": float(np.mean(values >= thresholds[0])),
        f"cov{thresholds[1]:g}": float(np.mean(values >= thresholds[1])),
    }


def _classify_cell(row: dict, args: argparse.Namespace) -> str:
    combined_cov03 = float(row["combined_cov03"])
    combined_cov05 = float(row["combined_cov05"])
    marker_count = int(row["marker_count_inside_gt"])
    best_raw = float(row["best_raw_iou"])
    best_unranked = float(row["best_unranked_iou"])
    best_ranked = float(row["best_ranked_iou"])
    best_final = float(row["best_final_iou"])
    raw_gt_count = int(row["best_raw_proposal_gt_count"])

    if best_final >= args.iou_threshold:
        return "detected"
    if combined_cov03 < args.foreground_miss_cov03 and best_raw < 0.2:
        return "foreground_miss"
    if combined_cov03 >= args.foreground_miss_cov03 and combined_cov05 < args.weak_foreground_cov05:
        return "weak_foreground"
    if raw_gt_count >= 2 and best_raw < args.iou_threshold:
        return "merge_under_split"
    if combined_cov05 >= args.marker_ready_cov05 and (marker_count < args.min_markers_inside_gt or best_raw < 0.3):
        return "marker_miss"
    if best_raw >= args.iou_threshold and best_unranked < args.iou_threshold:
        return "selector_or_merge_filtered"
    if best_unranked >= args.iou_threshold and best_ranked < args.iou_threshold:
        return "ranker_filtered"
    if best_ranked >= args.iou_threshold and best_final < args.iou_threshold:
        return "final_merge_loss"
    if max(best_raw, best_unranked, best_ranked, best_final) >= 0.3:
        return "shape_low_iou"
    return "residual_unknown"


def _summarize_cells(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["source"]), str(row["failure_type"]))].append(row)
    output = []
    for (source, failure_type), items in sorted(grouped.items()):
        output.append(
            {
                "source": source,
                "failure_type": failure_type,
                "n_cells": len(items),
                "fraction": len(items) / float(max(1, sum(1 for row in rows if row["source"] == source))),
                "mean_combined_cov03": float(np.mean([float(row["combined_cov03"]) for row in items])),
                "mean_combined_cov05": float(np.mean([float(row["combined_cov05"]) for row in items])),
                "mean_best_raw_iou": float(np.mean([float(row["best_raw_iou"]) for row in items])),
                "mean_best_ranked_iou": float(np.mean([float(row["best_ranked_iou"]) for row in items])),
                "mean_best_final_iou": float(np.mean([float(row["best_final_iou"]) for row in items])),
            }
        )
    return output


def _summarize_images(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["source"]), str(row["image"]))].append(row)
    output = []
    for (source, image), items in sorted(grouped.items()):
        counts = Counter(str(row["failure_type"]) for row in items)
        output.append(
            {
                "source": source,
                "image": image,
                "gt_cells": len(items),
                "detected": counts.get("detected", 0),
                "foreground_miss": counts.get("foreground_miss", 0),
                "weak_foreground": counts.get("weak_foreground", 0),
                "marker_miss": counts.get("marker_miss", 0),
                "merge_under_split": counts.get("merge_under_split", 0),
                "selector_or_merge_filtered": counts.get("selector_or_merge_filtered", 0),
                "ranker_filtered": counts.get("ranker_filtered", 0),
                "final_merge_loss": counts.get("final_merge_loss", 0),
                "shape_low_iou": counts.get("shape_low_iou", 0),
                "residual_unknown": counts.get("residual_unknown", 0),
                "mean_combined_cov05": float(np.mean([float(row["combined_cov05"]) for row in items])),
                "mean_best_final_iou": float(np.mean([float(row["best_final_iou"]) for row in items])),
            }
        )
    return output


def _build_markers_for_semantics(pipeline: SAMCellPipeline, semantic_maps: dict[str, dict[str, np.ndarray | None]], image_id: str) -> dict[str, list[np.ndarray]]:
    markers_by_source: dict[str, list[np.ndarray]] = defaultdict(list)
    for expert in pipeline._active_semantic_experts(image_id):
        source = pipeline._expert_source(expert)
        maps = semantic_maps[source]
        fg_prob = maps["fg_prob"]
        if fg_prob is None:
            continue
        fg_prob = fg_prob.astype(np.float32, copy=False)
        boundary_prob = maps.get("boundary_prob")
        thresholds = expert.proposal_thresholds or [expert.foreground_threshold]
        for threshold in thresholds:
            fg_mask = pipeline._foreground_mask(fg_prob, float(threshold), semantic_cfg=expert)
            dist = compute_distance(fg_mask, sigma=pipeline.cfg.watershed.edt_sigma)
            proposal_dist = suppress_distance_by_boundary(
                dist,
                None if boundary_prob is None else boundary_prob.astype(np.float32, copy=False),
                weight=pipeline.cfg.watershed.boundary_suppression_weight,
            )
            markers_by_source[source].append(make_markers(proposal_dist, fg_mask, pipeline.cfg.watershed))
    return markers_by_source


def _combined_fg_prob(fg_prob_by_source: dict[str, np.ndarray]) -> np.ndarray:
    if not fg_prob_by_source:
        raise ValueError("No foreground probabilities available")
    return np.maximum.reduce(list(fg_prob_by_source.values())).astype(np.float32, copy=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="GT-cell diagnosis of semantic foreground coverage, markers, proposal, ranker, and final output.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--devset_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--source", default="cellpose")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--final_labels_dir")
    parser.add_argument("--iou_threshold", type=float, default=0.5)
    parser.add_argument("--foreground_miss_cov03", type=float, default=0.35)
    parser.add_argument("--weak_foreground_cov05", type=float, default=0.35)
    parser.add_argument("--marker_ready_cov05", type=float, default=0.5)
    parser.add_argument("--min_markers_inside_gt", type=int, default=1)
    parser.add_argument("--gt_area_overlap_threshold", type=float, default=0.25)
    args = parser.parse_args()

    rows = _read_rows(Path(args.devset_csv), args.limit)
    if args.source.lower() not in {"", "all", "*"}:
        rows = [row for row in rows if row.get("source", Path(row["image_path"]).stem.split("_", 1)[0]) == args.source]
    if not rows:
        raise ValueError("No rows selected for diagnosis")

    cfg = load_config(args.config)
    cfg.sam2.enabled = False
    pipeline = SAMCellPipeline(cfg)
    final_labels_dir = Path(args.final_labels_dir) if args.final_labels_dir else None

    cell_rows = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        mask_path = Path(row["mask_path"])
        image_id = image_path.stem
        source = row.get("source", image_id.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] gt-cell diagnosis {source} {image_path.name}")
        image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
        gt = load_label_map(mask_path)
        final_label = None
        if final_labels_dir is not None:
            final_path = final_labels_dir / f"{image_id}.tif"
            if final_path.exists():
                final_label = _load_label_any(final_path)

        previous = _apply_nested_overrides(pipeline.cfg, pipeline.cfg.source_overrides.get(source, {}))
        try:
            semantic_maps = pipeline._predict_all_semantics(image, image_id=image_id)
            fg_prob_by_source = {
                src: maps["fg_prob"].astype(np.float32, copy=False)
                for src, maps in semantic_maps.items()
                if maps.get("fg_prob") is not None
            }
            combined_fg = _combined_fg_prob(fg_prob_by_source)
            boundary_by_source = {
                src: maps["boundary_prob"].astype(np.float32, copy=False)
                for src, maps in semantic_maps.items()
                if maps.get("boundary_prob") is not None
            }
            markers_by_source = _build_markers_for_semantics(pipeline, semantic_maps, image_id)

            raw_proposals = []
            for expert in pipeline._active_semantic_experts(image_id):
                expert_source = pipeline._expert_source(expert)
                maps = semantic_maps[expert_source]
                fg_prob = maps["fg_prob"]
                if fg_prob is None:
                    continue
                *_debug, proposals = pipeline._generate_proposals(
                    fg_prob.astype(np.float32, copy=False),
                    image_id=image_id,
                    boundary_prob=None
                    if maps.get("boundary_prob") is None
                    else maps["boundary_prob"].astype(np.float32, copy=False),
                    semantic_cfg=expert,
                    source=expert_source,
                    include_external=False,
                )
                raw_proposals.extend(proposals)

            saved_ranker_enabled = pipeline.cfg.proposal_ranker.enabled
            pipeline.cfg.proposal_ranker.enabled = False
            try:
                *_debug, unranked_proposals, _fg_by_source, _mask, _proposal_diag = pipeline._generate_multi_expert_proposals(
                    semantic_maps,
                    image_id=image_id,
                    image=image,
                )
            finally:
                pipeline.cfg.proposal_ranker.enabled = saved_ranker_enabled
            *_debug, ranked_proposals, _fg_by_source, _mask, _proposal_diag = pipeline._generate_multi_expert_proposals(
                semantic_maps,
                image_id=image_id,
                image=image,
            )
        finally:
            _restore_nested_overrides(pipeline.cfg, previous)

        for gt_id in _ids(gt):
            gt_mask = gt == gt_id
            gt_area = int(gt_mask.sum())
            combined_stats = _coverage_stats(combined_fg, gt_mask, (0.3, 0.5))
            marker_count, marker_source_counts = _marker_count_inside(markers_by_source, gt_mask)
            raw_match = _best_proposal_match(raw_proposals, gt_mask, gt, args.gt_area_overlap_threshold)
            unranked_match = _best_proposal_match(unranked_proposals, gt_mask, gt, args.gt_area_overlap_threshold)
            ranked_match = _best_proposal_match(ranked_proposals, gt_mask, gt, args.gt_area_overlap_threshold)
            final_match = _best_label_match(final_label, gt_mask)

            out = {
                "source": source,
                "image": image_path.name,
                "gt_id": gt_id,
                "gt_area": gt_area,
                "combined_fg_mean": combined_stats["mean"],
                "combined_cov03": combined_stats["cov0.3"],
                "combined_cov05": combined_stats["cov0.5"],
                "marker_count_inside_gt": marker_count,
                "marker_source_counts": marker_source_counts,
                "best_raw_iou": raw_match["iou"],
                "best_raw_proposal_id": raw_match["proposal_id"],
                "best_raw_proposal_source": raw_match["proposal_source"],
                "best_raw_proposal_area": raw_match["proposal_area"],
                "best_raw_proposal_gt_count": raw_match["proposal_gt_count"],
                "best_unranked_iou": unranked_match["iou"],
                "best_unranked_proposal_id": unranked_match["proposal_id"],
                "best_unranked_proposal_source": unranked_match["proposal_source"],
                "best_ranked_iou": ranked_match["iou"],
                "best_ranked_proposal_id": ranked_match["proposal_id"],
                "best_ranked_proposal_source": ranked_match["proposal_source"],
                "best_final_iou": final_match["iou"],
                "best_final_instance_id": final_match["label_id"],
            }
            for src, prob in sorted(fg_prob_by_source.items()):
                stats = _coverage_stats(prob, gt_mask, (0.3, 0.5))
                out[f"{src}_fg_mean"] = stats["mean"]
                out[f"{src}_cov03"] = stats["cov0.3"]
                out[f"{src}_cov05"] = stats["cov0.5"]
            for src, boundary in sorted(boundary_by_source.items()):
                values = boundary[gt_mask]
                out[f"{src}_boundary_mean"] = float(values.mean()) if values.size else 0.0
            out["failure_type"] = _classify_cell(out, args)
            cell_rows.append(out)

    out_dir = Path(args.out_dir)
    _write_csv(out_dir / "gt_cell_diagnosis.csv", cell_rows)
    _write_csv(out_dir / "failure_type_summary.csv", _summarize_cells(cell_rows))
    _write_csv(out_dir / "image_summary.csv", _summarize_images(cell_rows))
    print(f"wrote {out_dir / 'gt_cell_diagnosis.csv'}")


if __name__ == "__main__":
    main()
