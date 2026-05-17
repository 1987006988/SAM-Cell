from __future__ import annotations

import numpy as np


def dice_binary(pred: np.ndarray, gt: np.ndarray) -> float:
    pred_bin = pred > 0
    gt_bin = gt > 0
    denom = int(pred_bin.sum() + gt_bin.sum())
    if denom == 0:
        return 1.0
    return float(2 * np.logical_and(pred_bin, gt_bin).sum() / denom)


def iou_binary(pred: np.ndarray, gt: np.ndarray) -> float:
    pred_bin = pred > 0
    gt_bin = gt > 0
    union = int(np.logical_or(pred_bin, gt_bin).sum())
    if union == 0:
        return 1.0
    return float(np.logical_and(pred_bin, gt_bin).sum() / union)

