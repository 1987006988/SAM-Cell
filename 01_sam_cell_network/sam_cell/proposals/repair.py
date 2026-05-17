from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

from sam_cell.proposals.regions import InstanceProposal, proposal_iou, relabel_proposals


def _source_priority(source: str) -> int:
    if source.startswith("external") or source.startswith("cellpose"):
        return 3
    if source == "watershed":
        return 1
    return 0


def _score_key(proposal: InstanceProposal) -> tuple[float, int, float, int]:
    return (float(proposal.rank_score), _source_priority(proposal.source), float(proposal.mean_fg_prob), -int(proposal.area))


def proposal_compactness(proposal: InstanceProposal) -> float:
    x1, y1, x2, y2 = proposal.bbox_xyxy
    local = proposal.mask[y1:y2, x1:x2]
    if not np.any(local):
        return 0.0
    eroded = ndi.binary_erosion(local, structure=np.ones((3, 3), dtype=bool), border_value=0)
    perimeter = int((local & ~eroded).sum())
    if perimeter <= 0:
        return 0.0
    return float(4.0 * math.pi * max(1, proposal.area) / float(perimeter * perimeter))


def split_repair_proposals(
    proposals: list[InstanceProposal],
    dist: np.ndarray,
    fg_prob: np.ndarray,
    cfg,
) -> list[InstanceProposal]:
    if not getattr(cfg, "enabled", False) or not getattr(cfg, "split_enabled", False) or not proposals:
        return proposals

    areas = np.asarray([proposal.area for proposal in proposals if proposal.area > 0], dtype=np.float32)
    median_area = float(np.median(areas)) if areas.size else 0.0
    repaired: list[InstanceProposal] = []
    for proposal in proposals:
        large_by_relative = median_area > 0 and proposal.area >= median_area * float(cfg.split_min_area_factor)
        large_by_absolute = proposal.area >= int(cfg.split_min_area_absolute)
        irregular = proposal_compactness(proposal) <= float(cfg.split_max_compactness)
        if not (large_by_relative or (large_by_absolute and irregular)):
            repaired.append(proposal)
            continue
        children = _split_one_proposal(proposal, dist, fg_prob, cfg)
        if children is None:
            repaired.append(proposal)
        elif getattr(cfg, "split_keep_parent", False):
            # Keep the parent as a fallback candidate; ranker/set-selector can then choose
            # between conservative and split hypotheses instead of forcing a replacement.
            repaired.extend([proposal, *children])
        else:
            repaired.extend(children)
    return relabel_proposals(repaired)


def _split_one_proposal(
    proposal: InstanceProposal,
    dist: np.ndarray,
    fg_prob: np.ndarray,
    cfg,
) -> list[InstanceProposal] | None:
    x1, y1, x2, y2 = proposal.bbox_xyxy
    local_mask = proposal.mask[y1:y2, x1:x2]
    if int(local_mask.sum()) < max(2 * int(cfg.split_min_child_area), 2):
        return None

    local_dist = dist[y1:y2, x1:x2].astype(np.float32, copy=True)
    local_dist[~local_mask] = 0.0
    max_dist = float(local_dist.max())
    if max_dist <= 0:
        return None

    peaks = np.zeros(local_mask.shape, dtype=bool)
    norm = local_dist / max_dist
    h_values = getattr(cfg, "split_h_maxima_values", None) or [0.08, 0.12]
    for h in h_values:
        peaks |= h_maxima(norm, float(h)).astype(bool) & local_mask

    radius = math.sqrt(float(max(1, proposal.area)) / math.pi)
    min_distance = max(int(cfg.split_min_marker_distance), int(radius * float(cfg.split_min_distance_factor)))
    coords = peak_local_max(
        local_dist,
        labels=local_mask.astype(np.uint8),
        min_distance=max(1, min_distance),
        threshold_abs=max_dist * float(cfg.split_peak_threshold_rel),
        exclude_border=False,
    )
    if coords.size:
        peaks[coords[:, 0], coords[:, 1]] = True

    markers, n_markers = ndi.label(peaks)
    max_children = int(cfg.split_max_children)
    if n_markers < 2 or n_markers > max_children:
        return None

    local_labels = watershed(-local_dist, markers, mask=local_mask).astype(np.int32, copy=False)
    children: list[InstanceProposal] = []
    for child_id in range(1, int(local_labels.max()) + 1):
        child_local = local_labels == child_id
        area = int(child_local.sum())
        if area < int(cfg.split_min_child_area):
            continue
        min_area_fraction = float(getattr(cfg, "split_min_child_area_fraction", 0.0))
        if min_area_fraction > 0 and area < int(proposal.area * min_area_fraction):
            continue
        ys, xs = np.nonzero(child_local)
        if ys.size == 0:
            continue
        child_mask = np.zeros(proposal.mask.shape, dtype=bool)
        child_mask[y1:y2, x1:x2] = child_local
        cy1, cy2 = int(y1 + ys.min()), int(y1 + ys.max() + 1)
        cx1, cx2 = int(x1 + xs.min()), int(x1 + xs.max() + 1)
        mean_fg = float(fg_prob[child_mask].mean()) if area else proposal.mean_fg_prob
        if mean_fg < float(getattr(cfg, "split_min_child_mean_fg_prob", 0.0)):
            continue
        if mean_fg < proposal.mean_fg_prob + float(getattr(cfg, "split_min_child_parent_fg_delta", -1.0)):
            continue
        compactness = _compactness_from_local_mask(child_local, area)
        if compactness < float(getattr(cfg, "split_min_child_compactness", 0.0)):
            continue
        children.append(
            InstanceProposal(
                id=len(children) + 1,
                bbox_xyxy=(cx1, cy1, cx2, cy2),
                mask=child_mask,
                area=area,
                centroid_xy=(float(x1 + xs.mean()), float(y1 + ys.mean())),
                mean_fg_prob=mean_fg,
                source=proposal.source,
                rank_score=proposal.rank_score,
            )
        )

    if len(children) < 2:
        return None
    covered = sum(child.area for child in children) / float(max(1, proposal.area))
    if covered < float(getattr(cfg, "split_min_covered_fraction", 0.85)):
        return None
    return children


