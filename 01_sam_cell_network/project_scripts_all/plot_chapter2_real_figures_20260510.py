#!/usr/bin/env python3
"""Plot real-data Chapter 2 figures for SAM-Cell thesis sections 2.6.2 and 2.6.4."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_DIR = Path("outputs/chapter2_real_figures_20260510")
FULL_METRICS = Path("outputs/cellcosmos_full_16777_by_dataset_metrics_20260507/all_models_by_dataset_metrics.csv")
FAR_STAGE = OUT_DIR / "raw/farood_attribution/combined_summary.csv"
FAR_DELTA = OUT_DIR / "raw/farood_attribution/paired_delta_summary.csv"
PROMPT_MATCHED = Path("outputs/sam2_prompt_matched_eval50_20260507/prompt_matched_same50_comparison.csv")

METHOD_ORDER = ["cellpose_official_cyto3", "cellsam_generalist", "samcell_refine_final"]
METHOD_LABEL = {
    "cellpose_official_cyto3": "Cellpose cyto3",
    "cellsam_generalist": "CellSAM",
    "samcell_refine_final": "SAM-Cell",
}
METHOD_COLOR = {
    "cellpose_official_cyto3": "#F8766D",
    "cellsam_generalist": "#00BFC4",
    "samcell_refine_final": "#7CAE00",
}

SOURCE_ORDER = ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet", "ALL"]
SOURCE_LABEL = {
    "cellpose": "Cellpose",
    "dsb2018": "DSB2018",
    "livecell": "LIVECell",
    "pannuke": "PanNuke",
    "tissuenet": "TissueNet",
    "ALL": "ALL",
}

STAGE_ORDER = ["semantic_cc", "raw_watershed", "current_proposal", "coarse_no_sam2", "full_samcell"]
STAGE_LABEL = {
    "semantic_cc": "Semantic CC",
    "raw_watershed": "EDT + Watershed",
    "current_proposal": "Proposal selection",
    "coarse_no_sam2": "Coarse map",
    "full_samcell": "Full SAM-Cell",
}
STAGE_COLOR = ["#BDBDBD", "#80B1D3", "#FDB462", "#B3DE69", "#1B9E77"]

PROMPT_ORDER = ["same_proposals_before_sam2", "sam2_prompt_matched_box_mask", "samcell_refine_final_same50"]
PROMPT_LABEL = {
    "same_proposals_before_sam2": "Before SAM2\n(proposal map)",
    "sam2_prompt_matched_box_mask": "Native SAM2\nbox+mask prompts",
    "samcell_refine_final_same50": "SAM-Cell final\nsame 50",
}
PROMPT_COLOR = {
    "same_proposals_before_sam2": "#FDB462",
    "sam2_prompt_matched_box_mask": "#756BB1",
    "samcell_refine_final_same50": "#1B9E77",
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


def savefig(fig: plt.Figure, stem: str) -> None:
    png = OUT_DIR / f"{stem}.png"
    pdf = OUT_DIR / f"{stem}.pdf"
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)


def load_full_metrics() -> pd.DataFrame:
    df = pd.read_csv(FULL_METRICS)
    df = df[df["source"].isin(SOURCE_ORDER)].copy()
    df["source"] = pd.Categorical(df["source"], SOURCE_ORDER, ordered=True)
    df["method"] = pd.Categorical(df["method"], METHOD_ORDER, ordered=True)
    df = df.sort_values(["source", "method"]).reset_index(drop=True)
    df["error_1_minus_pq"] = 1.0 - df["pq"]
    return df


def plot_2_09_error_grouped(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    x = np.arange(len(SOURCE_ORDER))
    width = 0.23

    for i, method in enumerate(METHOD_ORDER):
        sub = df[df["method"] == method].set_index("source").loc[SOURCE_ORDER]
        y = sub["error_1_minus_pq"].to_numpy()
        offset = (i - 1) * width
        bars = ax.bar(
            x + offset,
            y,
            width=width,
            label=METHOD_LABEL[method],
            color=METHOD_COLOR[method],
            edgecolor="#222222",
            linewidth=0.45,
        )
        for bar, value in zip(bars, y):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.012,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=7.8,
                rotation=0,
            )

    ax.axvline(len(SOURCE_ORDER) - 1.5, color="#666666", linestyle="--", linewidth=0.9, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([SOURCE_LABEL[s] for s in SOURCE_ORDER])
    ax.set_ylabel("Error = 1 - PQ (lower is better)")
    ax.set_ylim(0, 0.85)
    ax.set_title("Dataset-wise instance segmentation error on CellCosmos")
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    savefig(fig, "fig_2_09_cellcosmos_error_by_source")


def plot_2_10_error_transition(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.7))
    y = np.arange(len(SOURCE_ORDER))

    for yi, source in enumerate(SOURCE_ORDER):
        vals = []
        for method in METHOD_ORDER:
            val = float(df[(df["source"] == source) & (df["method"] == method)]["error_1_minus_pq"].iloc[0])
            vals.append(val)
        ax.plot(vals, [yi] * len(vals), color="#999999", linewidth=1.2, zorder=1)
        for method, val in zip(METHOD_ORDER, vals):
            ax.scatter(
                val,
                yi,
                s=75,
                color=METHOD_COLOR[method],
                edgecolor="white",
                linewidth=0.7,
                label=METHOD_LABEL[method] if yi == 0 else None,
                zorder=2,
            )

    ax.set_yticks(y)
    ax.set_yticklabels([SOURCE_LABEL[s] for s in SOURCE_ORDER])
    ax.invert_yaxis()
    ax.set_xlabel("Error = 1 - PQ (lower is better)")
    ax.set_xlim(0.1, 0.8)
    ax.set_title("Error transition among Cellpose, CellSAM, and SAM-Cell")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    savefig(fig, "fig_2_10_error_transition_three_models")


def plot_2_11_delta_pq(df: pd.DataFrame) -> None:
    pivot = df.pivot(index="source", columns="method", values="pq").loc[SOURCE_ORDER]
    delta_cellpose = pivot["samcell_refine_final"] - pivot["cellpose_official_cyto3"]
    delta_cellsam = pivot["samcell_refine_final"] - pivot["cellsam_generalist"]

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    x = np.arange(len(SOURCE_ORDER))
    width = 0.34
    bars1 = ax.bar(
        x - width / 2,
        delta_cellpose,
        width=width,
        label="SAM-Cell - Cellpose",
        color="#FBB4AE",
        edgecolor="#222222",
        linewidth=0.45,
    )
    bars2 = ax.bar(
        x + width / 2,
        delta_cellsam,
        width=width,
        label="SAM-Cell - CellSAM",
        color="#B3E2CD",
        edgecolor="#222222",
        linewidth=0.45,
    )
    ax.axhline(0, color="#333333", linewidth=1)
    ax.axvline(len(SOURCE_ORDER) - 1.5, color="#666666", linestyle="--", linewidth=0.9, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([SOURCE_LABEL[s] for s in SOURCE_ORDER])
    ax.set_ylabel("Delta PQ (positive favors SAM-Cell)")
    ax.set_ylim(-0.09, 0.36)
    ax.set_title("SAM-Cell PQ gain relative to each baseline")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    ax.grid(axis="y", alpha=0.18)
    for bars in [bars1, bars2]:
        for bar in bars:
            val = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + (0.008 if val >= 0 else -0.01),
                f"{val:+.2f}",
                ha="center",
                va="bottom" if val >= 0 else "top",
                fontsize=7.8,
                rotation=0,
            )
    fig.tight_layout()
    savefig(fig, "fig_2_11_samcell_delta_pq_by_source")


def plot_2_12_parity(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.9, 6.5))
    sub_sources = SOURCE_ORDER
    label_offsets = {
        "cellpose": (0.006, 0.005, "left"),
        "dsb2018": (0.006, 0.005, "left"),
        "livecell": (0.006, 0.005, "left"),
        "pannuke": (0.006, 0.005, "left"),
        "tissuenet": (-0.055, 0.006, "left"),
        "ALL": (0.008, -0.020, "left"),
    }
    for baseline, color, marker in [
        ("cellpose_official_cyto3", METHOD_COLOR["cellpose_official_cyto3"], "o"),
        ("cellsam_generalist", METHOD_COLOR["cellsam_generalist"], "s"),
    ]:
        base = df[df["method"] == baseline].set_index("source").loc[sub_sources]
        sam = df[df["method"] == "samcell_refine_final"].set_index("source").loc[sub_sources]
        ax.scatter(
            base["pq"],
            sam["pq"],
            s=72,
            color=color,
            marker=marker,
            alpha=0.9,
            edgecolor="white",
            linewidth=0.7,
            label=f"vs {METHOD_LABEL[baseline]}",
        )
        for source, x, y in zip(sub_sources, base["pq"], sam["pq"]):
            if baseline == "cellpose_official_cyto3":
                dx, dy, ha = label_offsets[source]
                ax.text(
                    x + dx,
                    y + dy,
                    SOURCE_LABEL[source],
                    fontsize=7.8,
                    color="#333333",
                    ha=ha,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.55, "pad": 0.4},
                )

    lim_min, lim_max = 0.18, 0.88
    ax.plot([lim_min, lim_max], [lim_min, lim_max], color="#333333", linestyle="--", linewidth=1)
    ax.text(0.23, 0.83, "above diagonal: SAM-Cell better", fontsize=8.5, color="#444444")
    ax.set_xlim(lim_min, lim_max)
    ax.set_ylim(lim_min, lim_max)
    ax.set_xlabel("Baseline PQ")
    ax.set_ylabel("SAM-Cell PQ")
    ax.set_title("Pairwise PQ comparison against baselines")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=0.18)
    fig.tight_layout()
    savefig(fig, "fig_2_12_pairwise_pq_parity")


def load_far_stage() -> tuple[pd.DataFrame, pd.DataFrame]:
    stage = pd.read_csv(FAR_STAGE)
    delta = pd.read_csv(FAR_DELTA)
    return stage, delta


def plot_2_14_stage_metrics(stage: pd.DataFrame) -> None:
    all_stage = stage[(stage["source"] == "ALL") & (stage["method"].isin(STAGE_ORDER))].copy()
    all_stage["method"] = pd.Categorical(all_stage["method"], STAGE_ORDER, ordered=True)
    all_stage = all_stage.sort_values("method")

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    x = np.arange(len(STAGE_ORDER))
    for metric, color, marker in [("pq", "#1B9E77", "o"), ("aji", "#2C7FB8", "s"), ("dice", "#E6AB02", "^")]:
        y = all_stage[metric].to_numpy()
        ax.plot(x, y, marker=marker, linewidth=2.0, markersize=7, label=metric.upper(), color=color)
        for xi, yi in zip(x, y):
            ax.text(xi, yi + 0.015, f"{yi:.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([STAGE_LABEL[s] for s in STAGE_ORDER], rotation=18, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Metric value")
    ax.set_title("Far-OOD staged ablation of SAM-Cell modules")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    savefig(fig, "fig_2_14_farood_stage_ablation_metrics")


def plot_2_15_stage_source_heatmap(stage: pd.DataFrame) -> None:
    sources = ["cellpose", "dsb2018", "livecell", "tissuenet", "ALL"]
    mat = (
        stage[(stage["source"].isin(sources)) & (stage["method"].isin(STAGE_ORDER))]
        .pivot(index="source", columns="method", values="pq")
        .loc[sources, STAGE_ORDER]
    )
    fig, ax = plt.subplots(figsize=(9.2, 4.7))
    im = ax.imshow(mat.to_numpy(), cmap="YlGnBu", vmin=0, vmax=0.85, aspect="auto")
    ax.set_xticks(np.arange(len(STAGE_ORDER)))
    ax.set_xticklabels([STAGE_LABEL[s] for s in STAGE_ORDER], rotation=20, ha="right")
    ax.set_yticks(np.arange(len(sources)))
    ax.set_yticklabels([SOURCE_LABEL[s] for s in sources])
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat.iloc[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8.2, color="#111111")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("PQ")
    ax.set_title("Far-OOD PQ heatmap by source and module stage")
    fig.tight_layout()
    savefig(fig, "fig_2_15_farood_stage_pq_heatmap")


def plot_2_16_module_delta(delta: pd.DataFrame) -> None:
    labels = {
        "edt_watershed_over_semantic_cc": "EDT + watershed\nover semantic CC",
        "current_proposal_selection_over_raw_watershed": "Proposal selection\nover raw watershed",
        "crop_coarse_reinsertion_over_proposal_map": "Coarse reinsertion\nover proposal map",
        "sam2_refinement_over_coarse_no_sam2": "SAM2 refinement\nover coarse map",
    }
    order = list(labels.keys())
    sub = delta[(delta["source"] == "ALL") & (delta["delta"].isin(order))].set_index("delta").loc[order]

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    y = np.arange(len(order))
    vals = sub["mean_delta_pq"].to_numpy()
    colors = ["#1B9E77" if v >= 0 else "#D95F02" for v in vals]
    bars = ax.barh(y, vals, color=colors, edgecolor="#222222", linewidth=0.45)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[k] for k in order])
    ax.invert_yaxis()
    ax.set_xlim(-0.045, 0.48)
    ax.set_xlabel("Mean paired delta PQ")
    ax.set_title("Measured module contribution on Far-OOD")
    ax.grid(axis="x", alpha=0.18)
    for bar, key in zip(bars, order):
        value = bar.get_width()
        win = sub.loc[key, "pq_win_rate"]
        label = f"{value:+.3f}  win={win:.2f}" if abs(value) >= 0.001 else f"{value:+.4f}  win={win:.2f}"
        if abs(value) < 0.006:
            x_text = 0.012
            ha = "left"
        else:
            x_text = value + (0.008 if value >= 0 else -0.008)
            ha = "left" if value >= 0 else "right"
        ax.text(
            x_text,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            ha=ha,
            fontsize=8.6,
        )
    fig.subplots_adjust(left=0.32)
    savefig(fig, "fig_2_16_farood_module_delta_pq")


def plot_2_17_prompt_matched() -> None:
    df = pd.read_csv(PROMPT_MATCHED)
    all_rows = df[(df["source"] == "ALL") & (df["method"].isin(PROMPT_ORDER))].copy()
    all_rows["method"] = pd.Categorical(all_rows["method"], PROMPT_ORDER, ordered=True)
    all_rows = all_rows.sort_values("method")

    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    metrics = ["pq", "aji", "dice"]
    x = np.arange(len(metrics))
    width = 0.24
    for i, method in enumerate(PROMPT_ORDER):
        row = all_rows[all_rows["method"] == method].iloc[0]
        vals = [row[m] for m in metrics]
        bars = ax.bar(
            x + (i - 1) * width,
            vals,
            width=width,
            label=PROMPT_LABEL[method],
            color=PROMPT_COLOR[method],
            edgecolor="#222222",
            linewidth=0.45,
        )
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.012, f"{val:.3f}", ha="center", va="bottom", fontsize=7.8, rotation=90)

    ax.set_xticks(x)
    ax.set_xticklabels([m.upper() for m in metrics])
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Metric value")
    ax.set_title("Prompt-matched native SAM2 diagnostic on balanced eval50")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.20), fontsize=8.8)
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    savefig(fig, "fig_2_17_prompt_matched_sam2_diagnostic")


def write_figure_index(full_df: pd.DataFrame, stage: pd.DataFrame, delta: pd.DataFrame) -> None:
    full_df.to_csv(OUT_DIR / "source_model_metrics_used_for_2_6_2.csv", index=False)
    stage.to_csv(OUT_DIR / "farood_stage_metrics_used_for_2_6_4.csv", index=False)
    delta.to_csv(OUT_DIR / "farood_paired_delta_used_for_2_6_4.csv", index=False)

    all_metrics = full_df[(full_df["source"] == "ALL") & (full_df["method"].isin(METHOD_ORDER))]
    lines = [
        "# Chapter 2 Real-Data Figure Index",
        "",
        "Generated from real SAM-Cell project outputs, not synthetic placeholders.",
        "",
        "## 2.6.2 Quantitative Comparison",
        "",
        "- `fig_2_09_cellcosmos_error_by_source.png`: Error = 1 - PQ by source for Cellpose cyto3, CellSAM, and SAM-Cell.",
        "- `fig_2_10_error_transition_three_models.png`: Dataset-wise error transition across the three models.",
        "- `fig_2_11_samcell_delta_pq_by_source.png`: SAM-Cell PQ delta relative to Cellpose and CellSAM.",
        "- `fig_2_12_pairwise_pq_parity.png`: Pairwise PQ parity scatter against Cellpose and CellSAM.",
        "",
        "Full CellCosmos ALL metrics:",
        "",
        "| method | n | PQ | AJI | Dice |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in all_metrics.iterrows():
        lines.append(f"| {METHOD_LABEL[str(row['method'])]} | {int(row['n'])} | {row['pq']:.6f} | {row['aji']:.6f} | {row['dice']:.6f} |")

    lines.extend(
        [
            "",
            "## 2.6.4 Ablation Replacement",
            "",
            "- `fig_2_14_farood_stage_ablation_metrics.png`: staged module ablation on Far-OOD.",
            "- `fig_2_15_farood_stage_pq_heatmap.png`: source-wise Far-OOD PQ heatmap over stages.",
            "- `fig_2_16_farood_module_delta_pq.png`: paired module contribution in mean delta PQ.",
            "- `fig_2_17_prompt_matched_sam2_diagnostic.png`: prompt-matched native SAM2 diagnostic.",
            "",
            "Interpretation for 2.6.4: the dominant measured Far-OOD gain comes from EDT+watershed after the semantic foreground prior; proposal selection adds a smaller positive gain; coarse reinsertion is nearly neutral; SAM2 refinement is not the dominant contributor under the current measured proxy.",
            "",
        ]
    )
    (OUT_DIR / "figure_index.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    setup_style()

    full_df = load_full_metrics()
    plot_2_09_error_grouped(full_df)
    plot_2_10_error_transition(full_df)
    plot_2_11_delta_pq(full_df)
    plot_2_12_parity(full_df)

    stage, delta = load_far_stage()
    plot_2_14_stage_metrics(stage)
    plot_2_15_stage_source_heatmap(stage)
    plot_2_16_module_delta(delta)
    plot_2_17_prompt_matched()

    write_figure_index(full_df, stage, delta)
    print(f"Figures written to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
