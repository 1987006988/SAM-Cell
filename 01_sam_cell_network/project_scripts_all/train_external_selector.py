from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.proposals.internal_selector import proposal_features
from sam_cell.pipeline import SAMCellPipeline
from scripts.eval_devset import _apply_nested_overrides, _read_rows, _restore_nested_overrides, _write_csv
from scripts.train_internal_selector import _best_gt_match, _ids


def _collect_rows(pipeline: SAMCellPipeline, rows: list[dict[str, str]], match_iou: float) -> list[dict]:
    records = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        source = row.get("source", image_path.stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] external selector features {source} {image_path.name}")
        overrides = pipeline.cfg.source_overrides.get(source, {})
        previous = _apply_nested_overrides(pipeline.cfg, overrides) if overrides else {}
        saved_external_selector = pipeline.cfg.external_proposals.external_selector_model
        try:
            pipeline.cfg.external_proposals.external_selector_model = None
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            gt = load_label_map(row["mask_path"])
            fg_prob = pipeline._predict_foreground(image, image_id=image_path.stem)
            external = pipeline._external_proposals(image_path.stem, fg_prob)
        finally:
            pipeline.cfg.external_proposals.external_selector_model = saved_external_selector
            if previous:
                _restore_nested_overrides(pipeline.cfg, previous)

        gt_ids = _ids(gt)
        for proposal in external:
            gt_id, gt_iou = _best_gt_match(proposal.mask, gt, gt_ids)
            label = int(gt_id != 0 and gt_iou >= match_iou)
            records.append(
                {
                    "source": source,
                    "image": image_path.name,
                    "label": label,
                    "best_gt_id": gt_id,
                    "best_gt_iou": gt_iou,
                    **proposal_features(proposal, [], fg_prob, image_path.stem),
                }
            )
    return records


def _evaluate(name: str, model, vectorizer, rows: list[dict], thresholds: list[float]) -> list[dict]:
    if not rows:
        return []
    exclude = {"label", "image", "best_gt_id", "best_gt_iou"}
    y = np.asarray([int(row["label"]) for row in rows], dtype=np.int32)
    x = vectorizer.transform([{k: v for k, v in row.items() if k not in exclude} for row in rows])
    score = model.predict_proba(x)[:, 1]
    reports = []
    for threshold in thresholds:
        pred = score >= threshold
        precision, recall, f1, _support = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        reports.append(
            {
                "split": name,
                "threshold": float(threshold),
                "n": int(y.size),
                "positives": int(y.sum()),
                "kept": int(pred.sum()),
                "dropped": int((~pred).sum()),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "average_precision": float(average_precision_score(y, score)) if len(set(y.tolist())) > 1 else 0.0,
                "roc_auc": float(roc_auc_score(y, score)) if len(set(y.tolist())) > 1 else 0.0,
            }
        )
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a classifier that keeps reliable external Cellpose proposals.")
    parser.add_argument("--config", default="configs/sam_cell_fusion_selector20.yaml")
    parser.add_argument("--train_csv", default="outputs/benchmark_splits_selector20/dev_tune.csv")
    parser.add_argument("--val_csv")
    parser.add_argument("--out_dir", default="outputs/external_selector_selector20")
    parser.add_argument("--model_name", default="external_selector.joblib")
    parser.add_argument("--match_iou", type=float, default=0.5)
    parser.add_argument("--thresholds", default="0.01,0.03,0.05,0.1,0.2,0.3,0.5")
    parser.add_argument("--n_estimators", type=int, default=700)
    parser.add_argument("--min_samples_leaf", type=int, default=3)
    parser.add_argument("--max_depth", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = load_config(args.config)
    pipeline = SAMCellPipeline(cfg)
    train_records = _collect_rows(pipeline, _read_rows(Path(args.train_csv)), args.match_iou)
    val_records = _collect_rows(pipeline, _read_rows(Path(args.val_csv)), args.match_iou) if args.val_csv else []
    labels = Counter(int(row["label"]) for row in train_records)
    if labels[1] == 0 or labels[0] == 0:
        raise ValueError(f"Need both positive and negative external selector samples, got {dict(labels)}")

    exclude = {"label", "image", "best_gt_id", "best_gt_iou"}
    vectorizer = DictVectorizer(sparse=False)
    x_train = vectorizer.fit_transform([{k: v for k, v in row.items() if k not in exclude} for row in train_records])
    y_train = np.asarray([int(row["label"]) for row in train_records], dtype=np.int32)
    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=args.seed,
    )
    model.fit(x_train, y_train)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / args.model_name
    joblib.dump({"vectorizer": vectorizer, "model": model, "feature_version": 1, "match_iou": args.match_iou}, model_path)
    _write_csv(out_dir / "train_features.csv", train_records)
    if val_records:
        _write_csv(out_dir / "val_features.csv", val_records)

    thresholds = [float(item) for item in args.thresholds.split(",") if item.strip()]
    reports = _evaluate("train", model, vectorizer, train_records, thresholds)
    reports.extend(_evaluate("val", model, vectorizer, val_records, thresholds))
    _write_csv(out_dir / "selector_report.csv", reports)

    print(f"wrote {model_path}")
    print(f"train labels: {dict(labels)}")
    for source, group in pd.DataFrame(train_records).groupby("source"):
        counts = group["label"].value_counts().to_dict()
        print(f"  {source}: positives={counts.get(1, 0)} negatives={counts.get(0, 0)}")


if __name__ == "__main__":
    main()
