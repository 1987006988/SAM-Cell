from __future__ import annotations

import numpy as np


def label_to_color(label_map: np.ndarray) -> np.ndarray:
    labels = label_map.astype(np.int64, copy=False)
    out = np.zeros((*labels.shape, 3), dtype=np.uint8)
    ids = np.unique(labels)
    for idx in ids:
        if idx == 0:
            continue
        rng = np.random.default_rng(int(idx) * 10007)
        out[labels == idx] = rng.integers(32, 255, size=3, dtype=np.uint8)
    return out


def overlay_instances(image: np.ndarray, label_map: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    color = label_to_color(label_map).astype(np.float32)
    base = image.astype(np.float32)
    mask = label_map > 0
    out = base.copy()
    out[mask] = (1.0 - alpha) * base[mask] + alpha * color[mask]
    return np.clip(out, 0, 255).astype(np.uint8)

