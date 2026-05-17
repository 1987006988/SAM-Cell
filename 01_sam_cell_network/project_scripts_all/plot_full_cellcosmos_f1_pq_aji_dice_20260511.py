#!/usr/bin/env python3
"""Build Chapter 2.6.2 F1/PQ/AJI/Dice figures for five source datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_SPLIT_ROOT = Path("outputs/cellcosmos_full_16777_by_dataset_metrics_20260507")
DEFAULT_EXPERIMENT_ROOT = Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")
DEFAULT_OUT_DIR = Path("outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511")

SOURCES = ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet", "ALL"]
METHODS = ["cellpose_official_cyto3", "cellsam_generalist", "samcell_refine_final"]
METRICS = ["f1", "pq", "aji", "dice"]

SOURCE_LABEL = {
    "cellpose": "Cellpose",
    "dsb2018": "DSB2018",
    "livecell": "LIVECell",
    "pannuke": "PanNuke",
    "tissuenet": "TissueNet",
    "ALL": "All",
}
METHOD_LABEL = {
    "cellpose_official_cyto3": "Cellpose cyto3",
    "cellsam_generalist": "CellSAM",
    "samcell_refine_final": "SAM-Cell",
}
METHOD_COLOR = {
    "cellpose_official_cyto3": "#F4A6A6",
    "cellsam_generalist": "#74C7C3",
    "samcell_refine_final": "#8BCB88",
}
SOURCE_ONLY = [source for source in SOURCES if source != "ALL"]
METRIC_LABEL = {
    "f1": "F1",
    "pq": "PQ",
    "aji": "AJI",
    "dice": "Dice",
}
METRIC_COLOR = {
    "f1": "#5B8CC0",
    "pq": "#E28D47",
    "aji": "#7AA974",
    "dice": "#C76E9D",
}
SOURCE_COLOR = {
    "cellpose": "#7C6A55",
    "dsb2018": "#5C8BA8",
    "livecell": "#D49A3A",
    "pannuke": "#8F8BB8",
    "tissuenet": "#5FA88D",
    "ALL": "#333333",
}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#222222",
            "xtick.color": "#222222",
            "ytick.color": "#222222",
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def metric_column(df: pd.DataFrame, metric: str) -> str:
    if metric in df.columns:
        return metric
    final_metric = f"final_{metric}"
    if final_metric in df.columns:
        return final_metric
    raise KeyError(f"Missing metric column for {metric}: {list(df.columns)}")


def full_per_image_path(experiment_root: Path, method: str) -> Path:
    if method == "samcell_refine_final":
        return experiment_root / method / "per_image.csv"
    return experiment_root / method / "metrics" / "per_image.csv"


def load_method_rows(split_root: Path, experiment_root: Path, method: str) -> pd.DataFrame:
    source_files = [split_root / source / f"{method}_per_image.csv" for source in SOURCES if source != "ALL"]
    if all(path.exists() for path in source_files):
        return pd.concat([pd.read_csv(path) for path in source_files], ignore_index=True)
    path = full_per_image_path(experiment_root, method)
    return pd.read_csv(path)


def summarize_method_source(df: pd.DataFrame, source: str, method: str) -> dict[str, float | int | str]:
    sub = df if source == "ALL" else df[df["source"] == source]
    rows: dict[str, float | int | str] = {
        "source": source,
        "method": method,
        "n": len(sub),
    }
    for metric in METRICS:
        rows[metric] = float(sub[metric_column(sub, metric)].mean())
    return rows


def build_summary(split_root: Path, experiment_root: Path) -> pd.DataFrame:
    rows = []
    for method in METHODS:
        method_df = load_method_rows(split_root, experiment_root, method)
        for source in SOURCES:
            rows.append(summarize_method_source(method_df, source, method))
    out = pd.DataFrame(rows)
    out["source"] = pd.Categorical(out["source"], SOURCES, ordered=True)
    out["method"] = pd.Categorical(out["method"], METHODS, ordered=True)
    return out.sort_values(["source", "method"]).reset_index(drop=True)


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    lines = ["# Full CellCosmos F1/PQ/AJI/Dice", ""]
    lines.append("| source | method | n | F1 | PQ | AJI | Dice |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for row in df.itertuples(index=False):
        lines.append(
            f"| {row.source} | {row.method} | {int(row.n)} | "
            f"{row.f1:.6f} | {row.pq:.6f} | {row.aji:.6f} | {row.dice:.6f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_grouped(df: pd.DataFrame, out_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.6), sharex=True, sharey=True)
    axes = axes.ravel()
    x = np.arange(len(SOURCES))
    width = 0.23

    for ax, metric in zip(axes, METRICS):
        for idx, method in enumerate(METHODS):
            sub = df[df["method"] == method].set_index("source").loc[SOURCES]
            values = sub[metric].to_numpy(dtype=float)
            bars = ax.bar(
                x + (idx - 1) * width,
                values,
                width=width,
                label=METHOD_LABEL[method],
                color=METHOD_COLOR[method],
                edgecolor="#3A3A3A",
                linewidth=0.45,
            )
            for bar, value in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + 0.012,
                    f"{value:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=7.2,
                    rotation=0,
                    color="#222222",
                )
        ax.axvline(len(SOURCES) - 1.5, color="#777777", linestyle="--", linewidth=0.8, alpha=0.55)
        ax.set_title(METRIC_LABEL[metric])
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", color="#DDDDDD", linewidth=0.8, alpha=0.65)
        ax.set_axisbelow(True)

    for ax in axes[-2:]:
        ax.set_xticks(x)
        ax.set_xticklabels([SOURCE_LABEL[source] for source in SOURCES], rotation=0)
    for ax in [axes[0], axes[2]]:
        ax.set_ylabel("Mean per-image score")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.01))
    fig.suptitle("Five-dataset quantitative comparison", y=1.055, fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(out_dir / "fig_2_09_five_dataset_four_metrics_grouped.png", bbox_inches="tight")
    fig.savefig(out_dir / "fig_2_09_five_dataset_four_metrics_grouped.pdf", bbox_inches="tight")
    fig.savefig(out_dir / "fig_full_cellcosmos_f1_pq_aji_dice_grouped.png", bbox_inches="tight")
    fig.savefig(out_dir / "fig_full_cellcosmos_f1_pq_aji_dice_grouped.pdf", bbox_inches="tight")
    plt.close(fig)


def composite_error(row: pd.Series) -> float:
    return float(np.mean([1.0 - float(row[metric]) for metric in METRICS]))


def plot_multimetric_error_transition(df: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.9, 5.7))
    y = np.arange(len(SOURCES))
    err = df.copy()
    err["mean_error"] = err.apply(composite_error, axis=1)

    for yi, source in enumerate(SOURCES):
        vals = []
        for method in METHODS:
            val = float(err[(err["source"] == source) & (err["method"] == method)]["mean_error"].iloc[0])
            vals.append(val)
        ax.plot(vals, [yi] * len(vals), color="#A8A8A8", linewidth=1.3, zorder=1)
        for method, val in zip(METHODS, vals):
            ax.scatter(
                val,
                yi,
                s=82,
                color=METHOD_COLOR[method],
                edgecolor="white",
                linewidth=0.8,
                label=METHOD_LABEL[method] if yi == 0 else None,
                zorder=3,
            )
        ax.text(vals[-1] + 0.012, yi, f"{vals[-1]:.2f}", va="center", fontsize=8.0, color="#333333")

    ax.axhline(len(SOURCES) - 1.5, color="#666666", linestyle="--", linewidth=0.9, alpha=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([SOURCE_LABEL[source] for source in SOURCES])
    ax.invert_yaxis()
    ax.set_xlabel("Mean error across F1/PQ/AJI/Dice = mean(1 - metric), lower is better")
    ax.set_xlim(0.03, 0.67)
    ax.set_title("Multi-metric error transition among three models")
    ax.legend(
        frameon=True,
        facecolor="white",
        edgecolor="none",
        framealpha=0.92,
        loc="upper right",
    )
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_2_10_multimetric_error_transition.png", bbox_inches="tight")
    fig.savefig(out_dir / "fig_2_10_multimetric_error_transition.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_error_reduction_breakdown(df: pd.DataFrame, out_dir: Path) -> None:
    sam = df[df["method"] == "samcell_refine_final"].set_index("source").loc[SOURCES]
    baselines = ["cellpose_official_cyto3", "cellsam_generalist"]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.8), sharey=True)
    y = np.arange(len(SOURCES))
    metric_offsets = np.linspace(-0.18, 0.18, len(METRICS))

    for ax, baseline in zip(axes, baselines):
        base = df[df["method"] == baseline].set_index("source").loc[SOURCES]
        deltas = pd.DataFrame({metric: sam[metric] - base[metric] for metric in METRICS}, index=SOURCES)
        means = deltas.mean(axis=1)
        for yi, source in enumerate(SOURCES):
            values = deltas.loc[source, METRICS].to_numpy(dtype=float)
            ax.hlines(yi, values.min(), values.max(), color="#B7B7B7", linewidth=1.1, zorder=1)
            for offset, metric, value in zip(metric_offsets, METRICS, values):
                ax.scatter(
                    value,
                    yi + offset,
                    s=46,
                    color=METRIC_COLOR[metric],
                    edgecolor="white",
                    linewidth=0.6,
                    label=METRIC_LABEL[metric] if yi == 0 else None,
                    zorder=3,
                )
            ax.scatter(
                float(means.loc[source]),
                yi,
                s=70,
                marker="D",
                color="#222222",
                edgecolor="white",
                linewidth=0.6,
                label="Mean" if yi == 0 else None,
                zorder=4,
            )
            ax.text(float(means.loc[source]) + 0.012, yi, f"{means.loc[source]:+.2f}", va="center", fontsize=7.7)
        ax.axvline(0, color="#333333", linewidth=1.0)
        ax.axhline(len(SOURCES) - 1.5, color="#666666", linestyle="--", linewidth=0.9, alpha=0.6)
        ax.set_title(f"Error reduction vs {METHOD_LABEL[baseline]}")
        ax.set_xlabel("Metric gain = baseline error - SAM-Cell error")
        ax.grid(axis="x", alpha=0.18)
        ax.set_xlim(-0.12, 0.47)

    axes[0].set_yticks(y)
    axes[0].set_yticklabels([SOURCE_LABEL[source] for source in SOURCES])
    axes[0].invert_yaxis()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Where the error reduction comes from", y=1.08, fontsize=14.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(out_dir / "fig_2_11_error_reduction_breakdown.png", bbox_inches="tight")
    fig.savefig(out_dir / "fig_2_11_error_reduction_breakdown.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_best_baseline_parity(df: pd.DataFrame, out_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 9.0), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, metric in zip(axes, METRICS):
        for source in SOURCES:
            sub = df[df["source"] == source].set_index("method").loc[METHODS]
            best_baseline = float(sub.loc[["cellpose_official_cyto3", "cellsam_generalist"], metric].max())
            sam_value = float(sub.loc["samcell_refine_final", metric])
            ax.scatter(
                best_baseline,
                sam_value,
                s=96 if source == "ALL" else 62,
                color=SOURCE_COLOR[source],
                edgecolor="#111111" if source == "ALL" else "white",
                linewidth=0.9,
                alpha=0.92,
            )
        ax.plot([0.2, 1.0], [0.2, 1.0], color="#333333", linestyle="--", linewidth=1.0)
        ax.set_title(METRIC_LABEL[metric])
        ax.grid(alpha=0.18)
        ax.set_xlim(0.2, 1.0)
        ax.set_ylim(0.2, 1.0)
    axes[2].set_xlabel("Best baseline score")
    axes[3].set_xlabel("Best baseline score")
    axes[0].set_ylabel("SAM-Cell score")
    axes[2].set_ylabel("SAM-Cell score")
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=SOURCE_COLOR[source],
                   markeredgecolor="#111111" if source == "ALL" else "white", markersize=7,
                   label=SOURCE_LABEL[source])
        for source in SOURCES
    ]
    fig.legend(legend_handles, [SOURCE_LABEL[source] for source in SOURCES], ncol=6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Parity against the strongest baseline for each metric", y=1.06, fontsize=14.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_dir / "fig_2_12_best_baseline_parity_four_metrics.png", bbox_inches="tight")
    fig.savefig(out_dir / "fig_2_12_best_baseline_parity_four_metrics.pdf", bbox_inches="tight")
    plt.close(fig)


def write_figure_index(out_dir: Path) -> None:
    lines = [
        "# Chapter 2.6.2 Multi-Metric Figure Index",
        "",
        "| figure | file stem | role |",
        "|---|---|---|",
        "| Fig. 2-9 | `fig_2_09_five_dataset_four_metrics_grouped` | Four-metric grouped bars across five source datasets plus pooled ALL. |",
        "| Fig. 2-10 | `fig_2_10_multimetric_error_transition` | Mean error transition across Cellpose cyto3, CellSAM, and SAM-Cell. |",
        "| Fig. 2-11 | `fig_2_11_error_reduction_breakdown` | Metric-wise error reduction of SAM-Cell relative to each baseline. |",
        "| Fig. 2-12 | `fig_2_12_best_baseline_parity_four_metrics` | Four-metric parity against the strongest baseline for each dataset. |",
        "",
    ]
    (out_dir / "figure_index_2_6_2_multimetric.md").write_text("\n".join(lines), encoding="utf-8")


def write_section_text(out_dir: Path) -> None:
    text = """# 2.6.2 五个数据集上的多指标定量对比与性能分析

