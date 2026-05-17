from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

FULL_N = 16777
FAROOD_METHODS = {
    "semantic_cc",
    "raw_watershed",
    "current_proposal",
    "coarse_no_sam2",
    "full_samcell",
}
FULL_MODELS = {
    "cellpose_official_cyto3",
    "cellsam_generalist",
    "samcell_refine_final",
}
METRICS = {"pq", "aji", "dice"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _csv_data_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return max(0, sum(1 for _line in f) - 1)


def _has_metric(row: dict[str, str], metric: str) -> bool:
    return row.get(metric) not in (None, "") or row.get(f"final_{metric}") not in (None, "")


def _all_row(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    for row in _read_csv(path):
        if row.get("source") == "ALL":
            return row
    return None


def _summary_has_all_metrics(path: Path, expected_n: int | None = None) -> tuple[bool, str]:
    row = _all_row(path)
    if row is None:
        return False, f"missing ALL row: {path}"
    if expected_n is not None and row.get("n") not in (None, ""):
        n = int(float(row["n"]))
        if n != expected_n:
            return False, f"ALL n={n}, expected {expected_n}: {path}"
    missing = sorted(metric for metric in METRICS if not _has_metric(row, metric))
    if missing:
        return False, f"missing ALL metrics {missing}: {path}"
    return True, f"ALL metrics present: {path}"


def _tmux_alive(session: str) -> bool:
    try:
        subprocess.run(["tmux", "has-session", "-t", session], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _check(name: str, ok: bool, evidence: str, checks: list[dict[str, object]]) -> None:
    checks.append({"requirement": name, "ok": bool(ok), "evidence": evidence})


def audit(args: argparse.Namespace) -> dict[str, object]:
    full_root = Path(args.full_root)
    farood_out = Path(args.farood_out)
    farood_manifest = Path(args.farood_manifest)
    checks: list[dict[str, object]] = []

    watcher_log = full_root / "logs" / "hourly_full_postprocess_and_farood_20260507" / "watch.log"
    watcher_alive = _tmux_alive(args.watcher_session)
    _check(
        "hourly watcher is present",
        watcher_alive or watcher_log.exists(),
        f"session={args.watcher_session} alive={watcher_alive}; log={watcher_log} exists={watcher_log.exists()}",
        checks,
    )

    cellpose_summary = full_root / "cellpose_official_cyto3" / "metrics" / "summary_by_source.csv"
    cellpose_per_image = full_root / "cellpose_official_cyto3" / "metrics" / "per_image.csv"
    ok, evidence = _summary_has_all_metrics(cellpose_summary, args.expected_full_n)
    _check(
        "Cellpose full PQ/AJI/Dice complete",
        ok and _csv_data_rows(cellpose_per_image) == args.expected_full_n,
        f"{evidence}; per_image_rows={_csv_data_rows(cellpose_per_image)}/{args.expected_full_n}",
        checks,
    )

    cellsam_summary = full_root / "cellsam_generalist" / "metrics" / "summary_by_source.csv"
    cellsam_per_image = full_root / "cellsam_generalist" / "metrics" / "per_image.csv"
    ok, evidence = _summary_has_all_metrics(cellsam_summary, args.expected_full_n)
    _check(
        "CellSAM full PQ/AJI/Dice complete",
        ok and _csv_data_rows(cellsam_per_image) == args.expected_full_n,
        f"{evidence}; per_image_rows={_csv_data_rows(cellsam_per_image)}/{args.expected_full_n}",
        checks,
    )

    samcell_summary = full_root / "samcell_refine_final" / "summary.csv"
    samcell_per_image = full_root / "samcell_refine_final" / "per_image.csv"
    ok, evidence = _summary_has_all_metrics(samcell_summary)
    _check(
        "SAM-Cell full PQ/AJI/Dice complete",
        ok and _csv_data_rows(samcell_per_image) == args.expected_full_n,
        f"{evidence}; per_image_rows={_csv_data_rows(samcell_per_image)}/{args.expected_full_n}",
        checks,
    )

    comparison_csv = full_root / "metrics" / "full_model_comparison_20260507" / "full_model_comparison_pq_aji_dice.csv"
    comparison_md = comparison_csv.with_suffix(".md")
    comparison_delta_csv = comparison_csv.parent / "samcell_delta_vs_baselines.csv"
    comparison_delta_md = comparison_csv.parent / "samcell_delta_vs_baselines.md"
    comparison_rows = _read_csv(comparison_csv) if comparison_csv.exists() else []
    all_model_rows = {row.get("method") for row in comparison_rows if row.get("source") == "ALL"}
    comparison_metric_ok = all(all(row.get(metric) not in (None, "") for metric in METRICS) for row in comparison_rows if row.get("source") == "ALL")
    _check(
        "three-model full PQ/AJI/Dice comparison exists",
        FULL_MODELS.issubset(all_model_rows) and comparison_metric_ok and comparison_md.exists(),
        f"csv={comparison_csv} models={sorted(all_model_rows)} md_exists={comparison_md.exists()}",
        checks,
    )

    delta_rows = _read_csv(comparison_delta_csv) if comparison_delta_csv.exists() else []
    delta_baselines = {row.get("baseline_method") for row in delta_rows if row.get("source") == "ALL"}
    delta_metric_ok = all(
        row.get("delta_pq") not in (None, "")
        and row.get("delta_aji") not in (None, "")
        and row.get("delta_dice") not in (None, "")
        for row in delta_rows
        if row.get("source") == "ALL"
    )
    _check(
        "SAM-Cell full delta versus Cellpose and CellSAM exists",
        {"cellpose_official_cyto3", "cellsam_generalist"}.issubset(delta_baselines)
        and delta_metric_ok
        and comparison_delta_md.exists(),
        f"csv={comparison_delta_csv} baselines={sorted(delta_baselines)} md_exists={comparison_delta_md.exists()}",
        checks,
    )

    farood_n = _csv_data_rows(farood_manifest)
    combined = farood_out / "combined_summary.csv"
    interpretation = farood_out / "interpretation.md"
    paired_delta = farood_out / "paired_delta_summary.csv"
    combined_rows = _read_csv(combined) if combined.exists() else []
    methods = {row.get("method") for row in combined_rows if row.get("source") == "ALL"}
    farood_metric_ok = all(
        all(row.get(metric) not in (None, "") for metric in METRICS)
        for row in combined_rows
        if row.get("source") == "ALL" and row.get("method") in FAROOD_METHODS
    )
    farood_n_ok = all(
        int(float(row.get("n", "0"))) == farood_n
        for row in combined_rows
        if row.get("source") == "ALL" and row.get("method") in FAROOD_METHODS
    )
    _check(
        "Far-OOD attribution stage metrics complete",
        FAROOD_METHODS.issubset(methods) and farood_metric_ok and farood_n_ok and interpretation.exists(),
        f"combined={combined} methods={sorted(methods)} farood_n={farood_n} interpretation_exists={interpretation.exists()}",
        checks,
    )

    paired_rows = _read_csv(paired_delta) if paired_delta.exists() else []
    paired_names = {row.get("delta") for row in paired_rows if row.get("source") == "ALL"}
    expected_deltas = {
        "edt_watershed_over_semantic_cc",
        "current_proposal_selection_over_raw_watershed",
        "crop_coarse_reinsertion_over_proposal_map",
        "sam2_refinement_over_coarse_no_sam2",
    }
    paired_metric_ok = all(
        row.get("mean_delta_pq") not in (None, "")
        and row.get("median_delta_pq") not in (None, "")
        and row.get("pq_win_rate") not in (None, "")
        for row in paired_rows
        if row.get("source") == "ALL"
    )
    _check(
        "Far-OOD paired-delta attribution complete",
        expected_deltas.issubset(paired_names) and paired_metric_ok,
        f"paired_delta={paired_delta} deltas={sorted(paired_names)}",
        checks,
    )

    for method in sorted(FAROOD_METHODS):
        summary = farood_out / method / "summary.csv"
        per_image = farood_out / method / "per_image.csv"
        ok, evidence = _summary_has_all_metrics(summary, farood_n)
        _check(
            f"Far-OOD {method} per-stage artifacts complete",
            ok and _csv_data_rows(per_image) == farood_n,
            f"{evidence}; per_image_rows={_csv_data_rows(per_image)}/{farood_n}",
            checks,
        )

    complete = all(bool(check["ok"]) for check in checks)
    return {
        "objective": (
            "Hourly check until inference finishes; compute Cellpose, SAM-Cell and CellSAM PQ/AJI/Dice; "
            "then run Far-OOD attribution for nnU-Net, watershed, crop/coarse handling and SAM2 refinement."
        ),
        "complete": complete,
        "checks": checks,
    }


def _write_markdown(path: Path, report: dict[str, object]) -> None:
    lines = [
        "# Active Goal Audit 20260507",
        "",
        f"Complete: {report['complete']}",
        "",
        "| requirement | ok | evidence |",
        "|---|---:|---|",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['requirement']} | {check['ok']} | {check['evidence']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit completion of the current long-running SAM-Cell objective.")
    parser.add_argument("--full_root", default="/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503")
    parser.add_argument("--farood_out", default="/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507")
    parser.add_argument("--farood_manifest", default="/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/manifests/far_ood_test.csv")
    parser.add_argument("--expected_full_n", type=int, default=FULL_N)
    parser.add_argument("--watcher_session", default="hourly_full_postprocess_and_farood_20260507")
    parser.add_argument("--out_json")
    parser.add_argument("--out_md")
    args = parser.parse_args()

    report = audit(args)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    print(payload)
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(payload + "\n", encoding="utf-8")
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        _write_markdown(Path(args.out_md), report)
    raise SystemExit(0 if report["complete"] else 1)


if __name__ == "__main__":
    main()
