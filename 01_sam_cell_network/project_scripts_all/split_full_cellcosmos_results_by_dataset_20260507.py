#!/usr/bin/env python3
"""Split full CellCosmos results by source dataset and export per-source metrics.

The script is intentionally idempotent. It writes metrics CSV/Markdown files and
creates symlinks for prediction labels/overlays instead of copying large files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Iterable


SOURCES = ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]
METHODS = ["cellpose_official_cyto3", "cellsam_generalist", "samcell_refine_final"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    fieldnames.append(key)
                    seen.add(key)
    fieldnames = list(fieldnames)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_md_table(path: Path, title: str, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    for row in rows:
        values = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n")


def as_float(value: str | None) -> float:
    if value in (None, ""):
        return float("nan")
    return float(value)


def safe_symlink(target: Path, link: Path) -> bool:
    if not target.exists():
        return False
    link.parent.mkdir(parents=True, exist_ok=True)
    target_abs = target.resolve()
    if link.is_symlink():
        if Path(os.readlink(link)) == target_abs:
            return True
        link.unlink()
    elif link.exists():
        return True
    os.symlink(target_abs, link)
    return True


def metric_specs(root: Path) -> dict[str, dict[str, Path]]:
    return {
        "cellpose_official_cyto3": {
            "summary": root / "cellpose_official_cyto3" / "metrics" / "summary_by_source.csv",
            "per_image": root / "cellpose_official_cyto3" / "metrics" / "per_image.csv",
            "label_dir": root / "cellpose_official_cyto3" / "predictions",
        },
        "cellsam_generalist": {
            "summary": root / "cellsam_generalist" / "metrics" / "summary_by_source.csv",
            "per_image": root / "cellsam_generalist" / "metrics" / "per_image.csv",
            "label_dir": root / "cellsam_generalist" / "predictions" / "labels",
        },
        "samcell_refine_final": {
            "summary": root / "samcell_refine_final" / "summary.csv",
            "per_image": root / "samcell_refine_final" / "per_image.csv",
            "label_dir": root / "samcell_refine_final" / "labels",
        },
    }


def normalise_summary(method: str, rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        source = row.get("source", "")
        if not source:
            continue
        pq_key = "pq" if "pq" in row else "final_pq"
        aji_key = "aji" if "aji" in row else "final_aji"
        dice_key = "dice" if "dice" in row else "final_dice"
        out.append(
            {
                "source": source,
                "method": method,
                "n": int(float(row.get("n", "0") or 0)) if row.get("n") else "",
                "pq": as_float(row.get(pq_key)),
                "aji": as_float(row.get(aji_key)),
                "dice": as_float(row.get(dice_key)),
                "summary_path": str(row.get("summary_path", "")),
            }
        )
    return out


def image_stem(image_name: str) -> str:
    return Path(image_name).stem


def label_path_for(method: str, spec: dict[str, Path], image_name: str, per_image_row: dict[str, str] | None) -> Path | None:
    if per_image_row and per_image_row.get("prediction_path"):
        path = Path(per_image_row["prediction_path"])
        if path.exists():
            return path
    stem = image_stem(image_name)
    label_dir = spec["label_dir"]
    candidates: list[Path]
    if method == "cellpose_official_cyto3":
        candidates = [label_dir / f"{stem}_cp_masks.tif", label_dir / f"{stem}_cp_masks.png"]
    elif method == "cellsam_generalist":
        candidates = [label_dir / f"{stem}_cellsam.tif", label_dir / f"{stem}_cellsam.png"]
    else:
        candidates = [label_dir / f"{stem}.tif", label_dir / f"{stem}.png"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def overlay_dirs(root: Path, method: str) -> dict[str, Path]:
    if method in {"cellpose_official_cyto3", "cellsam_generalist"}:
        base = root / method / "overlays"
        return {
            "compare": base / "compare",
            "gt": base / "gt",
            "pred": base / "pred",
        }
    return {"pred": root / method / "overlays"}


def overlay_stem(filename: str, method: str, kind: str) -> str:
    stem = Path(filename).stem
    suffixes = [
        f"_{method}_{kind}",
        f"_{kind}",
    ]
    for suffix in suffixes:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503"),
    )
    parser.add_argument("--metrics_out", type=Path, default=None)
    parser.add_argument("--links_out", type=Path, default=None)
    parser.add_argument("--no_links", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    metrics_out = args.metrics_out or (root / "metrics" / "by_dataset_20260507")
    links_out = args.links_out or (root / "results_by_dataset_20260507")
    manifest_path = root / "manifests" / "full.csv"
    comparison_path = root / "metrics" / "full_model_comparison_20260507" / "full_model_comparison_pq_aji_dice.csv"

    manifest_rows = read_csv(manifest_path)
    manifest_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    stem_to_source: dict[str, str] = {}
    for row in manifest_rows:
        source = row["source"]
        manifest_by_source[source].append(row)
        stem_to_source[image_stem(row["image_name"])] = source

    specs = metric_specs(root)
    per_image_by_method: dict[str, dict[str, dict[str, str]]] = {}
    source_counts = [{"source": source, "n": len(manifest_by_source[source])} for source in SOURCES]
    source_counts.append({"source": "ALL", "n": len(manifest_rows)})
    write_csv(metrics_out / "source_counts.csv", source_counts, ["source", "n"])

    all_metric_rows: list[dict[str, object]] = []
    if comparison_path.exists():
        for row in read_csv(comparison_path):
            all_metric_rows.append(
                {
                    "source": row["source"],
                    "method": row["method"],
                    "n": int(float(row["n"])),
                    "pq": float(row["pq"]),
                    "aji": float(row["aji"]),
                    "dice": float(row["dice"]),
                    "summary_path": row.get("summary_path", ""),
                }
            )
    else:
        for method, spec in specs.items():
            all_metric_rows.extend(normalise_summary(method, read_csv(spec["summary"])))

    fields = ["source", "method", "n", "pq", "aji", "dice", "summary_path"]
    source_order = {source: idx for idx, source in enumerate(["ALL", *SOURCES, "SOURCE_MACRO"])}
    method_order = {method: idx for idx, method in enumerate(METHODS)}
    all_metric_rows.sort(key=lambda r: (source_order.get(str(r["source"]), 99), method_order.get(str(r["method"]), 99)))
    write_csv(metrics_out / "all_models_by_dataset_metrics.csv", all_metric_rows, fields)
    write_md_table(
        metrics_out / "all_models_by_dataset_metrics.md",
        "Full CellCosmos Metrics By Dataset",
        all_metric_rows,
        ["source", "method", "n", "pq", "aji", "dice"],
    )

    for source in SOURCES:
        write_csv(links_out / source / "manifest.csv", manifest_by_source[source], manifest_rows[0].keys())
        source_metrics = [row for row in all_metric_rows if row["source"] == source]
        write_csv(metrics_out / source / "model_metrics.csv", source_metrics, fields)
        write_md_table(
            metrics_out / source / "model_metrics.md",
            f"{source} Metrics",
            source_metrics,
            ["source", "method", "n", "pq", "aji", "dice"],
        )

    split_counts: list[dict[str, object]] = []
    for method, spec in specs.items():
        per_rows = read_csv(spec["per_image"])
        by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
        by_image: dict[str, dict[str, str]] = {}
        for row in per_rows:
            by_source[row["source"]].append(row)
            by_image[row["image"]] = row
        per_image_by_method[method] = by_image
        method_summary = [row for row in all_metric_rows if row["method"] == method]
        write_csv(metrics_out / "by_method" / f"{method}_summary_by_dataset.csv", method_summary, fields)
        for source in SOURCES:
            rows = by_source[source]
            if rows:
                write_csv(metrics_out / source / f"{method}_per_image.csv", rows, rows[0].keys())
            split_counts.append({"source": source, "method": method, "per_image_rows": len(rows)})

    link_counts: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    missing_labels: list[dict[str, str]] = []
    if not args.no_links:
        for source in SOURCES:
            for method, spec in specs.items():
                for row in manifest_by_source[source]:
                    image_name = row["image_name"]
                    per_image_row = per_image_by_method[method].get(image_name)
                    target = label_path_for(method, spec, image_name, per_image_row)
                    if target is None:
                        missing_labels.append({"source": source, "method": method, "image": image_name})
                        continue
                    link = links_out / source / method / "labels" / target.name
                    if safe_symlink(target, link):
                        link_counts[source][method]["labels"] += 1

        for method in METHODS:
            for kind, directory in overlay_dirs(root, method).items():
                if not directory.exists():
                    continue
                for target in directory.iterdir():
                    if not target.is_file():
                        continue
                    stem = overlay_stem(target.name, method, kind)
                    source = stem_to_source.get(stem)
                    if not source:
                        continue
                    link = links_out / source / method / "overlays" / kind / target.name
                    if safe_symlink(target, link):
                        link_counts[source][method][f"overlay_{kind}"] += 1

    for source in SOURCES:
        for method in METHODS:
            row = {"source": source, "method": method}
            row.update(dict(link_counts[source][method]))
            split_counts.append(row)
    write_csv(metrics_out / "split_artifact_counts.csv", split_counts)
    if missing_labels:
        write_csv(metrics_out / "missing_label_links.csv", missing_labels, ["source", "method", "image"])

    manifest = {
        "root": str(root),
        "metrics_out": str(metrics_out),
        "links_out": str(links_out),
        "sources": SOURCES,
        "methods": METHODS,
        "n_total": len(manifest_rows),
        "source_counts": {source: len(manifest_by_source[source]) for source in SOURCES},
        "link_results": not args.no_links,
        "missing_label_links": len(missing_labels),
    }
    (metrics_out / "split_run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
