from __future__ import annotations

import argparse
import csv
import inspect
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
import tifffile


def _read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def _stem(row: dict[str, str]) -> str:
    image_name = row.get("image_name") or Path(row["image_path"]).name
    return Path(image_name).stem


def _normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.dtype == np.uint8:
        return arr
    arr = arr.astype(np.float32, copy=False)
    lo, hi = np.percentile(arr, (1, 99))
    if hi <= lo:
        lo, hi = float(arr.min()), float(arr.max())
    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint8)
    arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    return (arr * 255.0 + 0.5).astype(np.uint8)


def _read_image_rgb(path: Path, grayscale_mode: str) -> np.ndarray:
    arr = np.asarray(Image.open(path))
    if arr.ndim == 2:
        channel = _normalize_to_uint8(arr)
        if grayscale_mode == "repeat":
            return np.ascontiguousarray(np.repeat(channel[:, :, None], 3, axis=2))
        out = np.zeros((*channel.shape, 3), dtype=np.uint8)
        out[{"red": 0, "green": 1, "blue": 2}[grayscale_mode]] = channel
        return np.ascontiguousarray(out)
    if arr.ndim != 3:
        raise ValueError(f"Unsupported image shape for {path}: {arr.shape}")
    if arr.shape[2] == 1:
        channel = _normalize_to_uint8(arr[:, :, 0])
        return np.ascontiguousarray(np.repeat(channel[:, :, None], 3, axis=2))
    if arr.shape[2] >= 4:
        arr = arr[:, :, :3]
    if arr.shape[2] != 3:
        raise ValueError(f"Expected 3 channels for {path}, got shape {arr.shape}")
    if arr.dtype == np.uint8:
        return np.ascontiguousarray(arr)
    return np.ascontiguousarray(np.stack([_normalize_to_uint8(arr[:, :, c]) for c in range(3)], axis=2))


