from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
import tifffile

try:
    import yaml
except Exception:  # pragma: no cover - audit should still run without PyYAML.
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sam_cell.metrics.instance import instance_metrics


SOURCES = ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]
METRICS = ["pq", "aji", "dice"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_label(path: Path) -> np.ndarray:
    if path.suffix.lower() in {".tif", ".tiff"}:
        arr = tifffile.imread(path)
    else:
        arr = np.asarray(Image.open(path))
    if arr.ndim == 3:
        arr = arr[..., 0]
    return arr.astype(np.int32, copy=False)


def stem_from_image(image_name: str) -> str:
    return Path(image_name).stem


def method_specs(root: Path) -> dict[str, dict[str, Any]]:
    return {
        "cellpose_official_cyto3": {
            "label_dir": root / "cellpose_official_cyto3" / "predictions",
            "pattern": "{stem}_cp_masks.tif",
            "per_image": root / "cellpose_official_cyto3" / "metrics" / "per_image.csv",
            "summary": root / "cellpose_official_cyto3" / "metrics" / "summary_by_source.csv",
            "inference_manifest": root / "cellpose_official_cyto3" / "predictions" / "inference_manifest.json",
        },
        "cellsam_generalist": {
            "label_dir": root / "cellsam_generalist" / "predictions" / "labels",
            "pattern": "{stem}_cellsam.tif",
            "per_image": root / "cellsam_generalist" / "metrics" / "per_image.csv",
            "summary": root / "cellsam_generalist" / "metrics" / "summary_by_source.csv",
            "inference_manifest": root / "cellsam_generalist" / "predictions" / "run_manifest.json",
        },
        "samcell_refine_final": {
            "label_dir": root / "samcell_refine_final" / "labels",
            "pattern": "{stem}.tif",
            "per_image": root / "samcell_refine_final" / "per_image.csv",
            "summary": root / "samcell_refine_final" / "summary.csv",
            "inference_manifest": root / "samcell_refine_final" / "run_manifest.json",
        },
    }


def expected_pred_path(spec: dict[str, Any], image_name: str) -> Path:
    return Path(spec["label_dir"]) / str(spec["pattern"]).format(stem=stem_from_image(image_name))


def summarize_numeric(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"]].append(row)
    out: dict[str, dict[str, float]] = {}
    for source, source_rows in {"ALL": rows, **dict(sorted(by_source.items()))}.items():
        metrics: dict[str, float] = {"n": float(len(source_rows))}
        for metric in METRICS:
            metrics[metric] = float(np.mean([row_metric(r, metric) for r in source_rows]))
        out[source] = metrics
    return out


def row_metric(row: dict[str, str], metric: str) -> float:
    for key in (metric, f"final_{metric}"):
        value = row.get(key)
        if value not in (None, ""):
            return float(value)
    raise KeyError(f"Missing metric {metric!r}; available columns: {sorted(row)}")


def load_summary(path: Path) -> dict[str, dict[str, float]]:
    rows = read_csv(path)
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        source = row.get("source", "")
        if not source:
            continue
        metrics: dict[str, float] = {}
        if row.get("n") not in (None, ""):
            metrics["n"] = float(row["n"])
        for metric in METRICS:
            key = metric if row.get(metric) not in (None, "") else f"final_{metric}"
            if row.get(key) not in (None, ""):
                metrics[metric] = float(row[key])
        out[source] = metrics
    return out


def audit_inference_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"exists": True}
    for key in [
        "manifest_csv",
        "pretrained_model",
        "diameter",
        "gpu_device",
        "n_images",
        "bbox_threshold",
        "use_wsi",
        "low_contrast_enhancement",
        "gauge_cell_size",
        "grayscale_mode",
        "model_path",
        "suffix",
    ]:
        if key in data:
            out[key] = data[key]
    if "outputs" in data:
        out["outputs_count"] = len(data["outputs"])
    if "filled_empty" in data:
        out["filled_empty_count"] = len(data["filled_empty"])
    if "records" in data:
        out["records_count"] = len(data["records"])
        out["status_counts"] = dict(Counter(str(r.get("status", "")) for r in data["records"]))
    return out


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {"exists": True, "path": str(path), **data}
    return {"exists": True, "path": str(path), "value": data}


def load_yaml_if_available(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    if yaml is None:
        return {"exists": True, "path": str(path), "yaml_available": False}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {"value": data}
    return {"exists": True, "path": str(path), "yaml_available": True, "data": data}


def resolve_config_path(value: str, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [base.parent / path, ROOT / path, ROOT / "configs" / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def compact_config_info(path: Path) -> dict[str, Any]:
    loaded = load_yaml_if_available(path)
    if not loaded.get("exists") or not loaded.get("yaml_available"):
        return loaded
    data = loaded["data"]
    info: dict[str, Any] = {
        "exists": True,
        "path": str(path),
        "extends": data.get("extends"),
    }
    if "source_overrides" in data:
        info["source_overrides"] = data["source_overrides"]
    experts = data.get("semantic_experts")
    if experts is None:
        semantic = data.get("semantic", {})
        experts = semantic.get("experts", {}) if isinstance(semantic, dict) else {}
    if isinstance(experts, list):
        experts = {
            str(expert.get("name", f"expert_{index}")): expert
            for index, expert in enumerate(experts)
            if isinstance(expert, dict)
        }
    if isinstance(experts, dict):
        compact_experts = {}
        for name, expert in experts.items():
            if not isinstance(expert, dict):
                compact_experts[name] = expert
                continue
            compact_experts[name] = {
                "backend": expert.get("backend") or expert.get("type"),
                "model_dir": expert.get("nnunet_model_dir") or expert.get("results_dir"),
                "folds": expert.get("nnunet_folds") or expert.get("folds"),
                "checkpoint_name": expert.get("checkpoint_name"),
                "foreground_classes": expert.get("foreground_class_indices") or expert.get("foreground_classes"),
                "boundary_class": expert.get("boundary_class_index") or expert.get("boundary_class"),
                "enabled_sources": expert.get("enabled_sources"),
                "cache_dir": expert.get("prob_cache_dir") or expert.get("cache_dir"),
            }
        info["semantic_experts"] = compact_experts
    ranker = data.get("proposal_ranker")
    if isinstance(ranker, dict):
        info["proposal_ranker"] = {
            key: ranker.get(key)
            for key in ["enabled", "model_path", "keep_threshold", "enabled_sources"]
            if key in ranker
        }
    sam = data.get("sam") if isinstance(data.get("sam"), dict) else data.get("sam2")
    if isinstance(sam, dict):
        info["sam"] = {
            key: sam.get(key)
            for key in ["checkpoint", "model_cfg", "config", "prompt_mode", "prompt_modes", "sam2_repo"]
            if key in sam
        }
    return info


def audit_samcell_config(root: Path) -> dict[str, Any]:
    run_manifest = load_json_if_exists(root / "run_manifest_samcell_tn_refine.json")
    final_config_value = run_manifest.get("final_config")
    out: dict[str, Any] = {
        "run_manifest": run_manifest,
        "config_chain": [],
    }
    if not final_config_value:
        return out
    current = Path(str(final_config_value))
    seen: set[Path] = set()
    for _ in range(10):
        current = current.resolve()
        if current in seen:
            break
        seen.add(current)
        info = compact_config_info(current)
        out["config_chain"].append(info)
        extends = info.get("extends")
        if not extends:
            break
        current = resolve_config_path(str(extends), current)
    return out


def pick_sample(rows: list[dict[str, str]], sample_per_source: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"]].append(row)
    selected: list[dict[str, str]] = []
    for source in SOURCES:
        source_rows = by_source.get(source, [])
        if not source_rows:
            continue
        take = min(sample_per_source, len(source_rows))
        selected.extend(rng.sample(source_rows, take))
    return selected


def audit_method(
    method: str,
    spec: dict[str, Any],
    manifest_by_image: dict[str, dict[str, str]],
    expected_n: int,
    sample_per_source: int,
    seed: int,
) -> dict[str, Any]:
    label_dir = Path(spec["label_dir"])
    per_rows = read_csv(Path(spec["per_image"]))
    summary = load_summary(Path(spec["summary"]))
    reagg = summarize_numeric(per_rows)
    row_by_image = {row["image"]: row for row in per_rows}
    row_sources = Counter(row["source"] for row in per_rows)

    label_files = list(label_dir.glob("*.tif")) + list(label_dir.glob("*.tiff")) + list(label_dir.glob("*.png"))
    missing_images = sorted(set(manifest_by_image) - set(row_by_image))
    extra_images = sorted(set(row_by_image) - set(manifest_by_image))

    bad_prediction_path_rows: list[str] = []
    missing_prediction_files: list[str] = []
    wrong_expected_name: list[str] = []
    for image_name, manifest_row in manifest_by_image.items():
        row = row_by_image.get(image_name)
        expected = expected_pred_path(spec, image_name)
        if row is None:
            continue
        recorded_value = row.get("prediction_path", "")
        recorded = Path(recorded_value) if recorded_value else expected
        if not recorded.exists():
            bad_prediction_path_rows.append(image_name)
        if not expected.exists():
            missing_prediction_files.append(image_name)
        if recorded.name and recorded.name != expected.name:
            wrong_expected_name.append(image_name)
        if row.get("source") != manifest_row.get("source"):
            wrong_expected_name.append(f"{image_name}:source={row.get('source')} expected={manifest_row.get('source')}")

    summary_diffs: dict[str, dict[str, float]] = {}
    for source, vals in reagg.items():
        if source not in summary:
            continue
        diffs: dict[str, float] = {}
        for key in ["n", *METRICS]:
            if key in vals and key in summary[source]:
                diffs[key] = abs(float(vals[key]) - float(summary[source][key]))
        summary_diffs[source] = diffs

    sample_rows = pick_sample(per_rows, sample_per_source=sample_per_source, seed=seed)
    recompute_mismatches: list[dict[str, Any]] = []
    shape_mismatches: list[dict[str, Any]] = []
    max_abs_metric_diff = 0.0
    for row in sample_rows:
        manifest_row = manifest_by_image[row["image"]]
        pred_path = Path(row.get("prediction_path") or expected_pred_path(spec, row["image"]))
        pred = read_label(pred_path)
        gt = read_label(Path(manifest_row["mask_path"]))
        if pred.shape != gt.shape:
            shape_mismatches.append({"image": row["image"], "pred_shape": list(pred.shape), "gt_shape": list(gt.shape)})
            continue
        metrics = instance_metrics(pred, gt)
        diffs = {key: abs(float(metrics[key]) - row_metric(row, key)) for key in METRICS}
        max_abs_metric_diff = max(max_abs_metric_diff, max(diffs.values()))
        if any(value > 1e-9 for value in diffs.values()):
            recompute_mismatches.append(
                {
                    "image": row["image"],
                    "source": row["source"],
                    "diffs": diffs,
                    "stored": {key: row_metric(row, key) for key in METRICS},
                    "recomputed": {key: float(metrics[key]) for key in METRICS},
                }
            )

    return {
        "method": method,
        "label_dir": str(label_dir),
        "label_file_count": len(label_files),
        "per_image_count": len(per_rows),
        "per_image_source_counts": dict(row_sources),
        "inference_manifest": audit_inference_manifest(Path(spec["inference_manifest"])),
        "expected_n_ok": len(per_rows) == expected_n,
        "label_count_at_least_expected": len(label_files) >= expected_n,
        "missing_per_image_rows": missing_images[:20],
        "missing_per_image_rows_count": len(missing_images),
        "extra_per_image_rows": extra_images[:20],
        "extra_per_image_rows_count": len(extra_images),
        "missing_recorded_prediction_paths_count": len(bad_prediction_path_rows),
        "missing_recorded_prediction_paths_examples": bad_prediction_path_rows[:20],
        "missing_expected_prediction_files_count": len(missing_prediction_files),
        "missing_expected_prediction_files_examples": missing_prediction_files[:20],
        "wrong_expected_name_or_source_count": len(wrong_expected_name),
        "wrong_expected_name_or_source_examples": wrong_expected_name[:20],
        "summary_max_abs_diff": max(
            [value for diffs in summary_diffs.values() for value in diffs.values()] or [0.0]
        ),
        "summary_diffs": summary_diffs,
        "sample_recomputed_count": len(sample_rows),
        "sample_shape_mismatches": shape_mismatches[:20],
        "sample_shape_mismatch_count": len(shape_mismatches),
        "sample_metric_mismatch_count": len(recompute_mismatches),
        "sample_metric_mismatch_examples": recompute_mismatches[:10],
        "sample_max_abs_metric_diff": max_abs_metric_diff,
        "all_summary": summary.get("ALL", {}),
    }


def audit(root: Path, sample_per_source: int, seed: int) -> dict[str, Any]:
    manifest_path = root / "manifests" / "full.csv"
    manifest_rows = read_csv(manifest_path)
    manifest_by_image = {row["image_name"]: row for row in manifest_rows}
    specs = method_specs(root)
    methods = {
        method: audit_method(method, spec, manifest_by_image, len(manifest_rows), sample_per_source, seed)
        for method, spec in specs.items()
    }
    comparison_path = root / "metrics" / "full_model_comparison_20260507" / "full_model_comparison_pq_aji_dice.csv"
    comparison_rows = read_csv(comparison_path) if comparison_path.exists() else []
    return {
        "root": str(root),
        "manifest": {
            "path": str(manifest_path),
            "n": len(manifest_rows),
            "source_counts": dict(Counter(row["source"] for row in manifest_rows)),
            "unique_image_names": len(set(row["image_name"] for row in manifest_rows)),
            "duplicate_image_names": [
                name for name, count in Counter(row["image_name"] for row in manifest_rows).items() if count > 1
            ][:20],
            "missing_image_paths_count": sum(1 for row in manifest_rows if not Path(row["image_path"]).exists()),
            "missing_mask_paths_count": sum(1 for row in manifest_rows if not Path(row["mask_path"]).exists()),
        },
        "methods": methods,
        "samcell_config": audit_samcell_config(root),
        "comparison": {
            "path": str(comparison_path),
            "exists": comparison_path.exists(),
            "row_count": len(comparison_rows),
            "all_rows": [
                row for row in comparison_rows if row.get("source") == "ALL"
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit full CellCosmos 16777 Cellpose/CellSAM/SAM-Cell repro artifacts.")
    parser.add_argument("--root", type=Path, default=Path("/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503"))
    parser.add_argument("--out_dir", type=Path, default=None)
    parser.add_argument("--sample_per_source", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260511)
    args = parser.parse_args()

    out_dir = args.out_dir or args.root / "metrics" / "audit_20260511"
    payload = audit(args.root, args.sample_per_source, args.seed)
    write_json(out_dir / "audit_full_cellcosmos_repro_20260511.json", payload)

    lines = ["# Full CellCosmos Reproduction Audit", ""]
    manifest = payload["manifest"]
    lines.extend(
        [
            f"- root: `{payload['root']}`",
            f"- manifest n: `{manifest['n']}`",
            f"- source counts: `{manifest['source_counts']}`",
            f"- missing image paths: `{manifest['missing_image_paths_count']}`",
            f"- missing mask paths: `{manifest['missing_mask_paths_count']}`",
            "",
            "| method | labels | per-image | summary diff | sampled | sample mismatches | ALL PQ | ALL AJI | ALL Dice | key params/status |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for method, item in payload["methods"].items():
        inf = item["inference_manifest"]
        status = []
        for key in ["pretrained_model", "diameter", "bbox_threshold", "grayscale_mode", "use_wsi", "filled_empty_count"]:
            if key in inf:
                status.append(f"{key}={inf[key]}")
        if "status_counts" in inf:
            status.append(f"status={inf['status_counts']}")
        all_summary = item["all_summary"]
        lines.append(
            "| {method} | {labels} | {per_image} | {summary_diff:.3g} | {sampled} | {mismatches} | {pq:.6f} | {aji:.6f} | {dice:.6f} | {status} |".format(
                method=method,
                labels=item["label_file_count"],
                per_image=item["per_image_count"],
                summary_diff=float(item["summary_max_abs_diff"]),
                sampled=item["sample_recomputed_count"],
                mismatches=item["sample_metric_mismatch_count"] + item["sample_shape_mismatch_count"],
                pq=float(all_summary.get("pq", float("nan"))),
                aji=float(all_summary.get("aji", float("nan"))),
                dice=float(all_summary.get("dice", float("nan"))),
                status="; ".join(status),
            )
        )
    lines.extend(["", "## Notes", ""])
    lines.append("- `summary diff` is the maximum absolute difference between summary CSV metrics and metrics re-aggregated from per-image CSV.")
    lines.append("- Sample recomputation reads prediction labels and GT masks and recomputes PQ/AJI/Dice with the repository evaluator.")
    samcell_config = payload.get("samcell_config", {})
    chain = samcell_config.get("config_chain") or []
    if chain:
        lines.extend(["", "## SAM-Cell Config Chain", ""])
        run_manifest = samcell_config.get("run_manifest", {})
        if run_manifest.get("exists"):
            lines.append(f"- run manifest: `{run_manifest.get('path')}`")
            lines.append(f"- final config: `{run_manifest.get('final_config')}`")
        for index, info in enumerate(chain, start=1):
            lines.append(f"- config {index}: `{info.get('path')}`")
            if info.get("extends"):
                lines.append(f"- config {index} extends: `{info.get('extends')}`")
            experts = info.get("semantic_experts") or {}
            for name, expert in experts.items():
                lines.append(
                    "- semantic expert `{name}`: model_dir=`{results_dir}`, folds=`{folds}`, checkpoint=`{checkpoint}`, "
                    "foreground=`{foreground}`, boundary=`{boundary}`, enabled_sources=`{enabled}`".format(
                        name=name,
                        results_dir=expert.get("model_dir"),
                        folds=expert.get("folds"),
                        checkpoint=expert.get("checkpoint_name"),
                        foreground=expert.get("foreground_classes"),
                        boundary=expert.get("boundary_class"),
                        enabled=expert.get("enabled_sources"),
                    )
                )
            ranker = info.get("proposal_ranker") or {}
            if ranker:
                lines.append(
                    f"- proposal ranker: enabled=`{ranker.get('enabled')}`, model=`{ranker.get('model_path')}`, "
                    f"keep_threshold=`{ranker.get('keep_threshold')}`, enabled_sources=`{ranker.get('enabled_sources')}`"
                )
            sam = info.get("sam") or {}
            if sam:
                lines.append(
                    f"- SAM prompt/model: checkpoint=`{sam.get('checkpoint')}`, cfg=`{sam.get('model_cfg') or sam.get('config')}`, "
                    f"prompt_mode=`{sam.get('prompt_mode') or sam.get('prompt_modes')}`"
                )
    write_md(out_dir / "audit_full_cellcosmos_repro_20260511.md", lines)
    print(out_dir / "audit_full_cellcosmos_repro_20260511.md")
    print(out_dir / "audit_full_cellcosmos_repro_20260511.json")


if __name__ == "__main__":
    main()
