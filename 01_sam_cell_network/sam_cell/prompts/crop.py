from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sam_cell.proposals.regions import InstanceProposal


@dataclass
class CropRecord:
    crop_image: np.ndarray
    crop_box_xyxy: tuple[int, int, int, int]
    local_box_xyxy: np.ndarray
    local_coarse_mask: np.ndarray
    proposal_id: int
    coarse_area: int
    local_fg_prob: np.ndarray | None = None


def _clip_square(x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> tuple[int, int, int, int]:
    crop_w = x2 - x1
    crop_h = y2 - y1
    if x1 < 0:
        x2 -= x1
        x1 = 0
    if y1 < 0:
        y2 -= y1
        y1 = 0
    if x2 > width:
        x1 -= x2 - width
        x2 = width
    if y2 > height:
        y1 -= y2 - height
        y2 = height
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, max(x1 + 1, x2))
    y2 = min(height, max(y1 + 1, y2))
    if x2 - x1 <= 0 or y2 - y1 <= 0:
        raise ValueError(f"Invalid crop after clipping: {(x1, y1, x2, y2)} from {(crop_w, crop_h)}")
    return x1, y1, x2, y2


def make_adaptive_crop(image: np.ndarray, proposal: InstanceProposal, cfg, fg_prob: np.ndarray | None = None) -> CropRecord:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = proposal.bbox_xyxy
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0

    if cfg.square_crop:
        side = max(box_w * (1 + 2 * cfg.alpha), box_h * (1 + 2 * cfg.alpha), cfg.min_crop_size)
        if cfg.max_crop_size:
            side = min(side, cfg.max_crop_size)
        crop_x1 = int(round(cx - side / 2.0))
        crop_y1 = int(round(cy - side / 2.0))
        crop_x2 = int(round(cx + side / 2.0))
        crop_y2 = int(round(cy + side / 2.0))
    else:
        pad_x = box_w * cfg.alpha
        pad_y = box_h * cfg.alpha
        crop_x1 = int(round(x1 - pad_x))
        crop_y1 = int(round(y1 - pad_y))
        crop_x2 = int(round(x2 + pad_x))
        crop_y2 = int(round(y2 + pad_y))

    if cfg.clip_to_image:
        crop_x1, crop_y1, crop_x2, crop_y2 = _clip_square(crop_x1, crop_y1, crop_x2, crop_y2, width, height)

    crop_image = np.ascontiguousarray(image[crop_y1:crop_y2, crop_x1:crop_x2])
    local_mask = np.ascontiguousarray(proposal.mask[crop_y1:crop_y2, crop_x1:crop_x2])
    local_fg_prob = None
    if fg_prob is not None:
        local_fg_prob = np.ascontiguousarray(fg_prob[crop_y1:crop_y2, crop_x1:crop_x2])
    local_box = np.asarray([x1 - crop_x1, y1 - crop_y1, x2 - crop_x1, y2 - crop_y1], dtype=np.float32)
    return CropRecord(
        crop_image=crop_image,
        crop_box_xyxy=(crop_x1, crop_y1, crop_x2, crop_y2),
        local_box_xyxy=local_box,
        local_coarse_mask=local_mask,
        proposal_id=proposal.id,
        coarse_area=proposal.area,
        local_fg_prob=local_fg_prob,
    )
