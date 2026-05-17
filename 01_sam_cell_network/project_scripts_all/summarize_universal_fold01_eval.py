from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_summary(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["source"]: row for row in csv.DictReader(f)}


def _f(row: dict[str, str], key: str) -> float:
    return float(row.get(key, 0.0) or 0.0)


def _metric(summary: dict[str, dict[str, str]], source: str, key: str) -> float | None:
    row = summary.get(source)
    if row is None:
        return None
    return _f(row, key)


def _fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.4f}"


def _load_optional(path: Path | None) -> dict[str, dict[str, str]] | None:
    if path is None or not path.exists():
        return None
    return _read_summary(path)


def _decision(primary: dict[str, dict[str, str]], baseline620: dict[str, dict[str, str]] | None) -> list[str]:
    all_delta = _metric(primary, "ALL", "delta_pq") or 0.0
    win_rate = _metric(primary, "ALL", "sam_win_rate") or 0.0
    cellpose_delta = _metric(primary, "cellpose", "delta_pq")
    non_cellpose = ["dsb2018", "livecell", "pannuke", "tissuenet"]
    non_cellpose_positive = sum((_metric(primary, s, "delta_pq") or 0.0) > 0.0 for s in non_cellpose)
    improved_vs_620 = None
    cellpose_vs_620 = None
    if baseline620 is not None:
        improved_vs_620 = (_metric(primary, "ALL", "sam_pq") or 0.0) - (_metric(baseline620, "ALL", "sam_pq") or 0.0)
        cellpose_vs_620 = (_metric(primary, "cellpose", "sam_pq") or 0.0) - (_metric(baseline620, "cellpose", "sam_pq") or 0.0)

    decisions = []
    if all_delta > 0.05 and win_rate >= 0.6 and (cellpose_delta is None or cellpose_delta > -0.10):
        decisions.append("Primary plan: keep Dataset621 as the main semantic model; after all five folds finish, run the full 250-image benchmark.")
    elif all_delta > 0.0 and non_cellpose_positive >= 3 and cellpose_delta is not None and cellpose_delta <= -0.10:
        decisions.append("Primary plan: Dataset621 improves broad-domain behavior but still damages Cellpose-style images; keep it for non-Cellpose domains and develop a dual-semantic/fusion fallback before full claims.")
    elif all_delta > 0.0:
        decisions.append("Primary plan: Dataset621 is directionally useful but not decisive; run source-level diagnostics before scaling to 250 images.")
    else:
        decisions.append("Primary plan: do not scale this checkpoint yet; inspect semantic foreground recall, boundary labels, and watershed thresholds first.")

    if improved_vs_620 is not None:
        if improved_vs_620 > 0.03:
            decisions.append(f"Compared with Dataset620 fold01, Dataset621 improves overall SAM-Cell PQ by {improved_vs_620:.4f}.")
        elif improved_vs_620 < -0.03:
            decisions.append(f"Compared with Dataset620 fold01, Dataset621 drops overall SAM-Cell PQ by {abs(improved_vs_620):.4f}; prioritize failure analysis over more training.")
        else:
            decisions.append(f"Compared with Dataset620 fold01, Dataset621 is roughly tied overall ({improved_vs_620:+.4f} PQ).")
    if cellpose_vs_620 is not None:
        if cellpose_vs_620 > 0.10:
            decisions.append(f"Cellpose-style recovery is meaningful versus Dataset620 ({cellpose_vs_620:+.4f} PQ).")
        elif cellpose_vs_620 < -0.10:
            decisions.append(f"Cellpose-style performance is worse than Dataset620 ({cellpose_vs_620:+.4f} PQ); the issue is not fixed by rebalancing alone.")
        else:
            decisions.append(f"Cellpose-style performance is near Dataset620 ({cellpose_vs_620:+.4f} PQ); inspect per-image FP/FN before deciding.")
    return decisions


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize fold01 auto-evaluation and write a markdown plan.")
    parser.add_argument("--primary_summary", required=True)
    parser.add_argument("--final_summary")
    parser.add_argument("--dataset620_summary", default="outputs/benchmark_splits_large/compare_cellcosmos_fold01_best_eval25/summary_by_source.csv")
    parser.add_argument("--out_md", required=True)
    parser.add_argument("--out_json")
    args = parser.parse_args()

    primary = _read_summary(Path(args.primary_summary))
    final = _load_optional(Path(args.final_summary) if args.final_summary else None)
    baseline620 = _load_optional(Path(args.dataset620_summary))
    sources = ["ALL", "cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]

    lines = [
        "# Dataset621 Fold01 Auto-Eval",
        "",
        "Primary checkpoint: `checkpoint_best.pth` for folds `[0, 1]`.",
        "",
        "## Best Checkpoint vs Cellpose",
        "",
        "| source | n | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate | SAM-Cell AJI | Cellpose AJI |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for source in sources:
        row = primary.get(source)
        if row is None:
            continue
        lines.append(
            "| {source} | {n} | {sam_pq} | {cp_pq} | {delta_pq} | {win_rate} | {sam_aji} | {cp_aji} |".format(
                source=source,
                n=row.get("n", "NA"),
                sam_pq=_fmt(_f(row, "sam_pq")),
                cp_pq=_fmt(_f(row, "cellpose_pq")),
                delta_pq=_fmt(_f(row, "delta_pq")),
                win_rate=_fmt(_f(row, "sam_win_rate")),
                sam_aji=_fmt(_f(row, "sam_aji")),
                cp_aji=_fmt(_f(row, "cellpose_aji")),
            )
        )

    if baseline620 is not None:
        lines.extend(
            [
                "",
                "## Dataset621 Best vs Dataset620 Fold01 Best",
                "",
                "| source | Dataset621 PQ | Dataset620 PQ | Diff |",
                "|---|---:|---:|---:|",
            ]
        )
        for source in sources:
            p = _metric(primary, source, "sam_pq")
            b = _metric(baseline620, source, "sam_pq")
            diff = None if p is None or b is None else p - b
            lines.append(f"| {source} | {_fmt(p)} | {_fmt(b)} | {_fmt(diff)} |")

    if final is not None:
        lines.extend(
            [
                "",
                "## Final Checkpoint Sanity Check",
                "",
                "| source | Final PQ | Best PQ | Final-Best |",
                "|---|---:|---:|---:|",
            ]
        )
        for source in sources:
            f = _metric(final, source, "sam_pq")
            b = _metric(primary, source, "sam_pq")
            diff = None if f is None or b is None else f - b
            lines.append(f"| {source} | {_fmt(f)} | {_fmt(b)} | {_fmt(diff)} |")

    decisions = _decision(primary, baseline620)
    lines.extend(["", "## Decision", ""])
    for item in decisions:
        lines.append(f"- {item}")
    lines.append("")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")

    if args.out_json:
        payload = {
            "primary_summary": str(args.primary_summary),
            "final_summary": str(args.final_summary) if args.final_summary else None,
            "dataset620_summary": str(args.dataset620_summary) if baseline620 is not None else None,
            "decision": decisions,
        }
        Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(out_md)


if __name__ == "__main__":
    main()