为避免单一混合测试集掩盖不同细胞图像来源之间的性能差异，本文将统一格式化后的评测样本按照来源划分为 Cellpose、DSB2018、LIVECell、PanNuke 和 TissueNet 五个数据集，并在每个数据集上分别比较 Cellpose cyto3、CellSAM 与本文方法 SAM-Cell。评价指标采用 F1、PQ、AJI 和 Dice，其中 F1 反映实例级检出与匹配能力，PQ 同时衡量实例识别质量和轮廓分割质量，AJI 强调密集实例集合的整体重叠质量，Dice 则反映前景区域覆盖程度。图 2-9 给出了五个数据集及总体 ALL 上的四指标分组结果。

从总体 ALL 结果看，SAM-Cell 在 F1、PQ、AJI 和 Dice 上分别达到 0.7466、0.6083、0.6183 和 0.8657，均高于 CellSAM 的 0.7012、0.5389、0.5248 和 0.7616，也明显高于 Cellpose cyto3 的 0.4567、0.3343、0.3048 和 0.5315。这说明在五个来源数据集共同构成的整体评测条件下，SAM-Cell 具有更强的综合实例分割性能。

图 2-10 将四个指标统一转换为平均误差，即对 F1、PQ、AJI 和 Dice 分别计算 \\(1-\\text{metric}\\) 后求均值，用于观察三个模型在不同数据集上的整体误差转移趋势。可以看到，SAM-Cell 在 Cellpose、DSB2018、PanNuke 以及总体 ALL 上均将平均误差压低到最低水平；在 TissueNet 上，SAM-Cell 明显优于 Cellpose cyto3，但平均误差略高于 CellSAM；在 LIVECell 上，SAM-Cell 相比 CellSAM 有显著改善，但仍未完全超过 Cellpose cyto3。该图从误差角度更直观地说明了 SAM-Cell 的总体鲁棒性优势及其局部短板。

