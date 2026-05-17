from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "thesis_experiment_package_20260512"


FINAL_FULL_METRICS = [
    ("Cellpose official cyto3", 16777, 0.456724, 0.334346, 0.304780, 0.531469),
    ("CellSAM generalist", 16777, 0.701177, 0.538885, 0.524821, 0.761598),
    ("SAM-Cell refine final", 16777, 0.746555, 0.608306, 0.618288, 0.865723),
]


REMOTE_PATHS = [
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.csv"),
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.md"),
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/samcell_delta_vs_baselines.csv"),
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/samcell_delta_vs_baselines.md"),
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.json"),
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.md"),
    ("full_comparison", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_final_report_20260507.md"),
    ("full_audit", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/audit_20260511/audit_full_cellcosmos_repro_20260511.json"),
    ("full_audit", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/audit_20260511/audit_full_cellcosmos_repro_20260511.md"),
    ("full_manifest", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv"),
    ("final_config", "/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml"),
    ("final_config", "/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/decision.json"),
    ("farood_attribution", "/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/combined_summary.csv"),
    ("farood_attribution", "/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/paired_delta_summary.csv"),
    ("farood_attribution", "/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/interpretation.md"),
    ("baseline_cellpose", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_iid_finetune_cyto3/iid_val/summary_by_source.csv"),
    ("baseline_cellpose", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_official_cyto3/iid_val/summary_by_source.csv"),
    ("baseline_cellpose", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_official_cyto3/pannuke_core_test/summary_by_source.csv"),
    ("baseline_cellpose", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_official_cyto3/far_ood_test/summary_by_source.csv"),
    ("baseline_cellpose", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_pannuke_finetune_cyto3/pannuke_core_test/summary_by_source.csv"),
    ("baseline_cellpose", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_pannuke_finetune_cyto3/far_ood_test/summary_by_source.csv"),
    ("baseline_stardist", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/stardist_iid/iid_val/summary_by_source.csv"),
    ("baseline_stardist", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/stardist_pannuke/pannuke_core_test/summary_by_source.csv"),
    ("baseline_stardist", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/stardist_pannuke/far_ood_test/summary_by_source.csv"),
    ("baseline_sam2", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/sam2_automatic_dense/iid_val/summary_by_source.csv"),
    ("baseline_sam2", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/sam2_automatic_dense/pannuke_core_test/summary_by_source.csv"),
    ("baseline_sam2", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/sam2_automatic_dense/far_ood_test/summary_by_source.csv"),
    ("baseline_sam2_prompt_matched", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_sam2_prompt_matched_20260507_eval50/summary.csv"),
    ("baseline_sam2_prompt_matched", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_sam2_prompt_matched_20260507_eval50/prompt_matched_same50_comparison.md"),
    ("baseline_hovernet", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke/metrics/core3500_all/summary_by_source.csv"),
    ("baseline_hovernet", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke/predictions/core3500_all/run_manifest.json"),
    ("baseline_cellsam", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_cellsam_generalist/metrics/eval250/summary_by_source.csv"),
    ("baseline_cellsam", "/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_cellsam_generalist/predictions/eval250/run_manifest.json"),
]


NNUNET_PATHS = [
    ("Dataset512_CellPose", "/backup/taotao_work/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d", "final full run Cellpose-style branch; folds 0-4 checkpoint_final.pth"),
    ("Dataset620_CellCosmosBoundary", "/backup/taotao_work/nnUNet_results/Dataset620_CellCosmosBoundary/nnUNetTrainer__nnUNetPlans__2d", "mixed CellCosmos ablation; folds 0-1 complete, folds 2-3 partial"),
    ("Dataset621_SAMCellUniversalBoundary", "/backup/taotao_work/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d", "main universal boundary expert; folds 0-4 checkpoint_final.pth"),
    ("Dataset622_SAMCellCellposeStyleBoundary", "/backup/taotao_work/nnUNet_results/Dataset622_SAMCellCellposeStyleBoundary/nnUNetTrainer__nnUNetPlans__2d", "Cellpose-style trained expert; diagnostic only, not final full-corpus default"),
]


LOCAL_ARTIFACT_DIRS = [
    "outputs/audit_full_cellcosmos_repro_20260511",
    "outputs/cellcosmos_full_16777_by_dataset_metrics_20260507",
    "outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511",
    "outputs/chapter2_qualitative_2_6_3_20260512",
    "outputs/chapter2_real_figures_20260510",
    "outputs/chapter3_cellpose_loss_fig3_12_20260512",
    "outputs/chapter3_pannuke_core_protocol_20260512",
    "outputs/chapter3_table_3_5_cellpose_cross_domain_20260512",
    "outputs/core_far_model_comparison_20260509",
    "outputs/sam2_prompt_matched_eval50_20260507",
]


LOCAL_MANIFEST_FILES = [
    "outputs/benchmark_splits_large/eval_250.csv",
    "outputs/benchmark_splits_large/eval_250_cellpose_only.csv",
    "outputs/benchmark_splits_large/eval_25_balanced.csv",
    "outputs/benchmark_splits_selector20/dev_tune.csv",
    "outputs/benchmark_splits_selector20/dev_holdout.csv",
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | 0o755)


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".git", ".idea", ".codex")
    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)


def write_csv(path: Path, headers: list[str], rows: list[tuple | list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def prepare_out_dir(out_dir: Path) -> None:
    if out_dir.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = out_dir.with_name(f"{out_dir.name}_previous_{stamp}")
        out_dir.rename(backup)
    out_dir.mkdir(parents=True)


def copy_code(out_dir: Path) -> None:
    net = out_dir / "01_sam_cell_network"
    copy_tree(ROOT / "sam_cell", net / "sam_cell")
    copy_tree(ROOT / "configs", net / "configs")
    copy_tree(ROOT / "tests", net / "tests")
    copy_tree(ROOT / "scripts", net / "project_scripts_all")
    for name in ["README.md", "AGENTS.md"]:
        copy_file(ROOT / name, net / name)
    copy_file(ROOT / "docs" / "project_memory.md", net / "docs" / "project_memory.md")
    write_text(
        net / "README.md",
        """
        # 01_sam_cell_network

        This directory contains the current SAM-Cell network code, configs, tests, and project scripts needed to rerun inference/evaluation.

        Recommended final full-corpus config:

        ```text
        /backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml
        ```

        Local packaged config nearest to the final lineage:

        ```text
        configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml
        ```

        Final audited full CellCosmos 16777 result uses mean per-image metrics:

        | method | n | F1 | PQ | AJI | Dice |
        |---|---:|---:|---:|---:|---:|
        | Cellpose official cyto3 | 16777 | 0.456724 | 0.334346 | 0.304780 | 0.531469 |
        | CellSAM generalist | 16777 | 0.701177 | 0.538885 | 0.524821 | 0.761598 |
        | SAM-Cell refine final | 16777 | 0.746555 | 0.608306 | 0.618288 | 0.865723 |

        Large checkpoint files are not copied into this package. See `../artifacts/path_index/large_file_manifest.csv` and `../docs/result_provenance.md`.
        """,
    )


def write_dataset_work(out_dir: Path) -> None:
    dst = out_dir / "02_cellcosmos_dataset_work"
    script_names = [
        "build_cellcosmos_boundary_nnunet.py",
        "build_universal_boundary_nnunet.py",
        "build_cellpose_style_boundary_nnunet.py",
        "cellcosmos_repro_prepare.py",
        "make_benchmark_splits.py",
        "make_eval_split_excluding.py",
        "build_separator_splits.py",
        "plot_chapter3_pannuke_core_protocol_20260512.py",
        "build_chapter3_table_3_5_cellpose_cross_domain_20260512.py",
        "plot_chapter3_cellpose_loss_fig3_12_20260512.py",
        "plot_chapter2_qualitative_2_6_3_20260512.py",
        "plot_full_cellcosmos_f1_pq_aji_dice_20260511.py",
    ]
    for name in script_names:
        copy_file(ROOT / "scripts" / name, dst / "scripts" / name)
    for file in LOCAL_MANIFEST_FILES:
        copy_file(ROOT / file, dst / "manifests" / Path(file).name)
    write_text(
        dst / "README.md",
        """
        # 02_cellcosmos_dataset_work

        Dataset construction and thesis dataset-protocol assets.

        Main dataset/protocol records:

        - Dataset621 `SAMCellUniversalBoundary`: source-balanced nnU-Net boundary/interior expert, 2540 images.
        - Dataset622 `SAMCellCellposeStyleBoundary`: Cellpose-source diagnostic expert, 490 images, not final full-corpus default.
        - Frozen Core3500 manifests and PanNuke-core/Far-OOD protocol live on the server under `/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/manifests`.
        - Full CellCosmos 16777 manifest: `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv`.

        Included outputs:

        - Fig. 3-11 PanNuke-core protocol and SAM2 feature-distance axis.
        - Table 3-5 Cellpose cross-domain data.
        - Fig. 3-12 real 500-epoch Cellpose loss curves.
        - Chapter 2.6.2/2.6.3/2.6.4 real metric/qualitative assets.

        Metric convention: mean per-image PQ/AJI/F1/Dice, not global aggregated PQ.
        """,
    )


def write_baselines(out_dir: Path) -> None:
    dst = out_dir / "03_reproduced_baselines"
    script_names = [
        "run_cellpose_manifest.py",
        "run_cellpose_manifest_cli_batch.py",
        "run_cellpose_manifest_fast.py",
        "run_server_cellpose_repro.sh",
        "run_server_cellpose_cyto3_eval.sh",
        "train_stardist_manifest.py",
        "run_stardist_manifest.py",
        "run_server_stardist_repro.sh",
        "run_cellsam_manifest.py",
        "run_cellsam_manifest_fast.py",
        "run_server_cellsam_repro_splits_20260503.sh",
        "run_sam2_automatic_manifest.py",
        "run_sam2_prompt_matched_baseline_20260507.py",
        "run_server_sam2_automatic_eval.sh",
        "run_hovernet_manifest.py",
        "run_server_hovernet_core3500_20260503.sh",
        "setup_server_cellpose_env.sh",
        "setup_server_stardist_env.sh",
        "setup_server_hovernet_env.sh",
        "eval_label_dir.py",
        "render_instance_overlays.py",
    ]
    for name in script_names:
        copy_file(ROOT / "scripts" / name, dst / "scripts" / name)
    write_text(
        dst / "README.md",
        """
        # 03_reproduced_baselines

        Reproduced comparison networks and evaluation wrappers.

        Included methods:

        - Cellpose official cyto3, IID finetuned cyto3, and PanNuke-finetuned cyto3.
        - StarDist IID and PanNuke-trained baselines.
        - CellSAM generalist.
        - Native SAM2 automatic dense and SAM2 prompt-matched box+mask diagnostic.
        - HoVer-Net fast PanNuke through TIAToolbox.

        Important caveats:

        - HoVer-Net here uses official PanNuke weights, not CellCosmos finetuning.
        - SAM2 prompt-matched eval50 is a supplementary prompt-fair diagnostic, not a full-corpus baseline.
        - Missing or stale baseline artifacts should be refreshed with `../scripts/sync_from_server.sh`.

        Key remote experiment root:

        ```text
        /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501
        ```
        """,
    )


def copy_local_artifacts(out_dir: Path) -> None:
    base = out_dir / "artifacts" / "local_outputs"
    for rel_dir in LOCAL_ARTIFACT_DIRS:
        src = ROOT / rel_dir
        if src.exists():
            copy_tree(src, base / Path(rel_dir).name)
    for rel_file in LOCAL_MANIFEST_FILES:
        copy_file(ROOT / rel_file, out_dir / "artifacts" / "manifests" / Path(rel_file).name)
    write_csv(
        out_dir / "artifacts" / "summary_tables" / "final_full16777_key_metrics.csv",
        ["method", "n", "f1", "pq", "aji", "dice", "metric_convention"],
        [(*row, "mean_per_image") for row in FINAL_FULL_METRICS],
    )


def write_indexes(out_dir: Path) -> None:
    write_csv(
        out_dir / "artifacts" / "path_index" / "remote_small_artifacts.csv",
        ["category", "remote_path"],
        REMOTE_PATHS,
    )
    write_csv(
        out_dir / "artifacts" / "path_index" / "nnunet_checkpoint_manifest.csv",
        ["dataset", "remote_root", "status"],
        NNUNET_PATHS,
    )
    large_rows = [
        ("Full CellCosmos image/mask manifest", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv", "copy small manifest only; raw data stays on server"),
        ("Full SAM-Cell predictions", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final", "do not copy full labels/overlays by default"),
        ("Full Cellpose predictions", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellpose_official_cyto3", "do not copy full labels/overlays by default"),
        ("Full CellSAM predictions", "/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist", "do not copy full labels/overlays by default"),
        ("nnU-Net Dataset621 checkpoints", "/backup/taotao_work/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d", "large checkpoint files referenced only"),
        ("nnU-Net Dataset512 checkpoints", "/backup/taotao_work/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d", "large checkpoint files referenced only"),
        ("Previous Windows CellCosmos zip", "/mnt/d/毕业数据/课题实验相关_backup_YYYYMMDD_HHMMSS/cellcosmos/CellCosmos_Benchmark .zip", "preserved in timestamp backup after replacement; not copied into new package"),
    ]
    write_csv(
        out_dir / "artifacts" / "path_index" / "large_file_manifest.csv",
        ["artifact", "path", "package_policy"],
        large_rows,
    )
    generated = []
    for path in sorted((out_dir / "artifacts").rglob("*")):
        if path.is_file():
            generated.append((path.relative_to(out_dir).as_posix(), path.stat().st_size))
    write_csv(out_dir / "artifacts" / "artifact_index.csv", ["relative_path", "bytes"], generated)


def write_docs(out_dir: Path) -> None:
    write_text(
        out_dir / "README.md",
        """
        # SAM-Cell Thesis Experiment Package

        Built from `/home/taotao/sam_cell` on 2026-05-12.

        This package is a runnable and traceable delivery bundle for the SAM-Cell master's thesis experiments. It intentionally includes code, configs, scripts, manifests, metric summaries, figures, logs/provenance notes, and path indexes, but not full prediction directories or multi-GB checkpoints.

        ## Directory Layout

        - `01_sam_cell_network/`: complete SAM-Cell source package, configs, tests, and project scripts.
        - `02_cellcosmos_dataset_work/`: CellCosmos/Core3500/Full16777 dataset construction and thesis figure/table scripts.
        - `03_reproduced_baselines/`: Cellpose, StarDist, CellSAM, SAM2, and HoVer-Net wrappers.
        - `scripts/`: top-level one-click smoke, verification, and server-sync scripts.
        - `docs/`: experiment protocol, environment, path mapping, and result provenance.
        - `artifacts/`: compact metric summaries, figures, manifests, path indexes, and remote-synced small files.

        ## One-Click Order

        ```bash
        cd /mnt/d/毕业数据/课题实验相关
        bash scripts/verify_package.sh
        bash scripts/run_all_smoke.sh
        ```

        The smoke scripts are safe by default: they verify paths and print reproducible commands without launching long full-corpus training/inference. Set `DRY_RUN=0` and provide explicit data paths to run real local smoke inference/evaluation.

        ## Final Audited Result

        Metrics are mean per-image values.

        | method | n | F1 | PQ | AJI | Dice |
        |---|---:|---:|---:|---:|---:|
        | Cellpose official cyto3 | 16777 | 0.456724 | 0.334346 | 0.304780 | 0.531469 |
        | CellSAM generalist | 16777 | 0.701177 | 0.538885 | 0.524821 | 0.761598 |
        | SAM-Cell refine final | 16777 | 0.746555 | 0.608306 | 0.618288 | 0.865723 |

        Source caveat: SAM-Cell is strongest overall, but not best on every source/metric. TissueNet has higher CellSAM PQ/AJI/F1, and LIVECell has higher Cellpose PQ/AJI/F1; SAM-Cell has the strongest overall pooled result and strongest Dice.
        """,
    )
    write_text(
        out_dir / "docs" / "experiment_protocol.md",
        """
        # Experiment Protocol

        Metric convention: all reported PQ/AJI/F1/Dice values in this package are mean per-image metrics produced by the repository evaluator. Do not mix them with global aggregated PQ.

        Core datasets:

        - Core3500 frozen manifest: 3472 images.
        - Full CellCosmos manifest: 16777 images across Cellpose, DSB2018, LIVECell, PanNuke, and TissueNet.
        - PanNuke-core domain-shift protocol: `pannuke_train` n=1341, `pannuke_core_test` n=336, `far_ood_test` n=1795 non-PanNuke images.
        - Eval250 internal benchmark: balanced 50/source.

        Final SAM-Cell method structure:

        1. nnU-Net semantic foreground/boundary prediction.
        2. EDT + watershed proposal generation.
        3. Local adaptive crop.
        4. Frozen SAM2 refinement with box + coarse mask prompts.
        5. Candidate filtering/fusion and instance evaluation.

        Final full-corpus config:

        ```text
        /backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml
        ```

        This config is an in-method TissueNet EDT/watershed refinement on top of the v3 source-specific boundary configuration; it does not add Cellpose/CellSAM prediction fusion.
        """,
    )
    write_text(
        out_dir / "docs" / "environment_reproduction.md",
        """
        # Environment Reproduction

        Local WSL environment used during development:

        ```text
        repo: /home/taotao/sam_cell
        conda env for plotting/runtime smoke: /home/taotao/anaconda3/envs/SAM-Cell
        nnU-Net local cache: /home/taotao/nnUNet/nnUNetFrame
        SAM2 local source: /home/taotao/segment-anything-2
        ```

        Remote workstation:

        ```text
        ssh taotao@10.181.10.20
        work root: /backup/taotao_work
        sam-cell root: /backup/taotao_work/sam_cell
        GPU: 2 x NVIDIA A100-PCIE-40GB
        nnU-Net/SAM-Cell env: /backup/taotao_work/venvs/nnunet
        Cellpose env: /backup/taotao_work/venvs/cellpose311
        CellSAM env: /backup/taotao_work/venvs/cellsam311_shared
        HoVer-Net env: /backup/taotao_work/venvs/hovernet311_shared
        ```

        Top-level smoke scripts expose path variables and default to dry-run. Do not launch long full training unless you explicitly set the corresponding environment variables and output paths.
        """,
    )
    write_text(
        out_dir / "docs" / "path_mapping.md",
        """
        # Path Mapping

        Windows target requested by the user:

        ```text
        D:\\毕业数据\\课题实验相关
        ```

        WSL path:

        ```text
        /mnt/d/毕业数据/课题实验相关
        ```

        Build staging path:

        ```text
        /home/taotao/sam_cell/outputs/thesis_experiment_package_20260512
        ```

        Remote experiment roots:

        ```text
        /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503
        /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501
        /backup/taotao_work/nnUNet_results
        ```
        """,
    )
    write_text(
        out_dir / "docs" / "result_provenance.md",
        """
        # Result Provenance

        Key final artifacts:

        - Full model comparison: `artifacts/local_outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511` and remote `metrics/full_model_comparison_20260507`.
        - Full reproduction audit: `artifacts/local_outputs/audit_full_cellcosmos_repro_20260511`.
        - Dataset/source metric split: `artifacts/local_outputs/cellcosmos_full_16777_by_dataset_metrics_20260507`.
        - Core/Far domain-shift comparison: `artifacts/local_outputs/core_far_model_comparison_20260509`.
        - SAM2 prompt-matched diagnostic: `artifacts/local_outputs/sam2_prompt_matched_eval50_20260507`.
        - Chapter 3 PanNuke protocol, Table 3-5, and Fig. 3-12: `artifacts/local_outputs/chapter3_*_20260512`.

        Large prediction/checkpoint bodies are not copied. Refresh compact remote artifacts with:

        ```bash
        DRY_RUN=0 bash scripts/sync_from_server.sh
        ```

        Missing data policy: if a referenced remote artifact is absent during refresh, keep the path row and mark it `TODO_NEEDS_REFRESH` rather than inventing a number.
        """,
    )


def write_top_scripts(out_dir: Path) -> None:
    write_text(
        out_dir / "scripts" / "verify_package.sh",
        r"""
        #!/usr/bin/env bash
        set -euo pipefail

        PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

        required=(
          "$PACKAGE_ROOT/README.md"
          "$PACKAGE_ROOT/01_sam_cell_network/sam_cell/pipeline.py"
          "$PACKAGE_ROOT/01_sam_cell_network/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml"
          "$PACKAGE_ROOT/02_cellcosmos_dataset_work/README.md"
          "$PACKAGE_ROOT/03_reproduced_baselines/README.md"
          "$PACKAGE_ROOT/docs/experiment_protocol.md"
          "$PACKAGE_ROOT/artifacts/summary_tables/final_full16777_key_metrics.csv"
          "$PACKAGE_ROOT/artifacts/path_index/large_file_manifest.csv"
        )

        for path in "${required[@]}"; do
          if [[ ! -e "$path" ]]; then
            echo "MISSING $path" >&2
            exit 1
          fi
        done

        while IFS= read -r script; do
          bash -n "$script"
        done < <(find "$PACKAGE_ROOT/scripts" -type f -name '*.sh' | sort)

        python - "$PACKAGE_ROOT" <<'PY'
        import csv
        import sys
        from pathlib import Path

        root = Path(sys.argv[1])
        metrics = root / "artifacts" / "summary_tables" / "final_full16777_key_metrics.csv"
        rows = list(csv.DictReader(metrics.open(newline="", encoding="utf-8")))
        if len(rows) != 3:
            raise SystemExit(f"expected 3 final metric rows, got {len(rows)}")
        names = {row["method"] for row in rows}
        if "SAM-Cell refine final" not in names:
            raise SystemExit("SAM-Cell refine final row missing")
        for row in rows:
            for key in ("f1", "pq", "aji", "dice"):
                value = float(row[key])
                if not (0.0 <= value <= 1.0):
                    raise SystemExit(f"metric out of range: {row['method']} {key}={value}")
        print("CSV sanity checks passed")
        PY

        if grep -RInE --exclude='verify_package.sh' --exclude='build_thesis_experiment_package_20260512.py' '\bsk-[A-Za-z0-9_-]{20,}|BEGIN (RSA|OPENSSH|PRIVATE) KEY|deepcell.*token|api[_-]?key' "$PACKAGE_ROOT" >/tmp/samcell_pkg_secret_scan.txt 2>/dev/null; then
          echo "Potential secret-like string found:" >&2
          cat /tmp/samcell_pkg_secret_scan.txt >&2
          exit 1
        fi

        echo "verify_package: OK"
        """,
        executable=True,
    )
    write_text(
        out_dir / "scripts" / "run_all_smoke.sh",
        r"""
        #!/usr/bin/env bash
        set -euo pipefail

        PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

        bash "$PACKAGE_ROOT/scripts/verify_package.sh"
        bash "$PACKAGE_ROOT/scripts/run_samcell_inference_smoke.sh"
        bash "$PACKAGE_ROOT/scripts/run_baseline_eval_smoke.sh"

        echo "run_all_smoke: OK"
        """,
        executable=True,
    )
    write_text(
        out_dir / "scripts" / "run_samcell_inference_smoke.sh",
        r"""
        #!/usr/bin/env bash
        set -euo pipefail

        PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
        PYTHON_BIN="${PYTHON_BIN:-python}"
        DRY_RUN="${DRY_RUN:-1}"
        IMAGE="${IMAGE:-}"
        IMAGE_DIR="${IMAGE_DIR:-}"
        LIMIT="${LIMIT:-1}"
        CONFIG="${CONFIG:-$PACKAGE_ROOT/01_sam_cell_network/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml}"
        OUT_DIR="${OUT_DIR:-$PACKAGE_ROOT/artifacts/smoke_outputs/samcell_inference}"

        export PYTHONPATH="$PACKAGE_ROOT/01_sam_cell_network:${PYTHONPATH:-}"

        cmd=("$PYTHON_BIN" "$PACKAGE_ROOT/01_sam_cell_network/project_scripts_all/infer.py" --config "$CONFIG" --out_dir "$OUT_DIR" --limit "$LIMIT")
        if [[ -n "$IMAGE" ]]; then
          cmd+=(--image "$IMAGE")
        elif [[ -n "$IMAGE_DIR" ]]; then
          cmd+=(--image_dir "$IMAGE_DIR")
        else
          echo "DRY_RUN: set IMAGE=/path/image.png or IMAGE_DIR=/path/images and DRY_RUN=0 to run SAM-Cell inference."
          printf 'Command template: '
          printf '%q ' "${cmd[@]}" --image "/path/to/image.png"
          printf '\n'
          exit 0
        fi

        if [[ "$DRY_RUN" != "0" ]]; then
          echo "DRY_RUN=1; command not executed:"
          printf '%q ' "${cmd[@]}"
          printf '\n'
          exit 0
        fi

        "${cmd[@]}"
        """,
        executable=True,
    )
    write_text(
        out_dir / "scripts" / "run_baseline_eval_smoke.sh",
        r"""
        #!/usr/bin/env bash
        set -euo pipefail

        PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
        PYTHON_BIN="${PYTHON_BIN:-python}"
        DRY_RUN="${DRY_RUN:-1}"
        MANIFEST_CSV="${MANIFEST_CSV:-}"
        PRED_DIR="${PRED_DIR:-}"
        PRED_PATTERN="${PRED_PATTERN:-}"
        if [[ -z "$PRED_PATTERN" ]]; then
          PRED_PATTERN='{stem}_cp_masks.tif'
        fi
        METHOD_NAME="${METHOD_NAME:-baseline_smoke}"
        OUT_DIR="${OUT_DIR:-$PACKAGE_ROOT/artifacts/smoke_outputs/baseline_eval}"

        export PYTHONPATH="$PACKAGE_ROOT/01_sam_cell_network:${PYTHONPATH:-}"
        cmd=("$PYTHON_BIN" "$PACKAGE_ROOT/03_reproduced_baselines/scripts/eval_label_dir.py" --manifest_csv "${MANIFEST_CSV:-/path/to/manifest.csv}" --pred_dir "${PRED_DIR:-/path/to/pred_labels}" --out_dir "$OUT_DIR" --pred_pattern "$PRED_PATTERN" --method_name "$METHOD_NAME" --missing_ok)

        if [[ -z "$MANIFEST_CSV" || -z "$PRED_DIR" || "$DRY_RUN" != "0" ]]; then
          echo "DRY_RUN: set MANIFEST_CSV, PRED_DIR, and DRY_RUN=0 to evaluate a baseline label directory."
          printf 'Command template: '
          printf '%q ' "${cmd[@]}"
          printf '\n'
          exit 0
        fi

        "${cmd[@]}"
        """,
        executable=True,
    )
    write_text(
        out_dir / "scripts" / "sync_from_server.sh",
        r"""#!/usr/bin/env bash
        set -u

        PACKAGE_ROOT="${PACKAGE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
        SSH_HOST="${SSH_HOST:-taotao@10.181.10.20}"
        DRY_RUN="${DRY_RUN:-1}"
        DEST_ROOT="${DEST_ROOT:-$PACKAGE_ROOT/artifacts/remote_synced}"
        MANIFEST="$PACKAGE_ROOT/artifacts/path_index/remote_small_artifacts.csv"
        MISSING="$DEST_ROOT/TODO_NEEDS_REFRESH_missing_remote_files.txt"

        mkdir -p "$DEST_ROOT"
        : > "$MISSING"

        tail -n +2 "$MANIFEST" | while IFS=, read -r category remote_path; do
          category="${category%$'\r'}"
          remote_path="${remote_path%$'\r'}"
          [ -n "$remote_path" ] || continue
          rel="${remote_path#/backup/taotao_work/sam_cell/}"
          rel="${rel#/backup/taotao_work/}"
          dest="$DEST_ROOT/$category/$rel"
          mkdir -p "$(dirname "$dest")"
          if [[ "$DRY_RUN" != "0" ]]; then
            echo "DRY_RUN scp $SSH_HOST:$remote_path $dest"
            continue
          fi
          if scp "$SSH_HOST:$remote_path" "$dest"; then
            echo "copied $remote_path"
          else
            echo "TODO_NEEDS_REFRESH $remote_path" | tee -a "$MISSING" >&2
          fi
        done

        if [[ "$DRY_RUN" != "0" ]]; then
          echo "sync_from_server: dry-run complete"
        else
          echo "sync_from_server: complete; missing list at $MISSING"
        fi
        """,
        executable=True,
    )


def write_package_manifest(out_dir: Path) -> None:
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_repo": str(ROOT),
        "package_root": str(out_dir),
        "target_path": "/mnt/d/毕业数据/课题实验相关",
        "metric_convention": "mean_per_image",
        "large_files_copied": False,
        "remote_refresh_script": "scripts/sync_from_server.sh",
    }
    (out_dir / "artifacts" / "package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build(out_dir: Path) -> None:
    prepare_out_dir(out_dir)
    copy_code(out_dir)
    write_dataset_work(out_dir)
    write_baselines(out_dir)
    copy_local_artifacts(out_dir)
    write_docs(out_dir)
    write_top_scripts(out_dir)
    write_indexes(out_dir)
    write_package_manifest(out_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SAM-Cell thesis experiment delivery package.")
    parser.add_argument("--out_dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    out_dir = Path(args.out_dir).resolve()
    build(out_dir)
    print(out_dir)


if __name__ == "__main__":
    main()
