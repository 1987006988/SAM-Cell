from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
import sys

import joblib
import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.io import load_image
from scripts.eval_devset import _read_rows, _write_csv


def _rewrite_path(path: str, data_root: str | None) -> str:
    if not data_root:
        return path
    normalized = path.replace("\\", "/")
    prefixes = [
        "/mnt/d/cell data/CellCosmos_Benchmark",
        "D:/cell data/CellCosmos_Benchmark",
    ]
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return data_root.rstrip("/") + normalized[len(prefix) :]
    return path


def _otsu_threshold(gray: np.ndarray) -> float:
    hist, edges = np.histogram(gray.reshape(-1), bins=128, range=(0.0, 1.0))
    total = float(hist.sum())
    if total <= 0:
        return 0.5
    centers = (edges[:-1] + edges[1:]) * 0.5
    weight_bg = np.cumsum(hist).astype(np.float64)
    weight_fg = total - weight_bg
    mean_bg = np.cumsum(hist * centers) / np.maximum(weight_bg, 1.0)
    mean_fg = (np.cumsum((hist * centers)[::-1]) / np.maximum(np.cumsum(hist[::-1]), 1.0))[::-1]
    variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    return float(centers[int(np.argmax(variance))])


def image_style_features(image_path: str | Path, normalize_mode: str, data_root: str | None = None) -> dict[str, float]:
    image = load_image(_rewrite_path(str(image_path), data_root), normalize_mode=normalize_mode).astype(np.float32) / 255.0
    gray = image.mean(axis=2)
    h, w = gray.shape
    area = max(1, h * w)
    gx = np.diff(gray, axis=1, append=gray[:, -1:])
    gy = np.diff(gray, axis=0, append=gray[-1:, :])
    grad = np.sqrt(gx * gx + gy * gy)
    otsu = _otsu_threshold(gray)
    bright = gray >= otsu
    dark = gray <= otsu
    bright_labels, bright_n = ndi.label(bright)
    dark_labels, dark_n = ndi.label(dark)
    bright_areas = np.bincount(bright_labels.reshape(-1))[1:] if bright_n else np.asarray([], dtype=np.int64)
    dark_areas = np.bincount(dark_labels.reshape(-1))[1:] if dark_n else np.asarray([], dtype=np.int64)

    features: dict[str, float] = {
        "height": float(h),
        "width": float(w),
        "log_area": float(np.log1p(area)),
        "aspect": float(w / max(1, h)),
        "gray_mean": float(gray.mean()),
        "gray_std": float(gray.std()),
        "gray_p01": float(np.quantile(gray, 0.01)),
        "gray_p10": float(np.quantile(gray, 0.10)),
        "gray_p50": float(np.quantile(gray, 0.50)),
        "gray_p90": float(np.quantile(gray, 0.90)),
        "gray_p99": float(np.quantile(gray, 0.99)),
        "gray_iqr": float(np.quantile(gray, 0.75) - np.quantile(gray, 0.25)),
        "grad_mean": float(grad.mean()),
        "grad_std": float(grad.std()),
        "grad_p90": float(np.quantile(grad, 0.90)),
        "grad_p99": float(np.quantile(grad, 0.99)),
        "otsu_threshold": otsu,
        "bright_fraction": float(bright.mean()),
        "dark_fraction": float(dark.mean()),
        "bright_components_per_mpix": float(bright_n / max(area / 1_000_000.0, 1e-6)),
        "dark_components_per_mpix": float(dark_n / max(area / 1_000_000.0, 1e-6)),
        "bright_largest_fraction": float(bright_areas.max() / area) if bright_areas.size else 0.0,
        "dark_largest_fraction": float(dark_areas.max() / area) if dark_areas.size else 0.0,
    }
    for c, name in enumerate(("r", "g", "b")):
        channel = image[:, :, c]
        features[f"{name}_mean"] = float(channel.mean())
        features[f"{name}_std"] = float(channel.std())
        features[f"{name}_p10"] = float(np.quantile(channel, 0.10))
        features[f"{name}_p90"] = float(np.quantile(channel, 0.90))
    rg_delta = image[:, :, 0] - image[:, :, 1]
    rb_delta = image[:, :, 0] - image[:, :, 2]
    gb_delta = image[:, :, 1] - image[:, :, 2]
    features.update(
        {
            "rg_delta_mean": float(rg_delta.mean()),
            "rb_delta_mean": float(rb_delta.mean()),
            "gb_delta_mean": float(gb_delta.mean()),
            "color_std_mean": float(image.std(axis=2).mean()),
            "color_std_p90": float(np.quantile(image.std(axis=2), 0.90)),
        }
    )
    for threshold in (0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 0.90, 0.95):
        features[f"gray_ge_{threshold:.2f}"] = float((gray >= threshold).mean())
    return features


