from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy.optimize import linear_sum_assignment

from sam_cell.metrics.semantic import dice_binary, iou_binary


def _ids(label_map: np.ndarray) -> list[int]:
    return [int(x) for x in np.unique(label_map) if int(x) != 0]


def _iou_matrix(pred: np.ndarray, gt: np.ndarray, pred_ids: list[int], gt_ids: list[int]) -> np.ndarray:
    return _overlap_stats(pred, gt, pred_ids, gt_ids)[0]


def _overlap_stats(
    pred: np.ndarray,
    gt: np.ndarray,
    pred_ids: list[int],
    gt_ids: list[int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pred_ids_arr = np.asarray(pred_ids, dtype=np.int64)
    gt_ids_arr = np.asarray(gt_ids, dtype=np.int64)
    n_pred = len(pred_ids)
    n_gt = len(gt_ids)
    iou = np.zeros((n_pred, n_gt), dtype=np.float32)
    inter = np.zeros((n_pred, n_gt), dtype=np.int64)
    pred_areas = np.zeros(n_pred, dtype=np.int64)
    gt_areas = np.zeros(n_gt, dtype=np.int64)
    if n_pred == 0 and n_gt == 0:
        return iou, inter, pred_areas, gt_areas

    pred_flat = pred.ravel()
    gt_flat = gt.ravel()
    if n_pred:
        pred_positive = pred_flat > 0
        pred_indices = np.searchsorted(pred_ids_arr, pred_flat[pred_positive])
        pred_areas = np.bincount(pred_indices, minlength=n_pred).astype(np.int64, copy=False)
    if n_gt:
        gt_positive = gt_flat > 0
        gt_indices = np.searchsorted(gt_ids_arr, gt_flat[gt_positive])
        gt_areas = np.bincount(gt_indices, minlength=n_gt).astype(np.int64, copy=False)
    if not (n_pred and n_gt):
        return iou, inter, pred_areas, gt_areas

    overlap = (pred_flat > 0) & (gt_flat > 0)
    if not np.any(overlap):
        return iou, inter, pred_areas, gt_areas
    pred_indices = np.searchsorted(pred_ids_arr, pred_flat[overlap])
    gt_indices = np.searchsorted(gt_ids_arr, gt_flat[overlap])
    pair_indices = pred_indices * n_gt + gt_indices
    inter = np.bincount(pair_indices, minlength=n_pred * n_gt).reshape(n_pred, n_gt).astype(np.int64, copy=False)
    union = pred_areas[:, None] + gt_areas[None, :] - inter
    np.divide(inter, union, out=iou, where=union > 0)
    return iou, inter, pred_areas, gt_areas


def instance_metrics(pred: np.ndarray, gt: np.ndarray, iou_threshold: float = 0.5) -> dict[str, float | int]:
    pred = np.asarray(pred, dtype=np.int32)
    gt = np.asarray(gt, dtype=np.int32)
    pred_ids = _ids(pred)
    gt_ids = _ids(gt)
    mat, inter_mat, pred_areas, gt_areas = _overlap_stats(pred, gt, pred_ids, gt_ids)
    matches: list[tuple[int, int, float]] = []
    if mat.size:
        rows, cols = linear_sum_assignment(-mat)
        matches = [(int(r), int(c), float(mat[r, c])) for r, c in zip(rows, cols) if mat[r, c] >= iou_threshold]

    tp = len(matches)
    fp = len(pred_ids) - tp
    fn = len(gt_ids) - tp
    sq = sum(m[2] for m in matches) / tp if tp else 0.0
    rq = tp / (tp + 0.5 * fp + 0.5 * fn) if (tp + fp + fn) else 1.0
    pq = sq * rq
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 1.0

    matched_pred = {r for r, _c, _iou in matches}
    matched_gt = {c for _r, c, _iou in matches}
    aji_inter = 0
    aji_union = 0
    for r, c, _iou in matches:
        aji_inter += int(inter_mat[r, c])
        aji_union += int(pred_areas[r] + gt_areas[c] - inter_mat[r, c])
    for i, _pid in enumerate(pred_ids):
        if i not in matched_pred:
            aji_union += int(pred_areas[i])
    for j, _gid in enumerate(gt_ids):
        if j not in matched_gt:
            aji_union += int(gt_areas[j])
    aji = aji_inter / aji_union if aji_union else 1.0

    return {
        "pred_n": len(pred_ids),
        "gt_n": len(gt_ids),
        "dice": dice_binary(pred, gt),
        "binary_iou": iou_binary(pred, gt),
        "pq": pq,
        "sq": sq,
        "rq": rq,
        "aji": aji,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def summarize_metrics(rows: Iterable[dict[str, float | int]]) -> dict[str, float]:
    rows = list(rows)
    if not rows:
        return {}
    keys = sorted({k for row in rows for k, v in row.items() if isinstance(v, (int, float))})
    summary = {}
    for key in keys:
        values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
        if values:
            summary[key] = float(np.mean(values))
    return summary
