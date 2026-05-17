from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from sam_cell.metrics.instance import summarize_metrics


ROOT = Path("/backup/taotao_work/sam_cell")
EXP_ROOT = ROOT / "outputs/tissuenet_local_combo_search_20260504"
CONFIG_DIR = EXP_ROOT / "configs"
BASELINE_NAME = "v3_baseline"


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
        if value is None:
            out[key] = value
            continue
        try:
            out[key] = float(value)
        except (TypeError, ValueError):
            out[key] = value
    return out


def summary_from_per_image(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [{"source": "ALL", **summarize_metrics(rows)}]
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[str(row["source"])].append(row)
    for source in sorted(by_source):
        out.append({"source": source, **summarize_metrics(by_source[source])})
    return out


def source_metric(summary: list[dict[str, Any]], source: str, key: str) -> float:
    for row in summary:
        if row.get("source") == source:
            return float(row.get(key, 0.0))
    return 0.0


def selected_candidate_names() -> list[str]:
    rows = read_csv(EXP_ROOT / "eval250_tissuenet_summary.csv")
    rows = [row for row in rows if row["candidate"] != BASELINE_NAME]
    rows.sort(key=lambda row: float(row["tissuenet_final_pq"]), reverse=True)
    return [row["candidate"] for row in rows[:3]]


def copy_best_config(candidate: str) -> Path:
    src = CONFIG_DIR / f"{candidate}.yaml"
    dst = EXP_ROOT / "sam_cell_tissuenet_combo_best_config.yaml"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


def main() -> None:
    baseline_dir = EXP_ROOT / "eval250_all" / BASELINE_NAME
    baseline_per_image = [numeric_row(row) for row in read_csv(baseline_dir / "per_image.csv")]
    baseline_summary = summary_from_per_image(baseline_per_image)
    write_csv(baseline_dir / "summary.csv", baseline_summary)

    baseline_by_non_tn = [row for row in baseline_per_image if row.get("source") != "tissuenet"]
    baseline_lookup = {row["source"]: row for row in baseline_summary}
    final_rows: list[dict[str, Any]] = []

    def add_final_row(candidate: str, summary: list[dict[str, Any]]) -> None:
        row: dict[str, Any] = {"stage": "eval250_all_full", "candidate": candidate}
        for source in ["ALL", "cellpose", "dsb2018", "livecell", "pannuke", "tissuenet"]:
            value = source_metric(summary, source, "final_pq")
            base = float(baseline_lookup[source]["final_pq"])
            row[f"{source}_final_pq"] = value
            row[f"{source}_delta"] = value - base
        row["objective"] = row["ALL_final_pq"] + 0.35 * row["tissuenet_delta"]
        final_rows.append(row)

    add_final_row(BASELINE_NAME, baseline_summary)

    for candidate in selected_candidate_names():
        tn_dir = EXP_ROOT / "eval250_tissuenet" / candidate
        candidate_dir = EXP_ROOT / "eval250_all" / candidate
        candidate_tn = [numeric_row(row) for row in read_csv(tn_dir / "per_image.csv")]
        combined = baseline_by_non_tn + candidate_tn
        summary = summary_from_per_image(combined)
        write_csv(candidate_dir / "per_image.csv", combined)
        write_csv(candidate_dir / "summary.csv", summary)
        add_final_row(candidate, summary)

    write_csv(EXP_ROOT / "eval250_all_summary.partial.csv", final_rows)
    write_csv(EXP_ROOT / "eval250_all_summary.csv", final_rows)

    candidates = [row for row in final_rows if row["candidate"] != BASELINE_NAME]
    best = max(candidates, key=lambda row: (float(row["ALL_final_pq"]), float(row["objective"])))
    accepted = bool(float(best["ALL_delta"]) > 0.0 and float(best["tissuenet_delta"]) > 0.0)
    best_config = CONFIG_DIR / f"{best['candidate']}.yaml"
    decision: dict[str, Any] = {
        "accepted": accepted,
        "best_candidate": best["candidate"],
        "best_row": best,
        "baseline_config": str(CONFIG_DIR / f"{BASELINE_NAME}.yaml"),
        "best_config": str(best_config),
        "output_root": str(EXP_ROOT),
        "note": (
            "All-source eval250 was derived exactly from baseline non-TissueNet per-image rows "
            "and candidate TissueNet per-image rows because this search changes only source-specific "
            "TissueNet EDT/watershed parameters."
        ),
    }
    if accepted:
        decision["copied_best_config"] = str(copy_best_config(str(best["candidate"])))

    (EXP_ROOT / "decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (EXP_ROOT / "derived_eval250_all_manifest.json").write_text(
        json.dumps(
            {
                "baseline_per_image": str(baseline_dir / "per_image.csv"),
                "selected_candidates": selected_candidate_names(),
                "decision": str(EXP_ROOT / "decision.json"),
                "assumption": "Only TissueNet source behavior changes across selected candidates.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
