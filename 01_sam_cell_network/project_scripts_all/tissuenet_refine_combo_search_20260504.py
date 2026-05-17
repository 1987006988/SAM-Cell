from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(os.environ.get("SAM_CELL_ROOT", "/backup/taotao_work/sam_cell"))
NNUNET_PYTHON = Path(os.environ.get("NNUNET_PYTHON", "/backup/taotao_work/venvs/nnunet/bin/python"))
DATA_ROOT = Path(os.environ.get("CELLCOSMOS_DATA_ROOT", "/backup/taotao_data/CellCosmos_Benchmark"))
BASE_CONFIG = ROOT / "configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml"
EXP_ROOT = ROOT / "outputs/tissuenet_refine_combo_search_20260504"

sys.path.insert(0, str(ROOT))

import tissuenet_local_combo_search_20260504 as base
from sam_cell.metrics.instance import summarize_metrics


def _wire_base_module() -> None:
    base.ROOT = ROOT
    base.NNUNET_PYTHON = NNUNET_PYTHON
    base.DATA_ROOT = DATA_ROOT
    base.BASE_CONFIG = BASE_CONFIG
    base.EXP_ROOT = EXP_ROOT


def current_tissuenet_override() -> dict[str, Any]:
    return {
        "watershed": {
            "boundary_additive_weight": 0.12,
            "min_distance_factor": 0.50,
            "h_maxima_values": [0.08, 0.12, 0.16],
        }
    }


