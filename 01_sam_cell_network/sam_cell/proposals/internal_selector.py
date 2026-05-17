from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy import ndimage as ndi

from sam_cell.proposals.regions import InstanceProposal


def infer_dataset_source(image_id: str | None) -> str:
    if not image_id:
        return "unknown"
    return image_id.split("_", 1)[0]


def proposal_features(
    proposal: InstanceProposal,
    external: list[InstanceProposal],
    fg_prob: np.ndarray,
    image_id: str | None,
    external_union: np.ndarray | None = None,
    extended: bool = False,
) -> dict[str, float | str]:
    x1, y1, x2, y2 = proposal.bbox_xyxy
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    area = max(1, proposal.area)
    image_h, image_w = fg_prob.shape[:2]
    image_area = max(1, image_h * image_w)
    bbox_area = max(1, width * height)
    external_count = len(external)
    if external:
        if external_union is None:
            external_union = np.zeros(fg_prob.shape, dtype=bool)
            for item in external:
                external_union |= item.mask
        uncovered = int((proposal.mask & ~external_union).sum())
    else:
        uncovered = area
    max_iou = 0.0
    max_candidate_overlap = 0.0
    max_external_overlap = 0.0
    min_centroid_distance = float(max(fg_prob.shape))
    px, py = proposal.centroid_xy
    for item in external:
        inter = int(np.logical_and(proposal.mask, item.mask).sum())
        if inter:
            union = int(np.logical_or(proposal.mask, item.mask).sum())
            max_iou = max(max_iou, inter / float(max(1, union)))
            max_candidate_overlap = max(max_candidate_overlap, inter / float(area))
            max_external_overlap = max(max_external_overlap, inter / float(max(1, item.area)))
        ex, ey = item.centroid_xy
        min_centroid_distance = min(min_centroid_distance, float(np.hypot(px - ex, py - ey)))
    features: dict[str, float | str] = {
        "source": infer_dataset_source(image_id),
        "proposal_source": proposal.source,
        "area": float(area),
        "log_area": float(np.log1p(area)),
        "bbox_width": float(width),
        "bbox_height": float(height),
        "bbox_aspect": float(width / height),
        "bbox_extent": float(area / bbox_area),
        "mean_fg_prob": float(proposal.mean_fg_prob),
        "uncovered_pixels": float(uncovered),
        "uncovered_fraction": float(uncovered / area),
        "external_count": float(external_count),
        "max_external_iou": float(max_iou),
        "max_candidate_overlap": float(max_candidate_overlap),
        "max_external_overlap": float(max_external_overlap),
        "min_centroid_distance": float(min_centroid_distance),
        "image_area": float(image_area),
    }
    if not extended:
        return features

    local_mask = proposal.mask[y1:y2, x1:x2]
    local_fg = fg_prob[y1:y2, x1:x2]
    mask_values = local_fg[local_mask]
    bbox_values = local_fg.reshape(-1)
    eroded = ndi.binary_erosion(local_mask, structure=np.ones((3, 3), dtype=bool), border_value=0)
    perimeter = int((local_mask & ~eroded).sum())
    dilated = ndi.binary_dilation(local_mask, structure=np.ones((3, 3), dtype=bool), border_value=0)
    ring = dilated & ~local_mask
    ring_values = local_fg[ring]
    compactness = (4.0 * np.pi * area / float(max(1, perimeter * perimeter))) if perimeter else 0.0
    mask_fg_mean = float(mask_values.mean()) if mask_values.size else 0.0
    ring_fg_mean = float(ring_values.mean()) if ring_values.size else 0.0
    features.update(
        {
            "area_fraction": float(area / image_area),
            "bbox_width_fraction": float(width / max(1, image_w)),
            "bbox_height_fraction": float(height / max(1, image_h)),
            "bbox_area_fraction": float(bbox_area / image_area),
            "bbox_fg_mean": float(bbox_values.mean()) if bbox_values.size else 0.0,
            "bbox_fg_std": float(bbox_values.std()) if bbox_values.size else 0.0,
            "centroid_x_fraction": float(px / max(1, image_w - 1)),
            "centroid_y_fraction": float(py / max(1, image_h - 1)),
            "compactness": float(compactness),
            "perimeter": float(perimeter),
            "perimeter_sqrt_area_ratio": float(perimeter / np.sqrt(area)),
            "touches_image_border": float(x1 <= 0 or y1 <= 0 or x2 >= image_w or y2 >= image_h),
            "mask_fg_mean": mask_fg_mean,
            "mask_fg_std": float(mask_values.std()) if mask_values.size else 0.0,
            "mask_fg_p10": float(np.quantile(mask_values, 0.1)) if mask_values.size else 0.0,
            "mask_fg_p90": float(np.quantile(mask_values, 0.9)) if mask_values.size else 0.0,
            "ring_fg_mean": ring_fg_mean,
            "mask_ring_fg_delta": float(mask_fg_mean - ring_fg_mean),
        }
    )
    return features


def load_selector(path: str | Path) -> dict[str, Any]:
    payload = joblib.load(Path(path))
    if not isinstance(payload, dict) or "vectorizer" not in payload or "model" not in payload:
        raise ValueError(f"Invalid internal selector payload: {path}")
    return payload


def selector_scores(payload: dict[str, Any], features: list[dict[str, float | str]]) -> np.ndarray:
    if not features:
        return np.empty((0,), dtype=np.float32)
    vectorizer = payload["vectorizer"]
    model = payload["model"]
    x = vectorizer.transform(features)
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(x)[:, 1], dtype=np.float32)
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x), dtype=np.float32)
        return 1.0 / (1.0 + np.exp(-np.clip(raw, -50, 50)))
    return np.asarray(model.predict(x), dtype=np.float32)
