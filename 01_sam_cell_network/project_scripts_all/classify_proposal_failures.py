from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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


def _float(row: dict | None, key: str, default: float = 0.0) -> float:
    if row is None:
        return default
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _int(row: dict | None, key: str, default: int = 0) -> int:
    if row is None:
        return default
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return default


def _action_for(error_type: str) -> str:
    return {
        "semantic_or_marker_miss": "increase raw proposal recall: lower thresholds, stronger adaptive markers, or stronger Cellpose-style proposal front-end",
        "merge_lost_recall": "relax duplicate merge or prefer split/local candidates before global merge",
        "ranker_filtered_true_cells": "lower/retune ranker threshold or train recall-aware ranker on similar cases",
        "fp_duplicate_pressure": "tighten selector/NMS and add duplicate/containment features",
        "nonoverlap_layout_loss": "change proposal ordering/selector because oracle candidates exist but label-map conflicts lose them",
        "sam2_or_final_merge_loss": "inspect SAM2 acceptance/merge gates; proposal stage is already better than final",
        "residual_fn_limited": "add targeted split/low-threshold candidates while preserving precision",
        "residual_fp_limited": "tighten selector/ranker; current candidates oversegment",
        "balanced_low_quality": "inspect overlay; likely mixed split/merge/shape quality issue",
    }.get(error_type, "inspect overlay")


def _classify_image(stages: dict[str, dict], args: argparse.Namespace) -> dict:
    raw = stages.get("raw_expert_unranked")
    merged = stages.get("merged_unranked")
    ranked = stages.get("ranked_merged")
    label = stages.get("ranked_label_map_nonoverlap")
    final = stages.get("final_cached") or label or ranked

    raw_recall = _float(raw, "gt_recall_at_iou")
    merged_recall = _float(merged, "gt_recall_at_iou", raw_recall)
    ranked_recall = _float(ranked, "gt_recall_at_iou", merged_recall)
    label_pq = _float(label, "oracle_pq", _float(ranked, "oracle_pq"))
    ranked_pq = _float(ranked, "oracle_pq")
    final_pq = _float(final, "oracle_pq", label_pq)
    final_recall = _float(final, "gt_recall_at_iou", ranked_recall)
    final_precision = _float(final, "proposal_precision_at_iou", _float(ranked, "proposal_precision_at_iou"))

    if raw_recall < args.raw_recall_target:
        error_type = "semantic_or_marker_miss"
    elif raw_recall - merged_recall > args.recall_drop_tolerance:
        error_type = "merge_lost_recall"
    elif merged_recall - ranked_recall > args.recall_drop_tolerance:
        error_type = "ranker_filtered_true_cells"
    elif final_precision < args.precision_target and _int(ranked, "oracle_fp") >= args.fp_count_threshold:
        error_type = "fp_duplicate_pressure"
    elif ranked_pq - label_pq > args.pq_drop_tolerance:
        error_type = "nonoverlap_layout_loss"
    elif label_pq - final_pq > args.pq_drop_tolerance:
        error_type = "sam2_or_final_merge_loss"
    elif final_recall < args.final_recall_target and final_precision >= args.precision_target:
        error_type = "residual_fn_limited"
    elif final_precision < args.precision_target:
        error_type = "residual_fp_limited"
    else:
        error_type = "balanced_low_quality"

    seed = next(iter(stages.values()))
    return {
        "source": seed.get("source", ""),
        "image": seed.get("image", ""),
        "error_type": error_type,
        "recommended_action": _action_for(error_type),
        "raw_recall": raw_recall,
        "merged_recall": merged_recall,
        "ranked_recall": ranked_recall,
        "final_recall": final_recall,
        "final_precision": final_precision,
        "raw_pq": _float(raw, "oracle_pq"),
        "merged_pq": _float(merged, "oracle_pq"),
        "ranked_pq": ranked_pq,
        "label_pq": label_pq,
        "final_pq": final_pq,
        "ranked_fp": _int(ranked, "oracle_fp"),
        "ranked_fn": _int(ranked, "oracle_fn"),
        "gt_n": _int(ranked, "gt_n", _int(raw, "gt_n")),
        "proposal_n": _int(ranked, "proposal_n"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify proposal/final failure modes from proposal_oracle_diagnosis outputs.")
    parser.add_argument("--per_image_stage_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--raw_recall_target", type=float, default=0.80)
    parser.add_argument("--final_recall_target", type=float, default=0.78)
    parser.add_argument("--precision_target", type=float, default=0.80)
    parser.add_argument("--recall_drop_tolerance", type=float, default=0.03)
    parser.add_argument("--pq_drop_tolerance", type=float, default=0.03)
    parser.add_argument("--fp_count_threshold", type=int, default=10)
    args = parser.parse_args()

    by_image: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in _read_rows(Path(args.per_image_stage_csv)):
        if row.get("proposal_source", "ALL") != "ALL":
            continue
        by_image[(row.get("source", ""), row.get("image", ""))][row["stage"]] = row

    classified = [_classify_image(stages, args) for _key, stages in sorted(by_image.items())]
    classified = sorted(classified, key=lambda row: float(row["final_pq"]))
    out_dir = Path(args.out_dir)
    _write_csv(out_dir / "classified_failures.csv", classified)

    counts = Counter(row["error_type"] for row in classified)
    summary = [
        {
            "error_type": error_type,
            "n": count,
            "fraction": count / float(max(1, len(classified))),
            "recommended_action": _action_for(error_type),
        }
        for error_type, count in counts.most_common()
    ]
    _write_csv(out_dir / "failure_type_summary.csv", summary)

    worst = []
    seen = set()
    for row in classified:
        error_type = row["error_type"]
        if (error_type, row["image"]) in seen:
            continue
        if sum(1 for item in worst if item["error_type"] == error_type) >= 5:
            continue
        seen.add((error_type, row["image"]))
        worst.append(row)
    _write_csv(out_dir / "worst_examples_by_failure_type.csv", worst)
    print(f"wrote {out_dir / 'failure_type_summary.csv'}")


if __name__ == "__main__":
    main()
