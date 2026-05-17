from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import binary_closing, disk, remove_small_objects


def binarize_foreground(prob: np.ndarray, threshold: float) -> np.ndarray:
    return np.asarray(prob >= threshold, dtype=bool)


def clean_foreground(mask: np.ndarray, min_area: int, fill_holes: bool = True, closing_radius: int = 1) -> np.ndarray:
    cleaned = np.asarray(mask, dtype=bool)
    if closing_radius and closing_radius > 0:
        cleaned = binary_closing(cleaned, disk(closing_radius))
    if fill_holes:
        cleaned = ndi.binary_fill_holes(cleaned)
    if min_area and min_area > 0:
        cleaned = remove_small_objects(cleaned, min_size=min_area)
    return np.asarray(cleaned, dtype=bool)

