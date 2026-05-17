#!/usr/bin/env python3
"""Build thesis Table 3-5 data for Cellpose under the CellCosmos cross-domain protocol."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_OUT_DIR = Path("outputs/chapter3_table_3_5_cellpose_cross_domain_20260512")
RAW_DIR = DEFAULT_OUT_DIR / "raw"


SUMMARY_INPUTS = {
    ("official_cyto3", "iid_val"): RAW_DIR / "cellpose_official_cyto3_iid_val_summary_by_source.csv",
    ("official_cyto3", "pannuke_core_test"): RAW_DIR / "cellpose_official_cyto3_pannuke_core_test_summary_by_source.csv",
    ("official_cyto3", "far_ood_test"): RAW_DIR / "cellpose_official_cyto3_far_ood_test_summary_by_source.csv",
    ("iid_finetune_cyto3", "iid_val"): RAW_DIR / "cellpose_iid_finetune_cyto3_iid_val_summary_by_source.csv",
    ("pannuke_finetune_cyto3", "pannuke_core_test"): RAW_DIR / "cellpose_pannuke_finetune_cyto3_pannuke_core_test_summary_by_source.csv",
    ("pannuke_finetune_cyto3", "far_ood_test"): RAW_DIR / "cellpose_pannuke_finetune_cyto3_far_ood_test_summary_by_source.csv",
}

MAIN_ROWS = [
    {
        "setting": "Cellpose official cyto3",
        "key": ("official_cyto3", "pannuke_core_test"),
        "training_domain": "public cyto3 pretrained; no CellCosmos finetune",
        "eval_paradigm": "PanNuke core/source test",
        "test_domain": "PanNuke",
        "row_source": "ALL",
        "note": "public generalist reference; weak on PanNuke core",
    },
    {
        "setting": "Cellpose official cyto3",
        "key": ("official_cyto3", "far_ood_test"),
        "training_domain": "public cyto3 pretrained; no CellCosmos finetune",
        "eval_paradigm": "non-PanNuke Far-OOD test",
        "test_domain": "TissueNet + DSB2018 + Cellpose + LIVECell",
        "row_source": "ALL",
        "note": "public generalist reference on unseen non-PanNuke domains",
    },
    {
        "setting": "Cellpose cyto3 + IID finetune",
        "key": ("iid_finetune_cyto3", "iid_val"),
        "training_domain": "CellCosmos mixed-source iid_train",
        "eval_paradigm": "random mixed-domain IID validation",
        "test_domain": "mixed CellCosmos iid_val",
        "row_source": "ALL",
        "note": "random split; not a strict OOD test",
    },
    {
        "setting": "Cellpose cyto3 + PanNuke finetune",
        "key": ("pannuke_finetune_cyto3", "pannuke_core_test"),
        "training_domain": "PanNuke train only",
        "eval_paradigm": "PanNuke core/source test",
        "test_domain": "PanNuke",
        "row_source": "ALL",
        "note": "single-source supervised in-domain performance",
    },
    {
        "setting": "Cellpose cyto3 + PanNuke finetune",
        "key": ("pannuke_finetune_cyto3", "far_ood_test"),
        "training_domain": "PanNuke train only",
        "eval_paradigm": "non-PanNuke Far-OOD test",
        "test_domain": "TissueNet + DSB2018 + Cellpose + LIVECell",
        "row_source": "ALL",
        "note": "strict cross-domain transfer after single-source training",
    },
]


def read_summary(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row["source"]: row for row in rows}


def f4(value: str | float) -> str:
    return f"{float(value):.4f}"


def build_main_rows() -> list[dict[str, str]]:
    summaries = {key: read_summary(path) for key, path in SUMMARY_INPUTS.items()}
    rows: list[dict[str, str]] = []
    for item in MAIN_ROWS:
        summary = summaries[item["key"]]
        all_row = summary[item["row_source"]]
        macro_row = summary.get("SOURCE_MACRO", all_row)
        rows.append(
            {
                "model_setting": item["setting"],
                "training_domain": item["training_domain"],
                "evaluation_paradigm": item["eval_paradigm"],
                "test_domain": item["test_domain"],
                "n": str(int(float(all_row["n"]))),
                "F1": f4(all_row["f1"]),
                "PQ": f4(all_row["pq"]),
                "AJI": f4(all_row["aji"]),
                "Dice": f4(all_row["dice"]),
                "Source_macro_PQ": f4(macro_row["pq"]),
                "Source_macro_F1": f4(macro_row["f1"]),
                "note": item["note"],
            }
        )
    return rows


def build_farood_source_rows() -> list[dict[str, str]]:
    summary = read_summary(SUMMARY_INPUTS[("pannuke_finetune_cyto3", "far_ood_test")])
    rows: list[dict[str, str]] = []
    for source in ["cellpose", "dsb2018", "livecell", "tissuenet", "SOURCE_MACRO", "ALL"]:
        row = summary[source]
        rows.append(
            {
                "source": source,
                "n": str(int(float(row["n"]))),
                "F1": f4(row["f1"]),
                "PQ": f4(row["pq"]),
                "AJI": f4(row["aji"]),
                "Dice": f4(row["dice"]),
                "Precision": f4(row["precision"]),
                "Recall": f4(row["recall"]),
            }
        )
    return rows


def build_thesis_compact_rows() -> list[dict[str, str]]:
    summaries = {key: read_summary(path) for key, path in SUMMARY_INPUTS.items()}
    specs = [
        {
            "评估基准设定": "传统随机混合基准",
            "测试集物理分布状态": "I.I.D",
            "锚点网络": "Cellpose（自主训练 500 Epochs）",
            "key": ("iid_finetune_cyto3", "iid_val"),
            "source": "ALL",
        },
        {
            "评估基准设定": "CellCosmos 单源域基准",
            "测试集物理分布状态": "Far-OOD",
            "锚点网络": "Cellpose（PanNuke 核心域训练）",
            "key": ("pannuke_finetune_cyto3", "far_ood_test"),
            "source": "ALL",
        },
        {
            "评估基准设定": "CellCosmos 通用跨域基准",
            "测试集物理分布状态": "Far-OOD",
            "锚点网络": "Cellpose（官方 cyto3 预训练模型）",
            "key": ("official_cyto3", "far_ood_test"),
            "source": "ALL",
        },
    ]
    rows: list[dict[str, str]] = []
    for spec in specs:
        metric_row = summaries[spec["key"]][spec["source"]]
        rows.append(
            {
                "评估基准设定": spec["评估基准设定"],
                "测试集物理分布状态": spec["测试集物理分布状态"],
                "锚点网络": spec["锚点网络"],
                "测试集全景质量PQ": f4(metric_row["pq"]),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("No rows to write.")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, title: str, rows: list[dict[str, str]], note: str) -> None:
    header = list(rows[0].keys())
    lines = [f"# {title}", "", note, "", "|" + "|".join(header) + "|", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("|" + "|".join(row[col] for col in header) + "|")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    main_rows = build_main_rows()
    farood_rows = build_farood_source_rows()
    compact_rows = build_thesis_compact_rows()

    write_csv(args.out_dir / "table_3_5_cellpose_cross_domain_compact_thesis.csv", compact_rows)
    write_markdown(
        args.out_dir / "table_3_5_cellpose_cross_domain_compact_thesis.md",
        "表 3-5 Cellpose 在 CellCosmos 跨域评估范式下的 PQ 对比",
        compact_rows,
        "PQ 为对应测试集 ALL 行的 mean per-image PQ；完整 F1/PQ/AJI/Dice 见 summary 表。",
    )
    write_csv(args.out_dir / "table_3_5_cellpose_cross_domain_summary.csv", main_rows)
    write_markdown(
        args.out_dir / "table_3_5_cellpose_cross_domain_summary.md",
        "Table 3-5 Cellpose under CellCosmos cross-domain evaluation",
        main_rows,
        "ALL is the mean over all images in the split; Source_macro is the unweighted mean over source-level rows.",
    )
    write_csv(args.out_dir / "table_3_5_cellpose_pannuke_finetune_farood_source_breakdown.csv", farood_rows)
    write_markdown(
        args.out_dir / "table_3_5_cellpose_pannuke_finetune_farood_source_breakdown.md",
        "Cellpose PanNuke-finetuned Far-OOD source breakdown",
        farood_rows,
        "This breakdown explains the Far-OOD collapse of the PanNuke-only Cellpose model.",
    )
    print(args.out_dir / "table_3_5_cellpose_cross_domain_compact_thesis.md")
    print(args.out_dir / "table_3_5_cellpose_cross_domain_summary.md")
    print(args.out_dir / "table_3_5_cellpose_pannuke_finetune_farood_source_breakdown.md")


if __name__ == "__main__":
    main()