图 2-11 进一步分解了 SAM-Cell 相对于两个基线模型的误差下降来源。图中彩色圆点表示 F1、PQ、AJI 和 Dice 四个指标的单项增益，黑色菱形表示四项指标的平均增益。相对于 Cellpose cyto3，SAM-Cell 在大多数数据集上均获得正向误差下降，尤其在 PanNuke 和 TissueNet 上提升明显；相对于 CellSAM，SAM-Cell 在 Cellpose、DSB2018、LIVECell、PanNuke 和总体 ALL 上整体占优，但 TissueNet 的实例匹配类指标出现负增益。这说明本文方法的优势并非来自单一指标，而是由实例匹配和前景覆盖的共同改善构成，同时也揭示了 TissueNet 中仍需改进的候选筛选与实例分离问题。

图 2-12 将每个数据集、每个指标上两个基线中的最优结果作为横轴，将 SAM-Cell 的对应结果作为纵轴进行 parity 对比。位于对角线以上的点表示 SAM-Cell 超过当前最强基线，位于对角线以下则表示仍存在差距。结果显示，SAM-Cell 在总体 ALL 以及多数数据集-指标组合上位于对角线以上；低于对角线的点主要集中在 LIVECell 的实例匹配指标以及 TissueNet 的 F1、PQ、AJI，说明这两个数据集是后续优化的主要误差来源。该图避免只与单个基线比较，更严格地反映了 SAM-Cell 相对于“当前最强可用基线”的真实优势边界。

