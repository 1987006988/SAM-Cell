#!/usr/bin/env python3
"""Generate Fig. 3-12 from real Cellpose 500-epoch training logs."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


DEFAULT_OUT_DIR = Path("outputs/chapter3_cellpose_loss_fig3_12_20260512")
WINDOWS_SYNC_DIR = Path("/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter3_cellpose_loss_fig3_12_20260512")

LOG_PATTERN = re.compile(
    r"\[INFO\]\s+(?P<epoch>\d+),\s+train_loss=(?P<train>[0-9.]+),\s+"
    r"test_loss=(?P<test>[0-9.]+),\s+LR=(?P<lr>[0-9.]+),\s+time\s+(?P<time>[0-9.]+)s"
)

RUNS = {
    "iid": {
        "label": "I.I.D mixed-domain training",
        "short": "I.I.D mixed",
        "log": DEFAULT_OUT_DIR / "raw/cellpose_iid_finetune_cyto3_train.log",
        "color": "#2E6FBB",
        "val_color": "#8EB6E5",
        "n_train": 2693,
        "n_test": 697,
        "pq": 0.6092,
    },
    "pannuke": {
        "label": "PanNuke core-domain training",
        "short": "PanNuke core",
        "log": DEFAULT_OUT_DIR / "raw/cellpose_pannuke_finetune_cyto3_train.log",
        "color": "#C94C4C",
        "val_color": "#E8A1A1",
        "n_train": 1269,
        "n_test": 336,
        "pq": 0.6207,
    },
}


def parse_loss_log(path: Path) -> list[dict[str, float]]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict[str, float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LOG_PATTERN.search(line)
        if not match:
            continue
        rows.append(
            {
                "epoch": float(match.group("epoch")),
                "train_loss": float(match.group("train")),
                "test_loss": float(match.group("test")),
                "lr": float(match.group("lr")),
                "time_s": float(match.group("time")),
            }
        )
    if not rows:
        raise ValueError(f"No loss rows parsed from {path}")
    return rows


def write_loss_csv(out_dir: Path, parsed: dict[str, list[dict[str, float]]]) -> None:
    rows: list[dict[str, str]] = []
    for run_name, run_rows in parsed.items():
        for row in run_rows:
            rows.append(
                {
                    "run": run_name,
                    "epoch": f"{row['epoch']:.0f}",
                    "train_loss": f"{row['train_loss']:.6f}",
                    "test_loss": f"{row['test_loss']:.6f}",
                    "lr": f"{row['lr']:.9f}",
                    "time_s": f"{row['time_s']:.2f}",
                }
            )
    with (out_dir / "fig_3_12_cellpose_real_loss_points.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _format_axes(ax) -> None:
    ax.grid(True, linestyle="--", linewidth=0.8, color="#D8D1C4", alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color("#303030")
        spine.set_linewidth(1.05)
    ax.tick_params(axis="both", labelsize=9.6, colors="#333333")


def plot_comparison(out_dir: Path, parsed: dict[str, list[dict[str, float]]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), sharey=False)
    fig.patch.set_facecolor("#FFFFFF")
    for ax in axes:
        ax.set_facecolor("#FFFFFF")

    for ax, run_name in zip(axes, ["iid", "pannuke"]):
        cfg = RUNS[run_name]
        rows = parsed[run_name]
        epochs = [row["epoch"] for row in rows]
        train = [row["train_loss"] for row in rows]
        test = [row["test_loss"] for row in rows]
        ax.plot(epochs, train, color=cfg["color"], marker="o", markersize=3.4, linewidth=2.0, label="Train loss")
        ax.plot(epochs, test, color=cfg["val_color"], marker="s", markersize=3.1, linewidth=2.0, label="Validation loss")
        ax.axvline(400, color="#5A5A5A", linestyle=":", linewidth=1.4)
        ax.text(403, max(max(train), max(test)) * 0.86, "LR decay", fontsize=8.4, color="#555555", ha="left")
        ax.set_title(cfg["label"], fontsize=12.2, fontweight="bold", color="#222222")
        ax.set_xlabel("Epoch", fontsize=10.4)
        ax.set_xlim(-8, 500)
        ax.set_ylim(min(min(train), min(test)) * 0.93, max(max(train), max(test)) * 1.08)
        info_y = 0.91 if run_name == "iid" else 0.18
        info_va = "top" if run_name == "iid" else "bottom"
        ax.text(
            0.98,
            info_y,
            f"n_train={cfg['n_train']}, n_val={cfg['n_test']}\nfinal reported PQ={cfg['pq']:.4f}",
            transform=ax.transAxes,
            ha="right",
            va=info_va,
            fontsize=8.8,
            color="#555555",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="#FFFFFF", edgecolor="#E2DDCF", alpha=0.92),
        )
        _format_axes(ax)
    axes[0].set_ylabel("Cellpose loss", fontsize=10.4)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=True, framealpha=0.94, fontsize=9.3)
    fig.suptitle("Real Cellpose 500-Epoch Training Loss", fontsize=14.8, fontweight="bold", y=1.10)
    fig.text(
        0.5,
        -0.02,
        "Loss points are parsed from the original Cellpose logs; Cellpose reports selected epochs and saves the final checkpoint after 500 epochs.",
        ha="center",
        va="center",
        fontsize=9.2,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(out_dir / "fig_3_12_cellpose_500epoch_real_loss_comparison.png", bbox_inches="tight", dpi=300, facecolor="#FFFFFF")
    fig.savefig(out_dir / "fig_3_12_cellpose_500epoch_real_loss_comparison.pdf", bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)


def plot_iid_only(out_dir: Path, parsed: dict[str, list[dict[str, float]]]) -> None:
    cfg = RUNS["iid"]
    rows = parsed["iid"]
    epochs = [row["epoch"] for row in rows]
    train = [row["train_loss"] for row in rows]
    test = [row["test_loss"] for row in rows]
    lr = [row["lr"] for row in rows]

    fig, ax = plt.subplots(figsize=(8.7, 5.1))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.plot(epochs, train, color=cfg["color"], marker="o", markersize=3.4, linewidth=2.2, label="Train loss")
    ax.plot(epochs, test, color=cfg["val_color"], marker="s", markersize=3.1, linewidth=2.2, label="Validation loss")
    ax.axvline(400, color="#5A5A5A", linestyle=":", linewidth=1.4)
    ax.text(403, max(max(train), max(test)) * 0.86, "LR decay", fontsize=8.7, color="#555555", ha="left")
    ax.set_title("Cellpose 500-Epoch Training Loss on I.I.D Mixed CellCosmos", fontsize=13.2, fontweight="bold")
    ax.set_xlabel("Epoch", fontsize=10.5)
    ax.set_ylabel("Cellpose loss", fontsize=10.5)
    ax.set_xlim(-8, 500)
    ax.set_ylim(min(min(train), min(test)) * 0.93, max(max(train), max(test)) * 1.08)
    ax.legend(loc="upper right", frameon=True, framealpha=0.95, fontsize=9.4)
    _format_axes(ax)

    ax2 = ax.twinx()
    ax2.plot(epochs, lr, color="#9A8C7A", linewidth=1.4, linestyle="--", alpha=0.78, label="LR")
    ax2.set_ylabel("Learning rate", fontsize=10.0, color="#6D6258")
    ax2.tick_params(axis="y", labelsize=8.8, colors="#6D6258")
    ax2.spines["right"].set_color("#6D6258")

    fig.text(
        0.5,
        -0.01,
        "Parsed from the original Cellpose log: n_epochs=500, n_train=2693, n_val=697, final checkpoint saved after training.",
        ha="center",
        va="center",
        fontsize=8.9,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(out_dir / "fig_3_12_cellpose_iid_500epoch_real_loss.png", bbox_inches="tight", dpi=300, facecolor="#FFFFFF")
    fig.savefig(out_dir / "fig_3_12_cellpose_iid_500epoch_real_loss.pdf", bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)


def write_notes(out_dir: Path, parsed: dict[str, list[dict[str, float]]]) -> None:
    iid = parsed["iid"]
    pannuke = parsed["pannuke"]
    text = f"""# Fig. 3-12 Cellpose 500-Epoch Real Loss Curves

