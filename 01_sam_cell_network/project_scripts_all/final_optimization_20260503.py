from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


ROOT = Path("/backup/taotao_work/sam_cell")
NNUNET_PYTHON = Path("/backup/taotao_work/venvs/nnunet/bin/python")
CELLPOSE_PYTHON = Path("/backup/taotao_work/venvs/cellpose311/bin/python")
CELLSAM_PYTHON = Path("/backup/taotao_work/venvs/cellsam311_shared/bin/python")
BASE_CONFIG = "configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml"
EXP_ROOT = ROOT / "outputs/final_optimization_20260503"
FULL_ROOT = ROOT / "experiments/cellcosmos_full_16777_20260503"
DATA_ROOT = Path("/backup/taotao_data/CellCosmos_Benchmark")


def run(cmd: list[str], log_path: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("$ " + " ".join(cmd), flush=True)
    if log_path is None:
        subprocess.run(cmd, cwd=ROOT, check=True, env=env)
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT, env=env)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def source_from_name(name: str) -> str:
    if name.startswith("cellpose_"):
        return "cellpose"
    if name.startswith("dsb2018_"):
        return "dsb2018"
    if name.startswith("livecell_"):
        return "livecell"
    if name.startswith("pannuke_"):
        return "pannuke"
    if name.startswith("tissuenet_"):
        return "tissuenet"
    return name.split("_", 1)[0]


def serverize_manifest(src: Path, dst: Path) -> None:
    rows = read_csv(src)
    out = []
    for row in rows:
        image_path = row["image_path"].replace("/mnt/d/cell data/CellCosmos_Benchmark", str(DATA_ROOT))
        mask_path = row["mask_path"].replace("/mnt/d/cell data/CellCosmos_Benchmark", str(DATA_ROOT))
        image_name = row.get("image_name") or Path(image_path).name
        out.append(
            {
                "source": row.get("source") or source_from_name(image_name),
                "image_name": image_name,
                "image_path": image_path,
                "mask_path": mask_path,
                "split": row.get("split", dst.stem),
            }
        )
    write_csv(dst, out, ["source", "image_name", "image_path", "mask_path", "split"])


def build_full_manifest(dst: Path) -> dict[str, int]:
    image_dir = DATA_ROOT / "images"
    mask_dir = DATA_ROOT / "masks"
    rows = []
    counts: dict[str, int] = {}
    for image_path in sorted(image_dir.iterdir()):
        if not image_path.is_file():
            continue
        mask_path = mask_dir / image_path.name
        if not mask_path.exists():
            raise FileNotFoundError(f"missing mask for {image_path}: {mask_path}")
        source = source_from_name(image_path.name)
        counts[source] = counts.get(source, 0) + 1
        rows.append(
            {
                "source": source,
                "image_name": image_path.name,
                "image_path": str(image_path),
                "mask_path": str(mask_path),
                "split": "full_16777",
            }
        )
    write_csv(dst, rows, ["source", "image_name", "image_path", "mask_path", "split"])
    return counts


