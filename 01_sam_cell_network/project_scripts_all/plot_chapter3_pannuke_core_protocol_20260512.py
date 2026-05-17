#!/usr/bin/env python3
"""Generate Fig. 3-11 for the PanNuke-core OOD evaluation protocol."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np


DEFAULT_OUT_DIR = Path("outputs/chapter3_pannuke_core_protocol_20260512")
WINDOWS_SYNC_DIR = Path("/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter3_pannuke_core_protocol_20260512")
DEFAULT_CORESET_INDEX = Path("/mnt/d/cell data/CellCosmos_Benchmark/CellCosmos_Core_3500/dataset_index.csv")
DEFAULT_FEATURE_INFO = Path("/mnt/d/cell data/CellCosmos_Benchmark/Features_Output/all_images_info_wsl.csv")
DEFAULT_SAM2_FEATURES = Path("/mnt/d/cell data/CellCosmos_Benchmark/Features_Output/sam2_features_all.npy")


COLORS = {
    "bg": "#F8F6EF",
    "ink": "#252525",
    "muted": "#666666",
    "core": "#7AA974",
    "core_dark": "#3E7A46",
    "train": "#A9D18E",
    "test": "#D8EEC4",
    "far": "#E9A36A",
    "far_dark": "#B75C2B",
    "tissue": "#5CA4A9",
    "live": "#7E83C9",
    "cellpose": "#D982A6",
    "dsb": "#E7C65F",
    "line": "#B7B1A3",
}

DISPLAY_NAMES = {
    "cellpose": "Cellpose",
    "dsb2018": "DSB2018",
    "livecell": "LIVECell",
    "pannuke": "PanNuke",
    "tissuenet": "TissueNet",
}

SOURCE_COLORS = {
    "pannuke": "#C94C4C",
    "tissuenet": "#2F8F46",
    "dsb2018": "#2F6FB0",
    "cellpose": "#C96D9A",
    "livecell": "#8061B7",
}

FAR_TEST_COUNTS = {
    "tissuenet": 1357,
    "livecell": 149,
    "cellpose": 147,
    "dsb2018": 142,
}


def rounded_box(ax, xy, width, height, facecolor, edgecolor=None, lw=1.6, radius=0.04, zorder=2):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=lw,
        facecolor=facecolor,
        edgecolor=edgecolor or facecolor,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, xy1, xy2, color=None, lw=2.4, rad=0.0, zorder=3):
    patch = FancyArrowPatch(
        xy1,
        xy2,
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=lw,
        color=color or COLORS["line"],
        connectionstyle=f"arc3,rad={rad}",
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def label(ax, x, y, text, size=12, weight="regular", color=None, ha="center", va="center", rotation=0):
    ax.text(
        x,
        y,
        text,
        ha=ha,
        va=va,
        fontsize=size,
        fontweight=weight,
        color=color or COLORS["ink"],
        rotation=rotation,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def compute_domain_distances(
    coreset_index: Path = DEFAULT_CORESET_INDEX,
    feature_info: Path = DEFAULT_FEATURE_INFO,
    sam2_features: Path = DEFAULT_SAM2_FEATURES,
) -> tuple[dict[str, float], dict[str, int]]:
    """Compute source-center cosine distance to PanNuke from saved SAM2 features."""
    if not coreset_index.exists():
        raise FileNotFoundError(coreset_index)
    if not feature_info.exists():
        raise FileNotFoundError(feature_info)
    if not sam2_features.exists():
        raise FileNotFoundError(sam2_features)

    all_rows = _read_csv_rows(feature_info)
    name_to_index = {os.path.basename(row["Image_Path"]): i for i, row in enumerate(all_rows)}
    core_rows = _read_csv_rows(coreset_index)
    features = np.load(sam2_features).astype(np.float64, copy=False)
    if len(all_rows) != len(features):
        raise ValueError(f"feature row mismatch: info={len(all_rows)} features={len(features)}")

    groups: dict[str, list[int]] = {}
    missing: list[str] = []
    for row in core_rows:
        name = row["Image_Name"]
        idx = name_to_index.get(name)
        if idx is None:
            missing.append(name)
            continue
        source = row["Source"].strip().lower()
        groups.setdefault(source, []).append(idx)
    if missing:
        raise ValueError(f"{len(missing)} coreset images were not found in feature info, e.g. {missing[:3]}")
    if "pannuke" not in groups:
        raise ValueError("PanNuke source is missing from the coreset groups.")

    features /= np.linalg.norm(features, axis=1, keepdims=True) + 1e-12
    centers: dict[str, np.ndarray] = {}
    for source, indices in groups.items():
        center = features[indices].mean(axis=0)
        centers[source] = center / (np.linalg.norm(center) + 1e-12)

    pannuke_center = centers["pannuke"]
    distances = {
        source: 1.0 - float(np.dot(pannuke_center, center))
        for source, center in centers.items()
        if source != "pannuke"
    }
    counts = {source: len(indices) for source, indices in groups.items()}
    return distances, counts


def draw_distance_axis(
    out_dir: Path,
    coreset_index: Path = DEFAULT_CORESET_INDEX,
    feature_info: Path = DEFAULT_FEATURE_INFO,
    sam2_features: Path = DEFAULT_SAM2_FEATURES,
) -> None:
    """Draw the thesis-facing Fig. 3-11 as a PanNuke-centered distance protocol."""
    out_dir.mkdir(parents=True, exist_ok=True)
    distances, coreset_counts = compute_domain_distances(coreset_index, feature_info, sam2_features)
    target_sources = [s for s in ("tissuenet", "dsb2018", "cellpose", "livecell") if s in distances]
    target_sources = sorted(target_sources, key=lambda s: distances[s])
    max_distance = max(distances[s] for s in target_sources)
    x_max = max(0.12, max_distance * 1.18)

    fig, ax = plt.subplots(figsize=(13.0, 4.7))
    fig.patch.set_facecolor("#FCFAF3")
    ax.set_facecolor("#FCFAF3")
    ax.set_xlim(-0.008, x_max)
    ax.set_ylim(-0.52, 0.52)
    ax.axis("off")

    ax.hlines(0, 0, x_max * 0.97, color="#202020", linewidth=2.2, zorder=1)
    arrow_end = FancyArrowPatch(
        (x_max * 0.955, 0),
        (x_max * 0.985, 0),
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=2.2,
        color="#202020",
        zorder=1,
    )
    ax.add_patch(arrow_end)

    lower_start = distances[target_sources[0]] * 0.78
    lower_end = distances[target_sources[min(1, len(target_sources) - 1)]] * 1.08
    higher_start = distances[target_sources[max(0, len(target_sources) - 2)]] * 0.92
    higher_end = min(x_max * 0.92, distances[target_sources[-1]] * 1.08)
    ax.axvspan(lower_start, lower_end, ymin=0.44, ymax=0.56, color="#CFE8CF", alpha=0.95, zorder=0)
    ax.axvspan(higher_start, higher_end, ymin=0.44, ymax=0.56, color="#F6CDBA", alpha=0.95, zorder=0)

    ax.scatter([0], [0], s=110, color="#111111", edgecolor="white", linewidth=1.6, zorder=4)
    ax.text(
        0,
        0.155,
        "Core / Source Domain\n(I.I.D)\nPanNuke",
        ha="center",
        va="bottom",
        fontsize=10.4,
        fontweight="bold",
        color="#1F1F1F",
    )
    ax.text(
        0,
        -0.118,
        f"train 1341 + test 336\nfeature n={coreset_counts.get('pannuke', 1677)}",
        ha="center",
        va="top",
        fontsize=8.8,
        color="#555555",
    )

    # Alternating label anchors keep the compact one-dimensional protocol readable.
    label_sides = {
        "tissuenet": "above",
        "dsb2018": "below",
        "cellpose": "above",
        "livecell": "below",
    }
    for source in target_sources:
        x = distances[source]
        color = SOURCE_COLORS[source]
        ax.scatter([x], [0], s=118, color=color, edgecolor="white", linewidth=1.6, zorder=4)
        above = label_sides.get(source, "above") == "above"
        y = 0.135 if above else -0.135
        va = "bottom" if above else "top"
        ax.text(
            x,
            y,
            f"{DISPLAY_NAMES[source]}\n(d={x:.3f})",
            ha="center",
            va=va,
            fontsize=9.5,
            fontweight="bold",
            color=color,
        )

    ax.text(
        (lower_start + higher_end) / 2,
        -0.365,
        "Non-PanNuke Far-OOD targets form a feature-distance gradient",
        ha="center",
        va="center",
        fontsize=9.3,
        color="#3F3F3F",
        fontweight="bold",
    )
    ax.text(
        x_max * 0.985,
        0.088,
        "larger domain shift",
        ha="right",
        va="bottom",
        fontsize=9.0,
        color="#4A4A4A",
    )

    ax.text(
        x_max * 0.49,
        0.465,
        "PanNuke-Core OOD Generalization Evaluation Protocol",
        ha="center",
        va="center",
        fontsize=15.0,
        fontweight="bold",
        color="#1F1F1F",
    )
    ax.text(
        x_max * 0.49,
        0.405,
        "Distances are recomputed from CellCosmos Core3500 SAM2 image-feature centers; all colored targets are evaluated zero-shot as the non-PanNuke Far-OOD split.",
        ha="center",
        va="center",
        fontsize=8.9,
        color="#555555",
    )
    ax.text(
        x_max * 0.49,
        -0.475,
        "Far-OOD test composition: TissueNet 1357 | DSB2018 142 | Cellpose 147 | LIVECell 149",
        ha="center",
        va="center",
        fontsize=8.7,
        color="#555555",
    )

    # Save with both the new explicit name and the original Fig. 3-11 filename used by the thesis folder.
    for stem in ["fig_3_11_pannuke_core_ood_distance_axis", "fig_3_11_pannuke_core_ood_protocol"]:
        fig.savefig(out_dir / f"{stem}.png", bbox_inches="tight", dpi=300)
        fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)

    distance_rows = ["source,distance_to_pannuke,coreset_feature_count,far_ood_test_count"]
    for source in target_sources:
        distance_rows.append(
            f"{source},{distances[source]:.9f},{coreset_counts.get(source, '')},{FAR_TEST_COUNTS.get(source, '')}"
        )
    (out_dir / "fig_3_11_pannuke_core_distance_values.csv").write_text("\n".join(distance_rows) + "\n", encoding="utf-8")


def draw_protocol(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.6, 7.6))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    label(ax, 0.5, 0.955, "PanNuke-Core OOD Evaluation Protocol", size=19, weight="bold")
    label(
        ax,
        0.5,
        0.915,
        "single-source supervised training on PanNuke; zero-shot transfer to non-PanNuke microscopy domains",
        size=10.8,
        color=COLORS["muted"],
    )

    # Left: dataset pool.
    rounded_box(ax, (0.045, 0.62), 0.22, 0.19, "#FFFFFF", COLORS["line"], lw=1.5)
    label(ax, 0.155, 0.755, "CellCosmos Core Set", size=14.5, weight="bold")
    label(ax, 0.155, 0.715, "n = 3472 images", size=11.8, color=COLORS["muted"])
    label(ax, 0.155, 0.675, "five source datasets", size=11.2, color=COLORS["muted"])
    label(ax, 0.155, 0.642, "same image/mask format", size=11.2, color=COLORS["muted"])

    # Middle: PanNuke core domain split.
    rounded_box(ax, (0.36, 0.60), 0.29, 0.24, "#FFFFFF", COLORS["core"], lw=2.2)
    label(ax, 0.505, 0.795, "Core / Source Domain", size=14.8, weight="bold", color=COLORS["core_dark"])
    label(ax, 0.505, 0.758, "PanNuke H&E pathology", size=11.8, color=COLORS["muted"])
    label(ax, 0.505, 0.725, "n = 1677", size=11.5, color=COLORS["muted"])

    x0, y0, w, h = 0.39, 0.635, 0.23, 0.055
    ax.add_patch(Rectangle((x0, y0), w * 1341 / 1677, h, facecolor=COLORS["train"], edgecolor="none", zorder=4))
    ax.add_patch(Rectangle((x0 + w * 1341 / 1677, y0), w * 336 / 1677, h, facecolor=COLORS["test"], edgecolor="none", zorder=4))
    ax.add_patch(Rectangle((x0, y0), w, h, facecolor="none", edgecolor=COLORS["core_dark"], linewidth=1.2, zorder=5))
    label(ax, x0 + 0.079, y0 + 0.027, "train\n1341", size=9.2, color=COLORS["ink"])
    label(ax, x0 + 0.205, y0 + 0.027, "test\n336", size=9.2, color=COLORS["ink"])

    # Right: Far-OOD target pool.
    rounded_box(ax, (0.72, 0.56), 0.235, 0.32, "#FFFFFF", COLORS["far"], lw=2.2)
    label(ax, 0.8375, 0.83, "Far-OOD Target Pool", size=14.8, weight="bold", color=COLORS["far_dark"])
    label(ax, 0.8375, 0.795, "non-PanNuke, unseen in training", size=11.2, color=COLORS["muted"])
    label(ax, 0.8375, 0.763, "n = 1795", size=11.2, color=COLORS["muted"])

    bar_x, bar_y, bar_w, bar_h = 0.75, 0.70, 0.175, 0.042
    far_segments = [
        ("TissueNet", 1357, COLORS["tissue"]),
        ("LIVECell", 149, COLORS["live"]),
        ("Cellpose", 147, COLORS["cellpose"]),
        ("DSB2018", 142, COLORS["dsb"]),
    ]
    start = bar_x
    total_far = sum(v for _name, v, _color in far_segments)
    for _name, count, color in far_segments:
        seg_w = bar_w * count / total_far
        ax.add_patch(Rectangle((start, bar_y), seg_w, bar_h, facecolor=color, edgecolor="none", zorder=4))
        start += seg_w
    ax.add_patch(Rectangle((bar_x, bar_y), bar_w, bar_h, facecolor="none", edgecolor=COLORS["far_dark"], linewidth=1.1, zorder=5))

    legend_y = 0.665
    for idx, (name, count, color) in enumerate(far_segments):
        yy = legend_y - idx * 0.045
        ax.add_patch(Rectangle((0.755, yy - 0.012), 0.018, 0.018, facecolor=color, edgecolor="none"))
        label(ax, 0.78, yy - 0.003, f"{name}: {count}", size=10.3, ha="left", color=COLORS["ink"])

    # Arrows.
    arrow(ax, (0.267, 0.715), (0.355, 0.715), COLORS["line"], lw=2.4)
    arrow(ax, (0.652, 0.715), (0.716, 0.715), COLORS["line"], lw=2.4)

    # Evaluation pressure ladder.
    rounded_box(ax, (0.07, 0.23), 0.86, 0.22, "#FFFFFF", "#D9D3C8", lw=1.4)
    label(ax, 0.5, 0.418, "Evaluation pressure ladder", size=14.5, weight="bold")
    rounded_box(ax, (0.12, 0.285), 0.22, 0.085, COLORS["test"], COLORS["core"], lw=1.4, radius=0.025)
    rounded_box(ax, (0.395, 0.285), 0.22, 0.085, "#F1F1ED", "#C8C3BA", lw=1.3, radius=0.025)
    rounded_box(ax, (0.67, 0.285), 0.22, 0.085, "#F8D5BD", COLORS["far"], lw=1.4, radius=0.025)
    label(ax, 0.23, 0.343, "Core-domain test", size=12.0, weight="bold", color=COLORS["core_dark"])
    label(ax, 0.23, 0.313, "PanNuke test n=336", size=10.0, color=COLORS["muted"])
    label(ax, 0.505, 0.343, "No target adaptation", size=12.0, weight="bold", color=COLORS["ink"])
    label(ax, 0.505, 0.313, "same metrics, same protocol", size=10.0, color=COLORS["muted"])
    label(ax, 0.78, 0.343, "Far-OOD test", size=12.0, weight="bold", color=COLORS["far_dark"])
    label(ax, 0.78, 0.313, "non-PanNuke n=1795", size=10.0, color=COLORS["muted"])
    arrow(ax, (0.345, 0.327), (0.39, 0.327), COLORS["line"], lw=2.0)
    arrow(ax, (0.62, 0.327), (0.665, 0.327), COLORS["line"], lw=2.0)
    label(ax, 0.5, 0.248, "The protocol separates in-domain fitting ability from cross-domain generalization under optical/staining shift.", size=10.2, color=COLORS["muted"])

    # Principle box.
    rounded_box(ax, (0.07, 0.065), 0.86, 0.10, "#EFEAE0", "#D3CABC", lw=1.2, radius=0.025)
    label(ax, 0.1, 0.132, "Protocol rule", size=11.5, weight="bold", ha="left")
    label(
        ax,
        0.1,
        0.095,
        "PanNuke-trained supervised baselines use only the core train split; all non-PanNuke images are reserved for Far-OOD evaluation.",
        size=10.2,
        color=COLORS["muted"],
        ha="left",
    )

    fig.savefig(out_dir / "fig_3_11_pannuke_core_ood_flowchart.png", bbox_inches="tight", dpi=300)
    fig.savefig(out_dir / "fig_3_11_pannuke_core_ood_flowchart.pdf", bbox_inches="tight")
    plt.close(fig)


def write_text(out_dir: Path) -> None:
    text = """# 3.3.3 阶梯式 OOD 评估协议制定（PanNuke 核心域版本）

