#!/usr/bin/env python3
"""Run a native SAM2 prompt-matched baseline on a small balanced CellCosmos subset.

This is a prompt-fair baseline, not the SAM-Cell main method:

- SAM-Cell semantic/proposal code is used only to create proposal boxes and
  coarse masks.
- Frozen SAM2 receives the same box + coarse-mask prompt per proposal.
- Coarse fallback candidates and SAM-Cell's candidate acceptance selector are
  not used.
- Minimal assembly is retained: empty-mask removal, duplicate suppression, and
  pixel competition to produce a non-overlapping instance label map.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
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
from sam_cell.postprocess.merge import pixel_competition, remove_duplicate_instances
from sam_cell.prompts.crop import make_adaptive_crop
from sam_cell.visualize import overlay_instances


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def balanced_subset(rows: list[dict[str, str]], per_source: int | None) -> list[dict[str, str]]:
    if per_source is None:
        return rows
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"]].append(row)
    selected: list[dict[str, str]] = []
    for source in sorted(by_source):
        selected.extend(by_source[source][:per_source])
    return selected


def save_outputs(out_dir: Path, stem: str, image: np.ndarray, label_map: np.ndarray, instances: list[dict]) -> None:
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    (out_dir / "overlays").mkdir(parents=True, exist_ok=True)
    (out_dir / "instances").mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(out_dir / "labels" / f"{stem}.tif", label_map.astype(np.int32))
    Image.fromarray(overlay_instances(image, label_map)).save(out_dir / "overlays" / f"{stem}.png")
    with (out_dir / "instances" / f"{stem}.json").open("w", encoding="utf-8") as f:
        json.dump(instances, f, ensure_ascii=False, indent=2)


def infer_prompt_matched(
    pipeline: SAMCellPipeline,
    image: np.ndarray,
    image_id: str,
    prompt_mode: str,
    score_threshold: float,
    duplicate_iou_threshold: float,
    use_pixel_logits: bool,
) -> dict:
    if pipeline.refiner is None:
        raise RuntimeError("SAM2 refiner is disabled; config must enable sam2 with prompt modes.")

    previous = pipeline._apply_source_overrides(image_id)
    try:
        semantic_maps_by_source = pipeline._predict_all_semantics(image, image_id=image_id)
        _fg_mask, _dist, _markers, proposal_label_map, proposals, fg_prob_by_source, _competition_fg_mask, proposal_diag = (
            pipeline._generate_multi_expert_proposals(semantic_maps_by_source, image_id=image_id, image=image)
        )
        default_fg_prob = pipeline._combined_fg_prob(fg_prob_by_source)
        refined_instances = []
        prompt_records = []
        for proposal in proposals:
            fg_prob = pipeline._fg_prob_for_proposal(proposal, fg_prob_by_source, default_fg_prob)
            crop = make_adaptive_crop(image, proposal, pipeline.cfg.crop, fg_prob=fg_prob)
            refined = pipeline.refiner.refine_one(crop, prompt_mode=prompt_mode)
            if refined.score < score_threshold:
                continue
            if not np.any(refined.local_mask):
                continue
            refined_instances.append(refined)
            prompt_records.append(
                {
                    "proposal_id": int(proposal.id),
                    "proposal_source": str(proposal.source),
                    "rank_score": float(getattr(proposal, "rank_score", 0.0)),
                    "sam2_score": float(refined.score),
                    "prompt_mode": prompt_mode,
                    "bbox_xyxy": list(map(int, proposal.bbox_xyxy)),
                }
            )
        refined_instances = remove_duplicate_instances(
            refined_instances,
            image.shape[:2],
            iou_threshold=duplicate_iou_threshold,
        )
        label_map, instances = pixel_competition(
            refined_instances,
            image.shape[:2],
            use_pixel_logits=use_pixel_logits,
            fg_mask=None,
            semantic_gate_dilation=0,
        )
        return {
            "label_map": label_map,
            "instances": instances,
            "proposal_label_map": proposal_label_map,
            "proposal_count": len(proposals),
            "sam2_candidate_count": len(prompt_records),
            "final_count": int(label_map.max()),
            "prompt_records": prompt_records,
            "proposal_diagnostics": proposal_diag,
        }
    finally:
        pipeline._restore_source_overrides(previous)


def make_summary(per_image: list[dict]) -> list[dict]:
    rows = [{"source": "ALL", **summarize_metrics(per_image)}]
    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in per_image:
        by_source[row["source"]].append(row)
    for source in sorted(by_source):
        rows.append({"source": source, **summarize_metrics(by_source[source])})
    source_rows = [row for row in rows if row["source"] != "ALL"]
    macro = {"source": "SOURCE_MACRO"}
    for metric in ["pq", "aji", "dice", "f1", "precision", "recall"]:
        vals = [float(row[metric]) for row in source_rows if metric in row]
        if vals:
            macro[metric] = float(np.mean(vals))
    rows.append(macro)
    return rows


def write_report(out_dir: Path, summary: list[dict], run_manifest: dict) -> None:
    lines = [
        "# Native SAM2 Prompt-Matched Baseline",
        "",
        "This baseline uses SAM-Cell proposals only to provide box + coarse-mask prompts to frozen SAM2.",
        "It disables coarse fallback and SAM-Cell candidate acceptance selection.",
        "",
        f"prompt_mode: `{run_manifest['prompt_mode']}`",
        f"n: `{run_manifest['n']}`",
        "",
        "| source | PQ | AJI | Dice |",
        "|---|---:|---:|---:|",
    ]
    for row in summary:
        if row["source"] == "SOURCE_MACRO":
            continue
        lines.append(
            "| {source} | {pq:.6f} | {aji:.6f} | {dice:.6f} |".format(
                source=row["source"],
                pq=float(row.get("pq", 0.0)),
                aji=float(row.get("aji", 0.0)),
                dice=float(row.get("dice", 0.0)),
            )
        )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--per_source", type=int, default=10)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--prompt_mode", default="box_mask", choices=["box_mask", "box_only", "mask_only"])
    parser.add_argument("--score_threshold", type=float, default=0.0)
    parser.add_argument("--duplicate_iou_threshold", type=float, default=0.85)
    parser.add_argument("--use_pixel_logits", action="store_true")
    parser.add_argument("--save_outputs", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    cfg.sam2.enabled = True
    cfg.sam2.prompt_modes = [args.prompt_mode]
    cfg.sam2.score_threshold = float(args.score_threshold)
    cfg.merge.keep_coarse_candidate = False
    cfg.merge.semantic_gate_dilation = 0
    cfg.merge.use_pixel_logits = bool(args.use_pixel_logits)
    cfg.merge.duplicate_iou_threshold = float(args.duplicate_iou_threshold)
    pipeline = SAMCellPipeline(cfg)

    rows = balanced_subset(read_rows(Path(args.manifest)), args.per_source)
    if args.limit:
        rows = rows[: args.limit]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "manifest.csv", rows)

    per_image = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        mask_path = Path(row["mask_path"])
        source = row.get("source", image_path.name.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] {source} {image_path.name}", flush=True)
        image = load_image(image_path, normalize_mode=cfg.image.normalize_mode)
        gt = load_label_map(mask_path)
        result = infer_prompt_matched(
            pipeline,
            image,
            image_path.stem,
            prompt_mode=args.prompt_mode,
            score_threshold=float(args.score_threshold),
            duplicate_iou_threshold=float(args.duplicate_iou_threshold),
            use_pixel_logits=bool(args.use_pixel_logits),
        )
        metrics = instance_metrics(result["label_map"], gt)
        proposal_metrics = instance_metrics(result["proposal_label_map"], gt) if np.any(result["proposal_label_map"]) else {}
        record = {
            "method": "sam2_prompt_matched_box_mask",
            "source": source,
            "image": image_path.name,
            "proposals": result["proposal_count"],
            "sam2_candidates": result["sam2_candidate_count"],
            "final_instances": result["final_count"],
            **metrics,
            **{f"proposal_{key}": value for key, value in proposal_metrics.items()},
        }
        per_image.append(record)
        if args.save_outputs:
            save_outputs(out_dir, image_path.stem, image, result["label_map"], result["instances"])
            with (out_dir / "instances" / f"{image_path.stem}_prompts.json").open("w", encoding="utf-8") as f:
                json.dump(result["prompt_records"], f, ensure_ascii=False, indent=2)

    summary = make_summary(per_image)
    write_csv(out_dir / "per_image.csv", per_image)
    write_csv(out_dir / "summary.csv", summary)
    run_manifest = {
        "method": "sam2_prompt_matched_box_mask",
        "config": str(Path(args.config).resolve()),
        "manifest": str(Path(args.manifest).resolve()),
        "out_dir": str(out_dir.resolve()),
        "n": len(rows),
        "per_source": args.per_source,
        "prompt_mode": args.prompt_mode,
        "score_threshold": args.score_threshold,
        "duplicate_iou_threshold": args.duplicate_iou_threshold,
        "use_pixel_logits": bool(args.use_pixel_logits),
        "save_outputs": bool(args.save_outputs),
        "notes": "SAM-Cell proposals create box+coarse-mask prompts; SAM2 masks are assembled with duplicate suppression and pixel competition only.",
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, summary, run_manifest)
    print(f"wrote {out_dir / 'summary.csv'}", flush=True)


if __name__ == "__main__":
    main()
