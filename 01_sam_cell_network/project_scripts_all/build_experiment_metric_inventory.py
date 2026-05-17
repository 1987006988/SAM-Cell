from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


SOURCES = ["ALL", "SOURCE_MACRO", "cellpose", "dsb2018", "livecell", "pannuke", "tissuenet", "yeast", "yeastnet"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "summary_path",
        "experiment",
        "method",
        "split",
        "metric_key",
        "n_all",
        "all_pq",
        "source_macro_pq",
        "cellpose_pq",
        "dsb2018_pq",
        "livecell_pq",
        "pannuke_pq",
        "tissuenet_pq",
        "yeast_pq",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def infer_method_split(path: Path, rows: list[dict[str, str]], root: Path) -> tuple[str, str, str]:
    rel = path.relative_to(root)
    parts = rel.parts
    method = rows[0].get("method") if rows and rows[0].get("method") else ""
    split = ""
    experiment = str(rel.parent)
    if "metrics" in parts:
        idx = parts.index("metrics")
        if not method and len(parts) > idx + 1:
            method = parts[idx + 1]
        if len(parts) > idx + 2:
            split = parts[idx + 2]
    if not method:
        method = rel.parent.name
    if not split:
        split = rel.parent.name
    return experiment, method, split


def metric_key_for_rows(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "pq"
    keys = rows[0].keys()
    if "pq" in keys:
        return "pq"
    if "final_pq" in keys:
        return "final_pq"
    if "proposal_pq" in keys:
        return "proposal_pq"
    return "pq"


def inventory_row(path: Path, root: Path) -> dict[str, Any] | None:
    rows = read_csv(path)
    if not rows or "source" not in rows[0]:
        return None
    key = metric_key_for_rows(rows)
    by_source = {row["source"]: row for row in rows if row.get("source")}
    experiment, method, split = infer_method_split(path, rows, root)
    all_row = by_source.get("ALL", {})
    yeast_row = by_source.get("yeast") or by_source.get("yeastnet") or {}
    return {
        "summary_path": str(path.relative_to(root)),
        "experiment": experiment,
        "method": method,
        "split": split,
        "metric_key": key,
        "n_all": all_row.get("n", ""),
        "all_pq": as_float(all_row.get(key)),
        "source_macro_pq": as_float(by_source.get("SOURCE_MACRO", {}).get(key)),
        "cellpose_pq": as_float(by_source.get("cellpose", {}).get(key)),
        "dsb2018_pq": as_float(by_source.get("dsb2018", {}).get(key)),
        "livecell_pq": as_float(by_source.get("livecell", {}).get(key)),
        "pannuke_pq": as_float(by_source.get("pannuke", {}).get(key)),
        "tissuenet_pq": as_float(by_source.get("tissuenet", {}).get(key)),
        "yeast_pq": as_float(yeast_row.get(key)),
    }


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = sorted(
        rows,
        key=lambda row: (
            "cellcosmos_full_16777" not in row["summary_path"],
            row["method"],
            row["split"],
            row["summary_path"],
        ),
    )
    lines = [
        "# Experiment Metric Inventory",
        "",
        "Generated from available `summary.csv` and `summary_by_source.csv` files.",
        "",
        "| method | split | metric | n | ALL PQ | source macro PQ | Cellpose | DSB2018 | LIVECell | PanNuke | TissueNet | Yeast | path |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in selected:
        lines.append(
            "| {method} | {split} | {metric_key} | {n_all} | {all_pq} | {source_macro_pq} | {cellpose_pq} | {dsb2018_pq} | {livecell_pq} | {pannuke_pq} | {tissuenet_pq} | {yeast_pq} | `{summary_path}` |".format(
                **{k: "" if v is None else v for k, v in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a thesis-facing inventory of available experiment metrics.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out_dir", default="outputs/thesis_experiment_inventory_20260504")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    candidates = []
    for pattern in ["**/summary_by_source.csv", "**/summary.csv"]:
        candidates.extend(root.glob(pattern))
    rows = []
    for path in sorted(set(candidates)):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        try:
            row = inventory_row(path, root)
        except Exception as exc:
            print(f"skip {path}: {exc}")
            continue
        if row is not None:
            rows.append(row)
    write_csv(out_dir / "experiment_metric_inventory.csv", rows)
    write_markdown(out_dir / "experiment_metric_inventory.md", rows)
    print(f"wrote {out_dir / 'experiment_metric_inventory.csv'}")
    print(f"wrote {out_dir / 'experiment_metric_inventory.md'}")


if __name__ == "__main__":
    main()