在完成 CellCosmos 核心集的多源异构数据构建与特征空间分析后，本文进一步制定面向跨域泛化能力验证的分布外评估协议。为使评估协议与后续模型训练和复现实验保持一致，本文选取 PanNuke 作为单源核心域（Core / Source Domain）。PanNuke 主要来源于 H&E 染色组织病理图像，具有细胞密度高、实例贴连明显、组织纹理复杂等特点，能够代表组织病理场景下具有明确物理成像机制的核心训练域。以该数据集作为单源训练域，可以更严格地检验传统全监督模型在离开单一染色与成像分布后的泛化退化程度。

具体而言，本文首先从 CellCosmos_Core_3500 中筛选 PanNuke 样本构成核心域，并按照固定随机种子进行 8:2 划分。其中，PanNuke 训练集包含 1341 张图像，用于训练 Cellpose、StarDist 等核心域监督基线；PanNuke 核心域测试集包含 336 张图像，用于验证模型是否已经充分掌握源域内的细胞形态与实例拓扑结构。该设置对应传统意义上的域内测试，主要衡量模型对核心域分布的拟合能力。

在分布外测试阶段，所有非 PanNuke 来源的样本均被严格保留为 Far-OOD 测试集，共 1795 张图像，包含 TissueNet、LIVECell、Cellpose 和 DSB2018 等来源。这些数据在成像方式、染色机制、背景纹理、目标尺度和细胞形态上均与 PanNuke 存在显著差异。例如，TissueNet 包含高密度组织荧光图像，LIVECell 主要为相差显微活细胞图像，DSB2018 以细胞核图像为主，Cellpose 则包含更复杂的细胞培养形态。因此，Far-OOD 测试集能够有效模拟模型从单一病理染色源域迁移到多种未见显微模态时所面临的真实域偏移压力。

