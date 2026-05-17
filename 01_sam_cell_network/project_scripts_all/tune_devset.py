from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from itertools import product
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.metrics.instance import summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from scripts.eval_devset import _read_rows, _write_csv, evaluate_rows


def _parse_floats(text: str) -> list[float]:
    return [float(x) for x in text.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Small SAM-Cell parameter search on the mini development set")
    parser.add_argument("--config", default="configs/sam_cell_optimized.yaml")
    parser.add_argument("--devset_csv", default="outputs/dev_eval/devset_25.csv")
    parser.add_argument("--out_dir", default="outputs/dev_eval/tuning")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max_configs", type=int, default=12)
    parser.add_argument("--thresholds", default="0.35,0.45,0.5")
    parser.add_argument("--h_maxima", default="0.05,0.1,0.15")
    parser.add_argument("--edt_sigma", default="0.5,1.0")
    args = parser.parse_args()

    cfg = load_config(args.config)
    rows = _read_rows(Path(args.devset_csv), args.limit)
    pipeline = SAMCellPipeline(cfg)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tried = []
    best_score = -1.0
    best_config = None
    grid = list(product(_parse_floats(args.thresholds), _parse_floats(args.h_maxima), _parse_floats(args.edt_sigma)))
    for run_id, (threshold, h_value, sigma) in enumerate(grid[: args.max_configs], start=1):
        cfg.semantic.foreground_threshold = threshold
        cfg.semantic.proposal_thresholds = [threshold]
        cfg.watershed.h_maxima = h_value
        cfg.watershed.h_maxima_values = [h_value]
        cfg.watershed.edt_sigma = sigma
        print(f"run {run_id}: threshold={threshold} h={h_value} sigma={sigma}")
        per_image = evaluate_rows(pipeline, rows)
        summary = summarize_metrics(per_image)
        row = {
            "run_id": run_id,
            "foreground_threshold": threshold,
            "h_maxima": h_value,
            "edt_sigma": sigma,
            **summary,
        }
        tried.append(row)
        score = float(summary.get("final_pq", 0.0)) + 0.5 * float(summary.get("final_aji", 0.0))
        if score > best_score:
            best_score = score
            best_config = asdict(cfg)
    _write_csv(out_dir / "tuning_summary.csv", tried)
    if best_config is not None:
        with (out_dir / "best_config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(best_config, f, sort_keys=False, allow_unicode=True)
    print(f"wrote tuning results to {out_dir}")


if __name__ == "__main__":
    main()
