from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.proposals.internal_selector import proposal_features
from sam_cell.proposals.regions import InstanceProposal
from scripts.eval_devset import _apply_nested_overrides, _read_rows, _restore_nested_overrides, _write_csv


def _ids(label_map: np.ndarray) -> list[int]:
    return [int(item) for item in np.unique(label_map) if int(item) != 0]


def _best_gt_match(mask: np.ndarray, gt: np.ndarray, gt_ids: list[int]) -> tuple[int, float]:
    best_id = 0
    best_iou = 0.0
    for gt_id in gt_ids:
        gt_mask = gt == gt_id
        inter = int((mask & gt_mask).sum())
        if not inter:
            continue
        union = int(np.logical_or(mask, gt_mask).sum())
        iou = inter / float(max(1, union))
        if iou > best_iou:
            best_iou = iou
            best_id = gt_id
    return best_id, best_iou


def _external_matched_gt(
    external: list[InstanceProposal],
    gt: np.ndarray,
    gt_ids: list[int],
    iou_threshold: float,
) -> set[int]:
    matched = set()
    for proposal in external:
        gt_id, iou = _best_gt_match(proposal.mask, gt, gt_ids)
        if gt_id and iou >= iou_threshold:
            matched.add(gt_id)
    return matched


def _raw_internal_proposals(pipeline, fg_prob: np.ndarray) -> list[InstanceProposal]:
    thresholds = pipeline.cfg.semantic.proposal_thresholds or [pipeline.cfg.semantic.foreground_threshold]
    proposals: list[InstanceProposal] = []
    for threshold in thresholds:
        *_debug, threshold_proposals = pipeline._proposals_for_threshold(fg_prob, float(threshold))
        proposals.extend(threshold_proposals)
    return proposals


def _collect_rows(pipeline, rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict]:
    records = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        source = row.get("source", image_path.stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] selector features {source} {image_path.name}")
        overrides = pipeline.cfg.source_overrides.get(source, {})
        previous = _apply_nested_overrides(pipeline.cfg, overrides) if overrides else {}
        saved_selector = pipeline.cfg.external_proposals.internal_selector_model
        saved_min_fraction = pipeline.cfg.external_proposals.min_internal_uncovered_fraction
        saved_min_pixels = pipeline.cfg.external_proposals.min_internal_uncovered_pixels
        try:
            pipeline.cfg.external_proposals.internal_selector_model = None
            pipeline.cfg.external_proposals.min_internal_uncovered_fraction = args.min_uncovered_fraction
            pipeline.cfg.external_proposals.min_internal_uncovered_pixels = args.min_uncovered_pixels
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            gt = load_label_map(row["mask_path"])
            fg_prob = pipeline._predict_foreground(image, image_id=image_path.stem)
            external = pipeline._external_proposals(image_path.stem, fg_prob)
            internal = _raw_internal_proposals(pipeline, fg_prob)
        finally:
            pipeline.cfg.external_proposals.internal_selector_model = saved_selector
            pipeline.cfg.external_proposals.min_internal_uncovered_fraction = saved_min_fraction
            pipeline.cfg.external_proposals.min_internal_uncovered_pixels = saved_min_pixels
            if previous:
                _restore_nested_overrides(pipeline.cfg, previous)

        if not external:
            continue
        external_union = np.zeros(fg_prob.shape, dtype=bool)
        for proposal in external:
            external_union |= proposal.mask
        gt_ids = _ids(gt)
        external_gt = _external_matched_gt(external, gt, gt_ids, args.external_match_iou)

        for proposal in internal:
            uncovered = int((proposal.mask & ~external_union).sum())
            uncovered_fraction = uncovered / float(max(1, proposal.area))
            if uncovered_fraction < args.min_uncovered_fraction:
                continue
            if uncovered < args.min_uncovered_pixels:
                continue
            features = proposal_features(proposal, external, fg_prob, image_path.stem, external_union)
            gt_id, gt_iou = _best_gt_match(proposal.mask, gt, gt_ids)
            label = int(gt_id not in external_gt and gt_iou >= args.positive_iou)
            record = {
                "source": source,
                "image": image_path.name,
                "label": label,
                "best_gt_id": gt_id,
                "best_gt_iou": gt_iou,
                **features,
            }
            records.append(record)
    return records


