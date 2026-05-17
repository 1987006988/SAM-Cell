from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

import numpy as np

from sam_cell.config import load_config
from sam_cell.io import load_image, load_label_map
from sam_cell.metrics.instance import instance_metrics, summarize_metrics
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.proposals.regions import proposals_to_label_map


ROOT = Path(os.environ.get("SAM_CELL_ROOT", "/backup/taotao_work/sam_cell"))
NNUNET_PYTHON = Path(os.environ.get("NNUNET_PYTHON", "/backup/taotao_work/venvs/nnunet/bin/python"))
DATA_ROOT = Path(os.environ.get("CELLCOSMOS_DATA_ROOT", "/backup/taotao_data/CellCosmos_Benchmark"))
BASE_CONFIG = ROOT / "configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml"
EXP_ROOT = ROOT / "outputs/tissuenet_local_combo_search_20260504"


def run(cmd: list[str], log_path: Path | None = None) -> None:
    print("$ " + " ".join(cmd), flush=True)
    env = os.environ.copy()
    if log_path is None:
        subprocess.run(cmd, cwd=ROOT, env=env, check=True)
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)


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
    for source in ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]:
        if name.startswith(f"{source}_"):
            return source
    return name.split("_", 1)[0]


def serverize_manifest(src: Path, dst: Path, source_filter: str | None = None) -> None:
    rows = []
    for row in read_csv(src):
        image_path = row["image_path"].replace("/mnt/d/cell data/CellCosmos_Benchmark", str(DATA_ROOT))
        mask_path = row["mask_path"].replace("/mnt/d/cell data/CellCosmos_Benchmark", str(DATA_ROOT))
        image_name = row.get("image_name") or Path(image_path).name
        source = row.get("source") or source_from_name(image_name)
        if source_filter and source != source_filter:
            continue
        rows.append(
            {
                "source": source,
                "image_name": image_name,
                "image_path": image_path,
                "mask_path": mask_path,
                "split": row.get("split", dst.stem),
            }
        )
    write_csv(dst, rows, ["source", "image_name", "image_path", "mask_path", "split"])


def read_summary(path: Path) -> dict[str, dict[str, float]]:
    summary = {}
    for row in read_csv(path):
        source = row["source"]
        values = {}
        for key, value in row.items():
            if key == "source" or value in {"", None}:
                continue
            try:
                values[key] = float(value)
            except ValueError:
                continue
        summary[source] = values
    return summary


def metric(summary: dict[str, dict[str, float]], source: str, key: str) -> float:
    return float(summary.get(source, {}).get(key, 0.0))


