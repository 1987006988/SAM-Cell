from __future__ import annotations

import numpy as np

from sam_cell.prompts.crop import CropRecord
from sam_cell.sam2_refine.predictor import RefinedInstance


def filter_refined_instance(refined: RefinedInstance, crop: CropRecord, cfg) -> bool:
    area = int(refined.local_mask.sum())
    if area < cfg.min_refined_area:
        return False
    if refined.score < getattr(cfg, "score_threshold", 0.0):
        return False
    if crop.coarse_area > 0 and area / float(crop.coarse_area) > cfg.max_area_growth_ratio:
        return False
    coarse = crop.local_coarse_mask.astype(bool)
    inter = int(np.logical_and(refined.local_mask, coarse).sum())
    union = int(np.logical_or(refined.local_mask, coarse).sum())
    iou = inter / union if union else 0.0
    return iou >= cfg.min_coarse_refined_iou

