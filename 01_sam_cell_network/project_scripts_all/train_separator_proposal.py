from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import sys
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.proposals.internal_selector import infer_dataset_source
from sam_cell.proposals.separator import SeparatorProposalNet, build_separator_input, build_separator_targets


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _source_allowed(source: str, enabled: list[str] | None, disabled: list[str] | None) -> bool:
    if enabled is not None and source not in set(enabled):
        return False
    if disabled is not None and source in set(disabled):
        return False
    return True


def _load_semantic_cache(cfg: Any, image_id: str, source: str, shape: tuple[int, int], allow_missing: bool) -> tuple[np.ndarray, np.ndarray | None]:
    fg_maps = []
    boundary_maps = []
    for expert in cfg.semantic_experts:
        if not getattr(expert, "enabled", True):
            continue
        if not _source_allowed(source, expert.enabled_sources, expert.disabled_sources):
            continue
        if not expert.prob_cache_dir:
            continue
        use_npz = expert.boundary_class_index is not None
        path = Path(expert.prob_cache_dir) / (f"{image_id}.npz" if use_npz else f"{image_id}.npy")
        if not path.exists():
            continue
        cached = np.load(path)
        if isinstance(cached, np.lib.npyio.NpzFile):
            fg = cached["fg_prob"].astype(np.float32, copy=False)
            boundary = cached["boundary_prob"].astype(np.float32, copy=False) if "boundary_prob" in cached else None
        else:
            fg = cached.astype(np.float32, copy=False)
            boundary = None
        if fg.shape == shape:
            fg_maps.append(fg)
        if boundary is not None and boundary.shape == shape:
            boundary_maps.append(boundary)
    if not fg_maps:
        if not allow_missing:
            raise FileNotFoundError(f"No semantic cache found for {image_id}")
        return np.zeros(shape, dtype=np.float32), None
    fg_prob = np.maximum.reduce(fg_maps).astype(np.float32, copy=False)
    boundary_prob = np.maximum.reduce(boundary_maps).astype(np.float32, copy=False) if boundary_maps else None
    return fg_prob, boundary_prob


def _crop_or_pad(arr: np.ndarray, y: int, x: int, size: int, fill: float = 0.0) -> np.ndarray:
    h, w = arr.shape[-2:]
    pad_y = max(0, y + size - h)
    pad_x = max(0, x + size - w)
    if pad_y or pad_x:
        pad_width = [(0, 0)] * arr.ndim
        pad_width[-2] = (0, pad_y)
        pad_width[-1] = (0, pad_x)
        arr = np.pad(arr, pad_width, mode="constant", constant_values=fill)
    return arr[..., y : y + size, x : x + size]