def deep_update(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            deep_update(dst[key], value)
        else:
            dst[key] = value
    return dst


def candidate_payload(name: str, overrides: dict[str, Any]) -> dict[str, Any]:
    payload = {"name": name, "extends": "../../../configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml"}
    if overrides:
        payload["source_overrides"] = overrides
    return payload


def make_candidates() -> list[dict[str, Any]]:
    base_cellpose = {
        "watershed": {
            "boundary_additive_weight": 0.12,
            "share_boundary_across_experts": True,
            "marker_rescue_enabled": False,
        }
    }
    candidates = [candidate_payload("v3_baseline", {})]
    for weight in [0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.20]:
        cp = deepcopy(base_cellpose)
        cp["watershed"]["boundary_additive_weight"] = weight
        candidates.append(candidate_payload(f"cp_add_{weight:.2f}", {"cellpose": cp}))
    for threshold in [0.40, 0.45, 0.50, 0.55, 0.60]:
        cp = deepcopy(base_cellpose)
        cp["proposal_ranker"] = {"keep_threshold": threshold}
        candidates.append(candidate_payload(f"cp_rank_{threshold:.2f}", {"cellpose": cp}))
    for iou in [0.45, 0.50, 0.55, 0.60, 0.65]:
        cp = deepcopy(base_cellpose)
        cp["proposal_repair"] = {"set_selector_iou_threshold": iou}
        candidates.append(candidate_payload(f"cp_selector_iou_{iou:.2f}", {"cellpose": cp}))
    for margin in [0.00, 0.01, 0.02, 0.04]:
        cp = deepcopy(base_cellpose)
        cp["proposal_repair"] = {"set_selector_score_margin": margin}
        candidates.append(candidate_payload(f"cp_selector_margin_{margin:.2f}", {"cellpose": cp}))

    tissuenet_variants = [
        ("tn_add_0.04", {"watershed": {"boundary_additive_weight": 0.04}}),
        ("tn_add_0.08", {"watershed": {"boundary_additive_weight": 0.08}}),
        ("tn_suppress_0.80", {"watershed": {"boundary_suppression_weight": 0.80}}),
        ("tn_suppress_0.90", {"watershed": {"boundary_suppression_weight": 0.90}}),
        ("tn_min_dist_0.45", {"watershed": {"min_distance_factor": 0.45}}),
        ("tn_min_dist_0.50", {"watershed": {"min_distance_factor": 0.50}}),
        ("tn_h_low", {"watershed": {"h_maxima_values": [0.04, 0.08, 0.12]}}),
        ("tn_h_high", {"watershed": {"h_maxima_values": [0.08, 0.12, 0.16]}}),
        ("tn_merge_support_0.30", {"merge": {"accept_sam2_min_semantic_support": 0.30, "semantic_support_threshold": 0.30}}),
        ("tn_merge_support_0.45", {"merge": {"accept_sam2_min_semantic_support": 0.45, "semantic_support_threshold": 0.45}}),
    ]
    for name, tn in tissuenet_variants:
        candidates.append(candidate_payload(name, {"cellpose": deepcopy(base_cellpose), "tissuenet": tn}))
    return candidates


def write_candidate_configs(config_dir: Path) -> list[dict[str, Any]]:
    config_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for payload in make_candidates():
        path = config_dir / f"{payload['name']}.yaml"
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump({k: v for k, v in payload.items() if k != "name"}, f, sort_keys=False)
        item = dict(payload)
        item["path"] = str(path)
        written.append(item)
    return written


def read_summary(path: Path) -> dict[str, dict[str, float]]:
    rows = read_csv(path)
    summary = {}
    for row in rows:
        source = row["source"]
        metrics = {}
        for key, value in row.items():
            if key == "source" or value in {"", None}:
                continue
            try:
                metrics[key] = float(value)
            except ValueError:
                continue
        summary[source] = metrics
    return summary


def metric(summary: dict[str, dict[str, float]], source: str, key: str) -> float:
    return float(summary.get(source, {}).get(key, 0.0))


def compare_rows(stage: str, candidate: str, summary: dict[str, dict[str, float]], baseline: dict[str, dict[str, float]], key: str) -> dict[str, Any]:
    row: dict[str, Any] = {"stage": stage, "candidate": candidate}
    for source in ["ALL", "cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]:
        value = metric(summary, source, key)
        base = metric(baseline, source, key)
        row[f"{source}_{key}"] = value
        row[f"{source}_delta"] = value - base
    row["objective"] = (
        row[f"ALL_{key}"]
        + 0.35 * row[f"cellpose_delta"]
        + 0.35 * row[f"tissuenet_delta"]
        - 0.20 * min(0.0, row["dsb2018_delta"], row["livecell_delta"], row["pannuke_delta"])
    )
    return row


def eval_samcell(config: Path, manifest: Path, out_dir: Path, sam2_enabled: bool, save_outputs: bool, log_dir: Path) -> dict[str, dict[str, float]]:
    if (out_dir / "summary.csv").exists():
        return read_summary(out_dir / "summary.csv")
    cmd = [
        str(NNUNET_PYTHON),
        "scripts/eval_devset.py",
        "--config",
        str(config),
        "--devset_csv",
        str(manifest),
        "--out_dir",
        str(out_dir),
        "--sam2_enabled",
        "true" if sam2_enabled else "false",
    ]
    if save_outputs:
        cmd.append("--save_outputs")
    run(cmd, log_dir / f"{out_dir.name}.log")
    return read_summary(out_dir / "summary.csv")


def choose_candidates(rows: list[dict[str, Any]], max_n: int, max_drop: float, key: str) -> list[str]:
    eligible = []
    for row in rows:
        if row["candidate"] == "v3_baseline":
            continue
        drops = [row[f"{source}_delta"] for source in ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]]
        target_gain = max(row["cellpose_delta"], row["tissuenet_delta"])
        if min(drops) >= -max_drop and target_gain > 0:
            eligible.append(row)
    eligible.sort(key=lambda r: (r["objective"], r[f"ALL_{key}"]), reverse=True)
    return [row["candidate"] for row in eligible[:max_n]]


def accepted_eval250(row: dict[str, Any]) -> bool:
    drops = [row[f"{source}_delta"] for source in ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]]
    return (
        row["ALL_delta"] >= 0.005
        and max(row["cellpose_delta"], row["tissuenet_delta"]) >= 0.01
        and min(drops) >= -0.01
    )