def _compactness_from_local_mask(local_mask: np.ndarray, area: int) -> float:
    eroded = ndi.binary_erosion(local_mask, structure=np.ones((3, 3), dtype=bool), border_value=0)
    perimeter = int((local_mask & ~eroded).sum())
    if perimeter <= 0:
        return 0.0
    return float(4.0 * math.pi * max(1, area) / float(perimeter * perimeter))


def select_proposal_set(proposals: list[InstanceProposal], cfg) -> list[InstanceProposal]:
    if not getattr(cfg, "enabled", False) or not getattr(cfg, "set_selector_enabled", False) or not proposals:
        return proposals
    kept: list[InstanceProposal] = []
    for proposal in sorted(proposals, key=_score_key, reverse=True):
        conflict_idx = _find_conflict(proposal, kept, cfg)
        if conflict_idx is None:
            kept.append(proposal)
            continue
        existing = kept[conflict_idx]
        if _score_key(proposal) > _score_key(existing) and _score_margin(proposal, existing) >= float(cfg.set_selector_score_margin):
            kept[conflict_idx] = proposal
    return relabel_proposals(kept)


def _score_margin(a: InstanceProposal, b: InstanceProposal) -> float:
    return max(float(a.rank_score), float(a.mean_fg_prob)) - max(float(b.rank_score), float(b.mean_fg_prob))


def _find_conflict(proposal: InstanceProposal, kept: list[InstanceProposal], cfg) -> int | None:
    for idx, existing in enumerate(kept):
        inter = _intersection_area(proposal, existing)
        if inter <= 0:
            continue
        containment = max(inter / float(max(1, proposal.area)), inter / float(max(1, existing.area)))
        if proposal_iou(proposal, existing) >= float(cfg.set_selector_iou_threshold):
            return idx
        if containment >= float(cfg.set_selector_containment_threshold):
            return idx
        px, py = proposal.centroid_xy
        ex, ey = existing.centroid_xy
        radius = math.sqrt(float(min(proposal.area, existing.area)) / math.pi)
        if containment >= 0.35 and np.hypot(px - ex, py - ey) <= radius * float(cfg.set_selector_center_distance_factor):
            return idx
    return None


def _intersection_area(a: InstanceProposal, b: InstanceProposal) -> int:
    ax1, ay1, ax2, ay2 = a.bbox_xyxy
    bx1, by1, bx2, by2 = b.bbox_xyxy
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    if x1 >= x2 or y1 >= y2:
        return 0
    return int(np.logical_and(a.mask[y1:y2, x1:x2], b.mask[y1:y2, x1:x2]).sum())