class SeparatorDataset(Dataset):
    def __init__(
        self,
        rows: list[dict[str, str]],
        cfg: Any,
        crop_size: int,
        train: bool,
        allow_missing_cache: bool,
    ) -> None:
        self.rows = rows
        self.cfg = cfg
        self.crop_size = int(crop_size)
        self.train = train
        self.allow_missing_cache = allow_missing_cache

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        row = self.rows[idx]
        image_path = Path(row["image_path"])
        image_id = image_path.stem
        source = row.get("source") or infer_dataset_source(image_id)
        image = load_image(image_path, normalize_mode=self.cfg.image.normalize_mode)
        labels = load_label_map(row["mask_path"])
        fg_prob, boundary_prob = _load_semantic_cache(self.cfg, image_id, source, labels.shape, self.allow_missing_cache)
        x = build_separator_input(image, fg_prob, boundary_prob, self.cfg.separator_proposals.fg_threshold)
        targets = build_separator_targets(labels)
        y = np.stack([targets["fg"], targets["center"], targets["contact"], targets["offset_y"], targets["offset_x"]], axis=0).astype(np.float32)

        h, w = labels.shape
        if self.train:
            yy = random.randint(0, max(0, h - self.crop_size))
            xx = random.randint(0, max(0, w - self.crop_size))
        else:
            yy = max(0, (h - self.crop_size) // 2)
            xx = max(0, (w - self.crop_size) // 2)
        x = _crop_or_pad(x, yy, xx, self.crop_size)
        y = _crop_or_pad(y, yy, xx, self.crop_size)
        if self.train:
            if random.random() < 0.5:
                x = x[..., ::-1].copy()
                y = y[..., ::-1].copy()
                y[4] *= -1.0
            if random.random() < 0.5:
                x = x[..., ::-1, :].copy()
                y = y[..., ::-1, :].copy()
                y[3] *= -1.0
        return {"x": torch.from_numpy(x), "y": torch.from_numpy(y)}


def _loss_fn(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    bce = nn.functional.binary_cross_entropy_with_logits
    fg_loss = bce(pred[:, 0], target[:, 0])
    center_loss = bce(pred[:, 1], target[:, 1])
    contact_loss = bce(pred[:, 2], target[:, 2])
    fg_mask = target[:, 0:1].clamp(0, 1)
    offset_loss = (torch.abs(pred[:, 3:5] - target[:, 3:5]) * fg_mask).sum() / fg_mask.sum().clamp_min(1.0)
    return fg_loss + 2.0 * center_loss + contact_loss + 0.2 * offset_loss


def _run_epoch(model, loader, optimizer, device: torch.device, train: bool) -> float:  # noqa: ANN001
    model.train(train)
    losses = []
    for batch in loader:
        x = batch["x"].to(device, non_blocking=True).float()
        y = batch["y"].to(device, non_blocking=True).float()
        with torch.set_grad_enabled(train):
            pred = model(x)
            loss = _loss_fn(pred, y)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return float(np.mean(losses)) if losses else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the SAM-Cell separator proposal head.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--train_csv", required=True)
    parser.add_argument("--val_csv")
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--crop_size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--allow_missing_cache", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    train_rows = _read_rows(Path(args.train_csv), args.limit)
    val_rows = _read_rows(Path(args.val_csv), args.limit) if args.val_csv else train_rows[: max(1, len(train_rows) // 10)]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device(cfg.separator_proposals.device or cfg.runtime.device)
    model = SeparatorProposalNet(
        in_channels=int(cfg.separator_proposals.input_channels),
        base_channels=int(cfg.separator_proposals.base_channels),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(args.lr), weight_decay=float(args.weight_decay))
    train_loader = DataLoader(
        SeparatorDataset(train_rows, cfg, args.crop_size, train=True, allow_missing_cache=args.allow_missing_cache),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
    )
    val_loader = DataLoader(
        SeparatorDataset(val_rows, cfg, args.crop_size, train=False, allow_missing_cache=args.allow_missing_cache),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
    )

    best_val = float("inf")
    history = []
    for epoch in range(1, int(args.epochs) + 1):
        train_loss = _run_epoch(model, train_loader, optimizer, device, train=True)
        val_loss = _run_epoch(model, val_loader, optimizer, device, train=False)
        row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss}
        history.append(row)
        print(row, flush=True)
        payload = {
            "state_dict": model.state_dict(),
            "input_channels": int(cfg.separator_proposals.input_channels),
            "base_channels": int(cfg.separator_proposals.base_channels),
            "epoch": epoch,
            "val_loss": val_loss,
        }
        torch.save(payload, out_dir / "checkpoint_last.pth")
        if val_loss < best_val:
            best_val = val_loss
            torch.save(payload, out_dir / "checkpoint_best.pth")
        (out_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")

    manifest = {
        "config": str(args.config),
        "train_csv": str(args.train_csv),
        "val_csv": str(args.val_csv) if args.val_csv else None,
        "epochs": int(args.epochs),
        "batch_size": int(args.batch_size),
        "crop_size": int(args.crop_size),
        "best_val_loss": best_val,
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
