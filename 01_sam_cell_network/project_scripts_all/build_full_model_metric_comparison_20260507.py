from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

METRICS = ("pq", "aji", "dice")
EXPECTED_N = 16777


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _metric(row: dict[str, str], metric: str) -> float:
    for key in (metric, f"final_{metric}"):
        value = row.get(key)
        if value not in (None, ""):
            return float(value)
    raise KeyError(f"Missing metric {metric!r} in row with columns: {sorted(row)}")


def _source_counts(per_image_path: Path) -> dict[str, int]:
    rows = _read_csv(per_image_path)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.get("source", "")] += 1
    counts["ALL"] = len(rows)
    counts["SOURCE_MACRO"] = len([source for source in counts if source not in {"", "ALL", "SOURCE_MACRO"}])
    return counts


def _normalise_summary(
    method: str,
    summary_path: Path,
    per_image_path: Path,
    expected_n: int,
) -> list[dict[str, object]]:
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    if not per_image_path.exists():
        raise FileNotFoundError(per_image_path)

    counts = _source_counts(per_image_path)
    summary = _read_csv(summary_path)
    rows: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []
    seen_source_macro = False

    for row in summary:
        source = row.get("source", "")
        if not source:
            continue
        n_value = row.get("n")
        n = int(float(n_value)) if n_value not in (None, "") else counts.get(source, 0)
        out = {
            "method": method,
            "source": source,
            "n": n,
            "pq": _metric(row, "pq"),
            "aji": _metric(row, "aji"),
            "dice": _metric(row, "dice"),
            "summary_path": str(summary_path),
        }
        rows.append(out)
        if source == "SOURCE_MACRO":
            seen_source_macro = True
        elif source != "ALL":
            source_rows.append(out)

    all_rows = [row for row in rows if row["source"] == "ALL"]
    if not all_rows:
        raise ValueError(f"{summary_path} has no ALL row")
    if int(all_rows[0]["n"]) != expected_n:
        raise ValueError(f"{method} ALL n={all_rows[0]['n']} expected {expected_n}: {summary_path}")

    if not seen_source_macro:
        macro = {
            "method": method,
            "source": "SOURCE_MACRO",
            "n": len(source_rows),
            "summary_path": str(summary_path),
        }
        for metric in METRICS:
            values = [float(row[metric]) for row in source_rows]
            macro[metric] = sum(values) / len(values) if values else 0.0
        rows.append(macro)

    return rows


def _write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    order = {"ALL": 0, "SOURCE_MACRO": 1}
    sorted_rows = sorted(rows, key=lambda r: (order.get(str(r["source"]), 10), str(r["source"]), str(r["method"])))
    lines = [
        "# Full CellCosmos 16777 Model Comparison",
        "",
        "| source | method | n | PQ | AJI | Dice |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in sorted_rows:
        lines.append(
            "| {source} | {method} | {n} | {pq:.6f} | {aji:.6f} | {dice:.6f} |".format(
                source=row["source"],
                method=row["method"],
                n=int(row["n"]),
                pq=float(row["pq"]),
                aji=float(row["aji"]),
                dice=float(row["dice"]),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_delta_outputs(out_dir: Path, rows: list[dict[str, object]]) -> None:
    by_key = {(str(row["method"]), str(row["source"])): row for row in rows}
    methods = ["cellpose_official_cyto3", "cellsam_generalist"]
    sources = sorted({str(row["source"]) for row in rows if str(row["source"]) not in {"SOURCE_MACRO"}})
    delta_rows: list[dict[str, object]] = []
    for source in sources:
        samcell = by_key.get(("samcell_refine_final", source))
        if samcell is None:
            continue
        for baseline in methods:
            base = by_key.get((baseline, source))
            if base is None:
                continue
            out = {
                "source": source,
                "samcell_method": "samcell_refine_final",
                "baseline_method": baseline,
                "n": int(samcell["n"]),
            }
            for metric in METRICS:
                out[f"samcell_{metric}"] = float(samcell[metric])
                out[f"baseline_{metric}"] = float(base[metric])
                out[f"delta_{metric}"] = float(samcell[metric]) - float(base[metric])
            delta_rows.append(out)
    if not delta_rows:
        return
    delta_csv = out_dir / "samcell_delta_vs_baselines.csv"
    _write_csv(delta_csv, delta_rows)

    lines = [
        "# SAM-Cell Delta Versus Baselines",
        "",
        "| source | baseline | n | delta PQ | delta AJI | delta Dice |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in sorted(delta_rows, key=lambda r: (str(r["source"]), str(r["baseline_method"]))):
        lines.append(
            "| {source} | {baseline} | {n} | {dpq:.6f} | {daji:.6f} | {ddice:.6f} |".format(
                source=row["source"],
                baseline=row["baseline_method"],
                n=int(row["n"]),
                dpq=float(row["delta_pq"]),
                daji=float(row["delta_aji"]),
                ddice=float(row["delta_dice"]),
            )
        )
    (out_dir / "samcell_delta_vs_baselines.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full CellCosmos PQ/AJI/Dice comparison for Cellpose, CellSAM and SAM-Cell.")
    parser.add_argument("--root", default="/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")
    parser.add_argument("--out_dir", default=None)
    parser.add_argument("--expected_n", type=int, default=EXPECTED_N)
    args = parser.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out_dir) if args.out_dir else root / "metrics" / "full_model_comparison_20260507"

    specs = [
        (
            "cellpose_official_cyto3",
            root / "cellpose_official_cyto3" / "metrics" / "summary_by_source.csv",
            root / "cellpose_official_cyto3" / "metrics" / "per_image.csv",
        ),
        (
            "cellsam_generalist",
            root / "cellsam_generalist" / "metrics" / "summary_by_source.csv",
            root / "cellsam_generalist" / "metrics" / "per_image.csv",
        ),
        (
            "samcell_refine_final",
            root / "samcell_refine_final" / "summary.csv",
            root / "samcell_refine_final" / "per_image.csv",
        ),
    ]

    rows: list[dict[str, object]] = []
    for method, summary_path, per_image_path in specs:
        rows.extend(_normalise_summary(method, summary_path, per_image_path, args.expected_n))

    csv_path = out_dir / "full_model_comparison_pq_aji_dice.csv"
    md_path = out_dir / "full_model_comparison_pq_aji_dice.md"
    manifest_path = out_dir / "comparison_manifest.json"
    _write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    _write_delta_outputs(out_dir, rows)
    manifest_path.write_text(
        json.dumps(
            {
                "root": str(root),
                "expected_n": args.expected_n,
                "models": [method for method, _summary, _per_image in specs],
                "csv": str(csv_path),
                "markdown": str(md_path),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