基于上述划分，本文构建了如图 3-11 所示的 PanNuke 中心化 OOD 评估协议。图中横轴表示各来源数据在 SAM2 图像特征空间中相对于 PanNuke 源域中心的余弦距离，用于可视化不同目标域的分布偏移强度。重新计算得到的中心距离分别为 TissueNet 0.069、DSB2018 0.076、Cellpose 0.086、LIVECell 0.113，说明非 PanNuke 目标域内部也存在由低到高的特征距离梯度。需要强调的是，该距离梯度仅用于解释域偏移强弱，并不引入新的训练集划分；所有非 PanNuke 样本在实验中均被统一视为未参与训练的 Far-OOD 测试集。

该协议的关键约束是：所有基于核心域训练的监督模型在训练阶段只能使用 PanNuke 训练集，不允许使用 Far-OOD 测试集中的图像或标注进行微调；而 CellSAM、官方 Cellpose cyto3、原生 SAM2 与 SAM-Cell 等通用或免微调模型则直接在相同测试划分上进行推理。通过这种设置，本文能够将“源域拟合能力”和“跨域泛化能力”明确区分开来，避免随机混合划分掩盖模型对单一数据集视觉捷径的依赖。

图 3-11 基于 PanNuke 核心域与 SAM2 特征中心余弦距离的 CellCosmos 跨域泛化评估协议。
"""
    (out_dir / "section_3_3_3_pannuke_core_replacement_text.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--coreset_index", type=Path, default=DEFAULT_CORESET_INDEX)
    parser.add_argument("--feature_info", type=Path, default=DEFAULT_FEATURE_INFO)
    parser.add_argument("--sam2_features", type=Path, default=DEFAULT_SAM2_FEATURES)
    parser.add_argument("--sync_windows", action="store_true")
    args = parser.parse_args()
    draw_protocol(args.out_dir)
    draw_distance_axis(args.out_dir, args.coreset_index, args.feature_info, args.sam2_features)
    write_text(args.out_dir)
    if args.sync_windows:
        WINDOWS_SYNC_DIR.mkdir(parents=True, exist_ok=True)
        for path in args.out_dir.iterdir():
            if path.is_file():
                (WINDOWS_SYNC_DIR / path.name).write_bytes(path.read_bytes())
    print(args.out_dir / "fig_3_11_pannuke_core_ood_protocol.png")
    print(args.out_dir / "fig_3_11_pannuke_core_ood_distance_axis.png")
    print(args.out_dir / "fig_3_11_pannuke_core_distance_values.csv")
    print(args.out_dir / "section_3_3_3_pannuke_core_replacement_text.md")


if __name__ == "__main__":
    main()
