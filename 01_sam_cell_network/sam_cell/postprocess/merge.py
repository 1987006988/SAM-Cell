from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from sam_cell.sam2_refine.predictor import RefinedInstance


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


def paste_instance_to_canvas(refined: RefinedInstance, full_shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    height, width = full_shape
    x1, y1, x2, y2 = refined.global_crop_box_xyxy
    mask_canvas = np.zeros((height, width), dtype=bool)
    logits_canvas = np.full((height, width), -np.inf, dtype=np.float32)
    crop_h = y2 - y1
    crop_w = x2 - x1
    local_mask = refined.local_mask[:crop_h, :crop_w]
    local_logits = refined.local_logits[:crop_h, :crop_w]
    mask_canvas[y1:y2, x1:x2] = local_mask
    logits_canvas[y1:y2, x1:x2] = local_logits
    return mask_canvas, logits_canvas


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return inter / union if union else 0.0


def remove_duplicate_instances(
    instances: list[RefinedInstance],
    full_shape: tuple[int, int],
    iou_threshold: float = 0.85,
) -> list[RefinedInstance]:
    kept: list[RefinedInstance] = []
    kept_masks: list[np.ndarray] = []
    for inst in sorted(instances, key=lambda x: x.score, reverse=True):
        mask, _ = paste_instance_to_canvas(inst, full_shape)
        if not np.any(mask):
            continue
        if any(mask_iou(mask, prev) >= iou_threshold for prev in kept_masks):
            continue
        kept.append(inst)
        kept_masks.append(mask)
    return kept


def pixel_competition(
    instances: list[RefinedInstance],
    full_shape: tuple[int, int],
    use_pixel_logits: bool = True,
    fg_mask: np.ndarray | None = None,
    semantic_gate_dilation: int = 0,
) -> tuple[np.ndarray, list[dict]]:
    height, width = full_shape
    label_map = np.zeros((height, width), dtype=np.int32)
    score_map = np.full((height, width), -np.inf, dtype=np.float32)
    allowed = None
    if fg_mask is not None:
        allowed = fg_mask.astype(bool)
        if semantic_gate_dilation and semantic_gate_dilation > 0:
            allowed = ndi.binary_dilation(allowed, iterations=int(semantic_gate_dilation))

    raw_metadata: dict[int, dict] = {}
    for new_id, inst in enumerate(instances, start=1):
        mask, logits = paste_instance_to_canvas(inst, full_shape)
        if allowed is not None:
            mask &= allowed
        if not np.any(mask):
            continue
        if use_pixel_logits:
            candidate_score = _sigmoid(logits) * float(inst.score)
        else:
            candidate_score = np.full((height, width), float(inst.score), dtype=np.float32)
        update = mask & (candidate_score > score_map)
        label_map[update] = new_id
        score_map[update] = candidate_score[update]
        raw_metadata[new_id] = {
            "proposal_id": inst.proposal_id,
            "score": float(inst.score),
            "quality": float(inst.quality),
            "source": inst.source,
            "crop_box_xyxy": list(map(int, inst.global_crop_box_xyxy)),
        }

    # Recompute metadata after pixel competition so JSON matches the final label map.
    remapped = np.zeros_like(label_map)
    metadata: list[dict] = []
    for final_id, old_id in enumerate([int(i) for i in np.unique(label_map) if i != 0], start=1):
        pixels = label_map == old_id
        ys, xs = np.nonzero(pixels)
        if ys.size == 0:
            continue
        remapped[pixels] = final_id
        item = dict(raw_metadata[old_id])
        item.update(
            {
                "id": final_id,
                "bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
                "area": int(pixels.sum()),
            }
        )
        metadata.append(item)
    return remapped, metadata