综上，SAM-Cell 在五个公开细胞数据集构成的多源评测中表现出更优的总体分割能力。其主要优势来自语义前景预测、EDT-分水岭实例候选生成以及冻结 SAM2 提示精修之间的互补作用，能够在不微调 SAM2 的条件下提升多源细胞图像的实例分割质量。同时，LIVECell 和 TissueNet 中仍存在实例匹配指标未完全领先的情况，说明后续仍需针对贴连细胞、形态差异较大的细胞边界以及候选筛选策略进行进一步优化。
"""
    (out_dir / "section_2_6_2_multimetric_replacement_text.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split_root", type=Path, default=DEFAULT_SPLIT_ROOT)
    parser.add_argument("--experiment_root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    setup_style()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df = build_summary(args.split_root, args.experiment_root)
    df.to_csv(args.out_dir / "full_cellcosmos_f1_pq_aji_dice_summary.csv", index=False)
    write_markdown(df, args.out_dir / "full_cellcosmos_f1_pq_aji_dice_summary.md")
    plot_grouped(df, args.out_dir)
    plot_multimetric_error_transition(df, args.out_dir)
    plot_error_reduction_breakdown(df, args.out_dir)
    plot_best_baseline_parity(df, args.out_dir)
    write_figure_index(args.out_dir)
    write_section_text(args.out_dir)
    print(args.out_dir / "full_cellcosmos_f1_pq_aji_dice_summary.csv")
    print(args.out_dir / "fig_2_09_five_dataset_four_metrics_grouped.png")
    print(args.out_dir / "fig_2_10_multimetric_error_transition.png")
    print(args.out_dir / "fig_2_11_error_reduction_breakdown.png")
    print(args.out_dir / "fig_2_12_best_baseline_parity_four_metrics.png")


if __name__ == "__main__":
    main()
