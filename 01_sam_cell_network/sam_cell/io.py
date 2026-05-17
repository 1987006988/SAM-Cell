from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def normalize_to_uint8(img: np.ndarray, lower_p: float = 1, upper_p: float = 99) -> np.ndarray:
    arr = img.astype(np.float32, copy=False)
    lo = np.percentile(arr, lower_p)
    hi = np.percentile(arr, upper_p)
    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint8)
    arr = np.clip(arr, lo, hi)
    arr = (arr - lo) / (hi - lo)
    return np.clip(arr * 255.0, 0, 255).astype(np.uint8)


def ensure_rgb_uint8(img: np.ndarray, normalize_mode: str = "none", lower_p: float = 1, upper_p: float = 99) -> np.ndarray:
    arr = np.asarray(img)
    if arr.ndim == 2:
        if arr.dtype != np.uint8 or normalize_mode == "percentile":
            arr = normalize_to_uint8(arr, lower_p, upper_p)
        arr = np.repeat(arr[:, :, None], 3, axis=2)
    elif arr.ndim == 3:
        if arr.shape[2] == 1:
            arr = np.repeat(arr, 3, axis=2)
        elif arr.shape[2] >= 4:
            arr = arr[:, :, :3]
        elif arr.shape[2] > 3:
            arr = arr[:, :, :3]
        if arr.dtype != np.uint8 or normalize_mode == "percentile":
            channels = [normalize_to_uint8(arr[:, :, c], lower_p, upper_p) for c in range(arr.shape[2])]
            arr = np.stack(channels, axis=2)
    else:
        raise ValueError(f"Unsupported image shape: {arr.shape}")
    if arr.shape[2] != 3:
        raise ValueError(f"Expected 3 channels after conversion, got {arr.shape}")
    return np.ascontiguousarray(arr.astype(np.uint8, copy=False))


def load_image(path: str | Path, normalize_mode: str = "none", lower_p: float = 1, upper_p: float = 99) -> np.ndarray:
    with Image.open(path) as img:
        arr = np.array(img)
    return ensure_rgb_uint8(arr, normalize_mode=normalize_mode, lower_p=lower_p, upper_p=upper_p)


def load_label_map(path: str | Path) -> np.ndarray:
    with Image.open(path) as img:
        arr = np.array(img)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    return arr.astype(np.int32, copy=False)