These figures replace the old simulated loss curve with values parsed from the original Cellpose training logs.

## Recommended thesis figure

- `fig_3_12_cellpose_500epoch_real_loss_comparison.png`
- `fig_3_12_cellpose_500epoch_real_loss_comparison.pdf`

This comparison figure shows the two real Cellpose 500-epoch training runs used in Chapter 3:

- I.I.D mixed-domain CellCosmos training: n_train=2693, n_val=697, reported IID validation PQ=0.6092.
- PanNuke core-domain training: n_train=1269, n_val=336, reported PanNuke core PQ=0.6207 and Far-OOD PQ=0.0247.

## IID-only figure

- `fig_3_12_cellpose_iid_500epoch_real_loss.png`
- `fig_3_12_cellpose_iid_500epoch_real_loss.pdf`

Use this if the text only discusses the traditional random mixed benchmark.

## Logging caveat

Cellpose does not print every single epoch loss in these logs. The curves use the logged checkpoints only: IID has {len(iid)} logged loss points from epoch {int(iid[0]['epoch'])} to {int(iid[-1]['epoch'])}; PanNuke has {len(pannuke)} logged loss points from epoch {int(pannuke[0]['epoch'])} to {int(pannuke[-1]['epoch'])}. Both runs were configured with `n_epochs=500`, and the final checkpoint was saved after training.
"""
    (out_dir / "fig_3_12_cellpose_real_loss_notes.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--sync_windows", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    parsed = {run_name: parse_loss_log(cfg["log"]) for run_name, cfg in RUNS.items()}
    write_loss_csv(args.out_dir, parsed)
    plot_comparison(args.out_dir, parsed)
    plot_iid_only(args.out_dir, parsed)
    write_notes(args.out_dir, parsed)

    if args.sync_windows:
        WINDOWS_SYNC_DIR.mkdir(parents=True, exist_ok=True)
        for path in args.out_dir.iterdir():
            if path.is_file():
                (WINDOWS_SYNC_DIR / path.name).write_bytes(path.read_bytes())
        raw_out = WINDOWS_SYNC_DIR / "raw"
        raw_out.mkdir(exist_ok=True)
        for path in (args.out_dir / "raw").iterdir():
            if path.is_file():
                (raw_out / path.name).write_bytes(path.read_bytes())

    print(args.out_dir / "fig_3_12_cellpose_500epoch_real_loss_comparison.png")
    print(args.out_dir / "fig_3_12_cellpose_iid_500epoch_real_loss.png")
    print(args.out_dir / "fig_3_12_cellpose_real_loss_notes.md")


if __name__ == "__main__":
    main()
