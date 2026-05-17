from __future__ import annotations

import numpy as np

from sam_cell.metrics.instance import instance_metrics


def test_instance_metrics_perfect_match() -> None:
    gt = np.zeros((20, 20), dtype=np.int32)
    gt[2:8, 2:8] = 1
    gt[12:18, 12:18] = 2
    metrics = instance_metrics(gt.copy(), gt)
    assert metrics["pq"] == 1.0
    assert metrics["aji"] == 1.0
    assert metrics["tp"] == 2
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0

