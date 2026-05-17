from __future__ import annotations

import numpy as np

from sam_cell.config import MergeConfig
from sam_cell.postprocess.selection import choose_instance, make_coarse_instance
from sam_cell.prompts.crop import CropRecord
from sam_cell.sam2_refine.predictor import RefinedInstance


def test_selection_keeps_coarse_when_sam2_growth_is_bad() -> None:
    coarse = np.zeros((32, 32), dtype=bool)
    coarse[10:20, 10:20] = True
    fg_prob = np.zeros((32, 32), dtype=np.float32)
    fg_prob[coarse] = 0.9
    crop = CropRecord(
        crop_image=np.zeros((32, 32, 3), dtype=np.uint8),
        crop_box_xyxy=(0, 0, 32, 32),
        local_box_xyxy=np.array([10, 10, 20, 20], dtype=np.float32),
        local_coarse_mask=coarse,
        proposal_id=1,
        coarse_area=int(coarse.sum()),
        local_fg_prob=fg_prob,
    )
    coarse_inst = make_coarse_instance(crop)
    huge = np.ones((32, 32), dtype=bool)
    huge_inst = RefinedInstance(
        proposal_id=1,
        global_crop_box_xyxy=(0, 0, 32, 32),
        local_mask=huge,
        local_logits=huge.astype(np.float32) * 10,
        score=0.99,
        local_box_xyxy=np.array([0, 0, 32, 32], dtype=np.float32),
        coarse_area=int(coarse.sum()),
        source="sam2_box_mask",
    )
    selected = choose_instance([coarse_inst, huge_inst], crop, MergeConfig(accept_sam2_max_area_growth_ratio=2.0))
    assert selected is not None
    assert selected.source == "watershed"