def make_refine_candidates() -> list[dict[str, Any]]:
    candidates = [base.candidate_payload("v3_baseline", current_tissuenet_override())]
    h_variants = {
        "h008_012_016": [0.08, 0.12, 0.16],
        "h010_014_018": [0.10, 0.14, 0.18],
        "h010_015_020": [0.10, 0.15, 0.20],
        "h012_016_020": [0.12, 0.16, 0.20],
    }
    for add in [0.12, 0.13, 0.14, 0.15, 0.16, 0.18]:
        for min_dist in [0.50, 0.55, 0.60, 0.65]:
            for h_name, h_values in h_variants.items():
                name = f"tn_refine_add_{add:.2f}_dist_{min_dist:.2f}_{h_name}"
                if add == 0.12 and min_dist == 0.50 and h_values == [0.08, 0.12, 0.16]:
                    continue
                candidates.append(
                    base.candidate_payload(
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


def numeric_row(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            out[key] = value
    return out


def summary_from_per_image(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [{"source": "ALL", **summarize_metrics(rows)}]
    for source in ["cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]:
        source_rows = [row for row in rows if row.get("source") == source]
        if source_rows:
            out.append({"source": source, **summarize_metrics(source_rows)})
    return out


def source_metric(summary: list[dict[str, Any]], source: str, key: str) -> float:
    for row in summary:
        if row.get("source") == source:
            return float(row.get(key, 0.0))
    return 0.0


def eval_samcell(config: Path, manifest: Path, out_dir: Path, sam2_enabled: bool, save_outputs: bool, log_dir: Path) -> dict[str, dict[str, float]]:
    if (out_dir / "summary.csv").exists():
        return base.read_summary(out_dir / "summary.csv")
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
        cmd.append("--use_cache")
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / f"{out_dir.name}.log").open("a", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, cwd=ROOT, env=os.environ.copy(), stdout=f, stderr=subprocess.STDOUT, check=True)
    return base.read_summary(out_dir / "summary.csv")


def compare_row(stage: str, candidate: str, summary: dict[str, dict[str, float]], baseline: dict[str, dict[str, float]], key: str) -> dict[str, Any]:
    value = base.metric(summary, "tissuenet", key)
    baseline_value = base.metric(baseline, "tissuenet", key)
    return {
        "stage": stage,
        "candidate": candidate,
        f"tissuenet_{key}": value,
        "tissuenet_delta": value - baseline_value,
        "objective": value,
    }


def choose_top(rows: list[dict[str, Any]], max_n: int, key: str) -> list[str]:
    eligible = [row for row in rows if row["candidate"] != "v3_baseline"]
    eligible.sort(key=lambda row: (float(row["objective"]), float(row[f"tissuenet_{key}"])), reverse=True)
    return [row["candidate"] for row in eligible[:max_n]]


def derive_allsource_from_tissuenet(final_names: list[str], config_paths: dict[str, Path]) -> dict[str, Any]:
    baseline_all_dir = ROOT / "outputs/tissuenet_local_combo_search_20260504/eval250_all/tn_add_0.12_dist_0.50_h008_012_016"
    if not (baseline_all_dir / "per_image.csv").exists():
        baseline_all_dir = ROOT / "outputs/tissuenet_local_combo_search_20260504/eval250_all/v3_baseline"
    baseline_rows = [numeric_row(row) for row in read_csv(baseline_all_dir / "per_image.csv")]
    baseline_summary = summary_from_per_image(baseline_rows)
    baseline_non_tn = [row for row in baseline_rows if row.get("source") != "tissuenet"]

    all_rows = []
    baseline_lookup = {row["source"]: row for row in baseline_summary}

    def add_row(candidate: str, summary: list[dict[str, Any]]) -> None:
        row: dict[str, Any] = {"stage": "eval250_all_derived", "candidate": candidate}
        for source in ["ALL", "cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]:
            value = source_metric(summary, source, "final_pq")
            base_value = float(baseline_lookup[source]["final_pq"])
            row[f"{source}_final_pq"] = value
            row[f"{source}_delta"] = value - base_value
        row["objective"] = row["ALL_final_pq"] + 0.35 * row["tissuenet_delta"]
        all_rows.append(row)

    add_row("v3_baseline", baseline_summary)
    for name in final_names:
        if name == "v3_baseline":
            continue
        tn_dir = EXP_ROOT / "eval250_tissuenet" / name
        candidate_tn = [numeric_row(row) for row in read_csv(tn_dir / "per_image.csv")]
        combined = baseline_non_tn + candidate_tn
        summary = summary_from_per_image(combined)
        candidate_dir = EXP_ROOT / "eval250_all_derived" / name
        write_csv(candidate_dir / "per_image.csv", combined)
        write_csv(candidate_dir / "summary.csv", summary)
        add_row(name, summary)

    write_csv(EXP_ROOT / "eval250_all_summary.csv", all_rows)
    candidates = [row for row in all_rows if row["candidate"] != "v3_baseline"]
    best = max(candidates, key=lambda row: (float(row["ALL_final_pq"]), float(row["objective"])), default=None)
    accepted = bool(best and float(best["ALL_delta"]) > 0.0 and float(best["tissuenet_delta"]) > 0.0)
    decision: dict[str, Any] = {
        "accepted": accepted,
        "best_candidate": None if best is None else best["candidate"],
        "best_row": best,
        "baseline": "v3_baseline is the previously accepted tn_add_0.12_dist_0.50_h008_012_016 setting in this refine run.",
        "baseline_all_source_per_image": str(baseline_all_dir / "per_image.csv"),
        "output_root": str(EXP_ROOT),
        "note": "This refine run only changes source-specific TissueNet EDT/watershed parameters; all-source metrics are derived by replacing only TissueNet per-image rows.",
    }
    if best is not None:
        decision["best_config"] = str(config_paths[best["candidate"]])
        if accepted:
            dst = EXP_ROOT / "sam_cell_tissuenet_refine_best_config.yaml"
            dst.write_text(config_paths[best["candidate"]].read_text(encoding="utf-8"), encoding="utf-8")
            decision["copied_best_config"] = str(dst)
    (EXP_ROOT / "decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return decision


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine the accepted TissueNet EDT/watershed combo without adding a new proposal front-end.")
    parser.add_argument("--top_proposal", type=int, default=10)
    parser.add_argument("--top_holdout", type=int, default=4)
    parser.add_argument("--top_eval250", type=int, default=3)
    args = parser.parse_args()

    _wire_base_module()
    EXP_ROOT.mkdir(parents=True, exist_ok=True)
    log_dir = EXP_ROOT / "logs"
    manifest_dir = EXP_ROOT / "manifests"
    config_dir = EXP_ROOT / "configs"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    tune_manifest = manifest_dir / "dev_tune_tissuenet_server_paths.csv"
    holdout_manifest = manifest_dir / "dev_holdout_tissuenet_server_paths.csv"
    eval250_tn_manifest = manifest_dir / "eval250_tissuenet_server_paths.csv"
    base.serverize_manifest(ROOT / "outputs/benchmark_splits_selector20/dev_tune.csv", tune_manifest, "tissuenet")
    base.serverize_manifest(ROOT / "outputs/benchmark_splits_selector20/dev_holdout.csv", holdout_manifest, "tissuenet")
    base.serverize_manifest(ROOT / "outputs/benchmark_splits_large/eval_250.csv", eval250_tn_manifest, "tissuenet")

    candidates = make_refine_candidates()
    config_paths = base.write_candidate_configs(config_dir, candidates)

    tune_rows = base.fast_tune_proposal(candidates, tune_manifest, EXP_ROOT)
    selected_names = ["v3_baseline", *choose_top(tune_rows, args.top_proposal, "proposal_pq")]
    selected_candidates = [candidate for candidate in candidates if candidate["name"] in selected_names]
    config_paths.update(base.write_candidate_configs(config_dir, selected_candidates))

    baseline_holdout = eval_samcell(config_paths["v3_baseline"], holdout_manifest, EXP_ROOT / "holdout_full" / "v3_baseline", True, True, log_dir)
    holdout_rows = []
    for candidate in selected_candidates:
        name = candidate["name"]
        summary = baseline_holdout if name == "v3_baseline" else eval_samcell(config_paths[name], holdout_manifest, EXP_ROOT / "holdout_full" / name, True, True, log_dir)
        holdout_rows.append(compare_row("holdout_tissuenet_full", name, summary, baseline_holdout, "final_pq"))
        write_csv(EXP_ROOT / "holdout_summary.partial.csv", holdout_rows)
    write_csv(EXP_ROOT / "holdout_summary.csv", holdout_rows)

    eval250_names = ["v3_baseline", *choose_top(holdout_rows, args.top_holdout, "final_pq")]
    baseline_eval250 = eval_samcell(config_paths["v3_baseline"], eval250_tn_manifest, EXP_ROOT / "eval250_tissuenet" / "v3_baseline", True, True, log_dir)
    eval250_rows = []
    for name in eval250_names:
        summary = baseline_eval250 if name == "v3_baseline" else eval_samcell(config_paths[name], eval250_tn_manifest, EXP_ROOT / "eval250_tissuenet" / name, True, True, log_dir)
        eval250_rows.append(compare_row("eval250_tissuenet_full", name, summary, baseline_eval250, "final_pq"))
        write_csv(EXP_ROOT / "eval250_tissuenet_summary.partial.csv", eval250_rows)
    write_csv(EXP_ROOT / "eval250_tissuenet_summary.csv", eval250_rows)

    final_names = ["v3_baseline", *choose_top(eval250_rows, args.top_eval250, "final_pq")]
    decision = derive_allsource_from_tissuenet(final_names, config_paths)
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
