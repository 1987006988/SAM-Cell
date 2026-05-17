from __future__ import annotations

from pathlib import Path

import numpy as np

from sam_cell.io import load_label_map
from sam_cell.semantic.base import SemanticPredictor


class MaskSemanticPredictor(SemanticPredictor):
    """Debug predictor that returns a binary foreground map from a label file."""

    def __init__(self, mask_path: str | Path) -> None:
        self.mask_path = Path(mask_path)

    def predict_proba(self, image: np.ndarray) -> np.ndarray:
        mask = load_label_map(self.mask_path)
        if mask.shape != image.shape[:2]:
            raise ValueError(f"Mask shape {mask.shape} does not match image shape {image.shape[:2]}")
        return (mask > 0).astype(np.float32)

