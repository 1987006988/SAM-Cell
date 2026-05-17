from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.morphology import h_maxima
from skimage.segmentation import watershed


def estimate_cell_radius(binary_mask: np.ndarray) -> float:
    labels, n = ndi.label(binary_mask)
    if n == 0:
        return 0.0
    areas = ndi.sum(binary_mask, labels, index=np.arange(1, n + 1))
    areas = np.asarray(areas, dtype=np.float32)
    areas = areas[areas > 0]
    if areas.size == 0:
        return 0.0
    return float(math.sqrt(float(np.median(areas)) / math.pi))


def compute_distance(binary_mask: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    dist = ndi.distance_transform_edt(binary_mask).astype(np.float32)
    if sigma and sigma > 0:
        dist = ndi.gaussian_filter(dist, sigma=sigma).astype(np.float32)
    return dist


def suppress_distance_by_boundary(
    dist: np.ndarray,
    boundary_prob: np.ndarray | None,
    weight: float = 0.0,
    additive_weight: float = 0.0,
    smoothing_sigma: float = 0.0,
) -> np.ndarray:
    if boundary_prob is None or (weight <= 0 and additive_weight <= 0):
        return dist.astype(np.float32, copy=False)
    if boundary_prob.shape != dist.shape:
        raise ValueError(f"boundary_prob shape {boundary_prob.shape} does not match dist shape {dist.shape}")
    boundary = np.clip(boundary_prob.astype(np.float32, copy=False), 0.0, 1.0)
    if smoothing_sigma and smoothing_sigma > 0:
        boundary = ndi.gaussian_filter(boundary, sigma=float(smoothing_sigma)).astype(np.float32, copy=False)
        boundary = np.clip(boundary, 0.0, 1.0)
    out = dist.astype(np.float32, copy=True)
    if weight > 0:
        scale = 1.0 - np.clip(float(weight), 0.0, 1.0) * boundary
        out *= scale
    if additive_weight > 0:
        out -= float(out.max()) * float(additive_weight) * boundary
        out[out < 0] = 0.0
    return out.astype(np.float32, copy=False)


def make_markers(dist: np.ndarray, binary_mask: np.ndarray, cfg) -> np.ndarray:
    if not np.any(binary_mask):
        return np.zeros(binary_mask.shape, dtype=np.int32)
    max_dist = float(dist.max())
    if max_dist <= 0:
        return ndi.label(binary_mask)[0].astype(np.int32)
    method = getattr(cfg, "marker_method", "h_maxima")
    if method in ("adaptive", "adaptive_h_maxima", "adaptive_hybrid"):
        return _make_adaptive_markers(dist, binary_mask, cfg, include_peak_local_max=(method == "adaptive_hybrid"))
    norm = dist / max_dist
    peaks = np.zeros(binary_mask.shape, dtype=bool)
    if method in ("h_maxima", "hybrid"):
        h_values = getattr(cfg, "h_maxima_values", None) or [float(cfg.h_maxima)]
        for h in h_values:
            peaks |= h_maxima(norm, float(h)).astype(bool) & binary_mask
    if method in ("peak_local_max", "hybrid"):
        radius = estimate_cell_radius(binary_mask)
        min_distance = max(int(getattr(cfg, "min_marker_distance", 3)), int(radius * float(getattr(cfg, "min_distance_factor", 0.45))))
        coords = peak_local_max(
            dist,
            labels=binary_mask.astype(np.uint8),
            min_distance=max(1, min_distance),
            threshold_abs=max_dist * float(getattr(cfg, "peak_threshold_rel", 0.2)),
            exclude_border=False,
        )
        if coords.size:
            peaks[coords[:, 0], coords[:, 1]] = True
    markers, n = ndi.label(peaks)
    if n == 0:
        y, x = np.unravel_index(np.argmax(dist), dist.shape)
        markers = np.zeros(dist.shape, dtype=np.int32)
        markers[y, x] = 1
    return markers.astype(np.int32, copy=False)


def _make_adaptive_markers(
    dist: np.ndarray,
    binary_mask: np.ndarray,
    cfg,
    include_peak_local_max: bool,
) -> np.ndarray:
    component_labels, n_components = ndi.label(binary_mask)
    markers = np.zeros(binary_mask.shape, dtype=np.int32)
    next_marker = 1
    h_values = getattr(cfg, "h_maxima_values", None) or [float(getattr(cfg, "h_maxima", 0.15))]
    for component_id in range(1, n_components + 1):
        component = component_labels == component_id
        if not np.any(component):
            continue
        slices = ndi.find_objects(component.astype(np.int32), max_label=1)[0]
        if slices is None:
            continue
        local_mask = component[slices]
        local_dist = dist[slices].astype(np.float32, copy=True)
        local_dist[~local_mask] = 0.0
        local_max = float(local_dist.max())
        if local_max <= 0:
            local_markers, local_n = ndi.label(local_mask)
        else:
            local_norm = local_dist / local_max
            peaks = np.zeros(local_mask.shape, dtype=bool)
            for h in h_values:
                peaks |= h_maxima(local_norm, float(h)).astype(bool) & local_mask
            if include_peak_local_max:
                area = int(local_mask.sum())
                radius = math.sqrt(float(max(1, area)) / math.pi)
                min_distance = max(
                    int(getattr(cfg, "min_marker_distance", 3)),
                    int(radius * float(getattr(cfg, "min_distance_factor", 0.45))),
                )
                coords = peak_local_max(
                    local_dist,
                    labels=local_mask.astype(np.uint8),
                    min_distance=max(1, min_distance),
                    threshold_abs=local_max * float(getattr(cfg, "peak_threshold_rel", 0.2)),
                    exclude_border=False,
                )
                if coords.size:
                    peaks[coords[:, 0], coords[:, 1]] = True
            if getattr(cfg, "marker_rescue_enabled", False):
                _rescue_sparse_component_markers(peaks, local_dist, local_mask, cfg)
            local_markers, local_n = ndi.label(peaks)
            if local_n == 0:
                y, x = np.unravel_index(np.argmax(local_dist), local_dist.shape)
                local_markers = np.zeros(local_dist.shape, dtype=np.int32)
                local_markers[y, x] = 1
                local_n = 1
        local_out = markers[slices]
        for local_id in range(1, int(local_n) + 1):
            local_out[local_markers == local_id] = next_marker
            next_marker += 1
        markers[slices] = local_out
    return markers.astype(np.int32, copy=False)


def _rescue_sparse_component_markers(
    peaks: np.ndarray,
    local_dist: np.ndarray,
    local_mask: np.ndarray,
    cfg,
) -> None:
    area = int(local_mask.sum())
    min_area = int(getattr(cfg, "marker_rescue_min_component_area", 80))
    if area < min_area:
        return
    local_max = float(local_dist.max())
    if local_max <= 0:
        return

    current_n = int(ndi.label(peaks)[1])
    typical_area = math.pi * max(1.0, local_max) ** 2 * float(getattr(cfg, "marker_rescue_area_factor", 1.35))
    target_n = int(math.ceil(area / max(1.0, typical_area)))
    target_n = max(1, min(target_n, int(getattr(cfg, "marker_rescue_max_markers", 128))))
    if current_n >= target_n:
        return

    min_distance = max(
        int(getattr(cfg, "min_marker_distance", 3)),
        int(local_max * float(getattr(cfg, "marker_rescue_min_distance_factor", 0.55))),
    )
    rescue_dist = local_dist.astype(np.float32, copy=True)
    rescue_dist[peaks] = 0.0
    coords = peak_local_max(
        rescue_dist,
        labels=local_mask.astype(np.uint8),
        min_distance=max(1, min_distance),
        threshold_abs=local_max * float(getattr(cfg, "marker_rescue_peak_threshold_rel", 0.08)),
        exclude_border=False,
        num_peaks=max(0, target_n - current_n),
    )
    if coords.size:
        peaks[coords[:, 0], coords[:, 1]] = True


def watershed_instances(binary_mask: np.ndarray, dist: np.ndarray, markers: np.ndarray) -> np.ndarray:
    if not np.any(binary_mask) or int(markers.max()) == 0:
        return np.zeros(binary_mask.shape, dtype=np.int32)
    labels = watershed(-dist, markers, mask=binary_mask)
    return labels.astype(np.int32, copy=False)