def write_full_scripts(final_config: Path, full_manifest: Path, full_root: Path) -> tuple[Path, Path]:
    samcell_script = full_root / "run_full_samcell.sh"
    baseline_script = full_root / "run_full_cellpose_cellsam.sh"
    samcell_script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
cd {ROOT}
LOG={full_root}/logs/full_samcell.log
mkdir -p {full_root}/logs
exec > >(tee -a "$LOG") 2>&1
date
PYTHONPATH=. {NNUNET_PYTHON} scripts/eval_devset.py \\
  --config {final_config} \\
  --devset_csv {full_manifest} \\
  --out_dir {full_root}/samcell_final \\
  --save_outputs \\
  --use_cache
date
""",
        encoding="utf-8",
    )
    baseline_script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
cd {ROOT}
LOG={full_root}/logs/full_cellpose_cellsam.log
mkdir -p {full_root}/logs
exec > >(tee -a "$LOG") 2>&1
date
PYTHONPATH=. {CELLPOSE_PYTHON} scripts/run_cellpose_manifest.py \\
  --manifest_csv {full_manifest} \\
  --out_dir {full_root}/cellpose_official_cyto3/predictions \\
  --pretrained_model cyto3 \\
  --gpu_device 1
PYTHONPATH=. {CELLPOSE_PYTHON} scripts/eval_label_dir.py \\
  --manifest_csv {full_manifest} \\
  --pred_dir {full_root}/cellpose_official_cyto3/predictions \\
  --out_dir {full_root}/cellpose_official_cyto3/metrics \\
  --pred_pattern "{{stem}}_cp_masks.tif" \\
  --method_name cellpose_official_cyto3
PYTHONPATH=. {CELLPOSE_PYTHON} scripts/render_instance_overlays.py \\
  --manifest_csv {full_manifest} \\
  --pred_dir {full_root}/cellpose_official_cyto3/predictions \\
  --out_dir {full_root}/cellpose_official_cyto3/overlays \\
  --pred_pattern "{{stem}}_cp_masks.tif" \\
  --method_name cellpose_official_cyto3
PYTHONPATH=. {CELLSAM_PYTHON} scripts/run_cellsam_manifest.py \\
  --manifest_csv {full_manifest} \\
  --out_dir {full_root}/cellsam_generalist/predictions \\
  --suffix _cellsam.tif \\
  --bbox_threshold 0.4 \\
  --grayscale_mode repeat \\
  --skip_existing
PYTHONPATH=. {NNUNET_PYTHON} scripts/eval_label_dir.py \\
  --manifest_csv {full_manifest} \\
  --pred_dir {full_root}/cellsam_generalist/predictions/labels \\
  --out_dir {full_root}/cellsam_generalist/metrics \\
  --pred_pattern "{{stem}}_cellsam.tif" \\
  --method_name cellsam_generalist
PYTHONPATH=. {NNUNET_PYTHON} scripts/render_instance_overlays.py \\
  --manifest_csv {full_manifest} \\
  --pred_dir {full_root}/cellsam_generalist/predictions/labels \\
  --out_dir {full_root}/cellsam_generalist/overlays \\
  --pred_pattern "{{stem}}_cellsam.tif" \\
  --method_name cellsam_generalist
date
""",
        encoding="utf-8",
    )
    samcell_script.chmod(0o755)
    baseline_script.chmod(0o755)
    return samcell_script, baseline_script


