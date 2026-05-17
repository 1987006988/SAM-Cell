from __future__ import annotations

import numpy as np

from sam_cell.config import CropConfig
from sam_cell.prompts.crop import make_adaptive_crop
from sam_cell.proposals.regions import InstanceProposal


def test_crop_local_box_matches_global_bbox() -> None:
    image = np.zeros((100, 120, 3), dtype=np.uint8)
    mask = np.zeros((100, 120), dtype=bool)
    mask[30:50, 40:70] = True
    proposal = InstanceProposal(1, (40, 30, 70, 50), mask, int(mask.sum()), (55.0, 40.0), 1.0)
    crop = make_adaptive_crop(image, proposal, CropConfig(alpha=0.2, min_crop_size=64))
    cx1, cy1, _cx2, _cy2 = crop.crop_box_xyxy
    local = crop.local_box_xyxy.astype(int)
    assert tuple(local[:2]) == (40 - cx1, 30 - cy1)
    assert tuple(local[2:]) == (70 - cx1, 50 - cy1)
    assert crop.local_coarse_mask.sum() == mask.sum()