def _evaluate_split(name: str, model, vectorizer, rows: list[dict], threshold: float) -> dict:
    if not rows:
        return {"split": name, "n": 0}
    y = np.asarray([int(row["label"]) for row in rows], dtype=np.int32)
    x = vectorizer.transform([{k: v for k, v in row.items() if k not in {"label", "image", "best_gt_id", "best_gt_iou"}} for row in rows])
    score = model.predict_proba(x)[:, 1]
    pred = score >= threshold
    precision, recall, f1, _support = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    output = {
        "split": name,
        "n": int(y.size),
        "positives": int(y.sum()),
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "average_precision": float(average_precision_score(y, score)) if len(set(y.tolist())) > 1 else 0.0,
        "roc_auc": float(roc_auc_score(y, score)) if len(set(y.tolist())) > 1 else 0.0,
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a classifier that selects useful internal SAM-Cell proposals.")
    parser.add_argument("--config", default="configs/sam_cell_fusion_source_adaptive.yaml")
    parser.add_argument("--train_csv", default="outputs/benchmark_splits_smoke/dev_tune.csv")
    parser.add_argument("--val_csv")
    parser.add_argument("--out_dir", default="outputs/internal_selector")
    parser.add_argument("--model_name", default="internal_selector.joblib")
    parser.add_argument("--positive_iou", type=float, default=0.5)
    parser.add_argument("--external_match_iou", type=float, default=0.5)
    parser.add_argument("--min_uncovered_fraction", type=float, default=0.0)
    parser.add_argument("--min_uncovered_pixels", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--n_estimators", type=int, default=400)
    parser.add_argument("--min_samples_leaf", type=int, default=2)
    parser.add_argument("--max_depth", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train_limit", type=int)
    parser.add_argument("--val_limit", type=int)
    args = parser.parse_args()

    cfg = load_config(args.config)
    pipeline = __import__("sam_cell.pipeline", fromlist=["SAMCellPipeline"]).SAMCellPipeline(cfg)
    train_records = _collect_rows(pipeline, _read_rows(Path(args.train_csv), args.train_limit), args)
    val_records = _collect_rows(pipeline, _read_rows(Path(args.val_csv), args.val_limit), args) if args.val_csv else []
    labels = Counter(int(row["label"]) for row in train_records)
    if labels[1] == 0 or labels[0] == 0:
        raise ValueError(f"Need both positive and negative selector samples, got {dict(labels)}")

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
    payload = {
        "vectorizer": vectorizer,
        "model": model,
        "threshold": float(args.threshold),
        "feature_version": 1,
        "positive_iou": float(args.positive_iou),
        "external_match_iou": float(args.external_match_iou),
    }
    model_path = out_dir / args.model_name
    joblib.dump(payload, model_path)
    _write_csv(out_dir / "train_features.csv", train_records)
    if val_records:
        _write_csv(out_dir / "val_features.csv", val_records)

    reports = [_evaluate_split("train", model, vectorizer, train_records, args.threshold)]
    if val_records:
        reports.append(_evaluate_split("val", model, vectorizer, val_records, args.threshold))
    _write_csv(out_dir / "selector_report.csv", reports)

    by_source = defaultdict(Counter)
    for row in train_records:
        by_source[str(row["source"])][int(row["label"])] += 1
    print(f"wrote {model_path}")
    print(f"train labels: {dict(labels)}")
    for source, counts in sorted(by_source.items()):
        print(f"  {source}: positives={counts[1]} negatives={counts[0]}")


if __name__ == "__main__":
    main()
