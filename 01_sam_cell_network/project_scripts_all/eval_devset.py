from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.visualize import overlay_instances


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
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _apply_nested_overrides(obj, values: dict) -> dict:
    previous = {}
    for key, value in values.items():
        if "." in key:
            head, tail = key.split(".", 1)
            child = getattr(obj, head)
            previous[key] = _apply_nested_overrides(child, {tail: value})[tail]
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


def _save_outputs(out_dir: Path, stem: str, image: np.ndarray, result: dict) -> None:
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)
    (out_dir / "instances").mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(out_dir / "labels" / f"{stem}.tif", result["instance_map"].astype(np.int32))
    Image.fromarray(overlay_instances(image, result["instance_map"])).save(out_dir / "overlays" / f"{stem}.png")
    with (out_dir / "instances" / f"{stem}.json").open("w", encoding="utf-8") as f:
        json.dump(result["instances"], f, ensure_ascii=False, indent=2)


def _result_from_cache(out_dir: Path, stem: str) -> np.ndarray | None:
    label_path = out_dir / "labels" / f"{stem}.tif"
    if not label_path.exists():
        return None
    return tifffile.imread(label_path).astype(np.int32)


def evaluate_rows(
    pipeline: SAMCellPipeline,
    rows: list[dict[str, str]],
    out_dir: Path | None = None,
    use_cache: bool = False,
) -> list[dict]:
    results = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        mask_path = Path(row["mask_path"])
        source = row.get("source", image_path.name.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] {source} {image_path.name}")
        gt = load_label_map(mask_path)
        stem = image_path.stem
        cached_label = _result_from_cache(out_dir, stem) if out_dir is not None and use_cache else None
        if cached_label is not None:
            instance_map = cached_label
            proposal_map = np.zeros_like(gt)
            source_counts = defaultdict(int)
            proposal_source_counts = defaultdict(int)
            proposals = []
            proposal_diagnostics = {}
        else:
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            result = pipeline.infer(image, image_id=image_path.stem)
            instance_map = result["instance_map"]
            proposal_map = result["proposal_label_map"]
            proposals = result["proposals"]
            proposal_diagnostics = result.get("proposal_diagnostics", {})
            source_counts = defaultdict(int)
            proposal_source_counts = defaultdict(int)
            for record in result.get("selection_records", []):
                source_counts[record["source"]] += 1
                proposal_source_counts[record.get("proposal_source", record["source"])] += 1
            if out_dir is not None:
                _save_outputs(out_dir, stem, image, result)
        metrics = instance_metrics(instance_map, gt)
        proposal_metrics = instance_metrics(proposal_map, gt) if np.any(proposal_map) else {}
        separator_source = pipeline.cfg.separator_proposals.source_name
        separator_selected = proposal_source_counts.get(separator_source, 0)
        output = {
            "source": source,
            "image": image_path.name,
            "proposals": len(proposals),
            "final_instances": int(instance_map.max()),
            "sam2_selected": sum(v for k, v in source_counts.items() if k.startswith("sam2")),
            "coarse_selected": sum(v for k, v in source_counts.items() if not k.startswith("sam2")),
            "watershed_selected": source_counts.get("watershed", 0),
            "universal_boundary_selected": proposal_source_counts.get("universal_boundary", 0),
            "cellpose_style_selected": proposal_source_counts.get("cellpose_style", 0),
            "separator_selected": separator_selected,
            "external_selected": sum(v for k, v in proposal_source_counts.items() if k.startswith("external")),
            "separator_generated": proposal_diagnostics.get("separator_generated", 0),
            "separator_before_ranker": proposal_diagnostics.get("separator_before_ranker", 0),
            "separator_after_ranker": proposal_diagnostics.get("separator_after_ranker", 0),
            "separator_after_set_selector": proposal_diagnostics.get("separator_after_set_selector", 0),
            "separator_after_merge": proposal_diagnostics.get("separator_after_merge", 0),
            "proposals_before_ranker": proposal_diagnostics.get("before_ranker", 0),
            "proposals_after_ranker": proposal_diagnostics.get("after_ranker", 0),
            "proposals_after_set_selector": proposal_diagnostics.get("after_set_selector", 0),
            "proposals_after_merge": proposal_diagnostics.get("after_merge", 0),
            "ranked_proposals": sum(1 for proposal in proposals if getattr(proposal, "rank_score", 0.0) > 0.0),
            **{f"final_{k}": v for k, v in metrics.items()},
            **{f"proposal_{k}": v for k, v in proposal_metrics.items()},
        }
        results.append(output)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SAM-Cell on a mini development set")
    parser.add_argument("--config", default="configs/sam_cell_optimized.yaml")
    parser.add_argument("--devset_csv", default="outputs/dev_eval/devset_25.csv")
    parser.add_argument("--out_dir", default="outputs/dev_eval/sam_cell")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--save_outputs", action="store_true")
    parser.add_argument("--use_cache", action="store_true")
    parser.add_argument(
        "--no_summary",
        action="store_true",
        help="Run inference/evaluation and save outputs without writing per_image.csv or summary.csv.",
    )
    parser.add_argument("--proposal_ranker_keep_threshold", type=float)
    parser.add_argument("--proposal_ranker_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_ranker_model_path")
    parser.add_argument("--watershed_marker_method", help="Diagnostic override for cfg.watershed.marker_method.")
    parser.add_argument("--watershed_boundary_suppression_weight", type=float)
    parser.add_argument("--watershed_boundary_additive_weight", type=float)
    parser.add_argument("--watershed_share_boundary_across_experts", type=_str_to_bool)
    parser.add_argument("--watershed_marker_rescue_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_repair_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_split_enabled", type=_str_to_bool)
    parser.add_argument("--proposal_set_selector_enabled", type=_str_to_bool)
    parser.add_argument("--separator_enabled", type=_str_to_bool)
    parser.add_argument("--separator_model_path")
    parser.add_argument("--separator_mode", choices=["augment", "replace"])
    parser.add_argument("--sam2_enabled", type=_str_to_bool)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.proposal_ranker_enabled is not None:
        cfg.proposal_ranker.enabled = args.proposal_ranker_enabled
    if args.proposal_ranker_model_path:
        cfg.proposal_ranker.model_path = args.proposal_ranker_model_path
    if args.proposal_ranker_keep_threshold is not None:
        cfg.proposal_ranker.keep_threshold = float(args.proposal_ranker_keep_threshold)
    if args.watershed_marker_method:
        cfg.watershed.marker_method = args.watershed_marker_method
    if args.watershed_boundary_suppression_weight is not None:
        cfg.watershed.boundary_suppression_weight = float(args.watershed_boundary_suppression_weight)
    if args.watershed_boundary_additive_weight is not None:
        cfg.watershed.boundary_additive_weight = float(args.watershed_boundary_additive_weight)
    if args.watershed_share_boundary_across_experts is not None:
        cfg.watershed.share_boundary_across_experts = args.watershed_share_boundary_across_experts
    if args.watershed_marker_rescue_enabled is not None:
        cfg.watershed.marker_rescue_enabled = args.watershed_marker_rescue_enabled
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
    if args.sam2_enabled is not None:
        cfg.sam2.enabled = args.sam2_enabled
    pipeline = SAMCellPipeline(cfg)
    rows = _read_rows(Path(args.devset_csv), args.limit)
    out_dir = Path(args.out_dir)
    per_image = evaluate_rows(pipeline, rows, out_dir if args.save_outputs or args.use_cache else None, use_cache=args.use_cache)
    if args.no_summary:
        print(f"completed {len(per_image)} rows without writing per_image.csv or summary.csv")
        return
    _write_csv(out_dir / "per_image.csv", per_image)

    summary_rows = [{"source": "ALL", **summarize_metrics(per_image)}]
    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in per_image:
        by_source[str(row["source"])].append(row)
    for source in sorted(by_source):
        summary_rows.append({"source": source, **summarize_metrics(by_source[source])})
    _write_csv(out_dir / "summary.csv", summary_rows)
    print(f"wrote {out_dir / 'per_image.csv'} and {out_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
