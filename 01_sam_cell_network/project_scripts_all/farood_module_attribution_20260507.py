from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import sys
from typing import Iterator

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.visualize import overlay_instances

METRICS = ("pq", "aji", "dice")


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_label(path: Path, label: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(path, label.astype(np.int32, copy=False))


def _save_overlay(path: Path, image: np.ndarray, label: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(overlay_instances(image, label)).save(path)


def _read_label(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    return tifffile.imread(path).astype(np.int32, copy=False)


def _semantic_cc_map(pipeline: SAMCellPipeline, image: np.ndarray, image_id: str) -> np.ndarray:
    previous = pipeline._apply_source_overrides(image_id)
    try:
        semantic_maps = pipeline._predict_all_semantics(image, image_id=image_id)
        combined_mask = np.zeros(image.shape[:2], dtype=bool)
        for expert in pipeline._active_semantic_experts(image_id):
            source = pipeline._expert_source(expert)
            fg_prob = semantic_maps[source]["fg_prob"]
            if fg_prob is None:
                continue
            threshold = float(expert.foreground_threshold)
            combined_mask |= pipeline._foreground_mask(fg_prob, threshold, semantic_cfg=expert)
        label_map, _n = ndi.label(combined_mask)
        return label_map.astype(np.int32, copy=False)
    finally:
        pipeline._restore_source_overrides(previous)


class _TemporaryConfig:
    def __init__(self, pipeline: SAMCellPipeline) -> None:
        self.pipeline = pipeline
        self.saved: list[tuple[object, str, object]] = []

    def set(self, obj: object, name: str, value: object) -> None:
        self.saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def __enter__(self) -> "_TemporaryConfig":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for obj, name, value in reversed(self.saved):
            setattr(obj, name, value)


def _raw_watershed_map(pipeline: SAMCellPipeline, image: np.ndarray, image_id: str) -> np.ndarray:
    previous = pipeline._apply_source_overrides(image_id)
    try:
        with _TemporaryConfig(pipeline) as temp:
            temp.set(pipeline.cfg.proposal_ranker, "enabled", False)
            temp.set(pipeline.cfg.proposal_repair, "enabled", False)
            temp.set(pipeline.cfg.proposal_repair, "set_selector_enabled", False)
            temp.set(pipeline.cfg.proposal_repair, "split_enabled", False)
            temp.set(pipeline.cfg.separator_proposals, "enabled", False)
            semantic_maps = pipeline._predict_all_semantics(image, image_id=image_id)
            _fg_mask, _dist, _markers, proposal_label_map, _proposals, _fg_probs, _competition, _diag = (
                pipeline._generate_multi_expert_proposals(semantic_maps, image_id=image_id, image=image)
            )
            return proposal_label_map.astype(np.int32, copy=False)
    finally:
        pipeline._restore_source_overrides(previous)


def _summary_rows(per_image: list[dict[str, object]]) -> list[dict[str, object]]:
    by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in per_image:
        by_source[str(row["source"])].append(row)
    rows: list[dict[str, object]] = [
        {"source": "ALL", "n": len(per_image), **summarize_metrics(per_image)},
    ]
    for source in sorted(by_source):
        source_rows = by_source[source]
        rows.append({"source": source, "n": len(source_rows), **summarize_metrics(source_rows)})
    source_only = [row for row in rows if row["source"] != "ALL"]
    macro: dict[str, object] = {"source": "SOURCE_MACRO", "n": len(source_only)}
    for metric in METRICS:
        values = [float(row[metric]) for row in source_only if metric in row]
        macro[metric] = sum(values) / len(values) if values else 0.0
    rows.append(macro)
    return rows


def _metric_row(method: str, source: str, image_name: str, pred: np.ndarray, gt: np.ndarray, pred_path: Path) -> dict[str, object]:
    return {
        "method": method,
        "source": source,
        "image": image_name,
        "prediction_path": str(pred_path),
        **instance_metrics(pred, gt),
    }


def _maybe_existing(path: Path, skip_existing: bool) -> np.ndarray | None:
    if skip_existing and path.exists():
        return _read_label(path)
    return None


def _method_dirs(out_dir: Path, method: str) -> tuple[Path, Path, Path]:
    root = out_dir / method
    return root / "labels", root / "overlays", root


def _source_macro(summary: list[dict[str, object]], metric: str) -> float:
    row = next(row for row in summary if row["source"] == "SOURCE_MACRO")
    return float(row[metric])


def _all_metric(summary: list[dict[str, object]], metric: str) -> float:
    row = next(row for row in summary if row["source"] == "ALL")
    return float(row[metric])


def _write_interpretation(out_dir: Path, summaries: dict[str, list[dict[str, object]]], cellpose_summary: Path | None) -> None:
    sequence = [
        ("semantic_cc", "nnU-Net semantic foreground connected components"),
        ("raw_watershed", "EDT/watershed instance separation"),
        ("current_proposal", "current proposal selection/merging before SAM2"),
        ("coarse_no_sam2", "adaptive crop plus coarse-mask reinsertion without SAM2"),
        ("full_samcell", "SAM2 refinement with box+mask prompts"),
    ]
    lines = [
        "# Far-OOD SAM-Cell Module Attribution",
        "",
        "This attribution uses the frozen Far-OOD manifest and reports mean per-image metrics.",
        "",
        "| stage | module interpretation | ALL PQ | SOURCE_MACRO PQ | ALL AJI | ALL Dice |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for method, label in sequence:
        if method not in summaries:
            continue
        summary = summaries[method]
        lines.append(
            "| {method} | {label} | {all_pq:.6f} | {macro_pq:.6f} | {all_aji:.6f} | {all_dice:.6f} |".format(
                method=method,
                label=label,
                all_pq=_all_metric(summary, "pq"),
                macro_pq=_source_macro(summary, "pq"),
                all_aji=_all_metric(summary, "aji"),
                all_dice=_all_metric(summary, "dice"),
            )
        )

    lines.extend(["", "## PQ Deltas", "", "| delta | ALL PQ delta | interpretation |", "|---|---:|---|"])
    pairs = [
        ("semantic_cc", "raw_watershed", "effect of EDT/watershed over semantic connected components"),
        ("raw_watershed", "current_proposal", "effect of current proposal filtering/selection/merge"),
        ("current_proposal", "coarse_no_sam2", "effect of crop/coarse-mask reinsertion without SAM2"),
        ("coarse_no_sam2", "full_samcell", "effect of SAM2 refinement"),
    ]
    best_name = None
    best_delta = -10.0
    for before, after, label in pairs:
        if before not in summaries or after not in summaries:
            continue
        delta = _all_metric(summaries[after], "pq") - _all_metric(summaries[before], "pq")
        if delta > best_delta:
            best_delta = delta
            best_name = label
        lines.append(f"| {before} -> {after} | {delta:.6f} | {label} |")

    if cellpose_summary and cellpose_summary.exists():
        rows = _read_rows(cellpose_summary)
        all_row = next((row for row in rows if row.get("source") == "ALL"), None)
        if all_row is not None and "full_samcell" in summaries:
            cellpose_pq = float(all_row["pq"])
            samcell_pq = _all_metric(summaries["full_samcell"], "pq")
            lines.extend(
                [
                    "",
                    "## Comparator Anchor",
                    "",
                    f"- Cellpose official cyto3 Far-OOD ALL PQ: {cellpose_pq:.6f}",
                    f"- Full SAM-Cell Far-OOD ALL PQ: {samcell_pq:.6f}",
                    f"- Full SAM-Cell minus Cellpose ALL PQ: {samcell_pq - cellpose_pq:.6f}",
                ]
            )

    if best_name is not None:
        lines.extend(
            [
                "",
                "## Current Evidence-Based Answer",
                "",
                f"The largest positive ALL-PQ step in this staged attribution is: {best_name} ({best_delta:.6f}).",
                "Treat this as a quantitative attribution within the current method, not a causal proof independent of component interactions.",
            ]
        )

    (out_dir / "interpretation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_delta_analysis(out_dir: Path, per_method: dict[str, list[dict[str, object]]]) -> None:
    pairs = [
        ("semantic_cc", "raw_watershed", "edt_watershed_over_semantic_cc"),
        ("raw_watershed", "current_proposal", "current_proposal_selection_over_raw_watershed"),
        ("current_proposal", "coarse_no_sam2", "crop_coarse_reinsertion_over_proposal_map"),
        ("coarse_no_sam2", "full_samcell", "sam2_refinement_over_coarse_no_sam2"),
    ]
    by_method_image = {
        method: {str(row["image"]): row for row in rows}
        for method, rows in per_method.items()
    }
    delta_rows: list[dict[str, object]] = []
    for before, after, label in pairs:
        before_rows = by_method_image.get(before, {})
        after_rows = by_method_image.get(after, {})
        for image_name in sorted(set(before_rows) & set(after_rows)):
            before_row = before_rows[image_name]
            after_row = after_rows[image_name]
            row = {
                "delta": label,
                "before_method": before,
                "after_method": after,
                "source": after_row["source"],
                "image": image_name,
            }
            for metric in METRICS:
                before_value = float(before_row[metric])
                after_value = float(after_row[metric])
                row[f"before_{metric}"] = before_value
                row[f"after_{metric}"] = after_value
                row[f"delta_{metric}"] = after_value - before_value
            row["pq_improved"] = float(row["delta_pq"]) > 0.0
            row["pq_worsened"] = float(row["delta_pq"]) < 0.0
            delta_rows.append(row)

    _write_csv(out_dir / "paired_delta_per_image.csv", delta_rows)

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in delta_rows:
        grouped[(str(row["delta"]), str(row["source"]))].append(row)
        grouped[(str(row["delta"]), "ALL")].append(row)

    summary_rows: list[dict[str, object]] = []
    for (delta_name, source), rows in sorted(grouped.items()):
        n = len(rows)
        summary: dict[str, object] = {
            "delta": delta_name,
            "source": source,
            "n": n,
            "pq_win_rate": sum(1 for row in rows if row["pq_improved"]) / float(max(1, n)),
            "pq_loss_rate": sum(1 for row in rows if row["pq_worsened"]) / float(max(1, n)),
        }
        for metric in METRICS:
            values = [float(row[f"delta_{metric}"]) for row in rows]
            summary[f"mean_delta_{metric}"] = float(np.mean(values)) if values else 0.0
            summary[f"median_delta_{metric}"] = float(np.median(values)) if values else 0.0
        summary_rows.append(summary)
    _write_csv(out_dir / "paired_delta_summary.csv", summary_rows)


def _append_delta_interpretation(out_dir: Path) -> None:
    summary_path = out_dir / "paired_delta_summary.csv"
    interpretation_path = out_dir / "interpretation.md"
    if not summary_path.exists() or not interpretation_path.exists():
        return
    rows = [row for row in _read_rows(summary_path) if row.get("source") == "ALL"]
    if not rows:
        return
    lines = [
        "",
        "## Paired Per-Image Delta Check",
        "",
        "| delta | mean delta PQ | median delta PQ | PQ win rate |",
        "|---|---:|---:|---:|",
    ]
    best = None
    for row in rows:
        mean_delta = float(row["mean_delta_pq"])
        if best is None or mean_delta > float(best["mean_delta_pq"]):
            best = row
        lines.append(
            "| {delta} | {mean_delta_pq:.6f} | {median_delta_pq:.6f} | {pq_win_rate:.3f} |".format(
                delta=row["delta"],
                mean_delta_pq=mean_delta,
                median_delta_pq=float(row["median_delta_pq"]),
                pq_win_rate=float(row["pq_win_rate"]),
            )
        )
    if best is not None:
        lines.extend(
            [
                "",
                "Paired-delta conclusion:",
                "",
                "- The largest mean paired per-image PQ gain is `{}` ({:.6f}).".format(
                    best["delta"],
                    float(best["mean_delta_pq"]),
                ),
            ]
        )
    with interpretation_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Far-OOD module attribution for SAM-Cell.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--full_samcell_label_dir", required=True)
    parser.add_argument("--cellpose_farood_summary")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start_index", type=int, default=0, help="0-based inclusive row offset after applying --limit.")
    parser.add_argument("--end_index", type=int, help="0-based exclusive row offset after applying --limit.")
    parser.add_argument("--save_overlays", action="store_true")
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--no_summary", action="store_true", help="Only write per-stage labels/overlays for this shard; do not write summaries.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    cfg.sam2.enabled = False
    cfg.sam2.prompt_modes = []
    pipeline = SAMCellPipeline(cfg)

    all_rows = _read_rows(Path(args.manifest_csv), args.limit)
    rows = all_rows[int(args.start_index) : args.end_index]
    out_dir = Path(args.out_dir)
    full_label_dir = Path(args.full_samcell_label_dir)
    methods = ["semantic_cc", "raw_watershed", "current_proposal", "coarse_no_sam2", "full_samcell"]
    per_method: dict[str, list[dict[str, object]]] = {method: [] for method in methods}

    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        mask_path = Path(row["mask_path"])
        image_name = row.get("image_name") or image_path.name
        stem = image_path.stem
        source = row.get("source", stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] {source} {image_name}", flush=True)
        image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
        gt = load_label_map(mask_path)

        semantic_path = _method_dirs(out_dir, "semantic_cc")[0] / f"{stem}.tif"
        semantic = _maybe_existing(semantic_path, args.skip_existing)
        if semantic is None:
            semantic = _semantic_cc_map(pipeline, image, stem)
            _write_label(semantic_path, semantic)
        per_method["semantic_cc"].append(_metric_row("semantic_cc", source, image_name, semantic, gt, semantic_path))

        raw_path = _method_dirs(out_dir, "raw_watershed")[0] / f"{stem}.tif"
        raw = _maybe_existing(raw_path, args.skip_existing)
        if raw is None:
            raw = _raw_watershed_map(pipeline, image, stem)
            _write_label(raw_path, raw)
        per_method["raw_watershed"].append(_metric_row("raw_watershed", source, image_name, raw, gt, raw_path))

        current_proposal_path = _method_dirs(out_dir, "current_proposal")[0] / f"{stem}.tif"
        coarse_path = _method_dirs(out_dir, "coarse_no_sam2")[0] / f"{stem}.tif"
        current_proposal = _maybe_existing(current_proposal_path, args.skip_existing)
        coarse = _maybe_existing(coarse_path, args.skip_existing)
        if current_proposal is None or coarse is None:
            result = pipeline.infer(image, image_id=stem)
            current_proposal = result["proposal_label_map"].astype(np.int32, copy=False)
            coarse = result["instance_map"].astype(np.int32, copy=False)
            _write_label(current_proposal_path, current_proposal)
            _write_label(coarse_path, coarse)
        per_method["current_proposal"].append(
            _metric_row("current_proposal", source, image_name, current_proposal, gt, current_proposal_path)
        )
        per_method["coarse_no_sam2"].append(_metric_row("coarse_no_sam2", source, image_name, coarse, gt, coarse_path))

        full_path = full_label_dir / f"{stem}.tif"
        full = _read_label(full_path)
        per_method["full_samcell"].append(_metric_row("full_samcell", source, image_name, full, gt, full_path))

        if args.save_overlays:
            for method, label in [
                ("semantic_cc", semantic),
                ("raw_watershed", raw),
                ("current_proposal", current_proposal),
                ("coarse_no_sam2", coarse),
                ("full_samcell", full),
            ]:
                _save_overlay(_method_dirs(out_dir, method)[1] / f"{stem}.png", image, label)

    if args.no_summary:
        print(f"completed shard rows={len(rows)} without writing summary files")
        return

    summaries: dict[str, list[dict[str, object]]] = {}
    combined_summary: list[dict[str, object]] = []
    for method in methods:
        method_out = _method_dirs(out_dir, method)[2]
        _write_csv(method_out / "per_image.csv", per_method[method])
        summary = _summary_rows(per_method[method])
        summaries[method] = summary
        _write_csv(method_out / "summary.csv", summary)
        for summary_row in summary:
            combined_summary.append({"method": method, **summary_row})

    _write_csv(out_dir / "combined_summary.csv", combined_summary)
    _write_delta_analysis(out_dir, per_method)
    _write_interpretation(out_dir, summaries, Path(args.cellpose_farood_summary) if args.cellpose_farood_summary else None)
    _append_delta_interpretation(out_dir)
    (out_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "config": args.config,
                "manifest_csv": args.manifest_csv,
                "out_dir": str(out_dir),
                "full_samcell_label_dir": args.full_samcell_label_dir,
                "cellpose_farood_summary": args.cellpose_farood_summary,
                "limit": args.limit,
                "start_index": args.start_index,
                "end_index": args.end_index,
                "methods": methods,
                "n": len(rows),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out_dir / 'combined_summary.csv'}")
    print(f"wrote {out_dir / 'interpretation.md'}")


if __name__ == "__main__":
    main()
