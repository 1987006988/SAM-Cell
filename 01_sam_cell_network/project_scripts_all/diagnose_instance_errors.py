from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


def _f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _category(row: dict[str, str]) -> str:
    sam_pred = _f(row, "sam_pred_n")
    sam_gt = max(1.0, _f(row, "sam_gt_n"))
    sam_precision = _f(row, "sam_precision")
    sam_recall = _f(row, "sam_recall")
    cp_precision = _f(row, "cellpose_precision")
    cp_recall = _f(row, "cellpose_recall")
    sam_fp = _f(row, "sam_fp")
    sam_fn = _f(row, "sam_fn")
    cp_fp = _f(row, "cellpose_fp")
    cp_fn = _f(row, "cellpose_fn")

    if sam_pred > 1.25 * sam_gt and sam_precision + 0.05 < sam_recall:
        return "over_split_or_fp"
    if sam_pred < 0.75 * sam_gt or sam_recall + 0.05 < sam_precision:
        return "under_split_or_fn"
    if sam_fp > cp_fp + 2 or sam_precision + 0.05 < cp_precision:
        return "fp_heavy"
    if sam_fn > cp_fn + 2 or sam_recall + 0.05 < cp_recall:
        return "fn_heavy"
    if _f(row, "delta_pq") < 0:
        return "quality_gap"
    return "sam_advantage_or_tie"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize SAM-Cell vs baseline instance error modes from compare_methods output.")
    parser.add_argument("--compare_csv", required=True, help="Path to compare_methods per_image.csv")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--worst_k", type=int, default=20)
    args = parser.parse_args()

    rows = _read_rows(Path(args.compare_csv))
    annotated = []
    for row in rows:
        item = dict(row)
        item["error_category"] = _category(row)
        annotated.append(item)

    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in annotated:
        by_source[row.get("source", "unknown")].append(row)

    summary = []
    for source, source_rows in [("ALL", annotated), *sorted(by_source.items())]:
        counts = Counter(row["error_category"] for row in source_rows)
        deltas = [_f(row, "delta_pq") for row in source_rows]
        summary.append(
            {
                "source": source,
                "n": len(source_rows),
                "mean_delta_pq": mean(deltas) if deltas else 0.0,
                "negative_delta_n": sum(1 for value in deltas if value < 0),
                "over_split_or_fp": counts["over_split_or_fp"],
                "under_split_or_fn": counts["under_split_or_fn"],
                "fp_heavy": counts["fp_heavy"],
                "fn_heavy": counts["fn_heavy"],
                "quality_gap": counts["quality_gap"],
                "sam_advantage_or_tie": counts["sam_advantage_or_tie"],
            }
        )

    worst = sorted(annotated, key=lambda row: _f(row, "delta_pq"))[: args.worst_k]
    out_dir = Path(args.out_dir)
    _write_csv(out_dir / "per_image_diagnosis.csv", annotated)
    _write_csv(out_dir / "summary_by_source.csv", summary)
    _write_csv(out_dir / "worst_cases.csv", worst)
    print(f"wrote {out_dir / 'summary_by_source.csv'}")


if __name__ == "__main__":
    main()
