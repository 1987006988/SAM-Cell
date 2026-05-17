#!/usr/bin/env python3
"""Build the CellCosmos core-domain vs far-domain model comparison table."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path("outputs/core_far_model_comparison_20260509")
RAW = ROOT / "raw"
OUT_CSV = ROOT / "core_far_model_comparison.csv"
OUT_MD = ROOT / "core_far_model_comparison.md"
DETAIL_CSV = ROOT / "core_far_model_comparison_with_official_cellpose.csv"
DETAIL_MD = ROOT / "core_far_model_comparison_with_official_cellpose.md"

SPLITS = {
    "core": RAW / "repro_manifests" / "pannuke_core_test.csv",
    "far": RAW / "repro_manifests" / "far_ood_test.csv",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def split_image_sets() -> dict[str, set[str]]:
    sets: dict[str, set[str]] = {}
    for split, path in SPLITS.items():
        rows = read_csv(path)
        sets[split] = {row["image_name"] for row in rows}
    return sets


def all_row_metrics(path: Path) -> dict[str, float | int]:
    rows = read_csv(path)
    row = next(r for r in rows if r["source"] == "ALL")
    return {
        "n": int(float(row["n"])),
        "pq": float(row["pq"]),
        "aji": float(row["aji"]),
        "dice": float(row["dice"]),
    }


def filtered_per_image_metrics(
    path: Path,
    images: set[str],
    *,
    pq_col: str = "pq",
    aji_col: str = "aji",
    dice_col: str = "dice",
) -> dict[str, float | int]:
    rows = [row for row in read_csv(path) if row["image"] in images]
    if not rows:
        raise ValueError(f"No rows matched {path}")
    return {
        "n": len(rows),
        "pq": sum(float(row[pq_col]) for row in rows) / len(rows),
        "aji": sum(float(row[aji_col]) for row in rows) / len(rows),
        "dice": sum(float(row[dice_col]) for row in rows) / len(rows),
    }


def model_metrics() -> list[dict[str, object]]:
    image_sets = split_image_sets()

    models = [
        {
            "model": "CellSAM generalist",
            "notes": "public generalist; filtered from full 16777 per-image metrics",
            "core": filtered_per_image_metrics(
                RAW / "cellsam_full_metrics" / "metrics" / "per_image.csv",
                image_sets["core"],
            ),
            "far": filtered_per_image_metrics(
                RAW / "cellsam_full_metrics" / "metrics" / "per_image.csv",
                image_sets["far"],
            ),
        },
        {
            "model": "Cellpose cyto3, PanNuke-finetuned",
            "notes": "core-domain supervised baseline",
            "core": all_row_metrics(
                RAW
                / "repro_metrics"
                / "cellpose_pannuke_finetune_cyto3"
                / "pannuke_core_test"
                / "summary_by_source.csv"
            ),
            "far": all_row_metrics(
                RAW
                / "repro_metrics"
                / "cellpose_pannuke_finetune_cyto3"
                / "far_ood_test"
                / "summary_by_source.csv"
            ),
        },
        {
            "model": "StarDist, PanNuke-trained",
            "notes": "core-domain supervised baseline",
            "core": all_row_metrics(
                RAW
                / "repro_metrics"
                / "stardist_pannuke"
                / "pannuke_core_test"
                / "summary_by_source.csv"
            ),
            "far": all_row_metrics(
                RAW
                / "repro_metrics"
                / "stardist_pannuke"
                / "far_ood_test"
                / "summary_by_source.csv"
            ),
        },
        {
            "model": "Native SAM2 automatic dense",
            "notes": "automatic masks, no SAM-Cell prompts",
            "core": all_row_metrics(
                RAW
                / "repro_metrics"
                / "sam2_automatic_dense"
                / "pannuke_core_test"
                / "summary_by_source.csv"
            ),
            "far": all_row_metrics(
                RAW
                / "repro_metrics"
                / "sam2_automatic_dense"
                / "far_ood_test"
                / "summary_by_source.csv"
            ),
        },
        {
            "model": "HoVer-Net fast PanNuke",
            "notes": "official PanNuke weights; filtered from Core3500 per-image metrics",
            "core": filtered_per_image_metrics(
                RAW / "hovernet_core3500_all" / "core3500_all" / "per_image.csv",
                image_sets["core"],
            ),
            "far": filtered_per_image_metrics(
                RAW / "hovernet_core3500_all" / "core3500_all" / "per_image.csv",
                image_sets["far"],
            ),
        },
        {
            "model": "SAM-Cell refine final",
            "notes": "final accepted SAM-Cell config; filtered from full 16777 metrics",
            "core": filtered_per_image_metrics(
                RAW / "samcell_refine_final" / "per_image.csv",
                image_sets["core"],
                pq_col="final_pq",
                aji_col="final_aji",
                dice_col="final_dice",
            ),
            "far": filtered_per_image_metrics(
                RAW / "samcell_refine_final" / "per_image.csv",
                image_sets["far"],
                pq_col="final_pq",
                aji_col="final_aji",
                dice_col="final_dice",
            ),
        },
    ]

    official = {
        "model": "Cellpose official cyto3",
        "notes": "public official cyto3; not core-domain finetuned",
        "core": all_row_metrics(
            RAW
            / "repro_metrics"
            / "cellpose_official_cyto3"
            / "pannuke_core_test"
            / "summary_by_source.csv"
        ),
        "far": all_row_metrics(
            RAW
            / "repro_metrics"
            / "cellpose_official_cyto3"
            / "far_ood_test"
            / "summary_by_source.csv"
        ),
    }
    return models, [models[0], official, *models[1:]]


def flatten(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for row in rows:
        core = row["core"]
        far = row["far"]
        assert isinstance(core, dict)
        assert isinstance(far, dict)
        out.append(
            {
                "model": row["model"],
                "core_n": core["n"],
                "core_pq": core["pq"],
                "core_aji": core["aji"],
                "core_dice": core["dice"],
                "far_n": far["n"],
                "far_pq": far["pq"],
                "far_aji": far["aji"],
                "far_dice": far["dice"],
                "delta_far_minus_core_pq": float(far["pq"]) - float(core["pq"]),
                "notes": row["notes"],
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_md(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "model",
        "core_n",
        "core_pq",
        "core_aji",
        "core_dice",
        "far_n",
        "far_pq",
        "far_aji",
        "far_dice",
        "delta_far_minus_core_pq",
    ]
    headers = [
        "model",
        "core n",
        "core PQ",
        "core AJI",
        "core Dice",
        "far n",
        "far PQ",
        "far AJI",
        "far Dice",
        "far-core PQ",
    ]
    lines = [
        "# CellCosmos Core-Domain vs Far-Domain Comparison",
        "",
        "- Core-domain split: `pannuke_core_test`.",
        "- Far-domain split: `far_ood_test`.",
        "- Metrics are mean per-image PQ/AJI/Dice using the project evaluator convention.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] + ["---:"] * (len(headers) - 1)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row[field]) for field in fields) + " |")
    lines.extend(["", "## Notes", ""])
    for row in rows:
        lines.append(f"- {row['model']}: {row['notes']}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    main_rows, detailed_rows = model_metrics()
    main_flat = flatten(main_rows)
    detailed_flat = flatten(detailed_rows)
    write_csv(OUT_CSV, main_flat)
    write_md(OUT_MD, main_flat)
    write_csv(DETAIL_CSV, detailed_flat)
    write_md(DETAIL_MD, detailed_flat)
    print(OUT_MD)
    print(DETAIL_MD)


if __name__ == "__main__":
    main()
