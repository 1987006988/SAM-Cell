from __future__ import annotations

import numpy as np

from sam_cell.prompts.crop import CropRecord
from sam_cell.sam2_refine.predictor import RefinedInstance


def make_coarse_instance(crop: CropRecord, score: float = 0.5, logit_scale: float = 10.0) -> RefinedInstance:
    mask = crop.local_coarse_mask.astype(bool)
    logits = (mask.astype(np.float32) * 2.0 - 1.0) * float(logit_scale)
    return RefinedInstance(
        proposal_id=crop.proposal_id,
        global_crop_box_xyxy=crop.crop_box_xyxy,
        local_mask=np.ascontiguousarray(mask),
        local_logits=np.ascontiguousarray(logits),
        score=float(score),
        local_box_xyxy=crop.local_box_xyxy.copy(),
        coarse_area=crop.coarse_area,
        source="watershed",
    )


def instance_quality(instance: RefinedInstance, crop: CropRecord, semantic_threshold: float = 0.35) -> dict[str, float]:
    area = int(instance.local_mask.sum())
    coarse = crop.local_coarse_mask.astype(bool)
    inter = int(np.logical_and(instance.local_mask, coarse).sum())
    union = int(np.logical_or(instance.local_mask, coarse).sum())
    coarse_iou = inter / union if union else 0.0
    growth = area / float(max(1, crop.coarse_area))
    if crop.local_fg_prob is not None and area > 0:
        semantic_support = float((crop.local_fg_prob[instance.local_mask] >= semantic_threshold).mean())
        mean_fg_prob = float(crop.local_fg_prob[instance.local_mask].mean())
    else:
        semantic_support = 1.0
        mean_fg_prob = 1.0
    area_balance = max(0.0, 1.0 - abs(np.log(max(growth, 1e-6))))
    quality = (
        0.35 * min(max(float(instance.score), 0.0), 1.0)
        + 0.30 * coarse_iou
        + 0.25 * semantic_support
        + 0.10 * area_balance
    )
    return {
        "area": float(area),
        "coarse_iou": float(coarse_iou),
        "growth_ratio": float(growth),
        "semantic_support": float(semantic_support),
        "mean_fg_prob": float(mean_fg_prob),
        "quality": float(quality),
    }


def passes_quality_gate(instance: RefinedInstance, crop: CropRecord, cfg, semantic_threshold: float) -> bool:
    stats = instance_quality(instance, crop, semantic_threshold)
    if stats["area"] < cfg.min_refined_area:
        return False
    if instance.source.startswith("sam2"):
        if instance.score < cfg.accept_sam2_min_score:
            return False
        if stats["coarse_iou"] < cfg.accept_sam2_min_coarse_iou:
            return False
        if stats["growth_ratio"] > cfg.accept_sam2_max_area_growth_ratio:
            return False
        if stats["semantic_support"] < cfg.accept_sam2_min_semantic_support:
            return False
    else:
        if stats["growth_ratio"] > cfg.max_area_growth_ratio:
            return False
    return True


def choose_instance(candidates: list[RefinedInstance], crop: CropRecord, cfg) -> RefinedInstance | None:
    valid: list[RefinedInstance] = []
    for candidate in candidates:
        if not passes_quality_gate(candidate, crop, cfg, cfg.semantic_support_threshold):
            continue
        stats = instance_quality(candidate, crop, cfg.semantic_support_threshold)
        candidate.quality = stats["quality"]
        valid.append(candidate)
    if not valid:
        return None
    return max(valid, key=lambda item: (item.quality, item.score))
