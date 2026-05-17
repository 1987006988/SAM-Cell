from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from sam_cell.proposals.regions import extract_proposals
from sam_cell.proposals.repair import select_proposal_set, split_repair_proposals
from sam_cell.proposals.watershed import compute_distance, make_markers, suppress_distance_by_boundary, watershed_instances


def test_watershed_splits_two_touching_cells() -> None:
    yy, xx = np.mgrid[:80, :100]
    mask = ((xx - 40) ** 2 + (yy - 40) ** 2 < 22 ** 2) | ((xx - 60) ** 2 + (yy - 40) ** 2 < 22 ** 2)
    dist = compute_distance(mask, sigma=1.0)
    markers = make_markers(dist, mask, SimpleNamespace(h_maxima=0.1))
    labels = watershed_instances(mask, dist, markers)
    assert labels.max() == 2


def test_boundary_probability_suppresses_distance_ridge() -> None:
    dist = np.ones((16, 16), dtype=np.float32)
    boundary = np.zeros_like(dist)
    boundary[:, 8] = 1.0

    suppressed = suppress_distance_by_boundary(dist, boundary, weight=0.75)

    assert float(suppressed[0, 0]) == 1.0
    assert float(suppressed[0, 8]) == 0.25


def test_adaptive_markers_create_component_local_markers() -> None:
    yy, xx = np.mgrid[:80, :120]
    mask = ((xx - 35) ** 2 + (yy - 40) ** 2 < 18 ** 2) | ((xx - 85) ** 2 + (yy - 40) ** 2 < 18 ** 2)
    dist = compute_distance(mask, sigma=1.0)
    cfg = SimpleNamespace(
        marker_method="adaptive_hybrid",
        h_maxima=0.1,
        h_maxima_values=[0.1],
        min_marker_distance=3,
        min_distance_factor=0.4,
        peak_threshold_rel=0.2,
    )
    markers = make_markers(dist, mask, cfg)
    assert markers.max() == 2


def test_split_repair_splits_large_two_peak_proposal() -> None:
    yy, xx = np.mgrid[:80, :100]
    mask = ((xx - 40) ** 2 + (yy - 40) ** 2 < 22 ** 2) | ((xx - 60) ** 2 + (yy - 40) ** 2 < 22 ** 2)
    fg_prob = mask.astype(np.float32)
    dist = compute_distance(mask, sigma=1.0)
    proposals = extract_proposals(mask.astype(np.int32), fg_prob, min_area=10)
    cfg = SimpleNamespace(
        enabled=True,
        split_enabled=True,
        split_min_area_factor=1.0,
        split_min_area_absolute=10,
        split_max_compactness=1.0,
        split_h_maxima_values=[0.08],
        split_peak_threshold_rel=0.2,
        split_min_distance_factor=0.35,
        split_min_marker_distance=3,
        split_max_children=4,
        split_min_child_area=10,
    )
    repaired = split_repair_proposals(proposals, dist, fg_prob, cfg)
    assert len(repaired) == 2


def test_set_selector_removes_contained_low_score_proposal() -> None:
    fg_prob = np.ones((32, 32), dtype=np.float32)
    outer = np.zeros((32, 32), dtype=np.int32)
    outer[4:20, 4:20] = 1
    inner = np.zeros((32, 32), dtype=np.int32)
    inner[8:16, 8:16] = 1
    outer_proposal = extract_proposals(outer, fg_prob, min_area=1)[0]
    inner_proposal = extract_proposals(inner, fg_prob, min_area=1)[0]
    outer_proposal.rank_score = 0.8
    inner_proposal.rank_score = 0.5
    cfg = SimpleNamespace(
        enabled=True,
        set_selector_enabled=True,
        set_selector_iou_threshold=0.9,
        set_selector_containment_threshold=0.75,
        set_selector_center_distance_factor=0.35,
        set_selector_score_margin=0.02,
    )
    selected = select_proposal_set([inner_proposal, outer_proposal], cfg)
    assert len(selected) == 1
    assert selected[0].area == outer_proposal.area
