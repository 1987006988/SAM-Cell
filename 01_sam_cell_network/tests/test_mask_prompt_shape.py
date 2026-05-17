from __future__ import annotations

import numpy as np

from sam_cell.prompts.mask_prompt import coarse_mask_to_sam2_logits


def test_mask_prompt_shape_and_range() -> None:
    mask = np.zeros((31, 47), dtype=bool)
    mask[8:20, 10:25] = True
    logits = coarse_mask_to_sam2_logits(mask, size=256, scale=10.0)
    assert logits.shape == (1, 256, 256)
    assert logits.dtype == np.float32
    assert logits.max() <= 10.0
    assert logits.min() >= -10.0
    assert logits[:, 100:150, 100:150].max() > 0

