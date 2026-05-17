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
from sam_cell.pipeline import SAMCellPipeline
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


def _pre_ranker_proposals(
    pipeline: SAMCellPipeline,
    semantic_maps_by_source: dict[str, dict[str, np.ndarray | None]],
    image_id: str,
    image: np.ndarray,
) -> tuple[list, dict[str, np.ndarray], np.ndarray]:
    proposals = []
    fg_prob_by_source: dict[str, np.ndarray] = {}
    shared_boundary_prob = (
        pipeline._shared_boundary_prob(semantic_maps_by_source)
        if pipeline.cfg.watershed.share_boundary_across_experts
        else None
    )
    for expert in pipeline._active_semantic_experts(image_id):
        source_name = pipeline._expert_source(expert)
        maps = semantic_maps_by_source[source_name]
        fg_prob = maps["fg_prob"]
        if fg_prob is None:
            continue
        fg_prob = fg_prob.astype(np.float32, copy=False)
        boundary_prob = maps.get("boundary_prob")
        if boundary_prob is None and shared_boundary_prob is not None:
            boundary_prob = shared_boundary_prob
        fg_prob_by_source[source_name] = fg_prob
        *_debug, expert_proposals = pipeline._generate_proposals(
            fg_prob,
            image_id=image_id,
            boundary_prob=None if boundary_prob is None else boundary_prob.astype(np.float32, copy=False),
            semantic_cfg=expert,
            source=source_name,
            include_external=False,
        )
        proposals.extend(expert_proposals)

    default_fg_prob = pipeline._combined_fg_prob(fg_prob_by_source)
    external = pipeline._external_proposals(image_id, default_fg_prob)
    separator_boundary = shared_boundary_prob if shared_boundary_prob is not None else pipeline._shared_boundary_prob(semantic_maps_by_source)
    separator = pipeline._separator_proposals(image, default_fg_prob, separator_boundary, image_id)
    if pipeline.cfg.external_proposals.enabled and pipeline.cfg.external_proposals.mode == "replace":
        proposals = external
    elif pipeline.cfg.separator_proposals.enabled and pipeline.cfg.separator_proposals.mode == "replace":
        proposals = separator
    else:
        proposals = pipeline._filter_internal_proposals(proposals, external, default_fg_prob, image_id)
        proposals.extend(external)
        proposals.extend(separator)
    return proposals, fg_prob_by_source, default_fg_prob


def _collect_rows(
    pipeline: SAMCellPipeline,
    rows: list[dict[str, str]],
    positive_iou: float,
    feature_version: int,
    collect_stage: str,
) -> list[dict]:
    records = []
    saved_ranker_enabled = pipeline.cfg.proposal_ranker.enabled
    pipeline.cfg.proposal_ranker.enabled = False
    try:
        for idx, row in enumerate(rows, start=1):
            image_path = Path(row["image_path"])
            source = row.get("source", image_path.stem.split("_", 1)[0])
            print(f"[{idx}/{len(rows)}] proposal ranker features {source} {image_path.name}")
            image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
            gt = load_label_map(row["mask_path"])
            gt_ids = _ids(gt)
            previous = _apply_nested_overrides(pipeline.cfg, pipeline.cfg.source_overrides.get(source, {}))
            try:
                semantic_maps = pipeline._predict_all_semantics(image, image_id=image_path.stem)
                if collect_stage == "pre_ranker":
                    proposals, fg_prob_by_source, default_fg_prob = _pre_ranker_proposals(
                        pipeline,
                        semantic_maps,
                        image_path.stem,
                        image,
                    )
                else:
                    *_debug, proposals, fg_prob_by_source, _combined_fg_mask, _proposal_diag = pipeline._generate_multi_expert_proposals(
                        semantic_maps,
                        image_id=image_path.stem,
                        image=image,
                    )
                    default_fg_prob = pipeline._combined_fg_prob(fg_prob_by_source)
            finally:
                _restore_nested_overrides(pipeline.cfg, previous)
            extended_features = feature_version >= 2
            for proposal in proposals:
                fg_prob = pipeline._fg_prob_for_proposal(proposal, fg_prob_by_source, default_fg_prob)
                gt_id, gt_iou = _best_gt_match(proposal.mask, gt, gt_ids)
                features = proposal_features(proposal, [], fg_prob, image_path.stem, extended=extended_features)
                features["proposal_source"] = proposal.source
                records.append(
                    {
                        "source": source,
                        "image": image_path.name,
                        "label": int(gt_iou >= positive_iou),
                        "best_gt_id": gt_id,
                        "best_gt_iou": gt_iou,
                        **features,
                    }
                )
    finally:
        pipeline.cfg.proposal_ranker.enabled = saved_ranker_enabled
    return records