def deep_update(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            deep_update(dst[key], value)
        else:
            dst[key] = value
    return dst


def apply_nested_overrides(obj, values: dict[str, Any]) -> dict[str, Any]:
    previous = {}
    for key, value in values.items():
        if "." in key:
            head, tail = key.split(".", 1)
            previous[key] = apply_nested_overrides(getattr(obj, head), {tail: value})[tail]
            continue
        old = getattr(obj, key)
        previous[key] = deepcopy(old)
        if isinstance(value, dict) and hasattr(old, "__dataclass_fields__"):
            previous[key] = apply_nested_overrides(old, value)
        else:
            setattr(obj, key, value)
    return previous


def restore_nested_overrides(obj, values: dict[str, Any]) -> None:
    for key, value in values.items():
        if "." in key:
            head, tail = key.split(".", 1)
            restore_nested_overrides(getattr(obj, head), {tail: value})
            continue
        current = getattr(obj, key)
        if isinstance(value, dict) and hasattr(current, "__dataclass_fields__"):
            restore_nested_overrides(current, value)
        else:
            setattr(obj, key, value)


def base_cellpose_override() -> dict[str, Any]:
    return {
        "watershed": {
            "boundary_additive_weight": 0.12,
            "share_boundary_across_experts": True,
            "marker_rescue_enabled": False,
        }
    }


def candidate_payload(name: str, tissuenet_override: dict[str, Any]) -> dict[str, Any]:
    overrides = {"cellpose": base_cellpose_override()}
    if tissuenet_override:
        overrides["tissuenet"] = tissuenet_override
    return {
        "name": name,
        "extends": str(BASE_CONFIG),
        "source_overrides": overrides,
    }


def make_proposal_candidates() -> list[dict[str, Any]]:
    candidates = [candidate_payload("v3_baseline", {})]
    h_variants = {
        "h004_008_012": [0.04, 0.08, 0.12],
        "h005_009_013": [0.05, 0.09, 0.13],
        "h006_010_014": [0.06, 0.10, 0.14],
        "h008_012_016": [0.08, 0.12, 0.16],
    }
    for add in [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12]:
        for min_dist in [0.35, 0.40, 0.45, 0.50]:
            for h_name, h_values in h_variants.items():
                name = f"tn_add_{add:.2f}_dist_{min_dist:.2f}_{h_name}"
                candidates.append(
                    candidate_payload(
                        name,
                        {
                            "watershed": {
                                "boundary_additive_weight": add,
                                "min_distance_factor": min_dist,
                                "h_maxima_values": h_values,
                            }
                        },
                    )
                )
    return candidates


def expand_merge_candidates(candidates: list[dict[str, Any]], merge_supports: list[float]) -> list[dict[str, Any]]:
    expanded = []
    for candidate in candidates:
        expanded.append(candidate)
        if candidate["name"] == "v3_baseline":
            continue
        tn_base = deepcopy(candidate.get("source_overrides", {}).get("tissuenet", {}))
        for support in merge_supports:
            tn = deepcopy(tn_base)
            deep_update(
                tn,
                {
                    "merge": {
                        "accept_sam2_min_semantic_support": support,
                        "semantic_support_threshold": support,
                    }
                },
            )
            expanded.append(candidate_payload(f"{candidate['name']}_merge_{support:.2f}", tn))
    return expanded


def write_candidate_configs(config_dir: Path, candidates: list[dict[str, Any]]) -> dict[str, Path]:
    config_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    manifest = []
    for candidate in candidates:
        path = config_dir / f"{candidate['name']}.yaml"
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump({k: v for k, v in candidate.items() if k != "name"}, f, sort_keys=False)
        out[candidate["name"]] = path
        item = dict(candidate)
        item["path"] = str(path)
        manifest.append(item)
    (EXP_ROOT / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


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


def compare_row(stage: str, candidate: str, summary: dict[str, dict[str, float]], baseline: dict[str, dict[str, float]], key: str) -> dict[str, Any]:
    value = metric(summary, "tissuenet", key)
    base = metric(baseline, "tissuenet", key)
    return {
        "stage": stage,
        "candidate": candidate,
        f"tissuenet_{key}": value,
        "tissuenet_delta": value - base,
        "objective": value,
    }


def summarize_candidate_metrics(per_image: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in per_image:
        grouped.setdefault(row["candidate"], []).append(row)
    return {name: {"tissuenet": summarize_metrics(rows)} for name, rows in grouped.items()}


def fast_tune_proposal(
    candidates: list[dict[str, Any]],
    manifest: Path,
    out_dir: Path,
) -> list[dict[str, Any]]:
    summary_path = out_dir / "tune_summary.csv"
    if summary_path.exists():
        return read_csv(summary_path)

    cfg = load_config(BASE_CONFIG)
    cfg.sam2.enabled = False
    pipeline = SAMCellPipeline(cfg)
    rows = read_csv(manifest)
    per_image = []
    for idx, row in enumerate(rows, start=1):
        image_path = Path(row["image_path"])
        print(f"[{idx}/{len(rows)}] fast tune TissueNet proposals {image_path.name}", flush=True)
        image = load_image(image_path, normalize_mode=pipeline.cfg.image.normalize_mode)
        gt = load_label_map(row["mask_path"])
        semantic_maps = pipeline._predict_all_semantics(image, image_id=image_path.stem)
        for candidate_idx, candidate in enumerate(candidates):
            source_overrides = candidate.get("source_overrides", {}).get("tissuenet", {})
            previous = apply_nested_overrides(pipeline.cfg, source_overrides)
            try:
                *_debug, proposals, _fg_prob_by_source, _combined_fg_mask, _proposal_diag = pipeline._generate_multi_expert_proposals(
                    semantic_maps,
                    image_id=image_path.stem,
                    image=image,
                )
                label_map = proposals_to_label_map(proposals, gt.shape)
                metrics = instance_metrics(label_map, gt)
                per_image.append(
                    {
                        "candidate": candidate["name"],
                        "candidate_idx": candidate_idx,
                        "source": "tissuenet",
                        "image": image_path.name,
                        "proposal_n": len(proposals),
                        **metrics,
                    }
                )
            finally:
                restore_nested_overrides(pipeline.cfg, previous)
        write_csv(out_dir / "tune_per_image.partial.csv", per_image)

    write_csv(out_dir / "tune_per_image.csv", per_image)
    grouped = summarize_candidate_metrics(per_image)
    baseline_value = float(grouped["v3_baseline"]["tissuenet"].get("pq", 0.0))
    tune_rows = []
    for candidate in candidates:
        value = float(grouped[candidate["name"]]["tissuenet"].get("pq", 0.0))
        tune_rows.append(
            {
                "stage": "tune_tissuenet_proposal",
                "candidate": candidate["name"],
                "tissuenet_proposal_pq": value,
                "tissuenet_delta": value - baseline_value,
                "objective": value,
            }
        )
    write_csv(out_dir / "tune_summary.csv", tune_rows)
    write_csv(out_dir / "tune_summary.partial.csv", tune_rows)
    return tune_rows


def choose_top(rows: list[dict[str, Any]], max_n: int, key: str) -> list[str]:
    eligible = [row for row in rows if row["candidate"] != "v3_baseline"]
    eligible.sort(key=lambda row: (row["objective"], row[f"tissuenet_{key}"]), reverse=True)
    return [row["candidate"] for row in eligible[:max_n]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Local TissueNet-only SAM-Cell EDT/watershed combination search.")
    parser.add_argument("--top_proposal", type=int, default=12)
    parser.add_argument("--top_holdout", type=int, default=5)
    parser.add_argument("--top_eval250", type=int, default=3)
    parser.add_argument(
        "--merge_supports",
        default="0.30,0.35,0.40,0.45",
        help="Comma-separated TissueNet merge support thresholds for holdout expansion, or 'none' to skip merge variants.",
    )
    args = parser.parse_args()
    if args.merge_supports.strip().lower() in {"", "none", "off", "false", "0"}:
        merge_supports = []
    else:
        merge_supports = [float(x) for x in args.merge_supports.split(",") if x.strip()]

    EXP_ROOT.mkdir(parents=True, exist_ok=True)
    log_dir = EXP_ROOT / "logs"
    manifest_dir = EXP_ROOT / "manifests"
    config_dir = EXP_ROOT / "configs"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    tune_manifest = manifest_dir / "dev_tune_tissuenet_server_paths.csv"
    holdout_manifest = manifest_dir / "dev_holdout_tissuenet_server_paths.csv"
    eval250_tn_manifest = manifest_dir / "eval250_tissuenet_server_paths.csv"
    eval250_all_manifest = manifest_dir / "eval250_all_server_paths.csv"
    serverize_manifest(ROOT / "outputs/benchmark_splits_selector20/dev_tune.csv", tune_manifest, "tissuenet")
    serverize_manifest(ROOT / "outputs/benchmark_splits_selector20/dev_holdout.csv", holdout_manifest, "tissuenet")
    serverize_manifest(ROOT / "outputs/benchmark_splits_large/eval_250.csv", eval250_tn_manifest, "tissuenet")
    serverize_manifest(ROOT / "outputs/benchmark_splits_large/eval_250.csv", eval250_all_manifest, None)

    proposal_candidates = make_proposal_candidates()
    by_name = write_candidate_configs(config_dir, proposal_candidates)

    tune_rows = fast_tune_proposal(proposal_candidates, tune_manifest, EXP_ROOT)

    selected_proposal_names = ["v3_baseline", *choose_top(tune_rows, args.top_proposal, "proposal_pq")]
    proposal_by_name = {candidate["name"]: candidate for candidate in proposal_candidates}
    selected_proposals = [proposal_by_name[name] for name in selected_proposal_names if name in proposal_by_name]
    holdout_candidates = expand_merge_candidates(selected_proposals, merge_supports)
    by_name.update(write_candidate_configs(config_dir, holdout_candidates))

    baseline_holdout = eval_samcell(by_name["v3_baseline"], holdout_manifest, EXP_ROOT / "holdout_full" / "v3_baseline", True, True, log_dir)
    holdout_rows = []
    for candidate in holdout_candidates:
        name = candidate["name"]
        summary = baseline_holdout if name == "v3_baseline" else eval_samcell(by_name[name], holdout_manifest, EXP_ROOT / "holdout_full" / name, True, True, log_dir)
        holdout_rows.append(compare_row("holdout_tissuenet_full", name, summary, baseline_holdout, "final_pq"))
        write_csv(EXP_ROOT / "holdout_summary.partial.csv", holdout_rows)
    write_csv(EXP_ROOT / "holdout_summary.csv", holdout_rows)

    eval250_names = ["v3_baseline", *choose_top(holdout_rows, args.top_holdout, "final_pq")]
    baseline_eval250_tn = eval_samcell(by_name["v3_baseline"], eval250_tn_manifest, EXP_ROOT / "eval250_tissuenet" / "v3_baseline", True, True, log_dir)
    eval250_tn_rows = []
    for name in eval250_names:
        summary = baseline_eval250_tn if name == "v3_baseline" else eval_samcell(by_name[name], eval250_tn_manifest, EXP_ROOT / "eval250_tissuenet" / name, True, True, log_dir)
        eval250_tn_rows.append(compare_row("eval250_tissuenet_full", name, summary, baseline_eval250_tn, "final_pq"))
        write_csv(EXP_ROOT / "eval250_tissuenet_summary.partial.csv", eval250_tn_rows)
    write_csv(EXP_ROOT / "eval250_tissuenet_summary.csv", eval250_tn_rows)

    final_names = ["v3_baseline", *choose_top(eval250_tn_rows, args.top_eval250, "final_pq")]
    baseline_eval250_all = eval_samcell(by_name["v3_baseline"], eval250_all_manifest, EXP_ROOT / "eval250_all" / "v3_baseline", True, True, log_dir)
    final_rows = []
    for name in final_names:
        summary = baseline_eval250_all if name == "v3_baseline" else eval_samcell(by_name[name], eval250_all_manifest, EXP_ROOT / "eval250_all" / name, True, True, log_dir)
        row = {"stage": "eval250_all_full", "candidate": name}
        for source in ["ALL", "cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]:
            value = metric(summary, source, "final_pq")
            base = metric(baseline_eval250_all, source, "final_pq")
            row[f"{source}_final_pq"] = value
            row[f"{source}_delta"] = value - base
        row["objective"] = row["ALL_final_pq"] + 0.35 * row["tissuenet_delta"]
        final_rows.append(row)
        write_csv(EXP_ROOT / "eval250_all_summary.partial.csv", final_rows)
    write_csv(EXP_ROOT / "eval250_all_summary.csv", final_rows)

    best = max([row for row in final_rows if row["candidate"] != "v3_baseline"], key=lambda row: (row["ALL_final_pq"], row["objective"]), default=None)
    decision = {
        "accepted": bool(best and best["ALL_delta"] > 0 and best["tissuenet_delta"] > 0),
        "best_candidate": None if best is None else best["candidate"],
        "best_row": best,
        "baseline_config": str(by_name["v3_baseline"]),
        "output_root": str(EXP_ROOT),
        "note": "This search only changes source-specific TissueNet EDT/watershed/merge parameters; no new proposal front-end is used.",
    }
    if best is not None:
        best_config = by_name[best["candidate"]]
        decision["best_config"] = str(best_config)
        if decision["accepted"]:
            target = EXP_ROOT / "sam_cell_tissuenet_combo_best_config.yaml"
            target.write_text(best_config.read_text(encoding="utf-8"), encoding="utf-8")
            decision["copied_best_config"] = str(target)
    (EXP_ROOT / "decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
