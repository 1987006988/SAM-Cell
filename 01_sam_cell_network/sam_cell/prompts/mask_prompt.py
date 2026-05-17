from __future__ import annotations

import cv2
import numpy as np


def coarse_mask_to_sam2_logits(local_mask: np.ndarray, size: int = 256, scale: float = 10.0) -> np.ndarray:
    mask_256 = cv2.resize(
        local_mask.astype(np.float32, copy=False),
        (size, size),
        interpolation=cv2.INTER_LINEAR,
    )
    logits = (mask_256 * 2.0 - 1.0) * float(scale)
    return logits[None, :, :].astype(np.float32, copy=False)

