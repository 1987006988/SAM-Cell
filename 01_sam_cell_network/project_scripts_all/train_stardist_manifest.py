from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.io import load_image, load_label_map


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _pad_pair(image: np.ndarray, label: np.ndarray, min_size: int) -> tuple[np.ndarray, np.ndarray]:
    pad_y = max(0, min_size - int(image.shape[0]))
    pad_x = max(0, min_size - int(image.shape[1]))
    if pad_y == 0 and pad_x == 0:
        return image, label
    image_pad = ((0, pad_y), (0, pad_x), (0, 0))
    label_pad = ((0, pad_y), (0, pad_x))
    return np.pad(image, image_pad, mode="edge"), np.pad(label, label_pad, mode="constant", constant_values=0)


def _load_xy(rows: list[dict[str, str]], min_size: int) -> tuple[list[np.ndarray], list[np.ndarray]]:
    from stardist import fill_label_holes

    images = []
    labels = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        print(f"[{idx}/{len(rows)}] load StarDist train sample {image_path.name}")
        image = load_image(image_path, normalize_mode="none")
        label = fill_label_holes(load_label_map(row["mask_path"]).astype(np.int32, copy=False))
        image, label = _pad_pair(image, label, min_size=min_size)
        images.append(image)
        labels.append(label)
    return images, labels


def _normalize_images(images: list[np.ndarray]) -> list[np.ndarray]:
    from csbdeep.utils import normalize

    return [normalize(image, 1, 99.8, axis=(0, 1)).astype(np.float32, copy=False) for image in images]


def _augmenter(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if random.random() < 0.5:
        x = x[::-1]
        y = y[::-1]
    if random.random() < 0.5:
        x = x[:, ::-1]
        y = y[:, ::-1]
    if random.random() < 0.5:
        scale = random.uniform(0.85, 1.15)
        offset = random.uniform(-0.08, 0.08)
        x = np.clip(x * scale + offset, 0.0, 1.0)
    return np.ascontiguousarray(x), np.ascontiguousarray(y)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a StarDist2D baseline from manifest CSV files.")
    parser.add_argument("--train_csv", required=True)
    parser.add_argument("--val_csv", required=True)
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--model_name", required=True)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--steps_per_epoch", type=int)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--patch_size", type=int, default=256)
    parser.add_argument("--n_rays", type=int, default=32)
    parser.add_argument("--grid", type=int, nargs=2, default=[2, 2])
    parser.add_argument("--learning_rate", type=float, default=0.0003)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train_limit", type=int)
    parser.add_argument("--val_limit", type=int)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    from stardist.models import Config2D, StarDist2D

    train_rows = _read_rows(Path(args.train_csv), args.train_limit)
    val_rows = _read_rows(Path(args.val_csv), args.val_limit)
    x_train, y_train = _load_xy(train_rows, min_size=args.patch_size)
    x_val, y_val = _load_xy(val_rows, min_size=args.patch_size)
    x_train = _normalize_images(x_train)
    x_val = _normalize_images(x_val)

    steps_per_epoch = args.steps_per_epoch
    if steps_per_epoch is None:
        steps_per_epoch = max(50, min(400, int(np.ceil(len(x_train) / max(1, args.batch_size)))))

    conf = Config2D(
        n_rays=args.n_rays,
        grid=tuple(args.grid),
        n_channel_in=3,
        train_patch_size=(args.patch_size, args.patch_size),
        train_batch_size=args.batch_size,
        train_learning_rate=args.learning_rate,
        train_epochs=args.epochs,
        train_steps_per_epoch=steps_per_epoch,
    )
    model = StarDist2D(conf, name=args.model_name, basedir=args.model_dir)
    history = model.train(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        augmenter=_augmenter,
        epochs=args.epochs,
        steps_per_epoch=steps_per_epoch,
    )
    model.optimize_thresholds(x_val, y_val)

    out_dir = Path(args.model_dir) / args.model_name
    payload = {
        "train_csv": args.train_csv,
        "val_csv": args.val_csv,
        "model_dir": args.model_dir,
        "model_name": args.model_name,
        "epochs": args.epochs,
        "steps_per_epoch": steps_per_epoch,
        "batch_size": args.batch_size,
        "patch_size": args.patch_size,
        "n_rays": args.n_rays,
        "grid": args.grid,
        "learning_rate": args.learning_rate,
        "train_n": len(x_train),
        "val_n": len(x_val),
        "history_keys": list(history.history.keys()) if hasattr(history, "history") else [],
    }
    (out_dir / "samcell_train_manifest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(out_dir)


if __name__ == "__main__":
    main()
