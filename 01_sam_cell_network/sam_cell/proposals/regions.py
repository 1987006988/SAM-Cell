from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi


@dataclass
class InstanceProposal:
    id: int
    bbox_xyxy: tuple[int, int, int, int]
    mask: np.ndarray
    area: int
    centroid_xy: tuple[float, float]
    mean_fg_prob: float
    source: str = "watershed"
    rank_score: float = 0.0


def extract_proposals(
    label_map: np.ndarray,
    fg_prob: np.ndarray,
    min_area: int,
    max_area: int | None = None,
    source: str = "watershed",
) -> list[InstanceProposal]:
    proposals: list[InstanceProposal] = []
    objects = ndi.find_objects(label_map)
    for idx, slices in enumerate(objects, start=1):
        if slices is None:
            continue
        yslice, xslice = slices
        local = label_map[yslice, xslice] == idx
        area = int(local.sum())
        if area < min_area:
            continue
        if max_area is not None and area > max_area:
            continue
        ys, xs = np.nonzero(local)
        y1, y2 = int(yslice.start), int(yslice.stop)
        x1, x2 = int(xslice.start), int(xslice.stop)
        full_mask = np.zeros(label_map.shape, dtype=bool)
        full_mask[yslice, xslice] = local
        cx = float(xs.mean() + x1)
        cy = float(ys.mean() + y1)
        mean_fg = float(fg_prob[full_mask].mean()) if area else 0.0
        proposals.append(
            InstanceProposal(
                id=idx,
                bbox_xyxy=(x1, y1, x2, y2),
                mask=full_mask,
                area=area,
                centroid_xy=(cx, cy),
                mean_fg_prob=mean_fg,
                source=source,
                rank_score=0.0,
            )
        )
    return proposals


def relabel_proposals(proposals: list[InstanceProposal]) -> list[InstanceProposal]:
    relabeled: list[InstanceProposal] = []
    for idx, proposal in enumerate(proposals, start=1):
        relabeled.append(
            InstanceProposal(
                id=idx,
                bbox_xyxy=proposal.bbox_xyxy,
                mask=proposal.mask,
                area=proposal.area,
                centroid_xy=proposal.centroid_xy,
                mean_fg_prob=proposal.mean_fg_prob,
                source=proposal.source,
                rank_score=proposal.rank_score,
            )
        )
    return relabeled


def proposal_iou(a: InstanceProposal, b: InstanceProposal) -> float:
    ax1, ay1, ax2, ay2 = a.bbox_xyxy
    bx1, by1, bx2, by2 = b.bbox_xyxy
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    if x1 >= x2 or y1 >= y2:
        return 0.0
    inter = int(np.logical_and(a.mask[y1:y2, x1:x2], b.mask[y1:y2, x1:x2]).sum())
    union = int(a.area) + int(b.area) - inter
    return inter / union if union else 0.0


def merge_duplicate_proposals(
    proposals: list[InstanceProposal],
    iou_threshold: float = 0.85,
) -> list[InstanceProposal]:
    kept: list[InstanceProposal] = []
    # Prefer strong external candidates when present; otherwise prefer confident, smaller splits.
    ordered = sorted(proposals, key=_proposal_sort_key, reverse=True)
    for proposal in ordered:
        duplicate_idx = None
        for idx, existing in enumerate(kept):
            if proposal_iou(proposal, existing) >= iou_threshold:
                duplicate_idx = idx
                break
        if duplicate_idx is None:
            kept.append(proposal)
            continue
        existing = kept[duplicate_idx]
        if _proposal_sort_key(proposal) > _proposal_sort_key(existing):
            kept[duplicate_idx] = proposal
    return relabel_proposals(kept)


def _proposal_sort_key(proposal: InstanceProposal) -> tuple[float, int, float, int]:
    return (float(proposal.rank_score), _source_priority(proposal.source), float(proposal.mean_fg_prob), -int(proposal.area))


def _source_priority(source: str) -> int:
    if source.startswith("external"):
        return 3
    if source.startswith("cellpose"):
        return 3
    if source == "watershed":
        return 1
    return 0


def proposals_to_label_map(proposals: list[InstanceProposal], shape: tuple[int, int]) -> np.ndarray:
    label_map = np.zeros(shape, dtype=np.int32)
    for proposal in proposals:
        # Later proposals fill only empty pixels so debug labels remain non-overlapping.
        fill = proposal.mask & (label_map == 0)
        label_map[fill] = int(proposal.id)
    return label_map