def _feature_dict(row: dict) -> dict:
    exclude = {"label", "image", "best_gt_id", "best_gt_iou"}
    return {k: v for k, v in row.items() if k not in exclude}


def _evaluate_split(name: str, model, vectorizer, rows: list[dict], threshold: float) -> dict:
    if not rows:
        return {"split": name, "n": 0}
    y = np.asarray([int(row["label"]) for row in rows], dtype=np.int32)
    x = vectorizer.transform([_feature_dict(row) for row in rows])
    score = model.predict_proba(x)[:, 1]
    pred = score >= threshold
    precision, recall, f1, _support = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    return {
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


def _write_source_counts(path: Path, rows: list[dict]) -> None:
    counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in rows:
        counts[(str(row["source"]), str(row["proposal_source"]))][int(row["label"])] += 1
    output = []
    for (source, proposal_source), counter in sorted(counts.items()):
        output.append(
            {
                "source": source,
                "proposal_source": proposal_source,
                "positives": counter[1],
                "negatives": counter[0],
                "total": counter[1] + counter[0],
            }
        )
    _write_csv(path, output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a proposal-level ranker for multi-expert SAM-Cell proposals.")
    parser.add_argument("--config", default="configs/sam_cell_multi_expert_dual.yaml")
    parser.add_argument("--train_csv", required=True)
    parser.add_argument("--val_csv")
    parser.add_argument("--out_dir", default="outputs/proposal_ranker_dual")
    parser.add_argument("--model_name", default="proposal_ranker.joblib")
    parser.add_argument("--positive_iou", type=float, default=0.5)
    parser.add_argument("--threshold", type=float, default=0.45)
    parser.add_argument("--source")
    parser.add_argument("--collect_stage", choices=["post_selector", "pre_ranker"], default="post_selector")
    parser.add_argument("--separator_enabled", type=str)
    parser.add_argument("--separator_model_path")
    parser.add_argument("--separator_mode", choices=["augment", "replace"])
    parser.add_argument("--n_estimators", type=int, default=500)
    parser.add_argument("--max_depth", type=int, default=10)
    parser.add_argument("--min_samples_leaf", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train_limit", type=int)
    parser.add_argument("--val_limit", type=int)
    parser.add_argument("--feature_version", type=int, default=1, choices=[1, 2])
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.separator_enabled is not None:
        cfg.separator_proposals.enabled = args.separator_enabled.strip().lower() in {"1", "true", "yes", "y", "on"}
    if args.separator_model_path:
        cfg.separator_proposals.model_path = args.separator_model_path
    if args.separator_mode:
        cfg.separator_proposals.mode = args.separator_mode
    pipeline = SAMCellPipeline(cfg)
    train_rows = _read_rows(Path(args.train_csv), args.train_limit)
    val_rows = _read_rows(Path(args.val_csv), args.val_limit) if args.val_csv else []
    if args.source:
        train_rows = [row for row in train_rows if row.get("source", Path(row["image_path"]).stem.split("_", 1)[0]) == args.source]
        val_rows = [row for row in val_rows if row.get("source", Path(row["image_path"]).stem.split("_", 1)[0]) == args.source]
    train_records = _collect_rows(
        pipeline,
        train_rows,
        args.positive_iou,
        args.feature_version,
        args.collect_stage,
    )
    val_records = (
        _collect_rows(
            pipeline,
            val_rows,
            args.positive_iou,
            args.feature_version,
            args.collect_stage,
        )
        if args.val_csv
        else []
    )
    labels = Counter(int(row["label"]) for row in train_records)
    if labels[1] == 0 or labels[0] == 0:
        raise ValueError(f"Need both positive and negative proposal samples, got {dict(labels)}")

    vectorizer = DictVectorizer(sparse=False)
    x_train = vectorizer.fit_transform([_feature_dict(row) for row in train_records])
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
        "feature_version": int(args.feature_version),
        "positive_iou": float(args.positive_iou),
    }
    model_path = out_dir / args.model_name
    joblib.dump(payload, model_path)
    _write_csv(out_dir / "train_features.csv", train_records)
    if val_records:
        _write_csv(out_dir / "val_features.csv", val_records)
    _write_csv(
        out_dir / "ranker_report.csv",
        [_evaluate_split("train", model, vectorizer, train_records, args.threshold)]
        + ([_evaluate_split("val", model, vectorizer, val_records, args.threshold)] if val_records else []),
    )
    _write_source_counts(out_dir / "source_proposal_counts.csv", train_records)
    print(f"wrote {model_path}")
    print(f"train labels: {dict(labels)}")


if __name__ == "__main__":
    main()