def _configure_cache_dirs(out_dir: Path, tiatoolbox_home: Path | None) -> Path:
    cache_root = out_dir / ".runtime_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    resolved_home = tiatoolbox_home or Path(os.environ.get("TIATOOLBOX_HOME", cache_root / "tiatoolbox"))
    resolved_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TIATOOLBOX_HOME", str(resolved_home))
    os.environ.setdefault("MPLCONFIGDIR", str(cache_root / "matplotlib"))
    os.environ.setdefault("NUMBA_CACHE_DIR", str(cache_root / "numba"))
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["NUMBA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    return resolved_home


def _prepare_weights(tiatoolbox_home: Path, model_name: str, weights_path: Path | None) -> Path | None:
    if not weights_path:
        return None
    if not weights_path.exists():
        raise FileNotFoundError(weights_path)
    return weights_path


def _resolve_device(requested: str) -> str:
    if requested in {"cpu", "cuda"}:
        return requested
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _make_segmentor(model_name: str, batch_size: int, device: str, weights_path: Path | None):
    import tiatoolbox
    from tiatoolbox.models.engine.nucleus_instance_segmentor import NucleusInstanceSegmentor

    tiatoolbox.rcParam["TIATOOLBOX_HOME"] = Path(os.environ["TIATOOLBOX_HOME"])
    try:
        return NucleusInstanceSegmentor(
            model=model_name,
            batch_size=batch_size,
            num_workers=0,
            weights=str(weights_path) if weights_path else None,
            device=device,
            verbose=False,
        )
    except TypeError:
        return NucleusInstanceSegmentor(
            pretrained_model=model_name,
            batch_size=batch_size,
            weights=str(weights_path) if weights_path else None,
            num_loader_workers=0,
            num_postproc_workers=0,
            auto_generate_mask=False,
            verbose=False,
        )


def _pad_reflect_safe(image: np.ndarray, pad_width: tuple[tuple[int, int], ...]) -> np.ndarray:
    mode = "reflect" if image.shape[0] > 1 and image.shape[1] > 1 else "edge"
    return np.pad(image, pad_width, mode=mode)


def _extract_patches(
    image: np.ndarray,
    patch_input_shape: tuple[int, int],
    patch_output_shape: tuple[int, int],
) -> tuple[list[np.ndarray], list[tuple[int, int]], tuple[int, int]]:
    out_h, out_w = patch_output_shape
    target_h = ((image.shape[0] + out_h - 1) // out_h) * out_h
    target_w = ((image.shape[1] + out_w - 1) // out_w) * out_w
    image = _pad_reflect_safe(image, ((0, target_h - image.shape[0]), (0, target_w - image.shape[1]), (0, 0)))

    margin_h = (patch_input_shape[0] - out_h) // 2
    margin_w = (patch_input_shape[1] - out_w) // 2
    image = _pad_reflect_safe(image, ((margin_h, margin_h), (margin_w, margin_w), (0, 0)))

    patches: list[np.ndarray] = []
    locations: list[tuple[int, int]] = []
    for top in range(0, target_h, out_h):
        for left in range(0, target_w, out_w):
            patches.append(image[top : top + patch_input_shape[0], left : left + patch_input_shape[1]].copy())
            locations.append((top, left))
    return patches, locations, (target_h, target_w)


def _label_array(prediction: Any) -> np.ndarray:
    if isinstance(prediction, dict):
        for key in ("inst_map", "instance_map", "nuclei_instance_map", "prediction", "label_map"):
            if key in prediction:
                return _label_array(prediction[key])
        raise KeyError(f"Cannot find label map key in prediction dict: {sorted(prediction.keys())}")
    arr = np.asarray(prediction)
    if arr.ndim == 3:
        if arr.shape[-1] == 1:
            arr = arr[..., 0]
        else:
            arr = arr[..., 0]
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D HoverNet prediction, got shape {arr.shape}")
    return arr.astype(np.int32, copy=False)


def _remap_positive(label_map: np.ndarray) -> np.ndarray:
    out = np.zeros(label_map.shape, dtype=np.int32)
    positive = np.unique(label_map)
    positive = positive[positive > 0]
    for new_id, old_id in enumerate(positive.tolist(), start=1):
        out[label_map == old_id] = new_id
    return out


def _stitch_predictions(
    predictions: list[Any] | np.ndarray,
    locations: list[tuple[int, int]],
    stitched_shape: tuple[int, int],
) -> np.ndarray:
    stitched = np.zeros(stitched_shape, dtype=np.int32)
    next_id = 1
    for prediction, (top, left) in zip(predictions, locations):
        patch_labels = _remap_positive(_label_array(prediction))
        positive = patch_labels > 0
        if not np.any(positive):
            continue
        patch_labels[positive] += next_id - 1
        patch_h, patch_w = patch_labels.shape
        stitched[top : top + patch_h, left : left + patch_w] = patch_labels
        next_id = int(stitched.max()) + 1
    return stitched


def _run_one(
    segmentor: Any,
    image_path: Path,
    device: str,
    patch_input_shape: tuple[int, int],
    patch_output_shape: tuple[int, int],
    grayscale_mode: str,
) -> tuple[np.ndarray, int]:
    image = _read_image_rgb(image_path, grayscale_mode)
    patches, locations, stitched_shape = _extract_patches(image, patch_input_shape, patch_output_shape)
    predict_fn = getattr(segmentor, "run")
    params = set(inspect.signature(predict_fn).parameters)
    if "images" not in params:
        raise RuntimeError("This script expects a TIAToolbox NucleusInstanceSegmentor.run API with an images= argument.")
    output = predict_fn(
        images=patches,
        patch_mode=True,
        patch_input_shape=patch_input_shape,
        patch_output_shape=patch_output_shape,
        output_type="dict",
        device=device,
        crash_on_exception=True,
    )
    predictions = output["predictions"] if isinstance(output, dict) and "predictions" in output else output
    labels = _stitch_predictions(predictions, locations, stitched_shape)
    labels = labels[: image.shape[0], : image.shape[1]]
    return labels.astype(np.int32, copy=False), len(patches)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TIAToolbox HoVer-Net inference on a CellCosmos manifest.")
    parser.add_argument("--manifest_csv", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default="hovernet_fast-pannuke")
    parser.add_argument("--weights_path")
    parser.add_argument("--suffix", default="_hovernet.tif")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--patch_input_size", type=int, default=256)
    parser.add_argument("--patch_output_size", type=int, default=164)
    parser.add_argument("--tiatoolbox_home")
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--grayscale_mode", choices=["repeat", "red", "green", "blue"], default="repeat")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    label_dir = out_dir / "labels"
    label_dir.mkdir(parents=True, exist_ok=True)
    tiatoolbox_home = _configure_cache_dirs(out_dir, Path(args.tiatoolbox_home) if args.tiatoolbox_home else None)
    weights_path = _prepare_weights(tiatoolbox_home, args.model, Path(args.weights_path) if args.weights_path else None)
    model_name = args.model
    device = _resolve_device(args.device)
    rows = _read_rows(Path(args.manifest_csv), args.limit)
    patch_input_shape = (int(args.patch_input_size), int(args.patch_input_size))
    patch_output_shape = (int(args.patch_output_size), int(args.patch_output_size))

    started = time.time()
    segmentor = _make_segmentor(model_name, int(args.batch_size), device, weights_path)
    records = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        pred_path = label_dir / f"{_stem(row)}{args.suffix}"
        print(f"[{idx}/{len(rows)}] HoVer-Net {image_path.name}", flush=True)
        if args.skip_existing and pred_path.exists():
            records.append({"image": image_path.name, "prediction_path": str(pred_path), "status": "skipped"})
            continue
        labels, num_patches = _run_one(
            segmentor,
            image_path,
            device,
            patch_input_shape,
            patch_output_shape,
            args.grayscale_mode,
        )
        tifffile.imwrite(pred_path, labels)
        records.append(
            {
                "image": image_path.name,
                "prediction_path": str(pred_path),
                "status": "done",
                "num_patches": num_patches,
                "instances": int(labels.max()),
            }
        )

    payload = {
        "manifest_csv": args.manifest_csv,
        "out_dir": str(out_dir),
        "model": model_name,
        "weights_path": str(weights_path) if weights_path else None,
        "device": device,
        "batch_size": args.batch_size,
        "patch_input_shape": list(patch_input_shape),
        "patch_output_shape": list(patch_output_shape),
        "suffix": args.suffix,
        "grayscale_mode": args.grayscale_mode,
        "n_images": len(rows),
        "elapsed_sec": time.time() - started,
        "python": sys.executable,
        "records": records,
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote labels to {label_dir}")


if __name__ == "__main__":
    main()
