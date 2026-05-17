from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _metric_row(rows: list[dict[str, str]], method: str, source: str = "ALL") -> dict[str, str]:
    for row in rows:
        if row.get("method") == method and row.get("source") == source:
            return row
    raise KeyError(f"Missing row method={method!r} source={source!r}")


def _all_rows(rows: list[dict[str, str]], source: str = "ALL") -> list[dict[str, str]]:
    return [row for row in rows if row.get("source") == source]


def _float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _best_farood_delta(rows: list[dict[str, str]]) -> dict[str, str]:
    all_rows = [row for row in rows if row.get("source") == "ALL"]
    if not all_rows:
        raise ValueError("No ALL rows in Far-OOD paired delta summary")
    return max(all_rows, key=lambda row: float(row["mean_delta_pq"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a concise final report for the current active SAM-Cell goal.")
    parser.add_argument("--full_root", default="/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")
    parser.add_argument("--farood_out", default="/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507")
    parser.add_argument("--audit_json", default=None)
    parser.add_argument("--out_md", default=None)
    args = parser.parse_args()

    full_root = Path(args.full_root)
    farood_out = Path(args.farood_out)
    comparison_dir = full_root / "metrics" / "full_model_comparison_20260507"
    comparison = _read_csv(comparison_dir / "full_model_comparison_pq_aji_dice.csv")
    baseline_delta = _read_csv(comparison_dir / "samcell_delta_vs_baselines.csv")
    farood_summary = _read_csv(farood_out / "combined_summary.csv")
    farood_delta = _read_csv(farood_out / "paired_delta_summary.csv")
    audit_path = Path(args.audit_json) if args.audit_json else full_root / "metrics" / "active_goal_audit_20260507.json"
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}

    cellpose_all = _metric_row(comparison, "cellpose_official_cyto3")
    cellsam_all = _metric_row(comparison, "cellsam_generalist")
    samcell_all = _metric_row(comparison, "samcell_refine_final")
    best_delta = _best_farood_delta(farood_delta)

    lines = [
        "# SAM-Cell Full Inference And Far-OOD Attribution Report",
        "",
        f"Audit complete: {audit_payload.get('complete', 'unknown')}",
        "",
        "## Full CellCosmos 16777 Metrics",
        "",
        "| method | n | PQ | AJI | Dice |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in [cellpose_all, cellsam_all, samcell_all]:
        lines.append(
            "| {method} | {n} | {pq:.6f} | {aji:.6f} | {dice:.6f} |".format(
                method=row["method"],
                n=int(float(row["n"])),
                pq=_float(row, "pq"),
                aji=_float(row, "aji"),
                dice=_float(row, "dice"),
            )
        )

    lines.extend(
        [
            "",
            "## SAM-Cell Delta On Full CellCosmos",
            "",
            "| baseline | delta PQ | delta AJI | delta Dice |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in _all_rows(baseline_delta):
        lines.append(
            "| {baseline} | {dpq:.6f} | {daji:.6f} | {ddice:.6f} |".format(
                baseline=row["baseline_method"],
                dpq=_float(row, "delta_pq"),
                daji=_float(row, "delta_aji"),
                ddice=_float(row, "delta_dice"),
            )
        )

    lines.extend(
        [
            "",
            "## Far-OOD Attribution",
            "",
            "| stage | ALL PQ | ALL AJI | ALL Dice |",
            "|---|---:|---:|---:|",
        ]
    )
    stage_order = ["semantic_cc", "raw_watershed", "current_proposal", "coarse_no_sam2", "full_samcell"]
    for method in stage_order:
        row = _metric_row(farood_summary, method)
        lines.append(
            "| {method} | {pq:.6f} | {aji:.6f} | {dice:.6f} |".format(
                method=method,
                pq=_float(row, "pq"),
                aji=_float(row, "aji"),
                dice=_float(row, "dice"),
            )
        )

    lines.extend(
        [
            "",
            "## Far-OOD Paired Deltas",
            "",
            "| delta | mean delta PQ | median delta PQ | PQ win rate |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in _all_rows(farood_delta):
        lines.append(
            "| {delta} | {mean_delta_pq:.6f} | {median_delta_pq:.6f} | {pq_win_rate:.3f} |".format(
                delta=row["delta"],
                mean_delta_pq=_float(row, "mean_delta_pq"),
                median_delta_pq=_float(row, "median_delta_pq"),
                pq_win_rate=_float(row, "pq_win_rate"),
            )
        )

    lines.extend(
        [
            "",
            "## Answer",
            "",
            "Within the staged current-method attribution, the largest mean paired per-image PQ gain on Far-OOD comes from `{}` "
            "with mean delta PQ {:.6f}. This indicates the dominant measured contribution is that stage, while earlier/later modules "
            "should be interpreted as interacting components rather than independent causal effects.".format(
                best_delta["delta"],
                _float(best_delta, "mean_delta_pq"),
            ),
        ]
    )

    out_md = Path(args.out_md) if args.out_md else full_root / "metrics" / "active_goal_final_report_20260507.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_md}")


if __name__ == "__main__":
    main()