def _collect(rows: list[dict[str, str]], positive_source: str, normalize_mode: str, data_root: str | None) -> list[dict]:
    records = []
    for idx, row in enumerate(rows, start=1):
        image_path = row["image_path"]
        source = row.get("source", Path(image_path).stem.split("_", 1)[0])
        print(f"[{idx}/{len(rows)}] style features {source} {Path(image_path).name}")
        records.append(
            {
                "source": source,
                "image": Path(image_path).name,
                "label": int(source == positive_source),
                **image_style_features(image_path, normalize_mode=normalize_mode, data_root=data_root),
            }
        )
    return records


def _feature_dict(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in {"source", "image", "label", "score", "pred"}}


def _score_rows(model, vectorizer, rows: list[dict], threshold: float) -> list[dict]:
    if not rows:
        return []
    scores = model.predict_proba(vectorizer.transform([_feature_dict(row) for row in rows]))[:, 1]
    output = []
    for row, score in zip(rows, scores, strict=True):
        item = dict(row)
        item["score"] = float(score)
        item["pred"] = int(score >= threshold)
        output.append(item)
    return output


def _report(name: str, rows: list[dict], threshold: float) -> dict:
    if not rows:
        return {"split": name, "n": 0}
    y = np.asarray([int(row["label"]) for row in rows], dtype=np.int32)
    scores = np.asarray([float(row["score"]) for row in rows], dtype=np.float32)
    preds = scores >= threshold
    precision, recall, f1, _support = precision_recall_fscore_support(y, preds, average="binary", zero_division=0)
    return {
        "split": name,
        "n": int(y.size),
        "positives": int(y.sum()),
        "threshold": float(threshold),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "average_precision": float(average_precision_score(y, scores)) if len(set(y.tolist())) > 1 else 0.0,
        "roc_auc": float(roc_auc_score(y, scores)) if len(set(y.tolist())) > 1 else 0.0,
    }


def _source_summary(rows: list[dict], threshold: float) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["source"])].append(row)
    summary = []
    for source, items in sorted(grouped.items()):
        scores = [float(row["score"]) for row in items]
        preds = [int(row["pred"]) for row in items]
        summary.append(
            {
                "source": source,
                "n": len(items),
                "mean_score": float(np.mean(scores)),
                "median_score": float(np.median(scores)),
                "positive_rate": float(np.mean(preds)),
                "threshold": float(threshold),
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a source-free image-style gate for Cellpose-style routing.")
    parser.add_argument("--train_csv", required=True)
    parser.add_argument("--val_csv")
    parser.add_argument("--eval_csv")
    parser.add_argument("--out_dir", default="outputs/image_style_gate")
    parser.add_argument("--model_name", default="image_style_gate.joblib")
    parser.add_argument("--positive_source", default="cellpose")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--n_estimators", type=int, default=500)
    parser.add_argument("--max_depth", type=int, default=8)
    parser.add_argument("--min_samples_leaf", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--normalize_mode", default="none")
    parser.add_argument("--data_root")
    args = parser.parse_args()

    train_rows = _collect(_read_rows(Path(args.train_csv)), args.positive_source, args.normalize_mode, args.data_root)
    labels = Counter(int(row["label"]) for row in train_rows)
    if labels[0] == 0 or labels[1] == 0:
        raise ValueError(f"Need positive and negative style samples, got {dict(labels)}")

    vectorizer = DictVectorizer(sparse=False)
    x_train = vectorizer.fit_transform([_feature_dict(row) for row in train_rows])
    y_train = np.asarray([int(row["label"]) for row in train_rows], dtype=np.int32)
    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=args.seed,
    )
    model.fit(x_train, y_train)

    val_rows = _collect(_read_rows(Path(args.val_csv)), args.positive_source, args.normalize_mode, args.data_root) if args.val_csv else []
    eval_rows = _collect(_read_rows(Path(args.eval_csv)), args.positive_source, args.normalize_mode, args.data_root) if args.eval_csv else []
    train_scored = _score_rows(model, vectorizer, train_rows, args.threshold)
    val_scored = _score_rows(model, vectorizer, val_rows, args.threshold)
    eval_scored = _score_rows(model, vectorizer, eval_rows, args.threshold)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "vectorizer": vectorizer,
            "model": model,
            "threshold": float(args.threshold),
            "positive_source": args.positive_source,
            "feature_kind": "image_style_v1",
        },
        out_dir / args.model_name,
    )
    _write_csv(out_dir / "train_predictions.csv", train_scored)
    if val_scored:
        _write_csv(out_dir / "val_predictions.csv", val_scored)
    if eval_scored:
        _write_csv(out_dir / "eval_predictions.csv", eval_scored)
        _write_csv(out_dir / "eval_source_summary.csv", _source_summary(eval_scored, args.threshold))
    report = [_report("train", train_scored, args.threshold)]
    if val_scored:
        report.append(_report("val", val_scored, args.threshold))
    if eval_scored:
        report.append(_report("eval", eval_scored, args.threshold))
    _write_csv(out_dir / "style_gate_report.csv", report)
    print(f"wrote {out_dir / args.model_name}")
    print(f"train labels: {dict(labels)}")


if __name__ == "__main__":
    main()