def launch_full_inference(final_config: Path, full_manifest: Path, final_name: str) -> None:
    FULL_ROOT.mkdir(parents=True, exist_ok=True)
    scripts = write_full_scripts(final_config, full_manifest, FULL_ROOT)
    manifest = {
        "final_config": str(final_config),
        "final_name": final_name,
        "full_manifest": str(full_manifest),
        "scripts": [str(path) for path in scripts],
        "models": ["samcell_final", "cellpose_official_cyto3", "cellsam_generalist"],
    }
    (FULL_ROOT / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run(["tmux", "new-session", "-d", "-s", "full_samcell_final", f"bash {scripts[0]}"])
    run(["tmux", "new-session", "-d", "-s", "full_cellpose_cellsam", f"bash {scripts[1]}"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Final SAM-Cell v3 in-method optimization and optional full-corpus inference.")
    parser.add_argument("--launch_full_if_improved", action="store_true")
    parser.add_argument("--skip_eval250_candidates", action="store_true")
    args = parser.parse_args()

    EXP_ROOT.mkdir(parents=True, exist_ok=True)
    log_dir = EXP_ROOT / "logs"
    manifest_dir = EXP_ROOT / "manifests"
    config_dir = EXP_ROOT / "configs"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    tune_manifest = manifest_dir / "dev_tune_server_paths.csv"
    holdout_manifest = manifest_dir / "dev_holdout_server_paths.csv"
    eval250_manifest = ROOT / "outputs/benchmark_splits_large/eval_250_server_paths.csv"
    if not eval250_manifest.exists():
        serverize_manifest(ROOT / "outputs/benchmark_splits_large/eval_250.csv", eval250_manifest)
    serverize_manifest(ROOT / "outputs/benchmark_splits_selector20/dev_tune.csv", tune_manifest)
    serverize_manifest(ROOT / "outputs/benchmark_splits_selector20/dev_holdout.csv", holdout_manifest)
    full_manifest = FULL_ROOT / "manifests/full.csv"
    counts = build_full_manifest(full_manifest)

    candidates = write_candidate_configs(config_dir)
    by_name = {item["name"]: Path(item["path"]) for item in candidates}
    (EXP_ROOT / "candidate_manifest.json").write_text(json.dumps(candidates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    baseline_tune = eval_samcell(by_name["v3_baseline"], tune_manifest, EXP_ROOT / "tune" / "v3_baseline", False, False, log_dir)
    tune_rows = []
    for item in candidates:
        name = item["name"]
        summary = baseline_tune if name == "v3_baseline" else eval_samcell(by_name[name], tune_manifest, EXP_ROOT / "tune" / name, False, False, log_dir)
        tune_rows.append(compare_rows("tune_proposal", name, summary, baseline_tune, "proposal_pq"))
    write_csv(EXP_ROOT / "tune_summary.csv", tune_rows)
    holdout_names = ["v3_baseline", *choose_candidates(tune_rows, 5, 0.025, "proposal_pq")]

    baseline_holdout = eval_samcell(by_name["v3_baseline"], holdout_manifest, EXP_ROOT / "holdout" / "v3_baseline", True, True, log_dir)
    holdout_rows = []
    for name in holdout_names:
        summary = baseline_holdout if name == "v3_baseline" else eval_samcell(by_name[name], holdout_manifest, EXP_ROOT / "holdout" / name, True, True, log_dir)
        holdout_rows.append(compare_rows("holdout_full", name, summary, baseline_holdout, "final_pq"))
    write_csv(EXP_ROOT / "holdout_summary.csv", holdout_rows)
    eval250_names = ["v3_baseline", *choose_candidates(holdout_rows, 3, 0.015, "final_pq")]

    baseline_eval250 = eval_samcell(by_name["v3_baseline"], eval250_manifest, EXP_ROOT / "eval250" / "v3_baseline", True, True, log_dir)
    eval250_rows = []
    if not args.skip_eval250_candidates:
        for name in eval250_names:
            summary = baseline_eval250 if name == "v3_baseline" else eval_samcell(by_name[name], eval250_manifest, EXP_ROOT / "eval250" / name, True, True, log_dir)
            eval250_rows.append(compare_rows("eval250_full", name, summary, baseline_eval250, "final_pq"))
    else:
        eval250_rows.append(compare_rows("eval250_full", "v3_baseline", baseline_eval250, baseline_eval250, "final_pq"))
    write_csv(EXP_ROOT / "eval250_summary.csv", eval250_rows)

    accepted = [row for row in eval250_rows if row["candidate"] != "v3_baseline" and accepted_eval250(row)]
    accepted.sort(key=lambda row: (row["ALL_final_pq"], row["objective"]), reverse=True)
    if accepted:
        final_name = accepted[0]["candidate"]
        final_config = by_name[final_name]
        decision = {"accepted": True, "final_name": final_name, "final_config": str(final_config), "row": accepted[0], "full_counts": counts}
        shutil.copy2(final_config, EXP_ROOT / "sam_cell_final_config.yaml")
        if args.launch_full_if_improved:
            launch_full_inference(EXP_ROOT / "sam_cell_final_config.yaml", full_manifest, final_name)
            decision["full_inference_launched"] = True
    else:
        decision = {
            "accepted": False,
            "final_name": "v3_baseline",
            "final_config": str(by_name["v3_baseline"]),
            "reason": "No candidate passed eval250 acceptance gates; full inference not launched by this script.",
            "full_counts": counts,
        }
    (EXP_ROOT / "final_decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
