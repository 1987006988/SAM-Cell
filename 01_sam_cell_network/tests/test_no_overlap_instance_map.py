from __future__ import annotations

import numpy as np

from sam_cell.postprocess.merge import pixel_competition
from sam_cell.sam2_refine.predictor import RefinedInstance


def test_pixel_competition_resolves_overlap() -> None:
    a_logits = np.zeros((20, 20), dtype=np.float32)
    b_logits = np.zeros((20, 20), dtype=np.float32)
    a_mask = np.zeros((20, 20), dtype=bool)
    b_mask = np.zeros((20, 20), dtype=bool)
    a_mask[2:14, 2:14] = True
    b_mask[8:18, 8:18] = True
    a_logits[a_mask] = 2.0
    b_logits[b_mask] = 4.0
    instances = [
        RefinedInstance(1, (0, 0, 20, 20), a_mask, a_logits, 0.8, np.array([2, 2, 14, 14]), int(a_mask.sum())),
        RefinedInstance(2, (0, 0, 20, 20), b_mask, b_logits, 0.9, np.array([8, 8, 18, 18]), int(b_mask.sum())),
    ]
    label_map, metadata = pixel_competition(instances, (20, 20), use_pixel_logits=True)
    assert label_map.shape == (20, 20)
    assert label_map[10, 10] == 2
    assert len(metadata) == 2
