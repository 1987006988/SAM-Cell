# SAM-Cell Project Memory

Last updated: 2026-05-12 05:17 CST

This file is the persistent project memory for future SAM-Cell work. Update it after every major training, evaluation, data, or design decision.

## Goal

SAM-Cell is intended as a general cell image instance segmentation framework, not a Cellpose-only method.

Core pipeline:

1. nnU-Net semantic foreground/boundary prediction.
2. EDT + watershed proposal generation.
3. Local adaptive crop.
4. Frozen SAM2 refinement with box + coarse mask prompts.
5. Candidate filtering/merging and instance metric evaluation.

Scientific target:

- Beat Cellpose on broad multi-source cell image segmentation.
- Preserve or recover competitiveness on Cellpose-style images.
- Approach stronger recent cell foundation/segmenter models through better semantic priors and SAM2 refinement.

## 2026-05-12 Thesis Experiment Package Delivery

User request:

- Organize the SAM-Cell master's thesis experiment project into a one-click runnable and deliverable package.
- Include the complete SAM-Cell network, CellCosmos/data construction work, and reproduced comparison baselines: Cellpose, StarDist, CellSAM, SAM2 automatic/prompt-matched, and HoVer-Net.
- Replace the Windows target directory:

```text
D:\毕业数据\课题实验相关
/mnt/d/毕业数据/课题实验相关
```

Staging package:

```text
/home/taotao/sam_cell/outputs/thesis_experiment_package_20260512
```

Target replacement:

```text
/mnt/d/毕业数据/课题实验相关
```

Timestamped backup of the previous target:

```text
/mnt/d/毕业数据/课题实验相关_backup_20260512_051454
```

Package size/status:

- New target package size: 44M.
- Backup size: 7.4G.
- The previous large `cellcosmos/CellCosmos_Benchmark .zip` is preserved in the backup, not copied into the new package.
- Full prediction directories and nnU-Net checkpoint bodies are not copied; they are referenced through manifests/path indexes.

Top-level package layout:

```text
README.md
01_sam_cell_network/
02_cellcosmos_dataset_work/
03_reproduced_baselines/
scripts/
docs/
artifacts/
```

Important package contents:

- `01_sam_cell_network/`: full `sam_cell` source package, configs, tests, all current project scripts, and project memory snapshot.
- `02_cellcosmos_dataset_work/`: dataset builders, split/protocol scripts, and manifest snapshots.
- `03_reproduced_baselines/`: Cellpose, StarDist, CellSAM, SAM2, HoVer-Net runner/evaluation scripts.
- `scripts/verify_package.sh`, `scripts/run_all_smoke.sh`, `scripts/run_samcell_inference_smoke.sh`, `scripts/run_baseline_eval_smoke.sh`, `scripts/sync_from_server.sh`.
- `artifacts/local_outputs/`: compact local figures/tables/audits for Chapter 2/3 and metric summaries.
- `artifacts/remote_synced/`: manually synced key small remote artifacts including full comparison, final config/decision, Far-OOD attribution, active-goal audit/final report, and full manifest.
- `artifacts/path_index/`: large-file and checkpoint path manifests.

Validation results:

```text
bash outputs/thesis_experiment_package_20260512/scripts/verify_package.sh
CSV sanity checks passed
verify_package: OK

bash outputs/thesis_experiment_package_20260512/scripts/run_all_smoke.sh
verify_package: OK
run_all_smoke: OK

bash /mnt/d/毕业数据/课题实验相关/scripts/verify_package.sh
CSV sanity checks passed
verify_package: OK

bash /mnt/d/毕业数据/课题实验相关/scripts/run_all_smoke.sh
verify_package: OK
run_all_smoke: OK
```

Remote/server status recorded in the package:

- Remote root: `/backup/taotao_work/sam_cell`.
- nnU-Net roots: `/backup/taotao_work/nnUNet_raw`, `/backup/taotao_work/nnUNet_preprocessed`, `/backup/taotao_work/nnUNet_results`.
- Full16777 root: `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503`.
- Reproduction baseline root: `/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501`.

Final audited full CellCosmos 16777 metric convention:

- Mean per-image F1/PQ/AJI/Dice, not global aggregated PQ.

Final key rows:

| method | n | F1 | PQ | AJI | Dice |
|---|---:|---:|---:|---:|---:|
| Cellpose official cyto3 | 16777 | 0.456724 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM generalist | 16777 | 0.701177 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell refine final | 16777 | 0.746555 | 0.608306 | 0.618288 | 0.865723 |

Outstanding/manual-confirmation items:

- Large raw datasets, full predictions/overlays, and nnU-Net checkpoints remain at the original local/server paths and in the Windows backup; copy them only if the user explicitly wants a heavy archive.
- `scripts/sync_from_server.sh` is included for future refresh. In this run, the sandbox blocked the script-level scp first; key remote small artifacts were then manually copied into `artifacts/remote_synced/`. Some baseline per-split summaries remain represented by local summary tables and remote path indexes rather than copied bodies.
- Long full training/inference is intentionally not launched by default. Smoke scripts default to dry-run and require explicit `DRY_RUN=0` plus data paths.

## Current Interpretation

The current evidence supports this statement:

SAM-Cell with a universal/balanced semantic prior is stronger than Cellpose on several non-Cellpose domains, but a single universal semantic front-end still underperforms Cellpose on Cellpose-style images.

Do not claim "all cell types outperform Cellpose" yet. A rigorous phrasing is:

SAM-Cell shows stronger cross-domain generalization on tested non-Cellpose domains and beats Cellpose overall on the current 250-image balanced benchmark, while Cellpose-style microscopy remains the main failure domain that needs multi-expert or adaptive fusion.

## Data Versions

### Dataset620_CellCosmosBoundary

Purpose: first mixed CellCosmos boundary/interior nnU-Net.

Local raw path:

```text
/home/taotao/nnUNet/nnUNetFrame/nnUNet_raw/Dataset620_CellCosmosBoundary
```

Remote raw/results:

```text
/backup/taotao_work/nnUNet_raw/Dataset620_CellCosmosBoundary
/backup/taotao_work/nnUNet_results/Dataset620_CellCosmosBoundary/nnUNetTrainer__nnUNetPlans__2d
```

Issue:

- Built from `CellCosmos_Core_3500`, only 3222 train cases after excluding eval.
- Source distribution was imbalanced:
  - pannuke 1627
  - tissuenet 1307
  - livecell 99
  - cellpose 97
  - dsb2018 92
- Cellpose effective share was about 3%, which is not suitable for the current generalist goal.

Status:

- Fold0/fold1 completed.
- Fold2/fold3 were stopped when switching to Dataset621.
- Keep as an ablation/baseline, not as the main model.

### Dataset621_SAMCellUniversalBoundary

Purpose: source-balanced universal boundary/interior nnU-Net.

Builder:

```text
scripts/build_universal_boundary_nnunet.py
```

Local raw path:

```text
/home/taotao/nnUNet/nnUNetFrame/nnUNet_raw/Dataset621_SAMCellUniversalBoundary
```

Remote raw/results:

```text
/backup/taotao_work/nnUNet_raw/Dataset621_SAMCellUniversalBoundary
/backup/taotao_work/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d
```

Composition:

- total 2540 unique images
- cellpose 490
- dsb2018 500
- livecell 500
- pannuke 500
- tissuenet 500
- yeastnet 50

Effective Cellpose share is about 19.3%, without duplicated oversampling.

Label format:

- 0 background
- 1 cell/interior
- 2 boundary

Important caveat:

- YeastNet is included as a rare domain, but it has not yet been independently evaluated.
- Bacteria/organoid/EM/3D are not yet covered enough to support broad claims.

## Training Status

Remote workstation:

```text
ssh taotao@10.181.10.20
work root: /backup/taotao_work
GPUs: 2 x NVIDIA A100-PCIE-40GB
```

### CellCosmos Reproduction Baselines

Experiment root:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501
```

Purpose:

- Reproduce thesis comparison baselines on the frozen Core3500 splits.
- Preserve all useful artifacts: formatted data, split CSVs, configs, logs, checkpoints, predictions, full overlays, metrics, and run manifests.
- Do not run current SAM-Cell Core3500 full evaluation yet; wait until SAM-Cell optimization is complete.
- Native SAM2 automatic-mask baseline remains valid to evaluate independently.

Frozen splits:

| split | n | intended use |
|---|---:|---|
| core3500_all | 3472 | frozen full Core3500 manifest |
| iid_train | 2775 | IID baseline training |
| iid_val | 697 | IID validation/test |
| pannuke_train | 1341 | PanNuke-domain baseline training |
| pannuke_core_test | 336 | PanNuke in-domain test |
| far_ood_test | 1795 | non-PanNuke far-OOD test |

Important Cellpose naming:

- `cellpose_official_cyto3`: official pretrained Cellpose cyto3 inference baseline.
- `cellpose_iid_finetune_cyto3`: Cellpose fine-tuned from cyto3 on `iid_train`.
- `cellpose_pannuke_finetune_cyto3`: Cellpose fine-tuned from cyto3 on `pannuke_train`.
- Old local `cellpose_cyto` outputs are legacy only and should not be used as the main future Cellpose comparator.

Environment:

```text
/backup/taotao_work/venvs/cellpose311
cellpose==3.1.1.1
torch==2.5.1+cu121
```

Scripts:

```text
scripts/cellcosmos_repro_prepare.py
scripts/run_server_cellpose_repro.sh
scripts/run_server_cellpose_cyto3_eval.sh
scripts/run_cellpose_manifest.py
scripts/eval_label_dir.py
scripts/render_instance_overlays.py
```

As of 2026-05-01 02:05 CST:

- `baseline_cellpose_iid` tmux session is running on GPU0.
- `baseline_cellpose_pannuke` tmux session is running on GPU1.
- Both jobs are training 500 epochs from cyto3 initialization.
- After each training job completes, the wrapper should copy checkpoints, run inference on its configured test split(s), render overlays, compute PQ/AJI/F1, and write a run manifest.
- Server GPUs are occupied by these baseline trainings; do SAM-Cell optimization locally unless remote idle capacity appears.

As of 2026-05-01 04:55 CST:

- `baseline_cellpose_iid` is still running; latest observed log was epoch 440/500.
- `baseline_cellpose_pannuke` finished training and is running wrapper inference on `far_ood_test`; latest observed progress was 475/1795.
- `setup_stardist_env_v2` is running after a failed first attempt caused by server default `python3` being too old for TensorFlow 2.15. The setup script now defaults to `/backup/taotao_work/venvs/nnunet/bin/python`.
- Queued tmux sessions are active:
  - `baseline_cellpose_official_cyto3`: waits for `baseline_cellpose_pannuke`, then runs official cyto3 inference/eval/overlays.
  - `baseline_stardist_iid`: waits for StarDist env, IID Cellpose, and official cyto3, then trains/evaluates StarDist IID.
  - `baseline_stardist_pannuke`: waits for StarDist env, PanNuke Cellpose, and official cyto3, then trains/evaluates StarDist PanNuke.
  - `baseline_sam2_automatic`: waits for official cyto3 and both StarDist sessions, then runs native SAM2 automatic-mask inference/eval/overlays.

New baseline scripts added on 2026-05-01:

```text
scripts/setup_server_stardist_env.sh
scripts/train_stardist_manifest.py
scripts/run_stardist_manifest.py
scripts/run_server_stardist_repro.sh
scripts/run_sam2_automatic_manifest.py
scripts/run_server_sam2_automatic_eval.sh
```

As of 2026-05-01 15:47 CST:

- Cellpose baseline training and official cyto3 inference are complete.
- Key Cellpose results:
  - `cellpose_iid_finetune_cyto3/iid_val`: SOURCE_MACRO PQ 0.6242, ALL PQ 0.6092.
  - `cellpose_official_cyto3/iid_val`: SOURCE_MACRO PQ 0.5314; strong on Cellpose/DSB/LiveCELL, weak on PanNuke/TissueNet.
  - `cellpose_pannuke_finetune_cyto3/pannuke_core_test`: ALL PQ 0.6207.
  - `cellpose_pannuke_finetune_cyto3/far_ood_test`: SOURCE_MACRO PQ 0.0577, showing severe domain shift.
- StarDist PanNuke baseline is complete:
  - `stardist_pannuke/pannuke_core_test`: ALL PQ 0.6261.
  - `stardist_pannuke/far_ood_test`: SOURCE_MACRO PQ 0.0679, also severe domain shift.
- StarDist IID is still training in tmux `baseline_stardist_iid` on GPU0.
- Native SAM2 automatic-mask baseline is running in tmux `baseline_sam2_automatic` on GPU1.
- SAM2 automatic required two server fixes:
  - `run_sam2_automatic_manifest.py` creates `sam2_configs/__init__.py` if missing.
  - `run_server_sam2_automatic_eval.sh` now passes `--min_mask_region_area 0` because SAM2's connected-components C extension requires a newer GLIBC than the server provides. Output-level `--label_min_area 10` is still applied.

### Local SAM-Cell Optimization Notes

As of 2026-05-01 15:47 CST:

- Rejected `proposal_ranker_cellpose_gate_v2` as a mainline improvement.
  - It added extended morphology/probability features, but on the 50 Cellpose subset `ranked_label_map_nonoverlap` PQ dropped from 0.5993 to 0.5838.
  - `ranked_merged` oracle PQ also slightly dropped from 0.6049 to 0.6019.
  - Keep the artifact for ablation only: `outputs/proposal_ranker_cellpose_gate_v2`.
- Proposal ranker threshold sweep on 50 Cellpose images found a small optimum at threshold 0.50:
  - threshold 0.45 proposal PQ 0.5993.
  - threshold 0.50 proposal PQ 0.6016.
  - Full 50-image evaluation at threshold 0.50 final PQ 0.5935 versus previous 0.45 final PQ 0.5919.
  - This is a small precision/recall tradeoff, not a structural breakthrough.
- Updated `configs/sam_cell_multi_expert_cellpose_gate.yaml` proposal ranker `keep_threshold` from 0.45 to 0.50.
- Performance fixes added:
  - `sam_cell/proposals/regions.py::proposal_iou` now computes IoU only in bbox intersection, avoiding full-image logical operations for every duplicate-merge pair.
  - `sam_cell/proposals/internal_selector.py::proposal_features` now avoids allocating external-union masks when no external proposals are present.
  - Extended ranker features are gated by `feature_version >= 2`; old rankers keep the original lightweight features.
- New/updated diagnostic utilities:
  - `scripts/sweep_proposal_ranker_thresholds.py` sweeps ranker thresholds without rerunning SAM2 and writes `per_image.partial.csv` incrementally.
  - `scripts/eval_devset.py` supports `--proposal_ranker_keep_threshold`.
  - `scripts/proposal_oracle_diagnosis.py` supports `--proposal_ranker_keep_threshold`.

### Dataset622_SAMCellCellposeStyleBoundary

Purpose: train a stronger Cellpose-style boundary/interior semantic expert to replace the weak old Dataset512 foreground-only Cellpose expert in the multi-expert SAM-Cell pipeline.

Decision:

- Do not discard Dataset621 universal boundary expert; it remains the broad-domain expert.
- Dataset622 is a Cellpose-focused expert, not the final universal model.
- Default training data is only Cellpose-source images from `CellCosmos_Benchmark`, excluding the frozen `eval_250.csv` benchmark names.
- Label format matches Dataset621:
  - 0 background
  - 1 cell/interior
  - 2 boundary

Builder and trainer:

```text
scripts/build_cellpose_style_boundary_nnunet.py
scripts/run_server_cellpose_style_nnunet.sh
```

Remote raw/results target:

```text
/backup/taotao_work/nnUNet_raw/Dataset622_SAMCellCellposeStyleBoundary
/backup/taotao_work/nnUNet_results/Dataset622_SAMCellCellposeStyleBoundary/nnUNetTrainer__nnUNetPlans__2d
```

As of 2026-05-01 20:30 CST:

- Server data root confirmed: `/backup/taotao_data/CellCosmos_Benchmark`.
- Full available Cellpose-source images: 540.
- Excluded benchmark names: 250 total from `eval_250.csv`, including 50 Cellpose-source images.
- Dataset622 written cases: 490 Cellpose-source images.
- nnU-Net plan/preprocess completed successfully.
- Training session started:
  - tmux: `samcell_cellpose_style_train`
  - log root: `/backup/taotao_work/logs/cellpose_style_boundary_20260501_202724`
  - fold0 running on GPU0
  - fold1 running on GPU1
- After fold0/fold1 finish, the wrapper will train fold2/fold3, then fold4.

As of 2026-05-03 02:35 CST:

- Dataset622 five-fold training is complete; no active tmux output was observed for `samcell_cellpose_style_train`.
- Server GPUs were idle at check time.
- Log root:

```text
/backup/taotao_work/logs/cellpose_style_boundary_20260501_202724
```

Five-fold final validation summary:

| fold | final epoch | Mean Validation Dice | best checkpoint time | final checkpoint time |
|---|---:|---:|---|---|
| 0 | 999 | 0.6847 | 2026-05-01 22:16 CST | 2026-05-02 03:06 CST |
| 1 | 999 | 0.6963 | 2026-05-01 21:52 CST | 2026-05-02 03:13 CST |
| 2 | 999 | 0.6804 | 2026-05-02 04:41 CST | 2026-05-02 09:50 CST |
| 3 | 999 | 0.6777 | 2026-05-02 04:35 CST | 2026-05-02 09:59 CST |
| 4 | 999 | 0.6988 | 2026-05-02 11:01 CST | 2026-05-02 16:36 CST |

Checkpoint root:

```text
/backup/taotao_work/nnUNet_results/Dataset622_SAMCellCellposeStyleBoundary/nnUNetTrainer__nnUNetPlans__2d
```

All folds have both `checkpoint_best.pth` and `checkpoint_final.pth`.

Near-term evaluation plan:

- Dataset622 proposal diagnostics were completed on the 50 held-out Cellpose images.
- Dataset622 should not replace the current Dataset512 Cellpose-style branch in the production multi-expert config.
- Next optimization should move beyond another Dataset622 parameter sweep: consider a stronger non-nnU-Net proposal front-end, or run an explicit external-proposal upper-bound experiment with clear fairness caveats.

Dataset622 diagnostic artifacts:

```text
/backup/taotao_work/sam_cell/configs/sam_cell_multi_expert_cellpose_gate_dataset622_workstation2.yaml
/backup/taotao_work/sam_cell/configs/sam_cell_multi_expert_cellpose_gate_dataset622_ranked_workstation2.yaml
/backup/taotao_work/sam_cell/configs/sam_cell_multi_expert_cellpose_gate_dataset622_interior_workstation2.yaml
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260501/proposal_oracle_dataset622_cellpose50_unranked
/backup/taotao_work/sam_cell/outputs/proposal_ranker_cellpose_gate_dataset622_cellposeonly
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260501/proposal_oracle_dataset622_cellpose50_ranked
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260501/proposal_ranker_threshold_sweep_dataset622_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260501/proposal_generation_sweep_dataset622_cellpose50_stage1
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260501/proposal_oracle_dataset622_interior_cellpose50_unranked
```

Dataset622 Cellpose-source 50-image diagnostic summary:

| variant | key setting | proposal PQ | recall | precision | note |
|---|---|---:|---:|---:|---|
| Dataset622 unranked | foreground `[1,2]`, no ranker | 0.4941 | 0.7407 | 0.5541 | too many FP/duplicates after non-overlap label map |
| Dataset622 ranked | Cellpose-only ranker, threshold 0.50 | 0.5791 | 0.7257 | 0.7524 | below old current config |
| Dataset622 threshold sweep | best threshold/generation stage1 | 0.5812 | 0.7290 | 0.7541 | best setting used single threshold `0.5`, ranker `0.45` |
| Dataset622 interior-only | foreground `[1]`, no ranker | 0.3368 | 0.6968 | 0.3596 | boundary excluded from foreground is worse |

Cellpose-only Dataset622 ranker report:

| split | n proposals | positives | AP | ROC-AUC | F1 at 0.50 |
|---|---:|---:|---:|---:|---:|
| train | 3434 | 1999 | 0.9945 | 0.9927 | 0.9738 |
| val | 2561 | 1626 | 0.9468 | 0.9358 | 0.9030 |

Comparison to old current strongest Dataset512+Dataset621 source-gated config:

- Old 50 Cellpose proposal diagnosis had `ranked_label_map_nonoverlap` PQ 0.5993 and `ranked_merged` oracle PQ 0.6049.
- Dataset622 best observed proposal PQ was 0.5812, and ranked merged oracle PQ was 0.5875.
- Conclusion: Dataset622 creates stronger-looking Cellpose-style semantic proposals than old Dataset512 in isolation, but its proposal distribution is harder to rank/merge and does not improve the final bottleneck.

Dataset621 training session:

```text
tmux session: samcell_universal_train
monitor session: samcell_universal_monitor
monitor file: /backup/taotao_work/logs/training_monitor_universal/latest_status.txt
```

As of 2026-04-30 15:24 CST:

- fold0 complete
- fold1 complete
- fold2 complete
- fold3 complete
- fold4 complete
- all Dataset621 folds have `checkpoint_best.pth` and `checkpoint_final.pth`
- remote GPUs are idle
- all five folds have been synced locally to `/home/taotao/nnUNet/nnUNetFrame/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d`

Latest direct fold status:

| fold | status | final epoch / current epoch | final pseudo dice or latest pseudo dice | checkpoint status |
|---|---|---:|---|---|
| 0 | complete | 999 | `[0.8560, 0.5815]` | best + final |
| 1 | complete | 999 | `[0.8541, 0.5705]` | best + final |
| 2 | complete | 999 | `[0.8518, 0.5757]` | best + final |
| 3 | complete | 999 | `[0.8533, 0.5813]` | best + final |
| 4 | complete | 999 | `[0.8529, 0.5784]` | best + final |

## Completed Evaluations

Auto-eval script:

```text
scripts/auto_eval_universal_fold01.sh
```

Report:

```text
outputs/auto_eval_universal_fold01/report.md
```

Evaluation set:

```text
outputs/benchmark_splits_large/eval_25_balanced.csv
```

Cellpose baseline predictions:

```text
outputs/benchmark_splits_large/cellpose_cyto
```

Dataset621 fold0+fold1 best vs Cellpose, 25 balanced images:

| source | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate |
|---|---:|---:|---:|---:|
| ALL | 0.5449 | 0.4508 | +0.0941 | 0.7600 |
| cellpose | 0.4327 | 0.7103 | -0.2776 | 0.0000 |
| dsb2018 | 0.8762 | 0.6844 | +0.1918 | 1.0000 |
| livecell | 0.5065 | 0.3573 | +0.1492 | 1.0000 |
| pannuke | 0.4577 | 0.1510 | +0.3067 | 1.0000 |
| tissuenet | 0.4514 | 0.3508 | +0.1005 | 0.8000 |

Dataset621 fold0+fold1 final vs best:

- final ALL PQ 0.5509
- best ALL PQ 0.5449
- final is slightly better overall on the 25-image check, but best remains safer as the default checkpoint policy unless full evaluation confirms final is consistently better.

Dataset621 best vs Dataset620 best:

- ALL: +0.0094 PQ
- cellpose: +0.0786 PQ
- livecell: +0.0755 PQ
- pannuke: -0.0569 PQ
- tissuenet: -0.0537 PQ

Interpretation:

- Rebalancing helped Cellpose and LIVECell.
- Cellpose is still far below Cellpose baseline.
- PanNuke/TissueNet dropped slightly relative to Dataset620 fold01.
- Dataset621 is not yet sufficient as a single universal semantic front-end.

### Dataset621 five-fold 25-image evaluation

Configs:

```text
configs/sam_cell_universal_boundary.yaml
configs/sam_cell_universal_boundary_final.yaml
```

Outputs:

```text
outputs/benchmark_splits_large/sam_universal_5fold_best_eval25
outputs/benchmark_splits_large/sam_universal_5fold_final_eval25
outputs/benchmark_splits_large/compare_universal_5fold_best_eval25
outputs/benchmark_splits_large/compare_universal_5fold_final_eval25
```

Dataset621 five-fold best vs Cellpose, 25 balanced images:

| source | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate |
|---|---:|---:|---:|---:|
| ALL | 0.5603 | 0.4508 | +0.1095 | 0.7600 |
| cellpose | 0.4580 | 0.7103 | -0.2524 | 0.0000 |
| dsb2018 | 0.8762 | 0.6844 | +0.1917 | 1.0000 |
| livecell | 0.5084 | 0.3573 | +0.1512 | 1.0000 |
| pannuke | 0.4857 | 0.1510 | +0.3346 | 1.0000 |
| tissuenet | 0.4733 | 0.3508 | +0.1225 | 0.8000 |

Dataset621 five-fold final vs Cellpose, 25 balanced images:

| source | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate |
|---|---:|---:|---:|---:|
| ALL | 0.5717 | 0.4508 | +0.1209 | 0.8000 |
| cellpose | 0.4580 | 0.7103 | -0.2523 | 0.0000 |
| dsb2018 | 0.8650 | 0.6844 | +0.1805 | 1.0000 |
| livecell | 0.5271 | 0.3573 | +0.1698 | 1.0000 |
| pannuke | 0.4926 | 0.1510 | +0.3415 | 1.0000 |
| tissuenet | 0.5161 | 0.3508 | +0.1652 | 1.0000 |

Decision:

- Use five-fold `checkpoint_final.pth` as the current Dataset621 default for PQ-oriented evaluation.
- `checkpoint_best.pth` has slightly higher AJI on the 25-image set, but final has higher PQ and win rate.

### Dataset621 five-fold final 250-image evaluation

Evaluation set:

```text
outputs/benchmark_splits_large/eval_250.csv
```

Outputs:

```text
outputs/benchmark_splits_large/sam_universal_5fold_final_eval250
outputs/benchmark_splits_large/compare_universal_5fold_final_eval250
```

Dataset621 five-fold final vs Cellpose, 250 balanced images:

| source | n | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate | SAM-Cell AJI | Cellpose AJI |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | 250 | 0.5778 | 0.4592 | +0.1186 | 0.7300 | 0.5739 | 0.4347 |
| cellpose | 50 | 0.5263 | 0.7136 | -0.1873 | 0.1000 | 0.5541 | 0.7315 |
| dsb2018 | 50 | 0.7472 | 0.5677 | +0.1795 | 0.9000 | 0.7559 | 0.5682 |
| livecell | 50 | 0.5847 | 0.4668 | +0.1179 | 0.8600 | 0.5410 | 0.3993 |
| pannuke | 50 | 0.5445 | 0.2018 | +0.3427 | 0.9600 | 0.5666 | 0.1728 |
| tissuenet | 50 | 0.4864 | 0.3463 | +0.1401 | 0.8400 | 0.4518 | 0.3015 |

Interpretation:

- The 250-image result supports broad cross-domain advantage over Cellpose on this benchmark.
- The advantage is not uniform: Cellpose-style images remain a clear weakness.
- The next optimization should not be another simple Dataset621 retrain. It should address source/expert mismatch.

## Next Decisions

Implement dual-semantic/adaptive fusion:

- old Cellpose-specific semantic prior for Cellpose-like images or Cellpose-like candidates
- Dataset621 universal boundary prior for broad non-Cellpose domains
- combine through proposal-level fusion, not hard image-level source classification

Scientific reason:

- Hard "source classifier" is brittle for unseen images.
- Proposal-level multi-expert fusion is more robust: run multiple semantic proposal generators, then use SAM2 score, semantic support, coarse/refined IoU, area growth, and NMS to select candidates.
- The 250-image benchmark already shows the universal prior is good enough outside Cellpose-style images; the largest remaining gain is recovering Cellpose-source performance without sacrificing non-Cellpose domains.

## Multi-Expert Implementation Status

As of 2026-04-30 18:23 CST, the first engineering pass for dual-semantic proposal fusion is implemented.

New behavior:

- `SAMCellConfig` supports `semantic_experts`, a list of nnU-Net semantic experts.
- `SAMCellConfig` supports `proposal_ranker`, a proposal-level selector model.
- `SAMCellPipeline` can instantiate multiple `NnUNetSemanticPredictor` objects, cache each expert separately, generate source-tagged proposals, merge them once, and use the proposal's own foreground probability for crop-level semantic support.
- `InstanceProposal` now carries `rank_score`.
- `eval_devset.py` records `universal_boundary_selected`, `cellpose_style_selected`, `external_selected`, `coarse_selected`, and `ranked_proposals`.

New configs:

```text
configs/sam_cell_multi_expert_dual.yaml
configs/sam_cell_multi_expert_dual_ranked.yaml
```

New scripts:

```text
scripts/diagnose_instance_errors.py
scripts/train_proposal_ranker.py
```

New operating note:

```text
docs/multi_expert_dual_plan.md
```

Validation:

- Full local tests passed: `13 passed in 1.28s`.
- `py_compile` passed for package and scripts.
- Real dual-expert smoke inference completed on one image:
  - output: `outputs/multi_expert/smoke_dual_limit1`
  - image: `cellpose_434.png`
  - proposals: 70
  - final PQ: 0.6251
  - selected proposal sources: 69 universal boundary, 1 cellpose-style
- Proposal ranker smoke training completed on 2 Cellpose images:
  - output: `outputs/proposal_ranker_dual_smoke`
  - samples: 196
  - positives: 163
  - negatives: 33

Important caveat:

- The smoke ranker is not a final model. Train `outputs/proposal_ranker_dual/proposal_ranker.joblib` using `dev_tune.csv` and validate on `dev_holdout.csv` before using `configs/sam_cell_multi_expert_dual_ranked.yaml` for serious evaluation.

## Multi-Expert Evaluation Results

Formal proposal ranker:

```text
outputs/proposal_ranker_dual/proposal_ranker.joblib
```

Training split:

```text
outputs/benchmark_splits_selector20/dev_tune.csv
```

Validation split:

```text
outputs/benchmark_splits_selector20/dev_holdout.csv
```

Ranker feature/result summary:

- train proposals: 14417
- train positives: 9214
- train negatives: 5203
- validation proposals: 9707
- validation AP: 0.9115
- validation ROC-AUC: 0.8655
- validation F1 at threshold 0.45: 0.8723

### Dual expert ranked on all sources

Config:

```text
configs/sam_cell_multi_expert_dual_ranked.yaml
```

25-image result:

| source | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate |
|---|---:|---:|---:|---:|
| ALL | 0.5679 | 0.4508 | +0.1171 | 0.6800 |
| cellpose | 0.5852 | 0.7103 | -0.1252 | 0.2000 |
| dsb2018 | 0.6791 | 0.6844 | -0.0053 | 0.2000 |
| livecell | 0.5230 | 0.3573 | +0.1657 | 1.0000 |
| pannuke | 0.5326 | 0.1510 | +0.3816 | 1.0000 |
| tissuenet | 0.5198 | 0.3508 | +0.1689 | 1.0000 |

Interpretation:

- Cellpose-source improved strongly.
- DSB2018 collapsed because the Cellpose-style expert/ranker retained inappropriate candidates.
- Global ranker threshold search did not fix the source mismatch. Best searched threshold was 0.55 with ALL PQ 0.5692, still below universal-only.

### Source-prefix gated multi-expert

Config:

```text
configs/sam_cell_multi_expert_cellpose_gate.yaml
```

Behavior:

- `cellpose_style` semantic expert is enabled only for image IDs whose inferred source is `cellpose`.
- proposal ranker is enabled only for `cellpose`.
- other known benchmark sources use Dataset621 universal-only behavior.

This is an interim source-prefix oracle gate for benchmarking and debugging. It should not be presented as the final unknown-image generalization mechanism.

25-image result:

| source | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate |
|---|---:|---:|---:|---:|
| ALL | 0.5967 | 0.4508 | +0.1459 | 0.8400 |
| cellpose | 0.5852 | 0.7103 | -0.1252 | 0.2000 |
| dsb2018 | 0.8566 | 0.6844 | +0.1722 | 1.0000 |
| livecell | 0.5272 | 0.3573 | +0.1699 | 1.0000 |
| pannuke | 0.4955 | 0.1510 | +0.3445 | 1.0000 |
| tissuenet | 0.5191 | 0.3508 | +0.1683 | 1.0000 |

250-image result:

| source | n | SAM-Cell PQ | Cellpose PQ | Delta PQ | Win Rate | SAM-Cell AJI | Cellpose AJI |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | 250 | 0.5903 | 0.4592 | +0.1311 | 0.7500 | 0.5816 | 0.4347 |
| cellpose | 50 | 0.5905 | 0.7136 | -0.1231 | 0.1800 | 0.5929 | 0.7315 |
| dsb2018 | 50 | 0.7449 | 0.5677 | +0.1773 | 0.9000 | 0.7552 | 0.5682 |
| livecell | 50 | 0.5848 | 0.4668 | +0.1179 | 0.8600 | 0.5410 | 0.3993 |
| pannuke | 50 | 0.5441 | 0.2018 | +0.3422 | 0.9600 | 0.5666 | 0.1728 |
| tissuenet | 50 | 0.4873 | 0.3463 | +0.1410 | 0.8400 | 0.4521 | 0.3015 |

Comparison to Dataset621 universal-only on 250:

- ALL PQ: 0.5903 vs 0.5778, improvement +0.0125
- Cellpose-source PQ: 0.5905 vs 0.5263, improvement +0.0642
- Non-Cellpose domains are effectively preserved.

Decision:

- `configs/sam_cell_multi_expert_cellpose_gate.yaml` is the current strongest benchmark config.
- It does not meet the next target yet: ALL PQ >= 0.62 and Cellpose-source PQ >= 0.62.
- The next scientific step is to replace source-prefix gating with image-style/domain confidence and improve Cellpose-style proposal generation to reduce remaining Cellpose false negatives and split/merge errors.

Additional threshold check:

- Low-threshold search on 25 images suggested `proposal_ranker.keep_threshold=0.35` could improve the small set:
  - 25-image ALL PQ 0.6003
  - 25-image Cellpose-source PQ 0.6030
- The same threshold did not generalize to the 50 Cellpose images in `eval_250`:
  - 50-image Cellpose-source PQ 0.5865
  - projected 250-image ALL PQ 0.5895
- Therefore keep `configs/sam_cell_multi_expert_cellpose_gate.yaml` at threshold 0.45.
- Conclusion: the next gain is not a simple global threshold; remaining Cellpose errors need better proposal generation/selection features.

## SAM-Cell Optimization 2026-05-01

Experiment root:

```text
outputs/samcell_optimization_20260501
```

New diagnostic script:

```text
scripts/proposal_oracle_diagnosis.py
```

Purpose:

- Separate proposal recall, ranker filtering, non-overlap proposal label maps, and cached final SAM-Cell output.
- Report oracle recall/PQ upper bounds without rerunning SAM2.

Current strongest config diagnosed:

```text
configs/sam_cell_multi_expert_cellpose_gate.yaml
outputs/samcell_optimization_20260501/proposal_oracle_cellpose_50
```

Cellpose-source 50-image proposal diagnosis:

| stage | GT recall@0.5 | oracle PQ | oracle no-FP PQ | proposal n | notes |
|---|---:|---:|---:|---:|---|
| raw expert unranked | 0.8096 | 0.4690 | 0.7322 | 181.62 | high recall but many FP/duplicates |
| merged unranked | 0.8090 | 0.5274 | 0.7295 | 158.08 | duplicate merge helps |
| ranked merged | 0.7571 | 0.6049 | 0.6969 | 105.72 | current best proposal tradeoff |
| ranked non-overlap label map | 0.7477 | 0.5993 | 0.5993 | 103.28 | coarse proposal map is close to final |
| final cached | 0.7380 | 0.5905 | 0.5905 | 103.62 | SAM2/coarse selection slightly below proposal map |

Source-specific interpretation:

- `universal_boundary` raw recall is 0.7511 on Cellpose-source images.
- `cellpose_style` raw recall is only 0.4188, but it still contributes selected candidates in the current combined ranker; do not assume the old Cellpose-style expert is independently strong.
- The current bottleneck is not semantic Dice alone. It is the proposal/ranker tradeoff: raw proposal recall can reach about 0.81, but robust final PQ is around 0.59 because extra proposals create FP/merge pressure.

A coarse-only Cellpose-source check:

```text
outputs/samcell_optimization_20260501/sam_cellpose_gate_coarse_cellpose50
outputs/samcell_optimization_20260501/compare_gate_coarse_cellpose50
```

Result:

- Cellpose-source PQ 0.5919 with SAM2 disabled, versus 0.5905 for current cached final.
- This is only +0.0014 PQ, so disabling SAM2 is not a meaningful improvement.

Rejected local optimization attempts:

- `configs/sam_cell_multi_expert_cellpose_aggressive_universal*.yaml`: adding a second aggressive universal proposal branch increased runtime sharply on some Cellpose images and was abandoned.
- `configs/sam_cell_universal_cellpose_ranked.yaml`: universal-only Cellpose ranker had lower proposal oracle PQ than the current multi-expert gate (`ranked_merged` oracle PQ 0.5887 vs 0.6049), so it is not a new default.

Current decision:

- Keep `configs/sam_cell_multi_expert_cellpose_gate.yaml` as the strongest local SAM-Cell config for now.
- Next optimization should not add broad extra proposal branches. Focus on more selective proposal ranking/merge features or a real image-style gate that does not depend on filename source prefixes.

## SAM-Cell Optimization 2026-05-03 Watershed Repair

Purpose:

- Test whether EDT/watershed postprocessing can improve Cellpose-style proposal quality without retraining nnU-Net.
- Keep this as proposal/front-end optimization; do not treat it as a new universal claim until 250-image and non-Cellpose checks are complete.

Implementation:

```text
sam_cell/proposals/repair.py
sam_cell/proposals/watershed.py
sam_cell/pipeline.py
scripts/proposal_oracle_diagnosis.py
scripts/eval_devset.py
scripts/run_server_proposal_diagnosis.sh
```

New configs:

```text
configs/sam_cell_multi_expert_cellpose_gate_adaptive_selector.yaml
configs/sam_cell_multi_expert_cellpose_gate_adaptive_selector_workstation2.yaml
configs/sam_cell_multi_expert_cellpose_gate_repair_v1_workstation2.yaml
```

Recommended candidate:

- Use `adaptive_hybrid` watershed markers plus ranker-aware proposal set selector.
- Disable split repair.
- Apply this only through `source_overrides.cellpose` in the recommended configs; non-Cellpose sources keep the previous strongest behavior.

Rejected component:

- Split repair increases recall but creates too many extra false-positive/duplicate proposals.
- Do not enable `proposal_repair.split_enabled` as a default without a better child-proposal ranker.

Server artifacts:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_watershed_repair
/backup/taotao_work/sam_cell/configs/sam_cell_multi_expert_cellpose_gate_adaptive_selector_workstation2.yaml
```

Server setup note:

- Synced missing old Cellpose expert to:

```text
/backup/taotao_work/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d
```

- Synced ranker to:

```text
/backup/taotao_work/sam_cell/outputs/proposal_ranker_dual/proposal_ranker.joblib
```

Validation:

- Local `py_compile` passed.
- Local pytest is still blocked by the known local `skimage`/`numpy` ABI issue.
- Server `py_compile` passed.
- Server `pytest` is not installed in `/backup/taotao_work/venvs/nnunet`; manual toy tests for adaptive markers, split repair, and set selector passed.
- sklearn issued `InconsistentVersionWarning` when loading the ranker because the ranker was trained with sklearn 1.7.2 and server env has 1.8.0. Results were still computed, but the ranker should eventually be reserialized or retrained in the server env.

Cellpose-source 50-image proposal oracle:

| variant | ranked merged PQ | ranked merged recall | ranked proposals | label-map PQ | label-map recall |
|---|---:|---:|---:|---:|---:|
| baseline | 0.6078 | 0.7438 | 101.3 | 0.6018 | 0.7353 |
| adaptive only | 0.6296 | 0.7642 | 101.6 | 0.6243 | 0.7550 |
| selector only | 0.6290 | 0.7322 | 90.0 | 0.6289 | 0.7321 |
| adaptive + selector, no split | 0.6493 | 0.7540 | 92.0 | 0.6491 | 0.7539 |
| split only | 0.5991 | 0.8014 | 121.2 | 0.5922 | 0.7837 |
| full repair v1 with split | 0.6218 | 0.7827 | 107.8 | 0.6210 | 0.7817 |

Cellpose-source 50-image final SAM2 evaluation:

| variant | final PQ | final AJI | final F1 | precision | recall | pred n | note |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline current strongest | 0.5936 | 0.5916 | 0.7193 | 0.7495 | 0.7263 | 99.8 | old Dataset512 + Dataset621 + ranker |
| adaptive + selector, no split | 0.6495 | 0.6319 | 0.7855 | 0.8420 | 0.7543 | 92.0 | best current Cellpose-style front-end candidate |

Decision:

- `configs/sam_cell_multi_expert_cellpose_gate_adaptive_selector.yaml` is the current best small-eval SAM-Cell candidate for Cellpose-style recovery.
- It is not yet promoted as the final all-source default until a 250-image evaluation confirms non-Cellpose sources are preserved.
- Next action: run 250-image evaluation for this candidate, then compare against official Cellpose cyto3 and finetuned Cellpose outputs in the thesis baseline table.

### 2026-05-03 follow-up: pipeline override fix, eval250, and source-free gate prototype

Engineering fix:

- `SAMCellPipeline.infer()` now applies and restores `cfg.source_overrides` internally based on `infer_dataset_source(image_id)`.
- `scripts/eval_devset.py` no longer manually applies source overrides before `pipeline.infer()`.
- Gate 0 consistency check passed on `cellpose_434.png`: CLI and `eval_devset.py` produced identical label maps (`diff_pixels=0`, final instances 30).

Artifacts:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_watershed_repair/source_override_gate_eval_smoke
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_watershed_repair/source_override_gate_cli_smoke
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_watershed_repair/final_adaptive_selector_eval250
```

250-image final SAM2 evaluation:

| source | n | candidate PQ | old strongest PQ | delta | candidate AJI | note |
|---|---:|---:|---:|---:|---:|---|
| ALL | 250 | 0.6023 | 0.5903 | +0.0120 | 0.5893 | new best eval250 result |
| cellpose | 50 | 0.6495 | 0.5905 | +0.0590 | 0.6319 | target `>=0.62` achieved |
| dsb2018 | 50 | 0.7445 | 0.7449 | -0.0004 | 0.7550 | preserved |
| livecell | 50 | 0.5851 | 0.5848 | +0.0003 | 0.5411 | preserved |
| pannuke | 50 | 0.5449 | 0.5441 | +0.0008 | 0.5666 | preserved |
| tissuenet | 50 | 0.4875 | 0.4873 | +0.0002 | 0.4521 | preserved |

Interpretation:

- `configs/sam_cell_multi_expert_cellpose_gate_adaptive_selector.yaml` is now the strongest source-prefix gated SAM-Cell config on eval250.
- It crosses the Cellpose-source internal target of PQ `>=0.62`, but ALL PQ is still below the previous next target `>=0.62`.
- Non-Cellpose performance is effectively unchanged because the adaptive selector is still gated to Cellpose-style images.
- Cellpose-source is still below the old Cellpose baseline on eval250 (`0.7136`), so do not claim Cellpose-style superiority yet.

Runtime note:

- LIVECell and TissueNet evaluation are substantially slower than Cellpose/DSB/PanNuke; the 250-image run completed but exposed a runtime bottleneck for high-instance or large images.

Source-free image-style gate prototype:

```text
scripts/train_image_style_gate.py
/backup/taotao_work/sam_cell/outputs/image_style_gate_v1_20260503
```

Training/evaluation:

- Train split: `outputs/benchmark_splits_selector20/dev_tune.csv` (100 images).
- Validation split: `outputs/benchmark_splits_selector20/dev_holdout.csv` (50 images).
- Diagnostic eval split: `outputs/benchmark_splits_large/eval_250.csv` (250 images).
- Positive class: `source == cellpose`.
- Features: image-only intensity, color, gradient, threshold, and connected-component statistics. File name/source is not used as a feature.

Style gate result:

| split | n | positives | precision | recall | F1 | AP | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 100 | 20 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| val | 50 | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| eval250 | 250 | 50 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Eval250 source scores:

| source | mean score | positive rate |
|---|---:|---:|
| cellpose | 0.9353 | 1.0000 |
| dsb2018 | 0.0149 | 0.0000 |
| livecell | 0.0014 | 0.0000 |
| pannuke | 0.0014 | 0.0000 |
| tissuenet | 0.0559 | 0.0000 |

Decision:

- Source-free gating is feasible on the current benchmark; the next implementation should integrate `image_style_gate_v1` into the pipeline as an optional routing mechanism.
- Until that integration is done and tested, the production config remains source-prefix gated and should be described as such.
- The ranker sklearn warning is resolved on the server: `outputs/proposal_ranker_dual/proposal_ranker.joblib` was backed up to `proposal_ranker.joblib.sklearn172_backup`, reserialized under sklearn 1.8.0, and reloaded with `InconsistentVersionWarning` promoted to error without warning.

### 2026-05-03 follow-up: Cellpose-first v2 and global adaptive selector

Purpose:

- Continue optimizing the Cellpose-source bottleneck first.
- Then test whether the same proposal strategy helps or hurts non-Cellpose sources.

New local/server files:

```text
sam_cell/proposals/repair.py
sam_cell/config.py
scripts/sweep_cellpose_proposal_v2.py
scripts/classify_proposal_failures.py
scripts/run_server_cellpose_proposal_v2_sweep.sh
configs/sam_cell_multi_expert_cellpose_gate_adaptive_selector_v2_workstation2.yaml
configs/sam_cell_global_adaptive_selector_v2_workstation2.yaml
```

Implementation notes:

- `ProposalRepairConfig` now has conservative split-v2 guard fields and `split_keep_parent`, but split remains disabled in the accepted v2 configs.
- `classify_proposal_failures.py` classifies proposal/final failures from `proposal_oracle_diagnosis.py` outputs.
- `sweep_cellpose_proposal_v2.py` runs proposal-only sweeps over marker, h-maxima, ranker threshold, duplicate IoU, and selector settings.

Diagnostics:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/classify_adaptive_selector_cellpose50
```

Adaptive selector Cellpose50 failure classification:

| error type | n | fraction |
|---|---:|---:|
| merge_lost_recall | 26 | 0.52 |
| semantic_or_marker_miss | 17 | 0.34 |
| balanced_low_quality | 4 | 0.08 |
| ranker_filtered_true_cells | 3 | 0.06 |

Cellpose-only search artifacts:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/sweep_no_split_worst12
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/sweep_no_split_cellpose50_top8
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/final_v2_cellpose50
```

Best Cellpose v2 setting:

- `marker_method: adaptive_hybrid`
- `h_maxima_values: [0.06, 0.1, 0.14]`
- `min_distance_factor: 0.40`
- `peak_threshold_rel: 0.18`
- `proposal_ranker.keep_threshold: 0.45`
- `set_selector_iou_threshold: 0.55`
- `set_selector_containment_threshold: 0.85`
- `split_enabled: false`

Cellpose50 result:

| config | final PQ | final AJI | precision | recall | proposal PQ |
|---|---:|---:|---:|---:|---:|
| previous adaptive selector | 0.6495 | 0.6319 | 0.8420 | 0.7543 | 0.6491 |
| Cellpose v2 | 0.6602 | 0.6503 | 0.8304 | 0.7868 | 0.6598 |

Cross-source proposal-only test:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/sweep_v2_strategy_all_sources_eval250
```

The v2 proposal strategy improved proposal PQ on LiveCELL, PanNuke, and especially TissueNet, with only a very small DSB2018 drop.

Full global v2 final evaluation:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/final_global_v2_eval250
```

| source | n | global v2 final PQ | previous final PQ | delta | global v2 AJI |
|---|---:|---:|---:|---:|---:|
| ALL | 250 | 0.6263 | 0.6023 | +0.0240 | 0.6235 |
| cellpose | 50 | 0.6602 | 0.6495 | +0.0106 | 0.6503 |
| dsb2018 | 50 | 0.7417 | 0.7445 | -0.0028 | 0.7608 |
| livecell | 50 | 0.6051 | 0.5851 | +0.0201 | 0.5829 |
| pannuke | 50 | 0.5497 | 0.5449 | +0.0048 | 0.5738 |
| tissuenet | 50 | 0.5746 | 0.4875 | +0.0872 | 0.5495 |

Decision:

- `configs/sam_cell_global_adaptive_selector_v2_workstation2.yaml` is the new strongest eval250 candidate.
- It crosses the previous internal ALL target `PQ >= 0.62`.
- It should replace the source-prefix-only adaptive selector for the next optimization/evaluation round.
- Remaining weakness: Cellpose-source is improved but still below Cellpose cyto3-style performance; next Cellpose-specific work should target remaining raw proposal misses such as `cellpose_469.png`.
- Do not enable split repair by default yet; conservative split-v2 hooks exist, but no split setting has beaten the no-split global v2 candidate.

### 2026-05-03 GT-cell diagnosis for Cellpose-source failures

Diagnostic scripts:

```text
scripts/diagnose_gt_cell_semantic_marker.py
scripts/summarize_gt_cell_diagnosis.py
```

Server output:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/gt_cell_semantic_marker_global_v2_cellpose50
```

Scope:

- `configs/sam_cell_global_adaptive_selector_v2_workstation2.yaml`
- 50 Cellpose-source images from `outputs/benchmark_splits_large/eval_250_cellpose_server_paths.csv`
- final labels from `final_global_v2_eval250/labels`
- 5609 GT cells

GT-cell failure breakdown:

| failure type | cells | fraction of all GT | fraction of missed/low-IoU GT |
|---|---:|---:|---:|
| detected | 4232 | 0.7545 | n/a |
| merge_under_split | 847 | 0.1510 | 0.6151 |
| selector_or_merge_filtered | 170 | 0.0303 | 0.1235 |
| marker_miss | 145 | 0.0259 | 0.1053 |
| shape_low_iou | 117 | 0.0209 | 0.0850 |
| ranker_filtered | 84 | 0.0150 | 0.0610 |
| foreground_miss | 5 | 0.0009 | 0.0036 |
| weak_foreground | 4 | 0.0007 | 0.0029 |
| final_merge_loss | 4 | 0.0007 | 0.0029 |

Mean missed/low-IoU GT diagnostics:

| metric | value |
|---|---:|
| combined foreground coverage at 0.3 | 0.9820 |
| combined foreground coverage at 0.5 | 0.9681 |
| Cellpose-style foreground coverage at 0.5 | 0.9478 |
| universal-boundary foreground coverage at 0.5 | 0.8474 |
| markers inside GT | 2.2636 |
| best raw proposal IoU | 0.3758 |
| best ranked proposal IoU | 0.1977 |
| best final IoU | 0.1968 |
| best raw proposal GT-cover count | 2.4452 |

Interpretation:

- Cellpose-source failures are not mainly caused by semantic foreground absence. `foreground_miss + weak_foreground` is only 9 cells out of 5609 GT cells.
- The dominant failure is proposal under-splitting/merged raw masks under good semantic coverage.
- Selector/ranker also remove some usable candidates, but that is secondary to raw proposal geometry on the worst cases.
- Typical hard cases:
  - `cellpose_469.png`: detected 0/22, mean combined coverage 0.9890 at 0.5, best raw proposal GT-cover count 8.7273.
  - `cellpose_280.png`: detected 129/391, 245 merge-under-split cells.
  - `cellpose_533.png`: many selector/merge-filtered cells despite high raw proposal IoU.

Split-repair validation:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/splitrepair_default_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/splitrepair_parent_sweep_cellpose50
```

Results:

| experiment | scope | final/proposal PQ | key observation |
|---|---|---:|---|
| global v2 no split | Cellpose50 | final PQ 0.6602, proposal PQ 0.6598 | current default |
| default split repair | Cellpose50 | final PQ 0.6217, proposal PQ 0.6221 | recall +0.0135, precision -0.0801 |
| split-parent sweep partial | 16 images, proposal-only | best proposal PQ 0.6563 | below same-image global v2 proposal PQ 0.6848, stopped early |

Decision:

- Do not enable existing `split_repair_proposals` globally or for Cellpose source in its current form.
- The right next optimization is not more nnU-Net semantic training alone and not the current simple split repair.
- Next viable direction: add a learned or morphology-aware instance-separation proposal module for Cellpose-source connected components, with parent/child competition trained against GT, or introduce a stronger proposal front-end only as an auxiliary candidate source.
- Any new split module must prove both recall gain and precision preservation on Cellpose50 before global eval250.

### 2026-05-03 watershed-enhanced v3 and separator scaffold

Code changes:

```text
sam_cell/proposals/watershed.py
sam_cell/proposals/separator.py
sam_cell/pipeline.py
sam_cell/config.py
scripts/sweep_cellpose_proposal_v2.py
scripts/eval_devset.py
scripts/train_separator_proposal.py
configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml
```

Implemented Phase 1 low-cost watershed enhancements:

- `watershed.boundary_additive_weight`: additive boundary/contact penalty on the distance energy.
- `watershed.share_boundary_across_experts`: lets Cellpose-style proposals reuse the universal-boundary expert's boundary map.
- `watershed.marker_rescue_enabled`: optional component-level seed rescue for large sparse-marker components.
- Config inheritance via `extends`, used by the new v3 config.

Phase 1 server outputs:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/watershed_enhance_sweep_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/watershed_enhance_final_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/watershed_enhance_v3_derived_eval250
```

Best Phase 1 setting:

```yaml
source_overrides:
  cellpose:
    watershed:
      boundary_additive_weight: 0.12
      share_boundary_across_experts: true
      marker_rescue_enabled: false
```

Cellpose50 proposal-only sweep:

| setting | proposal PQ | AJI | precision | recall | note |
|---|---:|---:|---:|---:|---|
| v2 baseline-like | 0.6598 | 0.6499 | 0.8302 | 0.7866 | no additive/shared boundary |
| shared boundary | 0.6733 | 0.6712 | 0.8226 | 0.8208 | useful |
| shared boundary + additive 0.12 | 0.6761 | 0.6825 | 0.8134 | 0.8434 | best |
| marker rescue variants | <=0.6570 | mixed | lower precision | higher recall | do not enable |

Cellpose50 final SAM2 result:

| config | final PQ | final AJI | precision | recall | proposal PQ |
|---|---:|---:|---:|---:|---:|
| global v2 | 0.6602 | 0.6503 | 0.8304 | 0.7868 | 0.6598 |
| v3 cellpose boundary | 0.6762 | 0.6826 | 0.8135 | 0.8435 | 0.6761 |

Derived eval250 result:

The derived eval250 combines old v2 non-Cellpose rows with the new v3 Cellpose50 rows. This is valid because v3 uses `source_overrides.cellpose`, so non-Cellpose sources keep the v2 inference path.

| source | n | final PQ | final AJI |
|---|---:|---:|---:|
| ALL | 250 | 0.6295 | 0.6299 |
| cellpose | 50 | 0.6762 | 0.6826 |
| dsb2018 | 50 | 0.7417 | 0.7608 |
| livecell | 50 | 0.6051 | 0.5829 |
| pannuke | 50 | 0.5497 | 0.5738 |
| tissuenet | 50 | 0.5746 | 0.5495 |

Decision:

- `configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml` is the new strongest candidate.
- The useful Phase 1 improvement is not marker rescue; it is cross-expert boundary sharing plus additive boundary energy for Cellpose source.
- This does not reach the planned learned-separator target (`Cellpose50 proposal PQ >= 0.70`), so continue with Phase 2 learned separator.
- The separator scaffold is implemented but not trained yet:
  - `SeparatorProposalNet`: lightweight U-Net producing fg, center, contact, offset heads.
  - `separator_proposals`: default-off config section and pipeline integration.
  - `scripts/train_separator_proposal.py`: training entrypoint using instance masks and cached nnU-Net semantics.
  - `scripts/eval_devset.py`: supports separator inference overrides.
  - Do not enable `separator_proposals` until a trained checkpoint passes Cellpose50 proposal-only gates.

### 2026-05-03 separator v1 training launch

New scripts:

```text
scripts/build_separator_splits.py
scripts/cache_semantics_for_csv.py
```

Frozen separator split:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_splits_v1/train.csv
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_splits_v1/val.csv
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_splits_v1/split_manifest.json
```

Split policy:

- Excludes `outputs/benchmark_splits_large/eval_250_server_paths.csv`.
- Train: 2440 images.
- Val: 250 images.
- Train source counts: Cellpose 440, DSB2018 500, LIVECell 500, PanNuke 500, TissueNet 500.
- Val source counts: Cellpose 50, DSB2018 50, LIVECell 50, PanNuke 50, TissueNet 50.

Server job:

```text
tmux session: samcell_separator_v1
output root: /backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train
log: /backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train/logs/cache_and_train.log
```

Launched at 2026-05-03 14:22 CST.

Job sequence:

1. `scripts/cache_semantics_for_csv.py` on train+val with `--skip_existing`.
2. `scripts/train_separator_proposal.py` for 80 epochs, batch 8, crop 256, lr 1e-3, weight decay 1e-4.

Initial status:

- Cache stage is running normally; observed progress around 99/2690 rows.
- GPU0 in use, GPU1 idle.
- Training will start automatically after cache stage completes.

Progress check at 2026-05-03 15:05 CST:

- Semantic cache stage completed successfully: 2690/2690 rows cached.
- Cache manifest:
  - Cellpose 490
  - DSB2018 550
  - LIVECell 550
  - PanNuke 550
  - TissueNet 550
- Training is active in tmux `samcell_separator_v1`.
- Latest observed epoch: 31/80.
- Latest observed losses:
  - epoch 30: train 0.4001, val 0.4211
  - epoch 31: train 0.3958, val 0.4249
- Checkpoints exist:
  - `checkpoint_best.pth`
  - `checkpoint_last.pth`
- GPU status: GPU0 active, GPU1 idle.

Completion check at 2026-05-03 15:35 CST:

- tmux session `samcell_separator_v1` has ended; no active separator training process was observed.
- Server GPUs are idle: both A100 cards showed about 14 MiB used and 0% utilization at check time.
- `/backup` has about 147G available.
- Semantic cache completed: 2690/2690 rows.
- Training completed all 80/80 epochs.
- Best checkpoint:
  - epoch 74
  - train loss 0.38871826172852125
  - val loss 0.41422026604413986
- Final epoch:
  - epoch 80
  - train loss 0.3871883278987447
  - val loss 0.4207714209333062
- Artifacts confirmed:
  - `checkpoint_best.pth`
  - `checkpoint_last.pth`
  - `history.json`
  - `run_manifest.json`
  - `semantic_cache_manifest.json`
- Next action: run the Cellpose50 proposal-only gate with `checkpoint_best.pth` before any full SAM2 evaluation.

Expected checkpoints:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train/checkpoint_best.pth
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train/checkpoint_last.pth
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train/history.json
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train/run_manifest.json
```

Post-training proposal-only check command:

```bash
cd /backup/taotao_work/sam_cell
PYTHONWARNINGS=ignore::FutureWarning /backup/taotao_work/venvs/nnunet/bin/python scripts/eval_devset.py \
  --config configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml \
  --devset_csv outputs/benchmark_splits_large/eval_250_cellpose_server_paths.csv \
  --out_dir outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_eval_cellpose50_proposal_only \
  --save_outputs \
  --sam2_enabled false \
  --separator_enabled true \
  --separator_model_path outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_train/checkpoint_best.pth
```

Promotion gate:

- Do not run full SAM2 eval until proposal-only Cellpose50 beats v3 proposal PQ 0.6761.
- Target remains Cellpose50 proposal PQ >= 0.70 with no precision collapse.

Proposal-only gate result at 2026-05-03 15:52 CST:

Output:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_eval_cellpose50_proposal_only
```

Cellpose50 result using `separator_v1_train/checkpoint_best.pth` and `--sam2_enabled false`:

| metric | value |
|---|---:|
| proposal PQ | 0.676049063972696 |
| proposal AJI | 0.6820112827241809 |
| proposal precision | 0.8132323897124835 |
| proposal recall | 0.8404218577181909 |
| final/coarse PQ | 0.67517613477745 |
| final/coarse AJI | 0.6810418315567097 |
| mean predicted instances | 109.72 |
| mean GT instances | 112.18 |

Decision:

- Separator v1 did not pass the promotion gate.
- It is essentially tied with v3 Cellpose50 proposal PQ 0.6761 and far below the planned learned-separator target >=0.70.
- Do not enable `separator_proposals` in the default config yet.
- Next step should diagnose whether separator candidates are not generated, are redundant with v3 watershed proposals, or are generated but suppressed by ranking/merge. `scripts/eval_devset.py` currently does not expose a dedicated `separator_selected` summary column, so add that before deeper separator ablations.

Follow-up confirmation at 2026-05-03 16:10 CST:

- Code inspection confirmed `separator_proposals.source_name` defaults to `separator`.
- `scripts/eval_devset.py` does not currently report `separator_selected`; it only reports universal/cellpose/external selected counts.
- Existing `proposal_ranker_dual/proposal_ranker.joblib` was trained before separator existed:
  - feature set includes `proposal_source=universal_boundary`
  - feature set includes `proposal_source=cellpose_style`
  - feature set does not include `proposal_source=separator`
- From the existing `separator_v1_eval_cellpose50_proposal_only/per_image.csv`, inferred separator selections are not zero:
  - mean inferred separator-selected instances: 9.62 per image
  - total inferred separator-selected instances: 481
  - images with inferred separator selections: 38/50
- Per-image comparison against `watershed_enhance_final_cellpose50`:
  - mean proposal PQ delta: -0.000063
  - mean precision delta: -0.000133
  - mean recall delta: -0.002930
  - per-image PQ wins/losses/ties: 19/18/13
  - correlation between inferred separator-selected count and PQ delta: about 0.425

Updated interpretation:

- Separator v1 is running and sometimes useful; it is not a dead code path.
- Its positive cases are almost exactly cancelled by negative cases, so the correct next work is selector/diagnostic and oracle analysis, not blind retraining.
- Add explicit separator accounting first, then run separator-only, v3+separator without ranker or with loose ranker, and union-oracle proposal ablations.

### 2026-05-03 separator diagnostics and CellSAM baseline launch

Code updates:

```text
sam_cell/pipeline.py
scripts/eval_devset.py
scripts/proposal_oracle_diagnosis.py
scripts/train_proposal_ranker.py
scripts/run_cellsam_manifest.py
```

Separator diagnostic changes:

- `SAMCellPipeline` now returns `proposal_diagnostics` with separator/internal/external counts before ranker, after ranker, after set selector, and after duplicate merge.
- `scripts/eval_devset.py` now reports explicit `separator_selected`, `separator_generated`, `separator_after_ranker`, `separator_after_set_selector`, and `separator_after_merge`.
- `scripts/eval_devset.py` supports diagnostic overrides:
  - `--proposal_ranker_enabled`
  - `--proposal_ranker_model_path`
  - `--separator_mode`
- `scripts/proposal_oracle_diagnosis.py` now includes `raw_separator` and `raw_expert_plus_separator` stages, and supports separator/ranker CLI overrides.
- `scripts/train_proposal_ranker.py` now supports `--collect_stage pre_ranker`, `--source`, and separator CLI overrides. This is required because separator-aware ranker training must sample pre-ranker candidates rather than candidates already suppressed by the old set selector.

Validation:

- Local `py_compile` passed for the modified files.
- Local `pytest` could not run because the local base environment has a `numpy`/`skimage` ABI mismatch.
- Server `py_compile` passed.
- Server smoke `eval_devset.py --limit 1 --separator_enabled true --sam2_enabled false` passed and wrote explicit separator diagnostic columns.

Cellpose50 separator ablation outputs:

```text
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_ablation_separator_only_no_ranker_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_ablation_v3_plus_separator_no_ranker_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_ablation_v3_plus_separator_loose_ranker_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_ablation_v3_plus_separator_default_ranker_stats_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_ablation_v3_plus_separator_default_ranker_no_set_selector_cellpose50
/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_v1_oracle_cellpose50
```

Cellpose50 ablation summary:

| variant | proposal PQ | precision | recall | separator after ranker | separator after set selector | note |
|---|---:|---:|---:|---:|---:|---|
| v3 baseline | 0.676112 | 0.813366 | 0.843352 | n/a | n/a | current strongest |
| v3 + separator default old ranker | 0.676049 | 0.813232 | 0.840422 | 35.58 | 9.62 | tie, no promotion |
| separator only, no ranker | 0.358344 | 0.513437 | 0.419239 | 43.90 | 43.90 | too weak alone |
| v3 + separator, no ranker | 0.534428 | 0.529368 | 0.870458 | 43.90 | 1.38 | recall rises, precision collapses |
| v3 + separator, ranker threshold 0.0 | 0.528582 | 0.531277 | 0.860100 | 43.90 | 11.56 | loose ranker is worse |
| v3 + separator default ranker, no set selector | 0.638524 | 0.734680 | 0.840385 | 35.58 | 35.58 | set selector prevents FP explosion |

Oracle summary:

| stage | proposal_n | oracle_no_fp_pq | gt_recall_at_iou | proposal_precision_at_iou | oracle_pq |
|---|---:|---:|---:|---:|---:|
| raw_expert_unranked | 199.62 | 0.764541 | 0.865581 | 0.607244 | 0.480987 |
| raw_separator | 43.90 | 0.388991 | 0.419239 | 0.513437 | 0.358344 |
| raw_expert_plus_separator | 243.52 | 0.776065 | 0.874501 | 0.616570 | 0.420655 |
| ranked_merged | 109.80 | 0.741582 | 0.841454 | 0.815168 | 0.676981 |
| ranked_label_map_nonoverlap | 109.72 | 0.676049 | 0.840422 | 0.813232 | 0.676049 |

Decision:

- Separator v1 has a small oracle upside over raw experts (`oracle_no_fp_pq` 0.764541 -> 0.776065), but the actual selector cannot convert it into a net PQ gain.
- Do not retrain separator v1 blindly.
- Next useful experiment is a separator-aware ranker/selector trained from pre-ranker candidates.

Separator-aware ranker v2:

```text
out: /backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/proposal_ranker_separator_v2_cellpose_preranker
train_csv: /backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_splits_v1/train.csv
val_csv: /backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/separator_splits_v1/val.csv
source: cellpose
collect_stage: pre_ranker
feature_version: 2
```

Status:

- Full Cellpose-source ranker v2 training completed on 2026-05-03 18:12 CST.
- Output files:
  - `/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/proposal_ranker_separator_v2_cellpose_preranker/proposal_ranker.joblib`
  - `/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/proposal_ranker_separator_v2_cellpose_preranker/ranker_report.csv`
  - `/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/proposal_ranker_separator_v2_cellpose_preranker/train_features.csv`
  - `/backup/taotao_work/sam_cell/outputs/samcell_optimization_20260503_cellpose_v2/proposal_ranker_separator_v2_cellpose_preranker/val_features.csv`
- Ranker v2 report at threshold 0.45:
  - train: n=173776, positives=116064, precision=0.943542, recall=0.989954, F1=0.966191, AP=0.986811, ROC-AUC=0.979993
  - val: n=19756, positives=12532, precision=0.952999, recall=0.983722, F1=0.968117, AP=0.987357, ROC-AUC=0.983663
- Next action: run Cellpose50 proposal-only evaluation with this ranker before promoting it. High candidate-level AP is not enough; promotion requires instance PQ gain over v3.
- A 5-train/2-val smoke completed successfully and confirmed separator samples are included:
  - cellpose_style: 146 positives, 107 negatives
  - separator: 79 positives, 33 negatives
  - universal_boundary: 145 positives, 93 negatives

CellSAM baseline:

```text
eval250 tmux session: baseline_cellsam_eval
repro-split tmux session: baseline_cellsam_repro_splits
eval250 script: /backup/taotao_work/sam_cell/run_cellsam_eval_20260503_fast.sh
repro-split script: /backup/taotao_work/sam_cell/scripts/run_server_cellsam_repro_splits_20260503.sh
env: /backup/taotao_work/venvs/cellsam311_shared
experiment root: /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_cellsam_generalist
eval250 manifest: /backup/taotao_work/sam_cell/outputs/benchmark_splits_large/eval_250_server_paths.csv
repro manifests:
  /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/manifests/iid_val.csv
  /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/manifests/pannuke_core_test.csv
  /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/manifests/far_ood_test.csv
```

Status:

- Official `vanvalenlab/cellSAM` was installed in `cellsam311_shared`.
- `cellsam311_shared` imports CellSAM while reusing server PyTorch from the nnU-Net environment via a `.pth` site-packages pointer:
  - torch 2.5.1+cu121
  - torchvision 0.20.1+cu121
  - cellSAM 0.0.dev1
- DeepCell access token was provided interactively by the user and used only as a runtime environment variable. Do not store the token in project memory, logs, scripts, or git.
- CellSAM successfully downloaded and extracted `cellsam-models_v1.2.tar.gz` to `/backup/taotao_home/.deepcell/models` via the official CellSAM pipeline.
- CellSAM smoke inference and smoke metric evaluation completed on 1 image.
- Full eval250 CellSAM completed on 2026-05-03 18:27 CST with 250 labels, full metrics, and 750 overlay files.
- eval250 source-macro / all-image metrics:
  - ALL: n=250, PQ=0.556385, AJI=0.543019, F1=0.717280, precision=0.762931, recall=0.707941
  - cellpose: PQ=0.681702
  - dsb2018: PQ=0.704300
  - livecell: PQ=0.341904
  - pannuke: PQ=0.399976
  - tissuenet: PQ=0.654041
- 2026-05-03 18:34 CST: launched CellSAM as a full paper comparison baseline on the same three repro splits used by Cellpose/StarDist:
  - `iid_val` (697 images)
  - `pannuke_core_test` (336 images)
  - `far_ood_test` (1795 images)
- Latest check at launch: `baseline_cellsam_repro_splits` was running `iid_val`, log progress had reached about 21/697, with outputs under `/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_cellsam_generalist/{predictions,metrics,overlays}/<split>`.

### 2026-05-03 final v3 in-method optimization and full-corpus automation

User decision:

- Keep the SAM-Cell method structure fixed:
  1. nnU-Net semantic map.
  2. EDT/watershed proposals.
  3. Local adaptive crop.
  4. bbox + coarse mask prompt.
  5. frozen SAM2 refinement.
  6. candidate filtering/fusion.
- Hyperparameters do not need to match the thesis draft; they may be systematically re-tuned as long as the method idea stays the same.
- Do not add new models, retrain nnU-Net, or fuse Cellpose/CellSAM predictions into SAM-Cell for the final main method.

Automation script:

```text
scripts/final_optimization_20260503.py
```

Server run:

```text
tmux session: final_samcell_opt_20260503
command: PYTHONPATH=. /backup/taotao_work/venvs/nnunet/bin/python scripts/final_optimization_20260503.py --launch_full_if_improved
root: /backup/taotao_work/sam_cell
output: /backup/taotao_work/sam_cell/outputs/final_optimization_20260503
log: /backup/taotao_work/sam_cell/outputs/final_optimization_20260503/logs/orchestrator.stdout
```

Optimization protocol:

- Build server-path manifests for:
  - `dev_tune` 100 images, balanced 20/source.
  - `dev_holdout` 50 images, balanced 10/source.
  - `eval250` 250 images, balanced 50/source.
- Generate in-method candidate configs under `/backup/taotao_work/sam_cell/outputs/final_optimization_20260503/configs`.
- Search only existing method knobs:
  - Cellpose boundary additive weight.
  - Cellpose proposal ranker threshold.
  - Cellpose set-selector IoU/score margin.
  - TissueNet watershed and merge/semantic-support parameters.
- Stage gates:
  - `dev_tune`: proposal-only (`sam2_enabled=false`), keep top candidates.
  - `dev_holdout`: full SAM2, filter unstable candidates.
  - `eval250`: full SAM2, accept only if:
    - ALL PQ improves by at least `+0.005` over full v3 rerun.
    - Cellpose or TissueNet improves by at least `+0.01`.
    - No source drops more than `0.01` PQ.

Full CellCosmos automation:

- Full manifest is generated at:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv
```

- Full dataset:

| source | n |
|---|---:|
| cellpose | 540 |
| dsb2018 | 670 |
| livecell | 1000 |
| pannuke | 7558 |
| tissuenet | 7009 |
| ALL | 16777 |

- If and only if a candidate passes the eval250 gates, the script launches:
  - `full_samcell_final`: SAM-Cell final full-corpus inference/eval/overlays.
  - `full_cellpose_cellsam`: Cellpose cyto3 full-corpus inference/eval/overlays followed by CellSAM full-corpus inference/eval/overlays.
- If no candidate passes the gates, full-corpus inference is not launched automatically.

Latest status:

- `final_samcell_opt_20260503` started on 2026-05-03 20:33 CST.
- Latest observed command on 2026-05-03 21:43 CST was `dev_tune` proposal-only evaluation for `cp_rank_0.45`.
- No `holdout_summary.csv`, `eval250_summary.csv`, or `final_decision.json` existed yet at that check.
- Full-corpus sessions `full_samcell_final` and `full_cellpose_cellsam` had not launched yet.
- Server GPUs were effectively idle at the check; `/backup` had about 140G free.

Progress at 2026-05-03 22:31 CST:

- `final_samcell_opt_20260503` is still in `dev_tune` proposal-only stage.
- Candidate configs total: 32.
- Completed `dev_tune` summaries: 16/32.
- Latest completed summaries:
  - `cp_rank_0.60`: 2026-05-03 22:03 CST.
  - `cp_selector_iou_0.45`: 2026-05-03 22:10 CST.
  - `cp_selector_iou_0.50`: 2026-05-03 22:17 CST.
  - `cp_selector_iou_0.55`: 2026-05-03 22:24 CST.
- Current observed subprocess was `cp_selector_iou_0.60`.
- No `tune_summary.csv`, `holdout_summary.csv`, `eval250_summary.csv`, or `final_decision.json` existed yet because the script writes summaries only after each full stage completes.
- Observed per-candidate `dev_tune` runtime is about 6.5-7.5 minutes.
- Corrected runtime interpretation:
  - `dev_tune` runs all 32 candidates proposal-only.
  - `dev_holdout` runs at most `v3_baseline + 5` candidates with full SAM2 on 50 images.
  - `eval250` runs at most `v3_baseline + 3` candidates with full SAM2 on 250 images.
  - Therefore eval250 full-SAM2 is not a 32-candidate sweep.
- Corrected rough remaining optimization time from this checkpoint:
  - `dev_tune`: about 1.5-2 hours.
  - `dev_holdout`: likely about 1-2.5 hours.
  - `eval250`: likely about 2-4 hours, depending on LIVECell/TissueNet runtime and cache hit rate.
  - Total optimization-only ETA: roughly 5-8 hours from 22:31 CST, not 8-14 hours.
- GPU interpretation:
  - Current proposal-only stage is not meaningfully using GPU.
  - Full-SAM2 stages run as one sequential `eval_devset.py` process and should mainly occupy one A100, not both.
  - Full-corpus inference later intentionally can launch SAM-Cell and Cellpose/CellSAM sessions in parallel, so that later phase may use both GPUs.

### 2026-05-03 HoverNet Core3500 baseline setup

Purpose:

- Add HoVer-Net as a paper comparison baseline on the frozen Core3500 set.
- Keep this separate from the three full-corpus models. The full-corpus trio remains SAM-Cell final, Cellpose official cyto3, and CellSAM generalist.

New scripts:

```text
scripts/run_hovernet_manifest.py
scripts/setup_server_hovernet_env.sh
scripts/run_server_hovernet_core3500_20260503.sh
scripts/ensure_full_inference_after_final_opt_20260503.sh
```

Server environment:

```text
/backup/taotao_work/venvs/hovernet311_shared
```

Setup result:

- Installed `tiatoolbox==2.0.1` in a dedicated environment.
- Reused server PyTorch from the nnU-Net environment through a `.pth` site-packages pointer.
- Verified imports:
  - `tiatoolbox 2.0.1`
  - `torch 2.5.1+cu121`
  - CUDA available

Important weight correction:

- Do not use `/backup/taotao_data/mmdetection/checkpoints/hovernet_pannuke.pth` for TIAToolbox HoVer-Net. It is not a compatible TIAToolbox state dict; `torch.load` showed only a `desc` key and model loading failed.
- Copied the locally verified TIAToolbox official weight to:

```text
/backup/taotao_home/.tiatoolbox/models/hovernet_fast-pannuke.official.pth
```

- SHA256 of the official weight:

```text
789b2be8bdaf532627f584a009f83b3ba06e04c0e55c1635252ff12785ef57e8
```

Smoke result:

```text
tmux/command context: direct ssh smoke, RUN_NAME=hovernet_fast_pannuke_smoke2, LIMIT=3
output root: /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke_smoke2
manifest: /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke_smoke2/manifests/core3500_all_limit3.csv
```

- Smoke completed label inference, metric evaluation, and overlays for 3 images.
- Smoke metrics are not scientifically meaningful because `n=3`, but they prove the environment and output format are working.
- Smoke ALL PQ was `0.1706`; one Cellpose image produced zero instances, while two PanNuke images produced nonzero labels. Treat this as a runtime smoke only.

Full Core3500 run:

```text
tmux session: baseline_hovernet_core3500
command: RUN_NAME=hovernet_fast_pannuke BATCH_SIZE=8 bash scripts/run_server_hovernet_core3500_20260503.sh
manifest: /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/manifests/core3500_all.csv
output root: /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke
```

Started at 2026-05-03 21:42 CST.

Progress at 2026-05-03 22:00 CST:

- HoVer-Net label inference completed for all 3472 Core3500 images.
- Metric evaluation completed and wrote `summary_by_source.csv`.
- Overlay rendering was still running; latest observed overlay count was 462 compare overlays and 462 prediction overlays.

Completion at 2026-05-03 22:31 CST:

- Overlay rendering completed:
  - compare overlays: 3472
  - prediction overlays: 3472
  - GT overlays: 3472
- `baseline_hovernet_core3500` tmux session had ended.

Core3500 metrics:

| source | n | PQ | AJI | F1 | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 3472 | 0.2700 | 0.2734 | 0.3384 | 0.8080 | 0.3789 |
| cellpose | 147 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 |
| dsb2018 | 142 | 0.0610 | 0.0571 | 0.0796 | 0.9295 | 0.0801 |
| livecell | 149 | 0.0006 | 0.0004 | 0.0010 | 0.8697 | 0.0005 |
| pannuke | 1677 | 0.5536 | 0.5610 | 0.6934 | 0.6477 | 0.7775 |
| tissuenet | 1357 | 0.0002 | 0.0001 | 0.0004 | 0.9658 | 0.0002 |
| SOURCE_MACRO | 5 | 0.1231 | 0.1237 | 0.1549 | 0.8825 | 0.1717 |

Interpretation:

- This is a domain-specific PanNuke HoVer-Net baseline, not a strong generalist.
- It is strong mainly on PanNuke and nearly fails on Cellpose/LIVECell/TissueNet under the current automatic setting.
- Keep it as a paper comparison baseline with the caveat that it uses official PanNuke weights, not CellCosmos finetuning.

Expected outputs:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke/predictions/core3500_all/labels
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke/metrics/core3500_all
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke/overlays/core3500_all
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_hovernet_fast_pannuke/run_manifests/core3500_all.json
```

Caveats:

- The current wrapper uses regular patch-mode TIAToolbox HoVer-Net stitched back into whole-image labels. It is a reasonable automatic baseline, but not a CellCosmos-finetuned HoVer-Net.
- Early smoke suggested the PanNuke-trained HoVer-Net may be weak on Cellpose-source images; wait for full Core3500 metrics before drawing conclusions.

### 2026-05-03 full-corpus inference watchdog

Purpose:

- Ensure the three required full-corpus models enter inference after final optimization completes.
- This compensates for `scripts/final_optimization_20260503.py` intentionally not launching full inference when no candidate passes its improvement gates.

Server session:

```text
tmux session: ensure_full_after_opt_20260503
script: /backup/taotao_work/sam_cell/scripts/ensure_full_inference_after_final_opt_20260503.sh
poll interval: 300 seconds
log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/ensure_full_inference.log
```

Behavior:

- Waits for `/backup/taotao_work/sam_cell/outputs/final_optimization_20260503/final_decision.json`.
- If the optimizer accepted a candidate, uses `/backup/taotao_work/sam_cell/outputs/final_optimization_20260503/sam_cell_final_config.yaml`.
- If the optimizer did not accept a candidate, copies the current v3 config as a fallback final config:

```text
/backup/taotao_work/sam_cell/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml
```

- Then launches, if not already present:
  - `full_samcell_final`
  - `full_cellpose_cellsam`
- The baseline full session runs Cellpose official cyto3 first, then CellSAM generalist.

Status:

- Started at 2026-05-03 21:47 CST.
- At launch, `final_decision.json` did not exist yet, so the watchdog was waiting.

### 2026-05-03 full Cellpose cyto3 and CellSAM prestart

User decision:

- Start the full-corpus baseline inference before SAM-Cell final optimization finishes, because the current tuning stage is mostly proposal-only and GPUs were idle.

New scripts:

```text
scripts/run_full_cellpose_cyto3_prestart_20260503.sh
scripts/run_full_cellsam_prestart_20260503.sh
```

Server sessions:

```text
tmux session: full_cellpose_cyto3_prestart
tmux session: full_cellsam_prestart
```

Launch time:

```text
2026-05-03 22:41 CST
```

Data/output:

```text
manifest: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv
Cellpose predictions: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellpose_official_cyto3/predictions
Cellpose metrics: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellpose_official_cyto3/metrics
Cellpose overlays: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellpose_official_cyto3/overlays
CellSAM predictions: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/predictions/labels
CellSAM metrics: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/metrics
CellSAM overlays: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/overlays
```

GPU assignment:

- Cellpose official cyto3 uses `--gpu_device 1`.
- CellSAM uses `CUDA_VISIBLE_DEVICES=0`.

Observed shortly after launch:

- GPU0 about 4.9GB used by CellSAM.
- GPU1 about 1.2GB used by Cellpose.
- Progress around 2026-05-03 22:43 CST:
  - Cellpose labels: 24/16777.
  - CellSAM labels: 19/16777.

Throughput check at 2026-05-03 22:48 CST:

- Progress:
  - Cellpose labels: 52/16777.
  - CellSAM labels: 46/16777.
- Approximate current throughput from 22:41-22:48:
  - Cellpose: about 7.5 images/minute.
  - CellSAM: about 6.5-7.0 images/minute.
- If this runner behavior remains unchanged, full label inference ETA is roughly:
  - Cellpose: about 36 hours.
  - CellSAM: about 41-42 hours.
  - Wall-clock for both in parallel: about 42 hours before metrics/overlays.
- This is not an A100 capacity limit. GPU utilization is low/intermittent because:
  - `run_cellpose_manifest.py` launches `python -m cellpose` once per image.
  - `run_cellsam_manifest.py` appears to reload/initialize model state repeatedly per image, based on repeated `torch.load` warnings.
- If this is too slow, the correct optimization is to replace the prestart runners with persistent in-process/batched runners that load each model once and process the manifest sequentially.

Watchdog interaction:

- `scripts/ensure_full_inference_after_final_opt_20260503.sh` was updated to skip duplicate baseline launch if both baseline metrics already exist, or if the prestart tmux sessions are still running when SAM-Cell final optimization ends.

Fast-runner update at 2026-05-03 23:30 CST:

- Replaced the slow per-image baseline wrappers with faster safe runners.
- Rejected `scripts/run_cellpose_manifest_fast.py` for official Cellpose evaluation because the persistent Python API path did not match official CLI outputs in the 5-image smoke check.
- Accepted `scripts/run_cellpose_manifest_cli_batch.py` for Cellpose official cyto3 because it keeps the official `python -m cellpose --dir ...` path and matched the slow per-image CLI outputs pixel-exactly on the 5-image smoke check.
- Updated `scripts/run_cellpose_manifest_cli_batch.py` to write all-zero label maps when official Cellpose predicts no objects and therefore does not save a mask file. This represents an empty prediction, not a model change.
- Accepted `scripts/run_cellsam_manifest_fast.py` for CellSAM because the persistent model path matched the slow CellSAM outputs pixel-exactly on the first 5 full-manifest images.
- `full_cellpose_cyto3_prestart` was restarted at 2026-05-03 23:27 CST with the patched CLI-batch runner and `--skip_existing`; existing outputs are retained.
- `full_cellsam_prestart` continues with the persistent CellSAM runner started at 2026-05-03 23:11 CST.

Monitoring update at 2026-05-03 23:30 CST:

```text
script: /backup/taotao_work/sam_cell/scripts/monitor_full_inference_and_optimization_20260503.sh
tmux session: monitor_full_inference_20260503
poll interval: 1800 seconds
latest status: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/full_inference_monitor_20260503/latest_status.txt
history: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/full_inference_monitor_20260503/history.tsv
monitor log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/full_inference_monitor_20260503/monitor.log
```

Snapshot at 2026-05-03 23:27 CST:

- `final_samcell_opt_20260503`: alive; `final_decision.json` not present yet.
- `ensure_full_after_opt_20260503`: alive and waiting.
- `full_cellpose_cyto3_prestart`: alive; 2068/16777 labels present at snapshot time.
- `full_cellsam_prestart`: alive; 332/16777 labels present at snapshot time.
- `full_samcell_final`: not started yet, expected to be launched by the watchdog after final optimization writes a decision.
- `/backup` free space: about 135G.

### 2026-05-04 CellSAM full inference recovery

Problem:

- Full CellSAM inference crashed at image 853 with:

```text
AttributeError: 'NoneType' object has no attribute 'ndim'
```

- Cause: CellSAM can return `None` internally when no valid mask is produced for an image. For evaluation, this should be treated as a valid empty prediction, not as a fatal run failure.

Fix:

- Updated both CellSAM runners to write an all-zero label map when CellSAM returns `None` or raises the known `NoneType.ndim` error:

```text
scripts/run_cellsam_manifest_fast.py
scripts/run_cellsam_manifest.py
```

Server status:

```text
tmux session: full_cellsam_prestart
restart time: 2026-05-04 12:40 CST
script: /backup/taotao_work/sam_cell/scripts/run_full_cellsam_prestart_20260503.sh
output: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/predictions/labels
```

Verification:

- Existing 852 predictions were retained through `--skip_existing`.
- The restarted run passed the previous crash point and reached 992/16777 labels by the follow-up check.
- CellSAM uses GPU0; the TissueNet combo search below uses GPU1.

Progress at 2026-05-04 13:46 CST:

- `full_cellsam_prestart` is still alive.
- Full CellSAM labels reached 2053/16777.
- The known `NoneType.ndim` crash has not recurred after the empty-prediction fallback patch.

Progress at 2026-05-04 13:55 CST:

- `full_cellsam_prestart` is still alive.
- Full CellSAM labels reached 2085/16777.
- Cellpose official cyto3 full prediction and metrics are complete.
- SAM-Cell full prediction has not started because TissueNet combo `decision.json` is still pending.

Progress at 2026-05-04 14:08 CST:

- `full_cellsam_prestart` is still alive.
- Full CellSAM labels reached 2133/16777.
- Full SAM-Cell remains at 0/16777 because the TissueNet combo decision is still pending.

Progress at 2026-05-04 15:00 CST:

- `full_cellsam_prestart` is still alive.
- Full CellSAM labels reached 3305/16777.
- Full SAM-Cell remains at 0/16777 because the TissueNet combo decision is still pending.

Progress at 2026-05-04 15:27 CST:

- `full_cellsam_prestart` is still alive.
- Full CellSAM labels reached 4258/16777.
- Full SAM-Cell remains at 0/16777 because the TissueNet combo decision is still pending.

Progress at 2026-05-04 15:58 CST:

- `full_cellsam_prestart` is still alive.
- Full CellSAM labels reached 5381/16777.
- Full SAM-Cell remains at 0/16777 because the TissueNet combo decision is still pending.

### 2026-05-04 TissueNet local combo search

Decision:

- Do not switch to a stronger proposal front-end in this round.
- Continue optimizing within the existing SAM-Cell method: source-specific EDT/watershed/merge parameter combinations for TissueNet.

Server session:

```text
tmux session: tn_combo_search_20260504
launch time: 2026-05-04 12:40 CST
script: /backup/taotao_work/sam_cell/scripts/tissuenet_local_combo_search_20260504.py
output root: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504
GPU: CUDA_VISIBLE_DEVICES=1
```

Search design:

- Stage 1: TissueNet-only tune split, proposal-only, no SAM2.
- Stage 2: top proposal candidates on TissueNet holdout with full SAM2.
- Stage 3: top holdout candidates on TissueNet eval250 subset with full SAM2.
- Stage 4: top eval250 TissueNet candidates on full eval250 all-source set to verify overall PQ and source deltas.

Candidate space:

- `boundary_additive_weight`: 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12
- `min_distance_factor`: 0.35, 0.40, 0.45, 0.50
- `h_maxima_values`:
  - `[0.04, 0.08, 0.12]`
  - `[0.05, 0.09, 0.13]`
  - `[0.06, 0.10, 0.14]`
  - `[0.08, 0.12, 0.16]`
- Holdout stage expands top proposal candidates with merge support thresholds 0.30, 0.35, 0.40, 0.45.

Artifacts:

```text
candidate manifest: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/candidate_manifest.json
tune summary: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/tune_summary.csv
holdout summary: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/holdout_summary.csv
eval250 TissueNet summary: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/eval250_tissuenet_summary.csv
eval250 all-source summary: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/eval250_all_summary.csv
decision: /backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/decision.json
```

Initial verification:

- Baseline tune row completed and matched the previous TissueNet proposal PQ: 0.6210184303.
- Search then entered the first local candidate.

Implementation update at 2026-05-04 13:12 CST:

- The original search implementation was too slow because each candidate reran `eval_devset.py` on all TissueNet tune images.
- `scripts/tissuenet_local_combo_search_20260504.py` was updated so the tune stage performs a fast in-memory proposal sweep:
  - each TissueNet tune image predicts semantic maps once;
  - all 129 EDT/watershed candidates are evaluated against the same cached semantic maps;
  - SAM2 is still disabled in tune, unchanged from the intended proposal-screening stage.
- The slow `tn_combo_search_20260504` session was stopped and restarted at 2026-05-04 13:06 CST with the fast sweep.
- Verification at 2026-05-04 13:10 CST: `tune_per_image.partial.csv` had 387 rows, corresponding to 3 images x 129 candidates.
- This is a search-speed change only; it does not change the SAM-Cell method or the candidate parameter definitions.

Progress at 2026-05-04 13:46 CST:

- Fast tune completed all 20 TissueNet tune images and wrote `tune_summary.csv` with 129 candidates.
- Best tune candidate:
  - `tn_add_0.07_dist_0.50_h008_012_016`
  - TissueNet proposal PQ: 0.6323195377
  - Delta over v3 baseline proposal PQ 0.6210184303: +0.0113011074
- Holdout full-SAM2 evaluation has started.
- First holdout rows:
  - `v3_baseline`: TissueNet final PQ 0.6439713212
  - `tn_add_0.05_dist_0.50_h008_012_016`: TissueNet final PQ 0.6469628821, delta +0.0029915609
- `decision.json` is still pending, so `full_samcell_final` has not started yet.

Progress at 2026-05-04 13:55 CST:

- Holdout partial rows reached 3.
- Best holdout row so far remains:
  - `tn_add_0.05_dist_0.50_h008_012_016`
  - TissueNet final PQ: 0.6469628821
  - Delta over holdout v3 baseline: +0.0029915609
- Current active child process is evaluating `tn_add_0.05_dist_0.50_h008_012_016_merge_0.35`.
- GPU1 showed about 2GB memory used and intermittent utilization, consistent with full-SAM2 holdout evaluation.
- `decision.json` remains pending.

Monitoring update:

```text
script: scripts/monitor_full_inference_tn_combo_20260504.sh
tmux session: monitor_full_inference_tn_combo_20260504
latest status: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/full_inference_tn_combo_monitor_20260504/latest_status.txt
history: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/full_inference_tn_combo_monitor_20260504/history.tsv
poll interval: 1800 seconds
```

The monitor records Cellpose/CellSAM/SAM-Cell full counts, TissueNet combo stage row counts, current best rows, decision state, GPU state, disk state, and recent tmux panes.

Progress at 2026-05-04 14:08 CST:

- Holdout partial rows reached 5.
- Best holdout row so far remains `tn_add_0.05_dist_0.50_h008_012_016` with TissueNet final PQ 0.6469628821, delta +0.0029915609.
- Merge variants 0.30 and 0.35 produced the same PQ as the base candidate; 0.40 was effectively tied at 0.6469623979.
- This is not enough to conclude a final improvement; wait for higher tune-ranked candidates such as `tn_add_0.07_dist_0.50_h008_012_016`.

Post-search full-inference watchdog:

```text
tmux session: ensure_samcell_after_tn_combo
launch time: 2026-05-04 12:50 CST
script: /backup/taotao_work/sam_cell/scripts/ensure_samcell_full_after_tn_combo_20260504.sh
log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/ensure_samcell_after_tn_combo.log
poll interval: 300 seconds
```

Behavior:

- Waits for `/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/decision.json`.
- If the search accepts a new config, starts `full_samcell_final` on GPU1 using the copied best config.
- If the search does not accept a new config, starts `full_samcell_final` on GPU1 using the current strongest v3 baseline/fallback config instead.
- This avoids the previous broken fallback config path from `outputs/final_optimization_20260503/sam_cell_final_config.yaml`, while preserving the goal that SAM-Cell full inference starts after this in-method optimization round ends.

Update at 2026-05-04 14:12 CST:

- `scripts/ensure_samcell_full_after_tn_combo_20260504.sh` was patched and synced to the server.
- `ensure_samcell_after_tn_combo` tmux session was restarted with the patched script.
- New fallback config default:

```text
/backup/taotao_work/sam_cell/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml
```

Progress at 2026-05-04 15:00 CST:

- Holdout partial rows reached 15.
- Current best holdout row:
  - `tn_add_0.07_dist_0.45_h008_012_016`
  - TissueNet final PQ: 0.6473745419
  - Delta over holdout v3 baseline: +0.0034032208
- This is slightly better than the earlier `0.05/0.06` rows but still not a large improvement.
- The important `tn_add_0.07_dist_0.50_h008_012_016` group had not appeared in the partial rows yet at this check.

Progress at 2026-05-04 15:27 CST:

- Holdout partial rows reached 20.
- `tn_add_0.07_dist_0.50_h008_012_016` has now been evaluated on holdout.
- Its TissueNet final PQ is 0.6473745419, delta +0.0034032208, effectively identical to `tn_add_0.07_dist_0.45_h008_012_016`.
- Interpretation: the tune-stage proposal gain of about +0.011 PQ converts to only about +0.0034 final SAM2 PQ on holdout so far; this is a small improvement, not a large one.
- Continue the planned search through remaining holdout candidates and eval250 validation before final accept/reject.

Execution update at 2026-05-04 15:34 CST:

- The running combo search was restarted with the same method and same tune candidate set but a faster holdout execution policy:
  - `--merge_supports none`
  - selected holdout candidates are now evaluated in tune-rank order instead of original grid order.
- Reason: the observed merge support variants for 0.05/0.06/0.07 were effectively identical to their base candidates, so continuing all four merge variants would add hours without meaningful information.
- This changes only search execution, not the SAM-Cell method or final candidate definitions.
- Previous holdout partial was backed up on the server:

```text
/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/holdout_summary.partial.before_merge_skip_20260504_153325.csv
```

- New post-restart holdout partial had two rows:
  - `v3_baseline`: TissueNet final PQ 0.6439713212
  - `tn_add_0.07_dist_0.50_h008_012_016`: TissueNet final PQ 0.6473745419, delta +0.0034032208
- The active candidate at that check was `tn_add_0.09_dist_0.50_h008_012_016`.

Progress at 2026-05-04 15:58 CST:

- Accelerated holdout partial reached 7 rows.
- Current best holdout row:
  - `tn_add_0.09_dist_0.50_h008_012_016`
  - TissueNet final PQ: 0.6488673107
  - Delta over holdout v3 baseline: +0.0048959895
- This is the best TissueNet holdout improvement so far, but still a small gain and not enough alone to establish a new final config without eval250 confirmation.

Progress at 2026-05-04 16:26 CST:

- Accelerated holdout completed with 13 rows.
- Best holdout row:
  - `tn_add_0.12_dist_0.50_h008_012_016`
  - TissueNet final PQ: 0.6530122711
  - Delta over holdout v3 baseline: +0.0090409499
- This is close to a useful TissueNet gain, so the search advanced to eval250 TissueNet validation.
- Active child process at the follow-up check was evaluating eval250 TissueNet `v3_baseline` on 50 TissueNet images.

Progress at 2026-05-04 17:09 CST:

- Full CellSAM labels reached 8000/16777.
- Eval250 TissueNet baseline row completed:
  - `v3_baseline`: TissueNet final PQ 0.5746183938.
- Active child process was evaluating `tn_add_0.12_dist_0.50_h008_012_016` on eval250 TissueNet.
- Full SAM-Cell still had not started because combo `decision.json` was pending.

Progress at 2026-05-04 17:47 CST:

- Full CellSAM labels reached 9460/16777.
- Eval250 TissueNet partial reached 3 rows:
  - `v3_baseline`: TissueNet final PQ 0.5746183938.
  - `tn_add_0.12_dist_0.50_h008_012_016`: TissueNet final PQ 0.5860226806, delta +0.0114042868.
  - `tn_add_0.11_dist_0.50_h008_012_016`: TissueNet final PQ 0.5853409206, delta +0.0107225269.
- Interpretation: this TissueNet local combo search is now showing a real eval250 TissueNet gain; it must still pass eval250 all-source validation before becoming the full-inference config.
- Active child process was evaluating `tn_add_0.10_dist_0.50_h008_012_016` on eval250 TissueNet.

Progress at 2026-05-04 18:14 CST:

- Full CellSAM labels reached 9976/16777.
- Eval250 TissueNet partial reached 4 rows:
  - `v3_baseline`: TissueNet final PQ 0.5746183938.
  - `tn_add_0.12_dist_0.50_h008_012_016`: TissueNet final PQ 0.5860226806, delta +0.0114042868.
  - `tn_add_0.11_dist_0.50_h008_012_016`: TissueNet final PQ 0.5853409206, delta +0.0107225269.
  - `tn_add_0.10_dist_0.50_h008_012_016`: TissueNet final PQ 0.5840784268, delta +0.0094600330.
- Active child process was evaluating `tn_add_0.10_dist_0.45_h008_012_016` on eval250 TissueNet.
- Full-source eval250 and `decision.json` were still pending.

CellSAM recovery update at 2026-05-04 18:50 CST:

- Full CellSAM crashed again at image 10280 (`tissuenet_test_269.png`) with:

```text
TypeError: not a sequence
```

- Root cause: `tissuenet_test_269.png` is a 256x256x3 all-zero image. CellSAM cannot process this blank input and fails internally during tensor conversion.
- The corresponding GT mask is not empty, so this remains a legitimate hard failure for CellSAM. For automated evaluation, the fair recoverable behavior is to record an all-zero prediction for that image and continue.
- Patched and synced:

```text
scripts/run_cellsam_manifest_fast.py
scripts/run_cellsam_manifest.py
```

- New behavior:
  - blank/constant image -> write empty label map and continue;
  - known CellSAM empty-output failures containing `NoneType` or `not a sequence` -> write empty label map and continue.
- Server `py_compile` passed.
- `full_cellsam_prestart` was restarted at 2026-05-04 18:49 CST.
- Verification: it wrote an empty label map for `tissuenet_test_269.png` and advanced to image 10281.

Progress at 2026-05-04 19:09 CST:

- Full CellSAM labels reached 10556/16777 after the blank-image fix.
- Full-source eval250 baseline for the TissueNet combo search was still running:
  - `eval250_all/v3_baseline/labels`: 133/250 labels written.
  - `eval250_all_summary.partial.csv`: pending.
  - `decision.json`: pending.
- Active processes:
  - `scripts/tissuenet_local_combo_search_20260504.py --merge_supports none --top_holdout 3`
  - `scripts/eval_devset.py` for `eval250_all/v3_baseline`
  - `scripts/run_cellsam_manifest_fast.py`

Final combo decision at 2026-05-04 20:13 CST:

- Full-source eval250 was derived from exact per-image rows because selected candidates only modify TissueNet source behavior:
  - baseline non-TissueNet rows from `eval250_all/v3_baseline/per_image.csv`
  - candidate TissueNet rows from `eval250_tissuenet/<candidate>/per_image.csv`
- Derivation script:

```text
scripts/derive_tissuenet_combo_allsource_20260504.py
```

- Decision file:

```text
/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/decision.json
```

- Accepted config:

```text
/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/sam_cell_tissuenet_combo_best_config.yaml
```

- Best candidate:
  - `tn_add_0.12_dist_0.50_h008_012_016`
  - eval250 ALL PQ: 0.6317465763 versus v3 baseline 0.6294657190, delta +0.0022808574
  - eval250 TissueNet PQ: 0.5860226806 versus v3 baseline 0.5746183938, delta +0.0114042868
  - cellpose/dsb2018/livecell/pannuke deltas: 0.0 by exact source-specific derivation.
- Interpretation: this is a real TissueNet improvement within the existing method, not a large all-source jump. It is accepted as the final in-method optimized config for full inference because it improves TissueNet without changing other sources.

Full SAM-Cell inference:

- `ensure_samcell_after_tn_combo` detected `decision.json` and started:

```text
tmux session: full_samcell_final
output: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_final
```

- Initial verification at 2026-05-04 20:13 CST:
  - `full_samcell_final` alive.
  - SAM-Cell labels: 5/16777.
  - CellSAM labels: 11192/16777.

Progress at 2026-05-04 20:29 CST:

- `full_samcell_final` is alive and running:
  - SAM-Cell labels: 94/16777.
  - Active command uses `/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/sam_cell_tissuenet_combo_best_config.yaml`.
- `full_cellsam_prestart` is alive and running:
  - CellSAM labels: 11236/16777.
- Metrics are still pending:
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_final/summary.csv`
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/metrics/summary_by_source.csv`
- Disk `/backup` had about 116G free.

Progress at 2026-05-04 20:36 CST:

- `full_samcell_final` is alive:
  - SAM-Cell labels: 129/16777.
  - Active process: `scripts/eval_devset.py --config outputs/tissuenet_local_combo_search_20260504/sam_cell_tissuenet_combo_best_config.yaml ... --use_cache`.
- `full_cellsam_prestart` is alive:
  - CellSAM labels: 11257/16777.
- Metrics are still pending for both SAM-Cell and CellSAM.
- GPU state: GPU0 about 4439MiB used by CellSAM; GPU1 about 2009MiB used by SAM-Cell.
- Disk `/backup` had about 116G free.

Progress at 2026-05-04 21:20 CST:

- `full_samcell_final` is alive:
  - SAM-Cell labels: 260/16777.
  - Active config remains `/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/sam_cell_tissuenet_combo_best_config.yaml`.
- `full_cellsam_prestart` is alive:
  - CellSAM labels: 11373/16777.
  - Previous CellSAM `NoneType` and blank-image failures remain fixed; metrics are still pending.
- Added and launched a boundary-out refine search because the accepted TissueNet optimum was at the previous grid edge:

```text
script: scripts/tissuenet_refine_combo_search_20260504.py
launcher: scripts/run_server_tissuenet_refine_combo_20260504.sh
tmux: tn_refine_combo_search_20260504
output root: /backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504
```

- Refine search scope:
  - No new proposal front-end.
  - Only source-specific TissueNet EDT/watershed parameters are changed.
  - Baseline inside this refine run is the previously accepted `tn_add_0.12_dist_0.50_h008_012_016`.
  - Expanded grid covers boundary additive weights `0.12-0.18`, min distance factors `0.50-0.65`, and higher h-maxima triplets.
- First launch failed because server-side `python scripts/...` did not place the repo root on `sys.path`; fixed by adding `SAM_CELL_ROOT` to `sys.path` in the refine script and relaunched at 2026-05-04 21:18 CST.
- At 2026-05-04 21:20 CST the refine run was active in proposal-only tuning:
  - `tune_per_image.partial.csv`: 193 rows.
  - `tune_summary.csv`: pending.
- GPU state at launch: GPU0 about 4439MiB used by CellSAM, GPU1 about 2009MiB used by full SAM-Cell. Refine search is pinned to GPU0 and should be watched for interference with CellSAM throughput.

Refine tune update at 2026-05-04 21:42 CST:

- Proposal-only tune completed:
  - `tune_per_image.partial.csv`: 1920 data rows.
  - `tune_summary.csv`: written.
- Current accepted config is the refine baseline:
  - `v3_baseline` in the refine run means previous accepted `tn_add_0.12_dist_0.50_h008_012_016`.
  - TissueNet tune proposal PQ: 0.6294666664.
- Best proposal-only refine candidates:
  - `tn_refine_add_0.16_dist_0.60_h008_012_016`: proposal PQ 0.6361930739, delta +0.0067264074.
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`: proposal PQ 0.6361930739, delta +0.0067264074.
  - `tn_refine_add_0.15_dist_0.60_h008_012_016`: proposal PQ 0.6359386114, delta +0.0064719450.
- Interpretation: refine search found a plausible proposal-level improvement by increasing TissueNet boundary additive weight to about 0.15-0.16 and min-distance to 0.60-0.65. This is not accepted yet; it must pass SAM2 holdout and eval250 TissueNet/all-source checks.
- At 2026-05-04 21:42 CST refine entered SAM2 holdout validation on GPU0.

Refine holdout update at 2026-05-04 22:03 CST:

- Full-inference progress:
  - CellSAM labels: 11485/16777.
  - SAM-Cell labels: 345/16777.
- Refine holdout partial rows:
  - baseline `v3_baseline` TissueNet holdout final PQ: 0.6530122711.
  - `tn_refine_add_0.13_dist_0.60_h010_014_018`: 0.6543630822, delta +0.0013508111.
  - `tn_refine_add_0.13_dist_0.65_h010_014_018`: 0.6543630822, delta +0.0013508111.
- Interpretation: first holdout candidates show only a very small but positive final-PQ gain. Continue refine for now because stronger proposal-tune candidates have not all reached holdout yet. If holdout/eval250 gains stay this small or disappear, do not replace the full SAM-Cell run.

Refine holdout update at 2026-05-04 22:18 CST:

- Full-inference progress:
  - CellSAM labels: 11511/16777.
  - SAM-Cell labels: 386/16777.
- Holdout partial now includes a stronger candidate:
  - `tn_refine_add_0.15_dist_0.60_h008_012_016`: TissueNet holdout final PQ 0.6584457609, delta +0.0054334897 over the current accepted config.
- Interpretation: this is a meaningful enough holdout gain to continue the refine run into eval250 if it remains among the top candidates after holdout completes. Still not accepted until eval250 TissueNet/all-source derivation confirms a positive gain.

Refine holdout update at 2026-05-04 22:33 CST:

- Full-inference progress:
  - CellSAM labels: 11535/16777.
  - SAM-Cell labels: 432/16777.
- Additional holdout row:
  - `tn_refine_add_0.16_dist_0.55_h008_012_016`: TissueNet holdout final PQ 0.6581451246, delta +0.0051328534.
- Current best holdout remains:
  - `tn_refine_add_0.15_dist_0.60_h008_012_016` or `tn_refine_add_0.15_dist_0.65_h008_012_016`: 0.6584457609, delta +0.0054334897.
- Interpretation: `add=0.15` currently looks slightly better than `add=0.16` after SAM2, despite `add=0.16` being best in proposal-only tune. Continue until holdout completes, then eval250 should test the top few.

Refine holdout update at 2026-05-04 22:37 CST:

- Full-inference progress:
  - CellSAM labels: 11542/16777.
  - SAM-Cell labels: 440/16777.
- New best holdout candidate:
  - `tn_refine_add_0.16_dist_0.60_h008_012_016`: TissueNet holdout final PQ 0.6594060968, delta +0.0063938256.
- Interpretation: the refine run now has a stronger enough holdout signal to justify eval250. If eval250 confirms a positive all-source derived delta, consider starting a new full SAM-Cell output directory with the refine config rather than overwriting the already-running `samcell_final` directory.

Refine holdout update at 2026-05-04 22:45 CST:

- Full-inference progress:
  - CellSAM labels: 11555/16777.
  - SAM-Cell labels: 461/16777.
- Current best holdout candidate:
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`: TissueNet holdout final PQ 0.6594075805, delta +0.0063953094.
- Eval250 has not started yet as of this check. Continue until holdout completes and the top holdout candidates enter eval250.

Refine monitor update at 2026-05-04 22:51 CST:

- Added refine monitor:

```text
script: scripts/monitor_tissuenet_refine_20260504.sh
tmux: monitor_tissuenet_refine_20260504
latest: /backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/logs/refine_monitor_20260504/latest_status.txt
history: /backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/logs/refine_monitor_20260504/history.tsv
```

- Full-inference progress from the monitor:
  - CellSAM labels: 11567/16777.
  - SAM-Cell labels: 486/16777.
- Best holdout at this point:
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`: TissueNet holdout final PQ 0.6606389202, delta +0.0076266491.
- Active refine process was evaluating:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`.
- Eval250 still pending. If eval250 confirms this direction, the likely refine winner is in the `add=0.18, dist=0.60-0.65, h=[0.08,0.12,0.16]` family.

Refine eval250 start at 2026-05-04 22:57 CST:

- Holdout finished enough to advance to eval250 TissueNet.
- Active process:

```text
scripts/eval_devset.py --config outputs/tissuenet_refine_combo_search_20260504/configs/v3_baseline.yaml \
  --devset_csv outputs/tissuenet_refine_combo_search_20260504/manifests/eval250_tissuenet_server_paths.csv \
  --out_dir outputs/tissuenet_refine_combo_search_20260504/eval250_tissuenet/v3_baseline \
  --sam2_enabled true --save_outputs --use_cache
```

- In this refine run, `v3_baseline` is the previous accepted TissueNet config `tn_add_0.12_dist_0.50_h008_012_016`.
- Decision remains pending until eval250 top candidates and derived all-source summary complete.

Refine/watchdog update at 2026-05-04 23:11 CST:

- Holdout is complete:
  - Best candidates are `tn_refine_add_0.18_dist_0.60_h008_012_016` and `tn_refine_add_0.18_dist_0.65_h008_012_016`.
  - TissueNet holdout final PQ: 0.6606389202.
  - Delta over the current accepted refine baseline: +0.0076266491.
- Eval250 TissueNet baseline was active and had written 6/50 labels at 2026-05-04 23:06 CST.
- Full-inference progress at 2026-05-04 23:05 CST:
  - CellSAM labels: 11593/16777.
  - SAM-Cell labels: 531/16777.
- Added and launched refine full-run watchdog:

```text
script: scripts/ensure_samcell_full_after_tn_refine_20260504.sh
tmux: ensure_samcell_after_tn_refine
log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/ensure_samcell_after_tn_refine.log
```

- Watchdog behavior:
  - Waits for `/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/decision.json`.
  - If `accepted=false`, exits without launching another full run.
  - If `accepted=true`, starts `full_samcell_refine_final` using the accepted refine config.
  - New full output directory is `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final`.
  - It does not overwrite the currently running `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_final`.

Hourly full-inference watch at 2026-05-04 23:28 CST:

- Added and launched:

```text
script: scripts/hourly_full_inference_watch_20260504.sh
tmux: hourly_full_inference_watch_20260504
latest: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/hourly_full_inference_watch_20260504/latest_status.txt
history: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/hourly_full_inference_watch_20260504/history.tsv
```

- Purpose:
  - Every hour, check CellSAM labels/metrics and the active SAM-Cell labels/metrics until both tracked metrics complete.
  - If TissueNet refine is accepted, the active SAM-Cell output becomes `samcell_refine_final`.
  - If TissueNet refine is rejected or pending, the active SAM-Cell output remains `samcell_final`.
- First hourly snapshot:
  - refine decision: pending.
  - CellSAM labels: 11635/16777.
  - active SAM-Cell labels: 690/16777.
  - both metrics pending.

Refine eval250 update at 2026-05-04 23:37 CST:

- Eval250 TissueNet baseline completed:
  - `eval250_tissuenet/v3_baseline/labels`: 50/50.
  - `v3_baseline` TissueNet final PQ: 0.5860226806.
  - This equals the previous accepted `tn_add_0.12_dist_0.50_h008_012_016` config and is the baseline for refine decision.
- Active refine eval250 candidate:
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`.
- `eval250_tissuenet_summary.partial.csv` currently has only the baseline row, so no refine candidate is accepted or rejected yet.

Refine/watchdog update at 2026-05-04 23:55 CST:

- Refine eval250 first candidate was still running:
  - `tn_refine_add_0.18_dist_0.60_h008_012_016` labels: 17/50 at 2026-05-04 23:50 CST.
  - `decision.json`: pending.
- Full-inference progress at 2026-05-04 23:50 CST:
  - CellSAM labels: 11681/16777.
  - current SAM-Cell labels: 847/16777.
  - `samcell_refine_final`: 0 labels because refine has not been accepted/launched.
- Updated `scripts/ensure_samcell_full_after_tn_refine_20260504.sh`:
  - If refine is accepted, it now waits for `full_samcell_final` to end before starting `full_samcell_refine_final`, avoiding two SAM-Cell full runs on GPU1 at the same time.
  - Restarted tmux `ensure_samcell_after_tn_refine` at 2026-05-04 23:54 CST so the new wait behavior is active.

Refine eval250 update at 2026-05-05 00:17 CST:

- First refine eval250 candidate completed:
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`
  - TissueNet eval250 final PQ: 0.5895689480.
  - Baseline in this refine run: 0.5860226806.
  - Delta: +0.0035462674.
- Active second refine eval250 candidate:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`.
  - labels: 6/50 at 2026-05-05 00:16 CST.
- Interpretation: the refine direction now has positive eval250 evidence, not just holdout evidence. It is still not final until remaining top candidates and derived all-source `decision.json` complete.

Refine/full-inference update at 2026-05-05 00:22 CST:

- Refine decision remains pending.
- Eval250 TissueNet rows currently written:
  - `v3_baseline`: 0.5860226806.
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`: 0.5895689480, delta +0.0035462674.
- Active refine eval250 candidate:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`.
  - labels: 10/50.
- Full-inference progress:
  - CellSAM labels: 11737/16777.
  - current SAM-Cell labels: 1106/16777.
  - `samcell_refine_final`: 0 labels because refine decision is not yet accepted/launched.
- Metrics remain pending for CellSAM and SAM-Cell.

Refine/full-inference update at 2026-05-05 00:33 CST:

- Refine decision remains pending.
- Eval250 TissueNet rows currently written:
  - `v3_baseline`: 0.5860226806.
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`: 0.5895689480, delta +0.0035462674.
- Active refine eval250 candidate:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`.
  - labels: 26/50 at 2026-05-05 00:32 CST.
- Direct full-inference counts at 2026-05-05 00:32 CST:
  - CellSAM labels: 11747/16777.
  - current SAM-Cell labels: 1189/16777.
  - `samcell_refine_final`: 0 labels because refine decision is not yet accepted/launched.
- Hourly watch status at 2026-05-05 00:27 CST:
  - refine decision: pending.
  - CellSAM labels: 11741/16777.
  - active SAM-Cell labels: 1146/16777.
  - both tracked metrics pending.

Refine eval250 update at 2026-05-05 00:46 CST:

- Second refine eval250 candidate completed and is currently the best eval250 candidate:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`
  - TissueNet eval250 final PQ: 0.5903649896.
  - Delta over refine baseline: +0.0043423090.
- Previous candidate:
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`
  - TissueNet eval250 final PQ: 0.5895689480.
  - Delta: +0.0035462674.
- Active next eval250 candidate:
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`.
- Refine decision remains pending until the configured eval250 top candidates and derived all-source summary finish.

Refine/full-inference update at 2026-05-05 01:00 CST:

- Refine decision remains pending; do not switch or complete the active goal yet.
- Eval250 TissueNet rows currently written:
  - `v3_baseline`: 0.5860226806.
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`: 0.5895689480, delta +0.0035462674.
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`: 0.5903649896, delta +0.0043423090.
- Active refine eval250 candidate:
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`.
  - labels: 12/50 at 2026-05-05 00:59 CST.
- Direct full-inference counts at 2026-05-05 00:59 CST:
  - CellSAM labels: 11772/16777.
  - current SAM-Cell labels: 1256/16777.
  - `samcell_refine_final`: 0 labels because refine decision is not yet accepted/launched.
- Hourly watch remains active in tmux `hourly_full_inference_watch_20260504`.
- Post-refine goal handling:
  - If refine is accepted, `ensure_samcell_after_tn_refine` waits for `full_samcell_final` to end, then starts `full_samcell_refine_final`; hourly watch tracks `samcell_refine_final`.
  - If refine is rejected, no duplicate full SAM-Cell run starts; hourly watch continues tracking `samcell_final`.
  - The practical next objective after refine completion is hourly CellSAM/SAM-Cell inference checking until both full metrics are complete.

Refine/full-inference update at 2026-05-05 01:05 CST:

- Refine decision remains pending.
- Eval250 TissueNet rows are unchanged from 01:00 CST:
  - `v3_baseline`: 0.5860226806.
  - `tn_refine_add_0.18_dist_0.60_h008_012_016`: 0.5895689480, delta +0.0035462674.
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`: 0.5903649896, delta +0.0043423090.
- Active refine eval250 candidate:
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`.
  - labels: 19/50 at 2026-05-05 01:04 CST.
- Direct full-inference counts at 2026-05-05 01:04 CST:
  - CellSAM labels: 11777/16777.
  - current SAM-Cell labels: 1260/16777.
  - `samcell_refine_final`: 0 labels because refine decision is not yet accepted/launched.
- Active sessions remain alive:
  - `tn_refine_combo_search_20260504`.
  - `ensure_samcell_after_tn_refine`.
  - `full_cellsam_prestart`.
  - `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.

Refine/full-inference update at 2026-05-05 01:11 CST:

- Refine decision remains pending.
- Active refine eval250 candidate:
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`.
  - labels: 31/50 at 2026-05-05 01:11 CST.
- Direct full-inference counts at 2026-05-05 01:11 CST:
  - CellSAM labels: 11782/16777.
  - current SAM-Cell labels: 1264/16777.
  - `samcell_refine_final`: 0 labels because refine decision is not yet accepted/launched.
- `ensure_samcell_after_tn_refine` is still waiting for `decision.json`.
- `hourly_full_inference_watch_20260504` is alive; its last snapshot is still 00:27 CST because the next hourly refresh is expected around 01:27 CST.

Refine eval250 update at 2026-05-05 01:22 CST:

- Third refine eval250 candidate completed:
  - `tn_refine_add_0.16_dist_0.65_h008_012_016`
  - TissueNet eval250 final PQ: 0.5898623601.
  - Delta over refine baseline: +0.0038396795.
- Current eval250 best remains:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`
  - TissueNet eval250 final PQ: 0.5903649896.
- Active fourth TissueNet eval250 candidate:
  - `tn_refine_add_0.16_dist_0.60_h008_012_016`.
  - labels: 2/50 at 2026-05-05 01:22 CST.
- Script inspection confirms `--top_holdout` default is 4 and `--top_eval250` default is 3, so this fourth TissueNet candidate should be the last TissueNet eval250 candidate before top-3 all-source derived summary and `decision.json`.

Refine/hourly-watch update at 2026-05-05 01:33 CST:

- Refine decision remains pending.
- Active fourth TissueNet eval250 candidate:
  - `tn_refine_add_0.16_dist_0.60_h008_012_016`.
  - labels: 9/50 at 2026-05-05 01:32 CST.
- Hourly full-inference watch refreshed successfully at 2026-05-05 01:27 CST:
  - CellSAM labels: 11798/16777.
  - active SAM-Cell labels: 1287/16777.
  - metrics pending for both.
  - active SAM-Cell output is still `samcell_final` because refine decision is pending.
- Direct counts at 2026-05-05 01:32 CST:
  - CellSAM labels: 11805/16777.
  - current SAM-Cell labels: 1302/16777.
  - `samcell_refine_final`: 0 labels.

Refine accepted at 2026-05-05 01:59 CST:

- TissueNet refine search completed and wrote:

```text
/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/decision.json
/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/eval250_tissuenet_summary.csv
/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/eval250_all_summary.csv
```

- Decision: accepted.
- New recommended SAM-Cell config for full inference:

```text
/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml
```

- Best candidate:
  - `tn_refine_add_0.18_dist_0.65_h008_012_016`.
  - Source-specific change only: TissueNet EDT/watershed parameters; no stronger proposal front-end or method-family change.
- Eval250 derived all-source result:
  - baseline `v3_baseline`/previous accepted config ALL PQ: 0.6317465763.
  - refine best ALL PQ: 0.6326150382.
  - ALL delta: +0.0008684618.
- Eval250 TissueNet result:
  - baseline TissueNet PQ: 0.5860226806.
  - refine best TissueNet PQ: 0.5903649896.
  - TissueNet delta: +0.0043423090.
- Source-specific derived rows for non-TissueNet are unchanged:
  - Cellpose PQ: 0.6762011998.
  - DSB2018 PQ: 0.7417150339.
  - LiveCELL PQ: 0.6051402608.
  - PanNuke PQ: 0.5496537067.
- Full-inference handoff:
  - `ensure_samcell_after_tn_refine` detected acceptance and is waiting for `full_samcell_final` to end before launching `full_samcell_refine_final`.
  - `full_samcell_refine_final` has not started yet; `samcell_refine_final` labels remain 0.
  - Current counts at 2026-05-05 01:59 CST: CellSAM 11838/16777, `samcell_final` 1331/16777.
- Practical goal is now the user-requested hourly inference watch until CellSAM and the active SAM-Cell full metrics complete.

Refine full-start watchdog adjustment at 2026-05-05 02:08 CST:

- Added and launched an auxiliary watchdog to avoid waiting for the obsolete old-config `full_samcell_final` to finish before starting final refine inference:

```text
script: scripts/ensure_samcell_refine_after_cellsam_20260505.sh
tmux: ensure_samcell_refine_after_cellsam
server log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/ensure_samcell_refine_after_cellsam.log
```

- Behavior:
  - Does not stop or delete the old `full_samcell_final`; partial old-config outputs remain preserved.
  - Waits for accepted refine decision and the generated `run_full_samcell_tn_refine.sh`.
  - Waits until `full_cellsam_prestart` ends, then starts `full_samcell_refine_final` on GPU0.
  - Checks for an existing `full_samcell_refine_final` session or `samcell_refine_final/summary.csv` before starting, so it should not launch duplicates.
- Reason:
  - The accepted refine config is now the final SAM-Cell model for full inference.
  - Waiting for the old-config full SAM-Cell run to finish before starting final refine would likely delay final results unnecessarily.
- Initial watchdog status at 2026-05-05 02:07 CST:
  - waiting for `full_cellsam_prestart` to finish.
  - CellSAM labels: 11863/16777 in watchdog log; 11866/16777 direct count immediately after.
  - `samcell_final` labels: 1336/16777.
  - `samcell_refine_final` labels: 0/16777.

Full-inference monitor update at 2026-05-05 02:13 CST:

- Direct counts:
  - CellSAM labels: 11882/16777.
  - old-config `samcell_final` labels: 1338/16777.
  - final `samcell_refine_final` labels: 0/16777.
- Metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv`: missing/pending.
  - `samcell_final/summary.csv`: missing/pending.
  - `samcell_refine_final/summary.csv`: missing/pending.
- Active sessions:
  - `full_cellsam_prestart`: alive.
  - `full_samcell_final`: alive.
  - `ensure_samcell_after_tn_refine`: alive and still waiting for old `full_samcell_final` to end.
  - `ensure_samcell_refine_after_cellsam`: alive and waiting for CellSAM to finish before starting final refine SAM-Cell on GPU0.
  - `hourly_full_inference_watch_20260504`: alive.
- Last hourly watch snapshot is still 01:27 CST and was taken before refine acceptance, so it still says `refine_decision: pending`; the next hourly snapshot around 02:27 CST should switch active SAM-Cell tracking to `samcell_refine_final`.

Hourly watch validation at 2026-05-05 02:32 CST:

- The 02:27 CST hourly watch snapshot successfully picked up the accepted refine decision.
- Active SAM-Cell directory tracked by hourly watch is now:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final
```

- Hourly watch 02:27 CST counts:
  - CellSAM labels: 11941/16777.
  - final `samcell_refine_final` labels: 0/16777.
  - metrics pending for both.
- Direct counts at 2026-05-05 02:32 CST:
  - CellSAM labels: 11956/16777.
  - old-config `samcell_final` labels: 1384/16777.
  - final `samcell_refine_final` labels: 0/16777.
- `ensure_samcell_refine_after_cellsam` remains alive and is waiting for `full_cellsam_prestart` to end before starting final refine SAM-Cell on GPU0.
- `tn_refine_combo_search_20260504` is dead/completed.

Full-inference monitor update at 2026-05-05 02:38 CST:

- Latest hourly watch snapshot remains 02:27 CST:
  - `refine_decision: accepted`.
  - active SAM-Cell directory: `samcell_refine_final`.
  - watch counts: CellSAM 11941/16777, final SAM-Cell 0/16777.
- Direct counts at 2026-05-05 02:38 CST:
  - CellSAM labels: 11979/16777.
  - old-config `samcell_final` labels: 1389/16777.
  - final `samcell_refine_final` labels: 0/16777.
- Metrics remain pending for CellSAM, old-config SAM-Cell, and final refine SAM-Cell.
- `ensure_samcell_refine_after_cellsam` is alive; last log at 02:37 CST says CellSAM labels 11975/16777 and it is still waiting for `full_cellsam_prestart` to finish before starting `full_samcell_refine_final` on GPU0.

Final refine full inference started at 2026-05-05 02:43 CST:

- Rationale for changing from wait-only to parallel start:
  - CellSAM was still progressing normally but slowly through TissueNet cases.
  - GPU0 memory use was only about 4.4GB before starting final SAM-Cell, leaving enough A100 memory headroom.
  - Waiting for CellSAM to finish before starting final SAM-Cell would delay final metrics unnecessarily.
- Started:

```text
tmux: full_samcell_refine_final
command: CUDA_VISIBLE_DEVICES=0 bash experiments/cellcosmos_full_16777_20260503/run_full_samcell_tn_refine.sh
output: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final
```

- This does not stop or delete:
  - `full_cellsam_prestart`.
  - old-config `full_samcell_final`.
- Duplicate protection remains:
  - `ensure_samcell_refine_after_cellsam` will later see `full_samcell_refine_final` exists and should not start another copy.
  - `ensure_samcell_after_tn_refine` also checks for the same session before starting.
- Verification at 2026-05-05 02:46 CST:
  - CellSAM labels: 12009/16777.
  - final `samcell_refine_final` labels: 7/16777.
  - old-config `samcell_final` labels: 1396/16777.
  - GPU0 memory: about 6430 MiB, utilization about 37%.
  - GPU1 memory: about 2155 MiB, utilization about 20%.

Parallel inference health check at 2026-05-05 03:06 CST:

- `full_samcell_refine_final` is alive and producing labels.
- `full_cellsam_prestart` is alive and still producing labels.
- Direct counts:
  - CellSAM labels: 12065/16777.
  - final `samcell_refine_final` labels: 119/16777.
  - old-config `samcell_final` labels: 1406/16777.
- Metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv`: pending.
  - `samcell_refine_final/summary.csv`: pending.
- GPU snapshot:
  - GPU0: about 6430 MiB, 37% utilization.
  - GPU1: about 2155 MiB, 0% utilization at the instant sampled.
- Interpretation: concurrent CellSAM + final SAM-Cell refine on GPU0 is viable so far; do not stop or restart sessions.

Hourly watch update at 2026-05-05 03:33 CST:

- The 03:27 CST hourly watch snapshot is valid and tracks final `samcell_refine_final`.
- Hourly watch counts at 03:27 CST:
  - CellSAM labels: 12119/16777.
  - final `samcell_refine_final` labels: 187/16777.
  - metrics pending for both.
- Direct counts at 2026-05-05 03:33 CST:
  - CellSAM labels: 12133/16777.
  - final `samcell_refine_final` labels: 211/16777.
  - old-config `samcell_final` labels: 1450/16777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_samcell_refine_final`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `ensure_samcell_after_tn_refine`.
  - `ensure_samcell_refine_after_cellsam`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Important sharding note:
  - `scripts/eval_devset.py` supports cached labels but writes `per_image.csv` and `summary.csv` when each process exits.
  - Do not naively run multiple sharded `eval_devset.py` processes into the same `samcell_refine_final` directory, because an early shard could write a partial `summary.csv` and cause hourly watch to falsely mark SAM-Cell metrics complete.
  - If future acceleration is needed, use separate shard output directories and an explicit merge/recompute step, or add a safe no-summary prediction mode first.

Safe final SAM-Cell refine tail helper at 2026-05-05 03:46 CST:

- Added `--no_summary` to `scripts/eval_devset.py`.
  - Behavior: run inference/evaluation and save outputs without writing `per_image.csv` or `summary.csv`.
  - Reason: avoid false completion in `hourly_full_inference_watch_20260504` while allowing helper processes to pre-fill cached labels.
  - Syntax checked locally and on the server with `python -m py_compile`.
- Created tail helper manifest:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full_tail_from_8000_for_samcell_refine_helper.csv
rows: 8777
source manifest: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv
start_index: 8000
```

- Started helper:

```text
tmux: full_samcell_refine_tail_helper
script: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/run_full_samcell_tn_refine_tail_helper.sh
gpu: CUDA_VISIBLE_DEVICES=1
output: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final
```

- Helper command uses:

```text
--save_outputs --use_cache --no_summary
```

- Safety interpretation:
  - It writes labels/overlays/instances into the final output dir but does not write final metrics.
  - The main `full_samcell_refine_final` process remains responsible for eventually writing full `per_image.csv` and `summary.csv` over the full 16777 manifest.
  - The main process will use cached tail labels later, reducing remaining full runtime.
- Verification at 2026-05-05 03:46 CST:
  - CellSAM labels: 12163/16777.
  - final `samcell_refine_final` total labels: 276/16777.
  - final tail-helper-covered labels among tail manifest: 32/8777.
  - GPU0: about 6430 MiB, 26% utilization.
  - GPU1: about 4294 MiB, 30% utilization.
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, `full_cellsam_prestart`, and old-config `full_samcell_final`.

CellSAM tail helper and full monitor update at 2026-05-05 12:03 CST:

- Added `--run_manifest_name` to `scripts/run_cellsam_manifest_fast.py`.
  - Default remains `run_manifest.json`.
  - Tail helper uses `run_manifest_tail_helper.json` to avoid overwriting the main CellSAM run manifest.
  - Syntax checked locally and on the server.
- Created CellSAM tail helper manifest:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full_tail_from_12500_for_cellsam_helper.csv
rows: 4277
source manifest: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full.csv
start_index: 12500
```

- Started CellSAM helper:

```text
tmux: full_cellsam_tail_helper
script: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/run_full_cellsam_tail_helper.sh
gpu: CUDA_VISIBLE_DEVICES=1
output: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/predictions
```

- Helper command uses `--skip_existing --run_manifest_name run_manifest_tail_helper.json`.
- It writes labels only through the CellSAM runner; CellSAM metrics are still produced later by the main wrapper/eval step.
- Verification at 2026-05-05 12:03 CST:
  - Latest hourly watch snapshot at 11:27 CST: CellSAM 12968/16777, final SAM-Cell refine 3861/16777, both metrics pending.
  - Direct CellSAM labels: 13016/16777.
  - Direct CellSAM helper-covered tail labels: 516/4277.
  - Direct final `samcell_refine_final` labels: 3975/16777.
  - Direct SAM-Cell tail helper-covered labels: 2521/8777.
  - Metrics remain pending for CellSAM and final SAM-Cell refine.
  - Active sessions include `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, old-config `full_samcell_final`, and `hourly_full_inference_watch_20260504`.
  - GPU snapshot: GPU0 about 6430 MiB, GPU1 about 8714 MiB.

Hourly watch update at 2026-05-05 12:38 CST:

- The 12:27 CST hourly watch snapshot is valid and did not falsely mark metrics complete after helper launches.
- Hourly watch counts at 12:27 CST:
  - CellSAM labels: 13045/16777.
  - final `samcell_refine_final` labels: 4042/16777.
  - metrics pending for both.
- Direct counts at 2026-05-05 12:38 CST:
  - CellSAM labels: 13056/16777.
  - CellSAM helper-covered tail labels: 556/4277.
  - final `samcell_refine_final` labels: 4074/16777.
  - final SAM-Cell tail helper-covered labels: 2598/8777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- GPU snapshot: GPU0 about 6430 MiB, GPU1 about 8714 MiB.

Post-CellSAM SAM-Cell extra helper watcher at 2026-05-05 13:10 CST:

- User allowed using the card freed by CellSAM to run more SAM-Cell after CellSAM finishes.
- Added and launched:

```text
script: scripts/start_extra_samcell_refine_after_cellsam_done_20260505.sh
tmux: start_extra_samcell_refine_after_cellsam_done
server log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/start_extra_samcell_refine_after_cellsam_done.log
```

- Behavior:
  - Waits until both `full_cellsam_prestart` and `full_cellsam_tail_helper` are no longer alive.
  - If final SAM-Cell refine `summary.csv` already exists, exits.
  - If final SAM-Cell refine labels are already complete, exits.
  - Otherwise creates/uses a tail manifest from index 12500:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full_tail_from_12500_for_samcell_refine_extra_after_cellsam.csv
```

  - Starts `full_samcell_refine_extra_after_cellsam` on GPU0 with `--save_outputs --use_cache --no_summary`.
- Safety:
  - The extra helper will not write `per_image.csv` or `summary.csv`, so hourly watch should not falsely mark SAM-Cell metrics complete.
  - The main `full_samcell_refine_final` process remains responsible for final full metrics.
- Initial watcher log at 2026-05-05 13:10 CST:
  - CellSAM still active.
  - CellSAM labels: 13090/16777.
  - final `samcell_refine_final` labels: 4167/16777.

Hourly watch update at 2026-05-05 13:36 CST:

- The 13:27 CST hourly watch snapshot is valid and still pending for both metrics.
- Hourly watch counts at 13:27 CST:
  - CellSAM labels: 13119/16777.
  - final `samcell_refine_final` labels: 4209/16777.
- Direct counts at 2026-05-05 13:35 CST:
  - CellSAM labels: 13135/16777.
  - CellSAM helper-covered tail labels: 635/4277.
  - final `samcell_refine_final` labels: 4225/16777.
  - final SAM-Cell tail helper-covered labels: 2699/8777.
- `start_extra_samcell_refine_after_cellsam_done` remains alive and is still waiting for CellSAM sessions to finish; last log at 13:35 CST: CellSAM 13135/16777, SAM-Cell refine 4224/16777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.

Hourly watch update at 2026-05-05 14:35 CST:

- The 14:27 CST hourly watch snapshot is valid and still pending for both metrics.
- Hourly watch counts at 14:27 CST:
  - CellSAM labels: 13230/16777.
  - final `samcell_refine_final` labels: 4363/16777.
- Direct counts at 2026-05-05 14:35 CST:
  - CellSAM labels: 13245/16777.
  - CellSAM helper-covered tail labels: 745/4277.
  - final `samcell_refine_final` labels: 4381/16777.
  - final SAM-Cell tail helper-covered labels: 2798/8777.
- `start_extra_samcell_refine_after_cellsam_done` remains alive and is still waiting for CellSAM sessions to finish; last log at 14:35 CST: CellSAM 13244/16777, SAM-Cell refine 4381/16777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.

Hourly watch update at 2026-05-05 15:34 CST:

- The 15:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 15:27 CST:
  - CellSAM labels: 13338/16777.
  - final `samcell_refine_final` labels: 4507/16777.
- Direct counts at 2026-05-05 15:33 CST:
  - CellSAM labels: 13348/16777.
  - final `samcell_refine_final` labels: 4518/16777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
- Metrics remain pending for CellSAM and final SAM-Cell refine.
- `start_extra_samcell_refine_after_cellsam_done` has not triggered yet because CellSAM sessions are still alive.

Hourly watch update at 2026-05-05 16:39 CST:

- The 16:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 16:27 CST:
  - CellSAM labels: 13438/16777.
  - final `samcell_refine_final` labels: 4624/16777.
- Direct counts at 2026-05-05 16:39 CST:
  - CellSAM labels: 13454/16777.
  - CellSAM helper-covered tail labels: 954/4277.
  - final `samcell_refine_final` labels: 4646/16777.
  - final SAM-Cell tail helper-covered labels: 2929/8777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- `start_extra_samcell_refine_after_cellsam_done` has not triggered yet because CellSAM sessions are still alive; last visible log at 16:35 CST: CellSAM 13449/16777, SAM-Cell refine 4636/16777.

Hourly watch update at 2026-05-05 17:46 CST:

- The 17:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 17:27 CST:
  - CellSAM labels: 13521/16777.
  - final `samcell_refine_final` labels: 4808/16777.
- Direct counts at 2026-05-05 17:45 CST:
  - CellSAM labels: 13546/16777.
  - CellSAM helper-covered tail labels: 1046/4277.
  - final `samcell_refine_final` labels: 4868/16777.
  - final SAM-Cell tail helper-covered labels: 3079/8777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- `start_extra_samcell_refine_after_cellsam_done` has not triggered yet because CellSAM sessions are still alive; last visible log at 17:45 CST: CellSAM 13545/16777, SAM-Cell refine 4867/16777.

Post-CellSAM GPU0 reuse watcher update at 2026-05-05 18:05 CST:

- User allowed using the card freed by CellSAM to run another SAM-Cell process.
- The earlier watcher `start_extra_samcell_refine_after_cellsam_done` is safe but conservative because it waits for both CellSAM sessions (`full_cellsam_prestart` and `full_cellsam_tail_helper`) to end.
- Added and launched a GPU0-specific watcher:

```text
script: scripts/start_extra_samcell_refine_after_cellsam_main_done_20260505.sh
tmux: start_extra_samcell_refine_after_cellsam_main_done
server log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/start_extra_samcell_refine_after_cellsam_main_done.log
target session: full_samcell_refine_extra_after_cellsam
target GPU: CUDA_VISIBLE_DEVICES=0
```

- Behavior:
  - Waits only for `full_cellsam_prestart` to end, so GPU0 can be reused immediately even if the GPU1 CellSAM tail helper is still alive.
  - If final SAM-Cell refine metrics or all labels already exist, exits without starting anything.
  - If `full_samcell_refine_extra_after_cellsam` already exists, exits without duplication.
  - Otherwise starts extra SAM-Cell refine inference into `samcell_refine_final` with `--save_outputs --use_cache --no_summary`.
- The extra helper still does not write `summary.csv`; the main `full_samcell_refine_final` process remains responsible for final full metrics.
- Verification at 2026-05-05 18:04 CST:
  - `start_extra_samcell_refine_after_cellsam_main_done` is alive.
  - `full_cellsam_prestart` is still alive, so the extra helper has not triggered yet.
  - Direct CellSAM labels: 13578/16777.
  - Direct final `samcell_refine_final` labels: 4894/16777.

Status check at 2026-05-05 18:16 CST:

- Full metrics are still pending:
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final/summary.csv` missing.
- Direct counts:
  - CellSAM labels: 13594/16777.
  - CellSAM helper-covered tail labels: 1094/4277.
  - final `samcell_refine_final` labels: 4903/16777.
  - final SAM-Cell tail helper-covered labels: 3092/8777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 18:14 CST: CellSAM 13591/16777, SAM-Cell refine 4903/16777.
- Pane checks show CellSAM main/tail and SAM-Cell refine main/tail are still emitting progress; no stuck state observed.

Hourly watch update at 2026-05-05 18:32 CST:

- The 18:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 18:27 CST:
  - CellSAM labels: 13611/16777.
  - final `samcell_refine_final` labels: 4930/16777.
- Direct counts at 2026-05-05 18:32 CST:
  - CellSAM labels: 13616/16777.
  - final `samcell_refine_final` labels: 4939/16777.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - old-config `full_samcell_final`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- Metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 18:29 CST: CellSAM 13613/16777, SAM-Cell refine 4934/16777.

Status check at 2026-05-05 18:41 CST:

- Direct counts:
  - CellSAM labels: 13628/16777.
  - CellSAM helper-covered tail labels: 1128/4277.
  - final `samcell_refine_final` labels: 4957/16777.
  - final SAM-Cell tail helper-covered labels: 3109/8777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain alive, including `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, both post-CellSAM watchers, and the hourly watch.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 18:39 CST: CellSAM 13627/16777, SAM-Cell refine 4956/16777.

Status check at 2026-05-05 18:49 CST:

- Direct counts:
  - CellSAM labels: 13642/16777.
  - CellSAM helper-covered tail labels: 1142/4277.
  - final `samcell_refine_final` labels: 4972/16777.
  - final SAM-Cell tail helper-covered labels: 3116/8777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain unchanged; `full_cellsam_prestart` is still alive, so `start_extra_samcell_refine_after_cellsam_main_done` has not triggered.

Status check at 2026-05-05 18:56 CST:

- Direct counts:
  - CellSAM labels: 13655/16777.
  - CellSAM helper-covered tail labels: 1155/4277.
  - final `samcell_refine_final` labels: 4987/16777.
  - final SAM-Cell tail helper-covered labels: 3123/8777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain unchanged; `full_cellsam_prestart` is still alive, so `start_extra_samcell_refine_after_cellsam_main_done` has not triggered.

Status check at 2026-05-05 19:03 CST:

- Direct counts:
  - CellSAM labels: 13674/16777.
  - final `samcell_refine_final` labels: 4997/16777.
- Full metrics remain pending for CellSAM and final SAM-Cell refine.
- `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, hourly watch, and GPU0-specific post-CellSAM watcher remain alive.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 18:59 CST: CellSAM 13660/16777, SAM-Cell refine 4993/16777.
- Next useful checkpoint is the 19:27 CST hourly watch snapshot unless a metrics file appears or `full_cellsam_prestart` ends first.

Quick pre-hourly check at 2026-05-05 19:10 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 13702/16777.
  - final `samcell_refine_final` labels: 5012/16777.
- Next useful checkpoint remains the 19:27 CST hourly watch snapshot unless a metrics file appears or `full_cellsam_prestart` ends first.

Hourly watch update at 2026-05-05 19:30 CST:

- The 19:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 19:27 CST:
  - CellSAM labels: 13793/16777.
  - final `samcell_refine_final` labels: 5038/16777.
- Direct counts at 2026-05-05 19:30 CST:
  - CellSAM labels: 13809/16777.
  - final `samcell_refine_final` labels: 5047/16777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 19:29 CST: CellSAM 13806/16777, SAM-Cell refine 5044/16777.

Status check at 2026-05-05 19:40 CST:

- Direct counts:
  - CellSAM labels: 13856/16777.
  - final `samcell_refine_final` labels: 5066/16777.
- CellSAM metrics and final SAM-Cell refine metrics remain pending.
- `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, hourly watch, and GPU0-specific post-CellSAM watcher remain alive.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.
- Next useful checkpoint is the 20:27 CST hourly watch snapshot unless a metrics file appears or `full_cellsam_prestart` ends first.

Quick pre-hourly check at 2026-05-05 19:48 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 13883/16777.
  - final `samcell_refine_final` labels: 5081/16777.

Quick pre-hourly check at 2026-05-05 19:57 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 13914/16777.
  - final `samcell_refine_final` labels: 5094/16777.

Quick pre-hourly check at 2026-05-05 20:05 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 13937/16777.
  - final `samcell_refine_final` labels: 5106/16777.

Hourly watch update at 2026-05-05 20:32 CST:

- The 20:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 20:27 CST:
  - CellSAM labels: 14015/16777.
  - final `samcell_refine_final` labels: 5131/16777.
- Direct counts at 2026-05-05 20:32 CST:
  - CellSAM labels: 14036/16777.
  - final `samcell_refine_final` labels: 5135/16777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 20:29 CST: CellSAM 14024/16777, SAM-Cell refine 5133/16777.

Status check at 2026-05-05 20:44 CST:

- Direct counts:
  - CellSAM labels: 14084/16777.
  - final `samcell_refine_final` labels: 5162/16777.
- CellSAM metrics and final SAM-Cell refine metrics remain pending.
- `full_cellsam_prestart` is still alive, and `full_samcell_refine_extra_after_cellsam` has not started.
- Next useful checkpoint is the 21:27 CST hourly watch snapshot unless a metrics file appears or `full_cellsam_prestart` ends first.

Quick pre-hourly check at 2026-05-05 20:55 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 14122/16777.
  - final `samcell_refine_final` labels: 5181/16777.

Quick pre-hourly check at 2026-05-05 21:07 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 14174/16777.
  - final `samcell_refine_final` labels: 5199/16777.

Hourly watch update at 2026-05-05 21:40 CST:

- The 21:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 21:27 CST:
  - CellSAM labels: 14305/16777.
  - final `samcell_refine_final` labels: 5227/16777.
- Direct counts at 2026-05-05 21:40 CST:
  - CellSAM labels: 14380/16777.
  - final `samcell_refine_final` labels: 5249/16777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive; latest watcher log at 21:39 CST: CellSAM 14376/16777, SAM-Cell refine 5248/16777.

Status check at 2026-05-05 21:56 CST:

- Direct counts:
  - CellSAM labels: 14454/16777.
  - final `samcell_refine_final` labels: 5266/16777.
- CellSAM metrics and final SAM-Cell refine metrics remain pending.
- `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, hourly watch, and GPU0-specific post-CellSAM watcher remain alive.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.
- Next useful checkpoint is the 22:27 CST hourly watch snapshot unless a metrics file appears or `full_cellsam_prestart` ends first.

Quick pre-hourly check at 2026-05-05 22:12 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 14523/16777.
  - final `samcell_refine_final` labels: 5278/16777.

Hourly watch update at 2026-05-05 22:36 CST:

- The 22:27 CST hourly watch snapshot is valid and still pending for both tracked metrics.
- Hourly watch counts at 22:27 CST:
  - CellSAM labels: 14573/16777.
  - final `samcell_refine_final` labels: 5289/16777.
- Direct counts at 2026-05-05 22:36 CST:
  - CellSAM labels: 14604/16777.
  - final `samcell_refine_final` labels: 5295/16777.
- Full metrics remain pending for CellSAM, final SAM-Cell refine, and old-config SAM-Cell.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `start_extra_samcell_refine_after_cellsam_main_done` has not triggered yet because `full_cellsam_prestart` is still alive.

Status check at 2026-05-05 22:55 CST:

- Direct counts:
  - CellSAM labels: 14674/16777.
  - final `samcell_refine_final` labels: 5305/16777.
- CellSAM metrics and final SAM-Cell refine metrics remain pending.
- `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, hourly watch, and GPU0-specific post-CellSAM watcher remain alive.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.
- Next useful checkpoint is the 23:27 CST hourly watch snapshot unless a metrics file appears or `full_cellsam_prestart` ends first.

Quick pre-hourly check at 2026-05-05 23:09 CST:

- No completion or trigger event yet:
  - CellSAM metrics: pending.
  - final SAM-Cell refine metrics: pending.
  - `full_cellsam_prestart` is still alive.
  - `full_samcell_refine_extra_after_cellsam` has not started.
- Direct counts:
  - CellSAM labels: 14705/16777.
  - final `samcell_refine_final` labels: 5313/16777.

Overnight status refresh at 2026-05-06 00:46 CST:

- Hourly watch remains alive and still tracks final `samcell_refine_final`.
- The 23:27 CST hourly watch snapshot remained pending for both tracked metrics:
  - CellSAM labels: 14783/16777.
  - final `samcell_refine_final` labels: 5327/16777.
- The 00:27 CST hourly watch snapshot remained pending for both tracked metrics:
  - CellSAM labels: 15068/16777.
  - final `samcell_refine_final` labels: 5380/16777.
- Direct counts at 2026-05-06 00:46 CST:
  - CellSAM labels: 15183/16777.
  - final `samcell_refine_final` labels: 5392/16777.
  - old-config `samcell_final` labels: 2178/16777.
- Full metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_final`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.

Status check at 2026-05-06 00:55 CST:

- Direct counts:
  - CellSAM labels: 15252/16777.
  - final `samcell_refine_final` labels: 5397/16777.
  - old-config `samcell_final` labels: 2178/16777.
- Full metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_final`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive; latest watcher log at 00:54 CST: CellSAM 15247/16777, SAM-Cell refine 5397/16777.

Status check at 2026-05-06 01:04 CST:

- Direct counts:
  - CellSAM labels: 15350/16777.
  - final `samcell_refine_final` labels: 5403/16777.
  - old-config `samcell_final` labels: 2179/16777.
- Full metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_final`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive; latest watcher log at 00:59 CST: CellSAM 15313/16777, SAM-Cell refine 5401/16777.

Status check at 2026-05-06 01:14 CST:

- Direct counts:
  - CellSAM labels: 15460/16777.
  - final `samcell_refine_final` labels: 5408/16777.
  - old-config `samcell_final` labels: 2180/16777.
- Full metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- No new hourly watch row after the 00:27 CST snapshot yet.
- Active sessions remain alive:
  - `full_cellsam_prestart`.
  - `full_cellsam_tail_helper`.
  - `full_samcell_final`.
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `hourly_full_inference_watch_20260504`.
  - `start_extra_samcell_refine_after_cellsam_done`.
  - `start_extra_samcell_refine_after_cellsam_main_done`.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.

Quick pre-hourly check at 2026-05-06 01:23 CST:

- Direct counts:
  - CellSAM labels: 15547/16777.
  - final `samcell_refine_final` labels: 5413/16777.
  - old-config `samcell_final` labels: 2180/16777.
- Full metrics remain pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- No new hourly watch row after the 00:27 CST snapshot yet; next expected snapshot is 01:27 CST.
- Active sessions remain alive, including `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, `full_samcell_final`, and hourly watch.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.

Status check at 2026-05-06 01:33 CST:

- Latest hourly watch row at 01:27 CST remained pending with CellSAM 15598/16777 and final `samcell_refine_final` 5416/16777.
- Direct counts:
  - CellSAM labels: 15655/16777.
  - final `samcell_refine_final` labels: 5419/16777.
  - old-config `samcell_final` labels: 2194/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` is still alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam` yet.
- GPU snapshot: GPU0 6430 MiB / 28%, GPU1 8716 MiB / 42%.

Status check at 2026-05-06 01:41 CST:

- Direct counts:
  - CellSAM labels: 15721/16777.
  - final `samcell_refine_final` labels: 5421/16777.
  - old-config `samcell_final` labels: 2198/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- Active sessions still include `full_cellsam_prestart`, `full_cellsam_tail_helper`, `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, `full_samcell_final`, both post-CellSAM watchers, and the hourly watch.
- `full_samcell_refine_extra_after_cellsam` has not started because `full_cellsam_prestart` is still alive.
- GPU snapshot: GPU0 6430 MiB / 4%, GPU1 8716 MiB / 40%.

Status check at 2026-05-06 01:47 CST:

- Direct counts:
  - CellSAM labels: 15782/16777.
  - final `samcell_refine_final` labels: 5425/16777.
  - old-config `samcell_final` labels: 2200/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- GPU snapshot: GPU0 6430 MiB / 33%, GPU1 8716 MiB / 42%.

Status check at 2026-05-06 01:52 CST:

- Direct counts:
  - CellSAM labels: 15842/16777.
  - final `samcell_refine_final` labels: 5429/16777.
  - old-config `samcell_final` labels: 2200/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0 extra session `full_samcell_refine_extra_after_cellsam` has not started.
- Latest post-CellSAM watcher log at 01:50 CST still reports CellSAM active.
- GPU snapshot: GPU0 6430 MiB / 2%, GPU1 8716 MiB / 21%.

Status check at 2026-05-06 01:58 CST:

- Direct counts:
  - CellSAM labels: 15890/16777.
  - final `samcell_refine_final` labels: 5438/16777.
  - old-config `samcell_final` labels: 2201/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 01:54 CST still reports `full_cellsam_prestart` active.
- GPU snapshot: GPU0 6430 MiB / 24%, GPU1 8716 MiB / 19%.

Status check at 2026-05-06 02:04 CST:

- Direct counts:
  - CellSAM labels: 15941/16777.
  - final `samcell_refine_final` labels: 5444/16777.
  - old-config `samcell_final` labels: 2202/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 01:59 CST still reports `full_cellsam_prestart` active.
- GPU snapshot: GPU0 6430 MiB / 1%, GPU1 8716 MiB / 43%.

Status check at 2026-05-06 02:08 CST:

- Direct counts:
  - CellSAM labels: 15977/16777.
  - final `samcell_refine_final` labels: 5449/16777.
  - old-config `samcell_final` labels: 2202/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 02:04 CST still reports `full_cellsam_prestart` active.
- GPU snapshot: GPU0 6430 MiB / 33%, GPU1 8716 MiB / 3%.

Status check at 2026-05-06 02:12 CST:

- Direct counts:
  - CellSAM labels: 16017/16777.
  - final `samcell_refine_final` labels: 5453/16777.
  - old-config `samcell_final` labels: 2202/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 02:09 CST still reports `full_cellsam_prestart` active.
- GPU snapshot: GPU0 6430 MiB / 33%, GPU1 8716 MiB / 33%.

Status check at 2026-05-06 02:17 CST:

- Direct counts:
  - CellSAM labels: 16052/16777.
  - final `samcell_refine_final` labels: 5456/16777.
  - old-config `samcell_final` labels: 2203/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 02:14 CST still reports `full_cellsam_prestart` active.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 41%.

Status check at 2026-05-06 02:21 CST:

- Direct counts:
  - CellSAM labels: 16075/16777.
  - final `samcell_refine_final` labels: 5459/16777.
  - old-config `samcell_final` labels: 2203/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 02:19 CST still reports `full_cellsam_prestart` active.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 5%.

Status check at 2026-05-06 02:29 CST:

- Direct counts:
  - CellSAM labels: 16123/16777.
  - final `samcell_refine_final` labels: 5463/16777.
  - old-config `samcell_final` labels: 2204/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 02:29 CST still reports `full_cellsam_prestart` active with CellSAM 16129/16777 and SAM-Cell refine 5464/16777.
- CellSAM pane is still emitting progress through TissueNet cases; do not manually start a duplicate extra SAM-Cell session while `full_cellsam_prestart` is alive.
- GPU snapshot: GPU0 6430 MiB / 4%, GPU1 8716 MiB / 30%.

Status check at 2026-05-06 02:36 CST:

- Direct counts:
  - CellSAM labels: 16171/16777.
  - final `samcell_refine_final` labels: 5468/16777.
  - old-config `samcell_final` labels: 2204/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so `full_samcell_refine_extra_after_cellsam` has not started.
- GPU0 has low utilization but still holds the CellSAM process memory; do not treat low utilization as completion while the tmux session is alive and labels are increasing.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 3%.

Status check at 2026-05-06 02:40 CST:

- Direct counts:
  - CellSAM labels: 16189/16777.
  - final `samcell_refine_final` labels: 5471/16777.
  - old-config `samcell_final` labels: 2205/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive; `full_samcell_refine_extra_after_cellsam` has not started.
- Latest GPU0-specific watcher log at 02:39 CST still reports `full_cellsam_prestart` active with CellSAM 16189/16777 and SAM-Cell refine 5471/16777.
- GPU snapshot: GPU0 6430 MiB / 33%, GPU1 8716 MiB / 37%.

Status check at 2026-05-06 02:44 CST:

- Direct counts:
  - CellSAM labels: 16206/16777.
  - final `samcell_refine_final` labels: 5472/16777.
  - old-config `samcell_final` labels: 2205/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest watcher row remains 02:39 CST; no failure signal, just waiting for next 5-minute watcher tick while labels continue increasing.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 6%.

Status check at 2026-05-06 02:48 CST:

- Direct counts:
  - CellSAM labels: 16228/16777.
  - final `samcell_refine_final` labels: 5476/16777.
  - old-config `samcell_final` labels: 2205/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 02:44 CST still reports `full_cellsam_prestart` active with CellSAM 16207/16777 and SAM-Cell refine 5472/16777.
- GPU snapshot: GPU0 6430 MiB / 88%, GPU1 8716 MiB / 33%.

Status check at 2026-05-06 02:53 CST:

- Direct counts:
  - CellSAM labels: 16242/16777.
  - final `samcell_refine_final` labels: 5478/16777.
  - old-config `samcell_final` labels: 2206/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 02:49 CST still reports `full_cellsam_prestart` active with CellSAM 16231/16777 and SAM-Cell refine 5477/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 36%.

Status check at 2026-05-06 02:57 CST:

- Direct counts:
  - CellSAM labels: 16256/16777.
  - final `samcell_refine_final` labels: 5479/16777.
  - old-config `samcell_final` labels: 2206/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 02:54 CST still reports `full_cellsam_prestart` active with CellSAM 16246/16777 and SAM-Cell refine 5478/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 36%.

Status check at 2026-05-06 03:00 CST:

- Direct counts:
  - CellSAM labels: 16274/16777.
  - final `samcell_refine_final` labels: 5482/16777.
  - old-config `samcell_final` labels: 2206/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 02:59 CST still reports `full_cellsam_prestart` active with CellSAM 16271/16777 and SAM-Cell refine 5481/16777.
- GPU snapshot: GPU0 6430 MiB / 27%, GPU1 8716 MiB / 32%.

Status check at 2026-05-06 03:04 CST:

- Direct counts:
  - CellSAM labels: 16289/16777.
  - final `samcell_refine_final` labels: 5483/16777.
  - old-config `samcell_final` labels: 2207/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest visible GPU0-specific watcher row at 02:59 CST still reports `full_cellsam_prestart` active; no duplicate extra SAM-Cell session exists.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 29%.

Status check at 2026-05-06 03:08 CST:

- Direct counts:
  - CellSAM labels: 16305/16777.
  - final `samcell_refine_final` labels: 5485/16777.
  - old-config `samcell_final` labels: 2207/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:04 CST still reports `full_cellsam_prestart` active with CellSAM 16290/16777 and SAM-Cell refine 5483/16777.
- GPU snapshot: GPU0 6430 MiB / 39%, GPU1 8716 MiB / 2%.

Status check at 2026-05-06 03:13 CST:

- Direct counts:
  - CellSAM labels: 16323/16777.
  - final `samcell_refine_final` labels: 5487/16777.
  - old-config `samcell_final` labels: 2207/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:09 CST still reports `full_cellsam_prestart` active with CellSAM 16310/16777 and SAM-Cell refine 5486/16777.
- GPU snapshot: GPU0 6430 MiB / 4%, GPU1 8716 MiB / 30%.

Status check at 2026-05-06 03:17 CST:

- Direct counts:
  - CellSAM labels: 16333/16777.
  - final `samcell_refine_final` labels: 5489/16777.
  - old-config `samcell_final` labels: 2208/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:14 CST still reports `full_cellsam_prestart` active with CellSAM 16328/16777 and SAM-Cell refine 5488/16777.
- GPU snapshot: GPU0 6430 MiB / 23%, GPU1 8716 MiB / 42%.

Status check at 2026-05-06 03:21 CST:

- Direct counts:
  - CellSAM labels: 16347/16777.
  - final `samcell_refine_final` labels: 5493/16777.
  - old-config `samcell_final` labels: 2208/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:19 CST still reports `full_cellsam_prestart` active with CellSAM 16339/16777 and SAM-Cell refine 5491/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 20%.

Status check at 2026-05-06 03:25 CST:

- Direct counts:
  - CellSAM labels: 16363/16777.
  - final `samcell_refine_final` labels: 5495/16777.
  - old-config `samcell_final` labels: 2208/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:24 CST still reports `full_cellsam_prestart` active with CellSAM 16360/16777 and SAM-Cell refine 5494/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8716 MiB / 21%.

Status check at 2026-05-06 03:29 CST:

- Direct counts:
  - CellSAM labels: 16382/16777.
  - final `samcell_refine_final` labels: 5497/16777.
  - old-config `samcell_final` labels: 2208/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest visible GPU0-specific watcher row at 03:24 CST still reports `full_cellsam_prestart` active; next watcher tick should appear shortly.
- GPU snapshot: GPU0 6430 MiB / 32%, GPU1 8716 MiB / 30%.

Status check at 2026-05-06 03:33 CST:

- Direct counts:
  - CellSAM labels: 16396/16777.
  - final `samcell_refine_final` labels: 5498/16777.
  - old-config `samcell_final` labels: 2209/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:29 CST still reports `full_cellsam_prestart` active with CellSAM 16384/16777 and SAM-Cell refine 5497/16777.
- GPU snapshot: GPU0 6430 MiB / 30%, GPU1 8714 MiB / 26%.

Status check at 2026-05-06 03:36 CST:

- Direct counts:
  - CellSAM labels: 16410/16777.
  - final `samcell_refine_final` labels: 5500/16777.
  - old-config `samcell_final` labels: 2209/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:34 CST still reports `full_cellsam_prestart` active with CellSAM 16402/16777 and SAM-Cell refine 5499/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8714 MiB / 42%.

Status check at 2026-05-06 03:42 CST:

- Direct counts:
  - CellSAM labels: 16433/16777.
  - final `samcell_refine_final` labels: 5503/16777.
  - old-config `samcell_final` labels: 2220/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:39 CST still reports `full_cellsam_prestart` active with CellSAM 16423/16777 and SAM-Cell refine 5501/16777.
- GPU snapshot: GPU0 6430 MiB / 32%, GPU1 8708 MiB / 18%.

Status check at 2026-05-06 03:47 CST:

- Direct counts:
  - CellSAM labels: 16446/16777.
  - final `samcell_refine_final` labels: 5505/16777.
  - old-config `samcell_final` labels: 2245/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:44 CST still reports `full_cellsam_prestart` active with CellSAM 16439/16777 and SAM-Cell refine 5504/16777.
- GPU snapshot: GPU0 6430 MiB / 5%, GPU1 8330 MiB / 27%.

Status check at 2026-05-06 03:52 CST:

- Direct counts:
  - CellSAM labels: 16462/16777.
  - final `samcell_refine_final` labels: 5506/16777.
  - old-config `samcell_final` labels: 2263/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:49 CST still reports `full_cellsam_prestart` active with CellSAM 16453/16777 and SAM-Cell refine 5505/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8708 MiB / 43%.

Status check at 2026-05-06 03:56 CST:

- Direct counts:
  - CellSAM labels: 16471/16777.
  - final `samcell_refine_final` labels: 5509/16777.
  - old-config `samcell_final` labels: 2283/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:54 CST still reports `full_cellsam_prestart` active with CellSAM 16469/16777 and SAM-Cell refine 5508/16777.
- GPU snapshot: GPU0 6430 MiB / 19%, GPU1 8330 MiB / 29%.

Status check at 2026-05-06 04:00 CST:

- Direct counts:
  - CellSAM labels: 16476/16777.
  - final `samcell_refine_final` labels: 5510/16777.
  - old-config `samcell_final` labels: 2308/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 03:59 CST still reports `full_cellsam_prestart` active with CellSAM 16475/16777 and SAM-Cell refine 5510/16777.
- GPU snapshot: GPU0 6430 MiB / 1%, GPU1 8708 MiB / 40%.

Status check at 2026-05-06 04:06 CST:

- Direct counts:
  - CellSAM labels: 16490/16777.
  - final `samcell_refine_final` labels: 5514/16777.
  - old-config `samcell_final` labels: 2370/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:04 CST still reports `full_cellsam_prestart` active with CellSAM 16487/16777 and SAM-Cell refine 5513/16777.
- GPU snapshot: GPU0 6430 MiB / 27%, GPU1 8708 MiB / 31%.

Status check at 2026-05-06 04:10 CST:

- Direct counts:
  - CellSAM labels: 16496/16777.
  - final `samcell_refine_final` labels: 5515/16777.
  - old-config `samcell_final` labels: 2388/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:09 CST still reports `full_cellsam_prestart` active with CellSAM 16495/16777 and SAM-Cell refine 5515/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8708 MiB / 42%.

Status check at 2026-05-06 04:14 CST:

- Direct counts:
  - CellSAM labels: 16505/16777.
  - final `samcell_refine_final` labels: 5516/16777.
  - old-config `samcell_final` labels: 2425/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:09 CST still reports `full_cellsam_prestart` active with CellSAM 16495/16777 and SAM-Cell refine 5515/16777.
- GPU snapshot: GPU0 6430 MiB / 9%, GPU1 8330 MiB / 13%.

Status check at 2026-05-06 04:19 CST:

- Direct counts:
  - CellSAM labels: 16516/16777.
  - final `samcell_refine_final` labels: 5518/16777.
  - old-config `samcell_final` labels: 2480/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:14 CST still reports `full_cellsam_prestart` active with CellSAM 16506/16777 and SAM-Cell refine 5516/16777.
- GPU snapshot: GPU0 6430 MiB / 32%, GPU1 8708 MiB / 31%.

Status check at 2026-05-06 04:23 CST:

- Direct counts:
  - CellSAM labels: 16531/16777.
  - final `samcell_refine_final` labels: 5520/16777.
  - old-config `samcell_final` labels: 2514/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:19 CST still reports `full_cellsam_prestart` active with CellSAM 16518/16777 and SAM-Cell refine 5519/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8426 MiB / 35%.

Status check at 2026-05-06 04:27 CST:

- Direct counts:
  - CellSAM labels: 16556/16777.
  - final `samcell_refine_final` labels: 5522/16777.
  - old-config `samcell_final` labels: 2557/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:24 CST still reports `full_cellsam_prestart` active with CellSAM 16544/16777 and SAM-Cell refine 5521/16777.
- GPU snapshot: GPU0 6430 MiB / 1%, GPU1 8706 MiB / 45%.

Status check at 2026-05-06 04:31 CST:

- Direct counts:
  - CellSAM labels: 16580/16777.
  - final `samcell_refine_final` labels: 5525/16777.
  - old-config `samcell_final` labels: 2591/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:29 CST still reports `full_cellsam_prestart` active with CellSAM 16568/16777 and SAM-Cell refine 5523/16777.
- GPU snapshot: GPU0 6430 MiB / 0%, GPU1 8708 MiB / 15%.

Status check at 2026-05-06 04:36 CST:

- Direct counts:
  - CellSAM labels: 16596/16777.
  - final `samcell_refine_final` labels: 5533/16777.
  - old-config `samcell_final` labels: 2625/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:34 CST still reports `full_cellsam_prestart` active with CellSAM 16592/16777 and SAM-Cell refine 5531/16777.
- GPU snapshot: GPU0 6430 MiB / 11%, GPU1 8426 MiB / 54%.

Status check at 2026-05-06 04:40 CST:

- Direct counts:
  - CellSAM labels: 16615/16777.
  - final `samcell_refine_final` labels: 5537/16777.
  - old-config `samcell_final` labels: 2672/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:39 CST still reports `full_cellsam_prestart` active with CellSAM 16611/16777 and SAM-Cell refine 5537/16777.
- GPU snapshot: GPU0 6430 MiB / 1%, GPU1 8708 MiB / 28%.

Status check at 2026-05-06 04:44 CST:

- Direct counts:
  - CellSAM labels: 16637/16777.
  - final `samcell_refine_final` labels: 5541/16777.
  - old-config `samcell_final` labels: 2709/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:44 CST still reports `full_cellsam_prestart` active with CellSAM 16636/16777 and SAM-Cell refine 5541/16777.
- GPU snapshot: GPU0 6430 MiB / 45%, GPU1 8708 MiB / 91%.

Status check at 2026-05-06 04:49 CST:

- Direct counts:
  - CellSAM labels: 16655/16777.
  - final `samcell_refine_final` labels: 5545/16777.
  - old-config `samcell_final` labels: 2739/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:44 CST still reports `full_cellsam_prestart` active with CellSAM 16636/16777 and SAM-Cell refine 5541/16777.
- GPU snapshot: GPU0 6430 MiB / 19%, GPU1 8708 MiB / 18%.

Status check at 2026-05-06 04:54 CST:

- Direct counts:
  - CellSAM labels: 16675/16777.
  - final `samcell_refine_final` labels: 5549/16777.
  - old-config `samcell_final` labels: 2762/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:49 CST still reports `full_cellsam_prestart` active with CellSAM 16655/16777 and SAM-Cell refine 5545/16777.
- GPU snapshot: GPU0 6430 MiB / 16%, GPU1 8708 MiB / 35%.

Status check at 2026-05-06 05:00 CST:

- Direct counts:
  - CellSAM labels: 16703/16777.
  - final `samcell_refine_final` labels: 5552/16777.
  - old-config `samcell_final` labels: 2825/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:59 CST still reports `full_cellsam_prestart` active with CellSAM 16701/16777 and SAM-Cell refine 5552/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8708 MiB / 40%.

Status check at 2026-05-06 05:04 CST:

- Direct counts:
  - CellSAM labels: 16719/16777.
  - final `samcell_refine_final` labels: 5554/16777.
  - old-config `samcell_final` labels: 2867/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 04:59 CST still reports `full_cellsam_prestart` active with CellSAM 16701/16777 and SAM-Cell refine 5552/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8708 MiB / 41%.

Status check at 2026-05-06 05:08 CST:

- Direct counts:
  - CellSAM labels: 16737/16777.
  - final `samcell_refine_final` labels: 5556/16777.
  - old-config `samcell_final` labels: 2898/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 05:04 CST still reports `full_cellsam_prestart` active with CellSAM 16722/16777 and SAM-Cell refine 5554/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8708 MiB / 22%.

Status check at 2026-05-06 05:13 CST:

- Direct counts:
  - CellSAM labels: 16755/16777.
  - final `samcell_refine_final` labels: 5559/16777.
  - old-config `samcell_final` labels: 2939/16777.
- Metrics still pending:
  - `cellsam_generalist/metrics/summary_by_source.csv` missing.
  - `samcell_refine_final/summary.csv` missing.
  - `samcell_final/summary.csv` missing.
- `full_cellsam_prestart` remains alive, so the GPU0-specific watcher has not started `full_samcell_refine_extra_after_cellsam`.
- Latest GPU0-specific watcher row at 05:09 CST still reports `full_cellsam_prestart` active with CellSAM 16742/16777 and SAM-Cell refine 5558/16777.
- GPU snapshot: GPU0 6430 MiB / 3%, GPU1 8708 MiB / 42%.

Status update at 2026-05-06 05:22 CST:

- CellSAM full inference labels are complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present and non-empty.
  - Summary has `ALL n=16777`, five source rows, and `SOURCE_MACRO`.
  - Key metric: CellSAM full CellCosmos `ALL` PQ 0.5388845173.
- At 05:18 CST, `full_cellsam_prestart` was still alive but only running `eval_label_dir.py`; CellSAM GPU inference was done.
- Manual early start was performed at 2026-05-06 05:20 CST because CellSAM labels were complete and GPU0 was available:
  - Started tmux `full_samcell_refine_extra_after_cellsam`.
  - Script used: `scripts/start_extra_samcell_refine_after_cellsam_main_done_20260505.sh` with `WAIT_SESSION=__cellsam_labels_complete_manual_start__`.
  - Helper manifest: `experiments/cellcosmos_full_16777_20260503/manifests/full_tail_from_12500_for_samcell_refine_extra_after_cellsam.csv`.
  - Helper rows: 4277 from index 12500.
  - Output: `experiments/cellcosmos_full_16777_20260503/samcell_refine_final`.
  - Mode: `--save_outputs --use_cache --no_summary`.
- Post-start check at 05:22 CST:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5563/16777.
  - `samcell_refine_final/summary.csv`: still pending.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:28 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5573/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4146 MiB / 23%, GPU1 4286 MiB / 39%.
- Old-config SAM-Cell is still running as a non-final comparator/ablation:
  - `samcell_final` labels: 3084/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:31 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running with both GPUs used:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5578/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 40%, GPU1 4286 MiB / 29%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3124/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:38 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine remains the active blocker:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5588/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 17%, GPU1 4286 MiB / 30%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3227/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:42 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5594/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 44%, GPU1 4286 MiB / 41%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3293/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:46 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5599/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 53%, GPU1 4286 MiB / 22%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3335/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:51 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5606/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 29%, GPU1 4286 MiB / 42%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3388/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:55 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5611/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4150 MiB / 42%, GPU1 4286 MiB / 47%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3435/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 05:59 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5619/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 37%, GPU1 4286 MiB / 45%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3499/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 06:04 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5624/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 21%, GPU1 4286 MiB / 40%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3544/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 06:08 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5629/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 56%, GPU1 4286 MiB / 9%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3596/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 06:13 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5637/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 40%, GPU1 4286 MiB / 55%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3659/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 06:18 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5646/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 24%, GPU1 4286 MiB / 40%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3709/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 06:23 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
  - Hourly watch row at 05:27 CST records CellSAM metric status as `done`.
- SAM-Cell refine is still running:
  - Active sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5651/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 38%, GPU1 4286 MiB / 40%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3734/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 06:29 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- Extra SAM-Cell refine after CellSAM is active:
  - `full_samcell_refine_extra_after_cellsam` is alive on the freed GPU0 path.
  - Active refine sessions include `full_samcell_refine_final`, `full_samcell_refine_tail_helper`, and `full_samcell_refine_extra_after_cellsam`.
  - `samcell_refine_final` labels: 5660/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - GPU snapshot: GPU0 4148 MiB / 29%, GPU1 4286 MiB / 52%.
- Old-config SAM-Cell remains a non-final comparator/ablation:
  - `samcell_final` labels: 3800/16777.
  - `samcell_final/summary.csv`: pending.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Execution update at 2026-05-06 06:43 CST:

- Added and launched `scripts/start_samcell_refine_gap_helpers_20260506.sh` to improve full SAM-Cell refine throughput.
- Reason: existing refine coverage had a large gap between the main run around row 2053 and the tail helper starting at row 8000, while both A100s had substantial idle memory/utilization headroom.
- New non-overlapping helper sessions:
  - `full_samcell_refine_gap_2500_5000` on GPU0, manifest `full_gap_2500_5000_for_full_samcell_refine_gap_2500_5000.csv`.
  - `full_samcell_refine_gap_5000_8000` on GPU1, manifest `full_gap_5000_8000_for_full_samcell_refine_gap_5000_8000.csv`.
- Both helpers use `--save_outputs --use_cache --no_summary` and write only cached final labels/overlays/instances into `samcell_refine_final`; they must not create `summary.csv`.
- Direct post-launch check at 06:42 CST: active refine sessions include main, tail, extra-after-CellSAM, and both gap helpers. `samcell_refine_final` labels increased to 5697/16777; `samcell_refine_final/summary.csv` remains pending.
- GPU snapshot after helper launch: GPU0 6140 MiB / 5%, GPU1 6424 MiB / 63%.
- Stability check at 06:47 CST: `samcell_refine_final` labels increased to 5779/16777. Both gap-helper Python processes are alive with high CPU usage, but their logs have not printed per-image progress yet, likely still in model/pipeline initialization.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Execution update at 2026-05-06 07:00 CST:

- Added and launched `scripts/start_samcell_refine_cached_summary_watcher_20260506.sh` in tmux `samcell_refine_cached_summary_watcher_20260506`.
- Purpose: avoid waiting for the original sequential full run to write `samcell_refine_final/summary.csv` after helper sessions have already filled all labels.
- Behavior:
  - Polls `samcell_refine_final/labels` every 300 seconds.
  - Requires labels to reach 16777/16777, then waits 600 seconds and rechecks stability.
  - Starts `full_samcell_refine_cached_summary_eval` only if `samcell_refine_final/summary.csv` is still missing.
  - The summary eval runs `scripts/eval_devset.py --use_cache` on the full manifest, so it reads cached labels and GT instead of running SAM2 inference.
- Initial watcher log at 06:59 CST: labels 5998/16777; direct count immediately after was 6013/16777.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 07:11 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 6191/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - Cached summary watcher is alive and recorded 5998/16777 at 06:59, 6088/16777 at 07:04, and 6162/16777 at 07:09.
  - Active refine sessions include main, tail helper, extra-after-CellSAM, both gap helpers, and cached summary watcher.
  - GPU snapshot: GPU0 6138 MiB / 5%, GPU1 6424 MiB / 50%.
- The current parallel label-generation strategy is still productive; do not start overlapping tail workers unless label growth stalls or a helper dies.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Execution update at 2026-05-06 07:23 CST:

- Added and launched `scripts/start_samcell_refine_late_tail_helper_20260506.sh`.
- Reason: direct interval audit showed `14500-end` was still 0/2277 while earlier intervals were already being filled. Waiting for the 12500-start helper to reach 14500 would delay final label completion.
- New helper:
  - Session: `full_samcell_refine_late_tail_14500_end`.
  - Manifest: `experiments/cellcosmos_full_16777_20260503/manifests/full_tail_from_14500_for_full_samcell_refine_late_tail_14500_end.csv`.
  - Rows: 2277, start index 14500.
  - GPU: 0.
  - Command mode: `--save_outputs --use_cache --no_summary`.
- Verification at 07:22 CST: session alive, Python process alive, GPU0 memory increased to 8279 MiB, and `samcell_refine_final` labels increased to 6393/16777.
- `samcell_refine_final/summary.csv` remains pending; cached-summary watcher remains responsible for starting the cached full metrics pass after labels reach 16777/16777 and remain stable.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 07:28 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 6477/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - Cached summary watcher is alive and recorded 6345/16777 at 07:19 and 6422/16777 at 07:24.
  - Interval audit: `main_0_2500` 2172/2500, `gap_2500_5000` 398/2500, `gap_5000_8000` 329/3000, `tail_8000_10000` 2000/2000, `tail_10000_12500` 1476/2500, `tail_12500_14500` 92/2000, `late_14500_end` 10/2277.
- Late-tail helper `full_samcell_refine_late_tail_14500_end` is now contributing to the final interval.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 07:35 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 6556/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - Cached summary watcher is alive; latest watcher count at 07:29 CST was 6488/16777.
  - Interval audit: `main_0_2500` 2173/2500, `gap_2500_5000` 440/2500, `gap_5000_8000` 353/3000, `tail_8000_10000` 2000/2000, `tail_10000_12500` 1477/2500, `midtail_12500_13500` 95/1000, `midtail_13500_14500` 0/1000, `late_14500_end` 18/2277.
  - Server load average is high at about 152/185/185, and active eval processes are already CPU-heavy, so do not add more helpers unless a current helper dies or label growth stalls.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 07:47 CST:

- CellSAM remains complete:
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 6746/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
  - Cached summary watcher is alive and recorded 6642/16777 at 07:39 and 6713/16777 at 07:44.
  - Active refine sessions: main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, and cached summary watcher.
- Server remains high-load at about 176/180/182, with GPU0/GPU1 active; do not add more helpers while labels continue growing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 07:52 CST:

- CellSAM remains complete:
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 6806/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
  - Cached summary watcher is alive and recorded 6779/16777 at 07:49.
  - Hourly watch row at 07:27 recorded CellSAM metrics `done` and SAM-Cell metrics `pending`.
  - Active refine helper sessions remain alive.
- Server load is very high at about 214/207/194; do not add more helpers while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 07:57 CST:

- CellSAM remains complete:
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 6890/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
  - Cached summary watcher is alive and recorded 6853/16777 at 07:54.
  - Active refine helper sessions remain alive.
  - Server load remains high at about 159/189/190; do not add more helpers while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 08:05 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- The card freed by CellSAM is already being used for SAM-Cell:
  - `full_samcell_refine_extra_after_cellsam` is alive.
  - Active refine sessions include main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, and cached summary watcher.
- SAM-Cell refine is still running and growing:
  - `samcell_refine_final` direct labels: 7039/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
  - Cached summary watcher recorded 6929/16777 at 07:59.
  - Interval audit: `main_0_2500` 2176/2500, `gap_2500_5000` 624/2500, `gap_5000_8000` 590/3000, `tail_8000_10000` 2000/2000, `tail_10000_12500` 1487/2500, `midtail_12500_13500` 108/1000, `midtail_13500_14500` 0/1000, `late_14500_end` 54/2277.
- Server load is very high at about 225/214/201. Do not add another helper while existing processes are still increasing labels; the 13500-14500 gap should be revisited only if label growth stalls or a current helper exits.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 08:13 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine continues to grow:
  - `samcell_refine_final` direct labels: 7148/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
  - Cached summary watcher recorded 7001/16777 at 08:04 and 7085/16777 at 08:09.
  - Hourly watch at 07:27 recorded CellSAM metrics `done` and SAM-Cell metrics `pending`.
- Active refine sessions remain alive: main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, and cached summary watcher.
- Process check showed all six `eval_devset.py` refine workers with high CPU usage. The main, tail, and gap helpers are printing progress; extra-after-CellSAM and late-tail have sparse pane output but live high-CPU Python processes.
- Server load remains very high at about 215/200/199. Do not add another helper while current workers remain active and label count is increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Resource-priority update at 2026-05-06 08:25 CST:

- Old non-final `full_samcell_final` is still running as a preserved ablation/comparator:
  - output: `experiments/cellcosmos_full_16777_20260503/samcell_final`.
  - active Python PID observed: `2193187`.
  - It was consuming about 15 CPU cores while the final refine run was still incomplete.
- To prioritize the accepted final model without deleting or stopping old outputs, PID `2193187` was reniced from priority `0` to nice `10`.
  - This is a scheduling-priority change only; it does not alter predictions or remove artifacts.
- Post-change status:
  - `samcell_refine_final` direct labels: 7341/16777.
  - Cached summary watcher recorded 7338/16777 at 08:24.
  - `samcell_refine_final/summary.csv`: pending.
  - Server load remained high at about 193/184/190.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status/resource update at 2026-05-06 08:31 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 7434/16777.
  - Cached summary watcher recorded 7428/16777 at 08:29.
  - Hourly watch at 08:27 recorded CellSAM metrics `done` and SAM-Cell metrics `pending`.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active refine sessions remain alive: main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, and cached summary watcher.
- Old non-final `full_samcell_final` PID `2193187` was further reniced from nice `10` to nice `19` to minimize CPU contention with final refine while preserving its partial ablation/comparator output.
- Server load remains high at about 164/196/195; do not add more helper processes while final refine labels are increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 08:36 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 7539/16777.
  - Cached summary watcher recorded 7514/16777 at 08:34.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active sessions remain alive: old non-final `full_samcell_final`, final refine main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, hourly watch, and cached summary watcher.
- Server load remains high at about 204/194/194 with both GPUs active. Do not add more helper processes while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 08:43 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 7662/16777.
  - Cached summary watcher recorded 7602/16777 at 08:39.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Interval audit:
  - `main_0_2500`: 2179/2500.
  - `gap_2500_5000`: 913/2500.
  - `gap_5000_8000`: 846/3000.
  - `tail_8000_10000`: 2000/2000.
  - `tail_10000_12500`: 1498/2500.
  - `midtail_12500_13500`: 126/1000.
  - `midtail_13500_14500`: 0/1000.
  - `late_14500_end`: 100/2277.
- All six final refine `eval_devset.py` workers remain alive with high CPU usage. Old non-final `samcell_final` worker remains alive at nice `19`.
- Server load remains very high at about 208/189/190. Do not start an additional midtail helper while current final refine workers continue increasing labels.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 08:49 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 7763/16777.
  - Cached summary watcher recorded 7675/16777 at 08:44.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active sessions remain alive: old non-final `full_samcell_final`, final refine main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, hourly watch, and cached summary watcher.
- Server load remains very high at about 216/206/198. Both GPUs are active. Do not add more helpers while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 08:56 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 7880/16777.
  - Cached summary watcher recorded 7861/16777 at 08:54.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- All six final refine `eval_devset.py` workers remain alive with high CPU usage:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, and late-tail 14500-end.
  - Old non-final `samcell_final` worker remains alive at nice `19`.
- Server load remains very high at about 202/200/197. Do not add more helper processes while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 09:03 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 7999/16777.
  - Cached summary watcher recorded 7948/16777 at 08:59.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active sessions remain alive: old non-final `full_samcell_final`, final refine main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, hourly watch, and cached summary watcher.
- Server load remains very high at about 220/210/202. Do not add more helper processes while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 09:08 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 8090/16777.
  - Cached summary watcher recorded 8033/16777 at 09:04.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active sessions remain alive: old non-final `full_samcell_final`, final refine main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, hourly watch, and cached summary watcher.
- Server load remains very high at about 214/205/201. Do not add more helper processes while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 09:15 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 8179/16777.
  - Cached summary watcher recorded 8117/16777 at 09:09.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active sessions remain alive: old non-final `full_samcell_final`, final refine main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, hourly watch, and cached summary watcher.
- Server load remains very high at about 198/208/205. Do not add more helper processes while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 09:20 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 8266/16777.
  - Cached summary watcher recorded 8260/16777 at 09:19.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active sessions remain alive: old non-final `full_samcell_final`, final refine main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, hourly watch, and cached summary watcher.
- Server load remains very high at about 212/205/204, with both GPUs active. Do not add more helper processes while current label generation continues.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Resource-priority update at 2026-05-06 09:30 CST:

- Old non-final `samcell_final` worker was still consuming about 15 CPU cores at nice `19` while the accepted final `samcell_refine_final` was incomplete.
- Added and launched a reversible pause watcher:

```text
script: scripts/pause_old_samcell_until_refine_done_20260506.sh
tmux: pause_old_samcell_until_refine_done_20260506
log: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/pause_old_samcell_until_refine_done_20260506.log
```

- Behavior:
  - Finds the old non-final `eval_devset.py` process for `samcell_final`.
  - Sends `SIGSTOP` to pause it without deleting output or killing the tmux session.
  - Polls until `samcell_refine_final/summary.csv` exists.
  - Sends `SIGCONT` to resume the old non-final process after final summary appears.
- Verification:
  - Old non-final PID `2193187` changed to stopped state `TNl+`.
  - `samcell_refine_final` direct labels: 8392/16777.
  - `samcell_refine_final/summary.csv`: pending.
- This should reduce CPU contention for final refine while preserving the old ablation/comparator run for later completion.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status/scheduling update at 2026-05-06 09:41 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 8545/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- The old non-final `samcell_final` process remains paused by `pause_old_samcell_until_refine_done_20260506` until final summary appears.
- Interval audit still showed `midtail_13500_14500` at 0/1000, but server load was still high. Added and launched a safe delayed midtail watcher:

```text
script: scripts/start_samcell_refine_midtail_when_safe_20260506.sh
tmux: start_samcell_refine_midtail_when_safe_20260506
target session: full_samcell_refine_midtail_13500_14500
manifest: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/manifests/full_midtail_13500_14500_for_full_samcell_refine_midtail_13500_14500.csv
rows: 1000
mode: --save_outputs --use_cache --no_summary
start condition: load1 <= 130
```

- Initial midtail watcher log:
  - wrote the 1000-row manifest.
  - did not start worker because `load1=165 > threshold=130`.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 09:49 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 8653/16777.
  - Cached summary watcher recorded 8594/16777 at 09:44.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Old non-final `samcell_final` remains paused:
  - `pause_old_samcell_until_refine_done_20260506` is alive.
  - latest log at 09:44 recorded final labels 8588/16777 and old PID still paused.
- Delayed midtail watcher remains alive:
  - latest log at 09:46: load1=183 > threshold=130, labels=8614/16777.
  - target worker `full_samcell_refine_midtail_13500_14500` has not started yet.
- Server load is lower than before but still high at about 162/164/176. Keep delayed midtail trigger; do not force-start a seventh final worker yet.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 09:57 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine is still incomplete but growing:
  - `samcell_refine_final` direct labels: 8757/16777.
  - Cached summary watcher recorded 8723/16777 at 09:54.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Old non-final `samcell_final` remains paused:
  - pause watcher is alive.
  - latest pause log at 09:54 recorded final labels 8718/16777 and old PID still paused.
- Delayed midtail watcher remains alive but has not triggered:
  - 09:46 log: load1=183 > threshold=130, labels=8614/16777.
  - 09:51 log: load1=193 > threshold=130, labels=8675/16777.
  - 09:56 log: load1=181 > threshold=130, labels=8743/16777.
- Server load at direct check was about 153/178/181. This is lower, but still high enough that forcing a seventh final worker may overload CPU/IO. Keep the delayed trigger for now.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 10:07 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- The card freed by CellSAM is already being used for final SAM-Cell refine:
  - `full_samcell_refine_extra_after_cellsam` is alive.
  - Active refine sessions include main, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, and cached summary watcher.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 8923/16777.
  - Cached summary watcher recorded 8885/16777 at 10:04 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Old non-final `samcell_final` remains paused:
  - `samcell_final` labels: 4834/16777.
  - pause watcher is alive and latest log recorded old PID still paused at 10:04 CST.
- Delayed midtail watcher remains alive but has not triggered:
  - latest log at 10:06 CST: `load1=177 > threshold=130`, labels 8907/16777.
- Server load remains high at about 172/173/176. GPU memory is moderate, but CPU/IO load is still the bottleneck, so do not force-start another helper while labels are increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 10:16 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 9079/16777.
  - Cached summary watcher recorded 9055/16777 at 10:14 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Interval audit:
  - `main_0_2500`: 2204/2500.
  - `gap_2500_5000`: 1445/2500.
  - `gap_5000_8000`: 1534/3000.
  - `tail_8000_10000`: 2000/2000.
  - `tail_10000_12500`: 1529/2500.
  - `midtail_12500_13500`: 168/1000.
  - `midtail_13500_14500`: 0/1000.
  - `late_14500_end`: 199/2277.
- The remaining explicit empty interval is still `13500:14500`, but server load is very high at about 199/186/180. Keep `start_samcell_refine_midtail_when_safe_20260506` as the trigger instead of force-starting another worker.
- Old non-final `samcell_final` remains paused until final refine summary appears.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Execution update at 2026-05-06 10:31 CST:

- Adjusted and restarted the delayed midtail watcher:
  - `scripts/start_samcell_refine_midtail_when_safe_20260506.sh`
  - default `LOAD_THRESHOLD` changed from 130 to 160.
  - target worker command now runs through `nice -n 10` so it contributes to the empty interval without taking normal-priority CPU from existing final workers.
- The restarted watcher triggered at 2026-05-06 10:29 CST:
  - session: `full_samcell_refine_midtail_13500_14500`.
  - manifest: `experiments/cellcosmos_full_16777_20260503/manifests/full_midtail_13500_14500_for_full_samcell_refine_midtail_13500_14500.csv`.
  - rows: 1000, index range 13500:14500.
  - GPU: 1.
  - mode: `--save_outputs --use_cache --no_summary`.
  - start condition observed: load1=147, labels=9334/16777.
- Verification:
  - target session is alive.
  - Python PID `2250811` has nice value 10 (`STAT=SNl+`) and high CPU usage, confirming the low-priority worker is active.
  - `samcell_refine_final` direct labels: 9366/16777 at 10:31 CST.
  - `samcell_refine_final/summary.csv`: pending.
- All major uncovered intervals now have a corresponding final refine worker. Continue waiting for label completion; cached summary watcher remains responsible for writing final full metrics after labels reach 16777/16777 and stabilize.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 10:43 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 9592/16777.
  - Cached summary watcher recorded 9534/16777 at 10:39 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Interval audit:
  - `main_0_2500`: 2206/2500.
  - `gap_2500_5000`: 1662/2500.
  - `gap_5000_8000`: 1781/3000.
  - `tail_8000_10000`: 2000/2000.
  - `tail_10000_12500`: 1538/2500.
  - `midtail_12500_13500`: 179/1000.
  - `midtail_13500_14500`: 7/1000.
  - `late_14500_end`: 219/2277.
- The new midtail worker is producing labels:
  - PID `2250811`, nice value 10, high CPU usage.
  - This confirms the last explicit empty interval is now covered.
- Server load is very high at about 225/202/188, so do not add more workers. Continue waiting for all labels to fill and for cached summary watcher to start final metrics.
- Old non-final `samcell_final` remains paused until final refine summary appears.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 10:51 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 9765/16777.
  - Cached summary watcher recorded 9748/16777 at 10:49 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - `full_samcell_refine_final`.
  - `full_samcell_refine_tail_helper`.
  - `full_samcell_refine_extra_after_cellsam`.
  - `full_samcell_refine_gap_2500_5000`.
  - `full_samcell_refine_gap_5000_8000`.
  - `full_samcell_refine_late_tail_14500_end`.
  - `full_samcell_refine_midtail_13500_14500`.
  - `samcell_refine_cached_summary_watcher_20260506`.
- Old non-final `samcell_final` remains paused by `pause_old_samcell_until_refine_done_20260506`.
- Server load remains very high at about 225/195/190. Do not add more workers while all intervals are covered and labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:00 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 9906/16777.
  - Cached summary watcher recorded 9811/16777 at 10:54 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Interval audit:
  - `main_0_2500`: 2207/2500.
  - `gap_2500_5000`: 1813/2500.
  - `gap_5000_8000`: 1902/3000.
  - `tail_8000_10000`: 2000/2000.
  - `tail_10000_12500`: 1543/2500.
  - `midtail_12500_13500`: 187/1000.
  - `midtail_13500_14500`: 14/1000.
  - `late_14500_end`: 240/2277.
- All major intervals are covered and increasing. Process count for active `eval_devset.py` commands writing to `samcell_refine_final` was 8 at this audit, consistent with the main full pass plus no-summary helpers.
- Server load is still high at about 178/184/189. Do not add more workers; wait for label completion and cached summary generation.
- Old non-final `samcell_final` remains paused until final refine summary appears.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:10 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but productive:
  - `samcell_refine_final` direct labels: 10061/16777.
  - Cached summary watcher recorded 10053/16777 at 11:09 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains very high at about 220/215/204. Do not add more workers; wait for label completion and cached summary generation.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:19 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 10188/16777.
  - Cached summary watcher recorded 10121/16777 at 11:14 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 166/186/195. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:27 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 10324/16777.
  - Cached summary watcher recorded 10275/16777 at 11:24 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 208/214/206. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:34 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 10436/16777.
  - Cached summary watcher recorded 10354/16777 at 11:29 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 221/206/204. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:43 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 10579/16777.
  - Cached summary watcher recorded 10509/16777 at 11:39 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load is very high at about 239/222/212. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:49 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 10676/16777.
  - Cached summary watcher recorded 10595/16777 at 11:44 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load is very high at about 231/220/214. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 11:56 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 10824/16777.
  - Cached summary watcher recorded 10795/16777 at 11:54 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load is very high at about 215/220/216. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:05 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11032/16777.
  - Cached summary watcher recorded 11017/16777 at 12:04 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 190/201/209. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:11 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11168/16777.
  - Cached summary watcher recorded 11137/16777 at 12:09 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load is very high at about 246/215/212. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:18 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11280/16777.
  - Cached summary watcher recorded 11216/16777 at 12:14 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load is very high at about 236/204/206. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:24 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11375/16777.
  - Cached summary watcher recorded 11306/16777 at 12:19 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 166/192/201. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:30 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11466/16777.
  - Cached summary watcher recorded 11460/16777 at 12:29 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 219/204/202. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:36 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11607/16777.
  - Cached summary watcher recorded 11573/16777 at 12:34 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 193/192/197. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Status check at 2026-05-06 12:42 CST:

- CellSAM remains complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present, 1982 bytes.
- SAM-Cell refine remains incomplete but still increasing:
  - `samcell_refine_final` direct labels: 11699/16777.
  - Cached summary watcher recorded 11660/16777 at 12:39 CST.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Active final refine sessions remain alive:
  - main full run, tail helper, extra-after-CellSAM, gap 2500-5000, gap 5000-8000, late-tail 14500-end, midtail 13500-14500, and cached summary watcher.
- Old non-final `samcell_final` remains paused.
- Server load remains high at about 223/208/203. Do not add more workers while labels continue increasing.
- Completion audit remains blocked by final SAM-Cell refine full metrics.

Execution/status update at 2026-05-06 18:20 CST:

- CellSAM full inference and metrics remain complete:
  - `cellsam_generalist/predictions/labels`: 16777/16777.
  - `cellsam_generalist/metrics/summary_by_source.csv`: present.
- SAM-Cell accepted final refine remains incomplete but has advanced substantially:
  - active output: `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final`.
  - direct labels: 14581/16777.
  - `samcell_refine_final/summary.csv`: pending.
  - `samcell_refine_final/per_image.csv`: pending.
- Interval coverage at 18:20 CST:
  - 0:2500, 2500:5000, 5000:8000, and 8000:10000 are complete.
  - 10000:12500 is 1740/2500.
  - 12500:13500 is 443/1000.
  - 13500:14500 is 548/1000.
  - 14500:16777 is 1850/2277.
- Because CellSAM is complete and both GPUs had usable headroom, launched an additional no-summary SAM-Cell helper:
  - tmux: `full_samcell_refine_tail_11500_12500`.
  - manifest: `experiments/cellcosmos_full_16777_20260503/manifests/full_tail_11500_12500_for_full_samcell_refine_tail_11500_12500.csv`.
  - run script: `experiments/cellcosmos_full_16777_20260503/run_full_samcell_refine_tail_11500_12500.sh`.
  - GPU: 0.
  - mode: `--save_outputs --use_cache --no_summary`, so it must not create partial `summary.csv`.
- Active final-refine sessions now include `full_samcell_refine_extra_after_cellsam`, `full_samcell_refine_late_tail_14500_end`, `full_samcell_refine_midtail_13500_14500`, `full_samcell_refine_tail_11500_12500`, `full_samcell_refine_tail_helper`, and `samcell_refine_cached_summary_watcher_20260506`.
- Completion audit remains blocked until `samcell_refine_final` has 16777 labels plus full `per_image.csv` and `summary.csv`.

Follow-up status check at 2026-05-06 18:29 CST:

- `samcell_refine_final` labels increased to 14633/16777.
- `full_samcell_refine_tail_11500_12500` remains alive.
- Active final-refine `eval_devset.py` process count is 6.
- GPUs: GPU0 about 6288 MiB / 68%, GPU1 about 6426 MiB / 22%.
- `samcell_refine_final/summary.csv` and `per_image.csv` remain pending.

Execution/status update at 2026-05-06 18:43 CST:

- Added one more narrow no-summary helper for the slow 12500:13500 interval:
  - tmux: `full_samcell_refine_midtail_12500_13500`.
  - manifest: `experiments/cellcosmos_full_16777_20260503/manifests/full_midtail_12500_13500_for_full_samcell_refine_midtail_12500_13500.csv`.
  - GPU: 1.
  - mode: `--save_outputs --use_cache --no_summary`.
- Verification after launch:
  - `samcell_refine_final` labels: 14700/16777.
  - active final-refine eval process count: 7.
  - GPU0 about 6288 MiB / 40%, GPU1 about 8417 MiB / 52%.
  - `summary.csv` and `per_image.csv` remain pending.
- Updated `scripts/remote_full_inference_status_20260506.py` so future status checks report all `samcell_refine` tmux sessions, including newly added narrow helpers.

Follow-up status check at 2026-05-06 18:51 CST:

- `samcell_refine_final` labels increased to 14735/16777.
- `summary.csv` and `per_image.csv` remain pending.
- Active final-refine eval process count is 7.
- The updated status script now correctly lists `full_samcell_refine_midtail_12500_13500`.
- Server load is high again at about 217/182/162, so do not add more helpers unless progress stalls or a worker exits.

Completion-audit update at 2026-05-06 19:04 CST:

- Added completion audit script:
  - local/server: `scripts/remote_full_inference_completion_audit_20260506.py`.
  - It checks CellSAM labels, CellSAM summary `ALL n=16777`, SAM-Cell refine labels, SAM-Cell refine `per_image.csv` rows, and SAM-Cell refine summary `ALL n=16777`.
- Audit result at 19:04 CST: `complete=false`.
- Passing checks:
  - CellSAM labels: 16777/16777.
  - CellSAM summary has `ALL n=16777`.
- Failing checks:
  - SAM-Cell refine labels: 14822/16777.
  - SAM-Cell refine `per_image.csv`: 0/16777 rows because metrics have not started.
  - SAM-Cell refine `summary.csv`: missing/no `ALL n=16777`.
- All remaining intervals already have active helper coverage; server load is high, so do not add more duplicate workers unless progress stalls or a worker exits.

Status/audit update at 2026-05-06 19:19 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 14871/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1751/2500.
  - 12500:13500 is 458/1000.
  - 13500:14500 is 696/1000.
  - 14500:16777 is 1966/2277.
- Active final-refine eval process count is 7; all remaining intervals have helper coverage.
- Server load is high at about 227/192/181. Do not add more helpers unless progress stalls or a process exits.
- Process/log check:
  - `full_samcell_refine_extra_after_cellsam` is actively processing TissueNet around 344/4277.
  - `full_samcell_refine_late_tail_14500_end` is actively processing around 1845/2277.
  - No old non-final `samcell_final` eval process was observed competing for CPU.

Status/audit update at 2026-05-06 19:31 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 14932/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1752/2500.
  - 12500:13500 is 460/1000.
  - 13500:14500 is 738/1000.
  - 14500:16777 is 1982/2277.
- Active final-refine eval process count remains 7.
- Server load decreased from the previous spike but remains high at about 139/169/175; do not add helpers unless a process exits or an interval stalls for a long period.
- Narrow helper pane checks show normal progress, not a hang:
  - `full_samcell_refine_tail_11500_12500`: around `[253/1000]`.
  - `full_samcell_refine_midtail_12500_13500`: around `[461/1000]`.

Status/audit update at 2026-05-06 19:40 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 14976/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1753/2500.
  - 12500:13500 is 463/1000.
  - 13500:14500 is 770/1000.
  - 14500:16777 is 1990/2277.
- Active final-refine eval process count remains 7.
- Server load is about 198/179/176; all remaining intervals have active coverage, so do not add more workers.
- Process/pane checks show helpers are active rather than hung:
  - `full_samcell_refine_tail_helper`: around `[3728/8777]`.
  - `full_samcell_refine_extra_after_cellsam`: around `[344/4277]`.
  - `full_samcell_refine_late_tail_14500_end`: around `[1845/2277]`.

Status/audit update at 2026-05-06 19:53 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 15033/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1754/2500.
  - 12500:13500 is 466/1000.
  - 13500:14500 is 811/1000.
  - 14500:16777 is 2002/2277.
- Active final-refine eval process count remains 7.
- Server load is about 189/183/180. All remaining intervals are covered and still increasing, so do not add more helpers.

Manual monitoring policy update at 2026-05-06 19:55 CST:

- The user explicitly said frequent manual checks are unnecessary.
- Do not keep issuing dense SSH status/audit checks while all final-refine helpers remain active and automatic watchers are running.
- Rely on the existing server watchers unless the user asks for a check or there is a clear completion window:
  - `hourly_full_inference_watch_20260504` records hourly status.
  - `samcell_refine_cached_summary_watcher_20260506` waits for `samcell_refine_final` labels to reach 16777/16777 and then triggers cached full metrics if needed.
- Suggested manual check cadence: no more than hourly during active label generation, and only run completion audit when labels are likely complete or metrics files appear.
- Before marking the goal complete, still run `scripts/remote_full_inference_completion_audit_20260506.py` and require all checks to pass.

Low-frequency status/audit and scheduling update at 2026-05-06 22:22 CST:

- Manual check was run after more than two hours, consistent with the reduced monitoring policy.
- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 15617/16777 at status check, 15618/16777 at helper launch.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state at 22:20 CST:
  - 0:10000 complete.
  - 10000:12500 is 1780/2500.
  - 12500:13500 is 560/1000.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Active final-refine eval process count had dropped to 5 and server load to about 92/94/108, so two narrow no-summary helpers were launched only for remaining tails:
  - `full_samcell_refine_late_11780_12500` on GPU0, manifest `experiments/cellcosmos_full_16777_20260503/manifests/full_late_11780_12500_for_full_samcell_refine_late_11780_12500.csv`.
  - `full_samcell_refine_late_13060_13500` on GPU1, manifest `experiments/cellcosmos_full_16777_20260503/manifests/full_late_13060_13500_for_full_samcell_refine_late_13060_13500.csv`.
- Both helpers use `scripts/start_samcell_refine_tail_11500_12500_helper_20260506.sh` with `--save_outputs --use_cache --no_summary`; they must not create partial metrics.
- Do not run dense follow-up queries. Next manual check should wait about an hour or until metrics files appear.

Low-frequency status/audit update at 2026-05-07 00:44 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 15813/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1809/2500.
  - 12500:13500 is 727/1000.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Remaining labels are concentrated in two active intervals: 11809:12500 and 13227:13500.
- Active final-refine eval process count is 7.
- Server load is about 170/167/174; do not add more helpers. Continue relying on existing helpers and cached summary watcher.

User-requested status/audit update at 2026-05-07 02:03 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 15932/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1822/2500.
  - 12500:13500 is 833/1000.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Remaining labels are concentrated in two active intervals: 11822:12500 and 13333:13500.
- Active final-refine eval process count is 7.
- Server load is about 174/154/158; do not add more helpers. Continue relying on existing helpers and cached summary watcher.

User-requested status/audit update at 2026-05-07 04:39 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 16179/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1906/2500.
  - 12500:13500 is 996/1000.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Remaining labels are mostly concentrated in 11906:12500; the 12500:13500 interval has only 4 missing labels left.
- Active final-refine eval process count is 6.
- Server load is about 127/144/157; GPU1 utilization was 0% in this sample but the narrow 13060:13500 helper session is still listed. Do not add new workers unless the remaining 4 labels in 12500:13500 stay missing in the next low-frequency check.

User-requested status/audit update at 2026-05-07 04:52 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 16198/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 1921/2500.
  - 12500:13500 is complete.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Remaining labels are now concentrated only in 11921:12500.
- Active final-refine eval process count is 4.
- Server load is about 102/112/132; both GPUs show moderate utilization. Do not add new workers; continue relying on existing tail workers and cached summary watcher.

Automation update at 2026-05-07 05:22 CST:

- Added scripts:
  - `scripts/build_full_model_metric_comparison_20260507.py`
  - `scripts/farood_module_attribution_20260507.py`
  - `scripts/run_farood_attribution_20260507.sh`
  - `scripts/hourly_full_postprocess_and_farood_20260507.sh`
- Local and remote syntax checks passed:
  - `python -m py_compile` for both Python scripts.
  - `bash -n` for both shell scripts.
- Remote single-pass verification using `RUN_ONCE=1` succeeded at 2026-05-07 05:20 CST:
  - CellSAM checks pass.
  - SAM-Cell refine labels: 16230/16777.
  - SAM-Cell `per_image.csv`: 0/16777 rows.
  - SAM-Cell `summary.csv`: missing/no `ALL n=16777`.
  - The script did not start duplicate summary or Far-OOD attribution early.
- Started tmux watcher:
  - session: `hourly_full_postprocess_and_farood_20260507`
  - script: `/backup/taotao_work/sam_cell/scripts/hourly_full_postprocess_and_farood_20260507.sh`
  - log: `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/hourly_full_postprocess_and_farood_20260507/watch.log`
- Watcher behavior:
  - Runs one pass every 3600 seconds.
  - Ensures Cellpose and CellSAM full metrics exist.
  - When SAM-Cell labels reach 16777 and full metrics are missing, starts cached SAM-Cell summary eval if needed.
  - After Cellpose, CellSAM, and SAM-Cell full metrics are all complete, writes:
    - `experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.csv`
    - `experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.md`
  - Then starts Far-OOD module attribution in tmux `farood_module_attribution_20260507` unless already complete/running.
- Far-OOD attribution output:
  - `/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507`
  - Stages: `semantic_cc`, `raw_watershed`, `current_proposal`, `coarse_no_sam2`, `full_samcell`.
  - Interpretation file: `interpretation.md`.
  - This staged design estimates nnU-Net foreground, EDT/watershed, proposal/crop-coarse handling, and SAM2 refinement contributions on the frozen `far_ood_test` manifest.

Far-OOD attribution smoke test at 2026-05-07 05:31 CST:

- Ran a remote one-image smoke test:
  - command pattern: `LIMIT=1 OUT_DIR=/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507_smoke_limit1 bash scripts/run_farood_attribution_20260507.sh`
  - output: `/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507_smoke_limit1`
- Smoke output exists for all five stages:
  - `semantic_cc`
  - `raw_watershed`
  - `current_proposal`
  - `coarse_no_sam2`
  - `full_samcell`
- Files written:
  - per-stage `per_image.csv`
  - per-stage `summary.csv`
  - `combined_summary.csv`
  - `interpretation.md`
  - `run_manifest.json`
- The smoke confirms the attribution script can load the final config, use existing full SAM-Cell labels, compute PQ/AJI/Dice, and write the staged interpretation. Treat the one-image numbers only as a runtime smoke check, not as scientific evidence.

Completion audit tooling added at 2026-05-07 05:38 CST:

- Added and synced:
  - `scripts/audit_active_goal_20260507.py`
- Local and remote `python -m py_compile` passed.
- Purpose:
  - Restates the active objective as concrete deliverables.
  - Verifies hourly watcher evidence.
  - Verifies full Cellpose, CellSAM, and SAM-Cell PQ/AJI/Dice metrics.
  - Verifies the three-model comparison CSV/Markdown.
  - Verifies Far-OOD attribution has all five stages and `interpretation.md`.
- Use after the automatic watcher finishes:

```bash
cd /backup/taotao_work/sam_cell
/backup/taotao_work/venvs/nnunet/bin/python scripts/audit_active_goal_20260507.py \
  --out_json /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.json \
  --out_md /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.md
```

- Do not mark the active goal complete unless this audit returns `complete=true`.

Watcher audit-loop update at 2026-05-07 05:46 CST:

- Updated `scripts/hourly_full_postprocess_and_farood_20260507.sh` so the automatic watcher now also runs the final active-goal audit after both prerequisites are complete:
  - full three-model comparison Markdown exists.
  - Far-OOD attribution has `combined_summary.csv` and `interpretation.md`.
- Audit outputs:
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.json`
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.md`
- If the audit returns `complete=true`, the watcher exits instead of sleeping forever.
- Remote `bash -n` passed, and tmux `hourly_full_postprocess_and_farood_20260507` was restarted to use the new script.

Watcher summary-trigger safety update at 2026-05-07 05:53 CST:

- Updated `scripts/hourly_full_postprocess_and_farood_20260507.sh` to avoid racing the existing stable cached-summary watcher.
- If SAM-Cell labels reach 16777 and `samcell_refine_cached_summary_watcher_20260506` is alive, the hourly postprocess watcher now waits instead of starting `full_samcell_refine_cached_summary_eval` itself.
- It only starts fallback cached-summary eval if the stable watcher is absent and the summary session is not already running.
- Remote `bash -n` passed, and tmux `hourly_full_postprocess_and_farood_20260507` was restarted to use the safer summary-trigger logic.

User-requested status/audit update at 2026-05-07 06:48 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 16335/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 2058/2500.
  - 12500:13500 is complete.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Remaining labels are concentrated only in 12058:12500, so 442 labels remain in the active tail interval.
- Active final-refine eval process count is 4.
- Server load is about 94/96/103. GPU0 was active around 40% with about 4.3GB used; GPU1 was idle in this sample.
- Active sessions include final-refine tail workers, `hourly_full_postprocess_and_farood_20260507`, and `samcell_refine_cached_summary_watcher_20260506`.
- The hourly postprocess watcher is alive; its last completed pass at 05:52 CST saw 16267/16777 labels, then correctly waited for SAM-Cell summary and final comparison.

Hourly/manual status update at 2026-05-07 06:54 CST:

- Completion audit remains `complete=false`.
- CellSAM remains complete:
  - labels: 16777/16777.
  - summary has `ALL n=16777`.
- SAM-Cell accepted final refine is still running:
  - labels: 16341/16777.
  - `per_image.csv`: pending/0 rows.
  - `summary.csv`: pending/no `ALL n=16777`.
- Interval state:
  - 0:10000 complete.
  - 10000:12500 is 2064/2500.
  - 12500:13500 is complete.
  - 13500:14500 is complete.
  - 14500:16777 is complete.
- Remaining labels are concentrated only in 12064:12500, so 436 labels remain in the active tail interval.
- Active final-refine eval process count is 4.
- Server load is about 88/94/101. Both GPUs showed activity in this sample.
- `hourly_full_postprocess_and_farood_20260507` completed its 06:52 pass normally: it saw 16339/16777 labels, waited for SAM-Cell summary, did not start comparison or final audit early.

Far-OOD attribution paired-delta update at 2026-05-07 07:02 CST:

- Enhanced `scripts/farood_module_attribution_20260507.py` to write paired per-image delta analysis:
  - `paired_delta_per_image.csv`
  - `paired_delta_summary.csv`
- Delta stages:
  - `edt_watershed_over_semantic_cc`
  - `current_proposal_selection_over_raw_watershed`
  - `crop_coarse_reinsertion_over_proposal_map`
  - `sam2_refinement_over_coarse_no_sam2`
- `interpretation.md` now appends a paired per-image delta table with mean delta PQ, median delta PQ, and PQ win rate.
- Updated `scripts/audit_active_goal_20260507.py` so final completion requires the paired-delta summary and all four delta rows.
- Local and remote `python -m py_compile` passed.
- Remote smoke test passed:
  - command pattern: `LIMIT=1 OUT_DIR=/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507_smoke_pairdelta_limit1 bash scripts/run_farood_attribution_20260507.sh`
  - output includes `paired_delta_summary.csv`.
- Treat the one-image delta values only as runtime validation, not as scientific evidence.

Full model comparison delta update at 2026-05-07 07:10 CST:

- Enhanced `scripts/build_full_model_metric_comparison_20260507.py` to also write SAM-Cell deltas versus baselines:
  - `samcell_delta_vs_baselines.csv`
  - `samcell_delta_vs_baselines.md`
- Deltas cover SAM-Cell minus:
  - `cellpose_official_cyto3`
  - `cellsam_generalist`
- Metrics included:
  - delta PQ
  - delta AJI
  - delta Dice
- Updated `scripts/audit_active_goal_20260507.py` so final completion requires these delta outputs.
- Local and remote `python -m py_compile` passed.

Final report builder update at 2026-05-07 07:17 CST:

- Added `scripts/build_active_goal_final_report_20260507.py`.
- Purpose:
  - combines full CellCosmos 16777 Cellpose/CellSAM/SAM-Cell PQ/AJI/Dice;
  - includes SAM-Cell delta versus Cellpose and CellSAM;
  - includes Far-OOD staged attribution;
  - includes Far-OOD paired per-image delta summary;
  - writes a concise answer for which module contributes the largest measured Far-OOD PQ gain.
- Output:
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_final_report_20260507.md`
- Updated `scripts/hourly_full_postprocess_and_farood_20260507.sh` so it runs the final report builder after `scripts/audit_active_goal_20260507.py` returns `complete=true`.
- Local checks passed:
  - `python -m py_compile scripts/build_active_goal_final_report_20260507.py`
  - `bash -n scripts/hourly_full_postprocess_and_farood_20260507.sh`
- Remote checks passed and tmux `hourly_full_postprocess_and_farood_20260507` was restarted to use the final-report workflow.

User-requested status/update at 2026-05-07 17:58 CST:

- Full CellCosmos 16777 inference/metrics status:
  - Cellpose metrics complete.
  - CellSAM labels and metrics complete.
  - SAM-Cell refine labels complete: 16777/16777.
  - SAM-Cell refine `per_image.csv` complete: 16777 rows.
  - SAM-Cell refine `summary.csv` exists and has an `ALL` row.
- Corrected `scripts/remote_full_inference_completion_audit_20260506.py` because SAM-Cell `summary.csv` has no `n` column; the script now accepts `summary.csv` ALL row plus `per_image.csv` row count as evidence for SAM-Cell summary completion.
- Re-ran the corrected audit on the server; it returned `complete=true` for the full CellSAM/SAM-Cell inference/metrics objective.
- Full model comparison has been generated:
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.csv`
  - `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.md`
- Key ALL metrics from the full comparison:
  - Cellpose official cyto3: PQ 0.3343458182, AJI 0.3047803869, Dice 0.5314693450.
  - CellSAM generalist: PQ 0.5388845173, AJI 0.5248209538, Dice 0.7615980137.
  - SAM-Cell refine final: PQ 0.6083056641, AJI 0.6182878545, Dice 0.8657230204.
- Far-OOD attribution status:
  - It crashed at row 1201/1795 (`tissuenet_train_675.png`) due to a corrupt semantic `.npz` cache (`zipfile.BadZipFile`).
  - Patched `sam_cell/pipeline.py` so unreadable semantic cache files are ignored, deleted, and regenerated.
  - Synced and verified the patch on the server.
  - Restarted tmux `farood_module_attribution_20260507` with existing outputs reused via `--skip_existing`.
  - Restart check showed the job advanced past the crash point to at least 1217/1795.
  - Current Far-OOD stage label counts at the restart check:
    - `semantic_cc`: 1217
    - `raw_watershed`: 1217
    - `current_proposal`: 1216
    - `coarse_no_sam2`: 1216
    - `full_samcell`: not written as stage labels because this stage reads the completed full SAM-Cell label directory directly.
- Active remaining blocker for the user objective:
  - Far-OOD attribution must finish 1795 rows.
  - Then the hourly postprocess watcher will run final active-goal audit and final report generation.

Execution update at 2026-05-04 18:29 CST:

- The running combo search was restarted with:

```text
--merge_supports none --top_holdout 3
```

- Reason: eval250 TissueNet already had baseline plus the top three holdout candidates, and the current `tn_add_0.10_dist_0.45_h008_012_016` candidate was a holdout duplicate of `tn_add_0.10_dist_0.50_h008_012_016`.
- The partial eval250 TissueNet file was backed up before restart:

```text
/backup/taotao_work/sam_cell/outputs/tissuenet_local_combo_search_20260504/eval250_tissuenet_summary.partial.before_top3_restart_<timestamp>.csv
```

- After restart, `eval250_tissuenet_summary.csv` was finalized with 4 rows:
  - `v3_baseline`: 0.5746183938.
  - `tn_add_0.12_dist_0.50_h008_012_016`: 0.5860226806, delta +0.0114042868.
  - `tn_add_0.11_dist_0.50_h008_012_016`: 0.5853409206, delta +0.0107225269.
  - `tn_add_0.10_dist_0.50_h008_012_016`: 0.5840784268, delta +0.0094600330.
- The search advanced to eval250 all-source validation and started `eval250_all/v3_baseline`.

### 2026-05-04 thesis experiment gap tracking

Reviewer experiment-only comments were extracted from:

```text
/mnt/c/Users/taotao/OneDrive/评审意见 (1).docx
毕业论文明审 -胡锦涛.docx
```

Tracking file:

```text
docs/thesis_experiment_gap_plan.md
```

Active goal completion checklist:

```text
docs/active_goal_completion_audit.md
```

Use this checklist before marking the long-running objective complete. Current blocking items are TissueNet combo `decision.json`, SAM-Cell full inference/metrics, CellSAM full metrics, Yeast quantitative coverage, and remaining thesis ablation/baseline table gaps.

YeastNet follow-up script prepared on 2026-05-04 15:17 CST:

```text
scripts/run_server_yeastnet_eval_20260504.sh
server path: /backup/taotao_work/sam_cell/scripts/run_server_yeastnet_eval_20260504.sh
default manifest: /backup/taotao_work/sam_cell/outputs/yeastnet_eval_50_20260504/manifest.csv
default output: /backup/taotao_work/sam_cell/experiments/yeastnet_eval_50_20260504
```

The script is syntax-checked and executable on the server, but it has not been launched yet. It can run SAM-Cell v3 fallback, Cellpose cyto3, and CellSAM generalist on YeastNet eval50 and preserve labels, metrics, overlays, logs, and a run manifest.

Main experiment gaps:

- Yeast appears in text but is not consistently evaluated in figures/tables.
- Dataset names, sample counts, splits, and PQ/Error values need one unified master table.
- Claims versus Cellpose must be source-wise and avoid unsupported broad superiority claims.
- CellCosmos needs non-SAM2 split/feature sensitivity analysis because SAM2 features are used in the benchmark design and SAM-Cell uses SAM2.
- Baseline fairness needs explicit weights, training domains, prompts, tuning, postprocessing, resource cost, and failure cases for Cellpose, StarDist, HoVer-Net, native SAM2, and CellSAM.
- The "fine-tuning-free"/"zero-shot" boundary needs a table separating frozen SAM2 from supervised nnU-Net training.
- Full numeric tables need dispersion/significance where possible.
- Module contribution ablations need to cover nnU-Net/proposal-only, SAM2 on/off, crop, box-only, mask-only, box+mask, and watershed sensitivity.
- Native SAM2 should include automatic masks and, if feasible, a prompt-matched SAM2 baseline using the same proposal prompts.

Metric inventory:

```text
script: scripts/build_experiment_metric_inventory.py
output csv: /backup/taotao_work/sam_cell/outputs/thesis_experiment_inventory_20260504/experiment_metric_inventory.csv
output md: /backup/taotao_work/sam_cell/outputs/thesis_experiment_inventory_20260504/experiment_metric_inventory.md
```

Initial inventory confirms:

- Full CellCosmos 16777 Cellpose cyto3 metrics are complete.
- Core3500/IID/Far-OOD Cellpose, StarDist, SAM2 automatic, CellSAM eval250, and HoVer-Net fast PanNuke artifacts exist.
- Full CellSAM 16777 and full SAM-Cell 16777 metrics are still pending.
- Yeast/YeastNet remains uncovered in current metric summaries.

### 2026-05-07 full metrics and Far-OOD attribution completed

Current active long-running objective is complete as of 2026-05-07 18:25 CST.

Objective covered:

- Hourly/automatic checking until full inference completed.
- Full CellCosmos 16777 PQ/AJI/Dice for Cellpose official cyto3, CellSAM generalist, and final SAM-Cell.
- Far-OOD module attribution answering whether the measured improvement mainly comes from nnU-Net semantic connected components, EDT/watershed, crop/coarse reinsertion, or SAM2 refinement.

Final full CellCosmos 16777 comparison:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.md
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/samcell_delta_vs_baselines.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/samcell_delta_vs_baselines.md
```

ALL metrics:

| method | n | PQ | AJI | Dice |
|---|---:|---:|---:|---:|
| Cellpose official cyto3 | 16777 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM generalist | 16777 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell refine final | 16777 | 0.608306 | 0.618288 | 0.865723 |

SAM-Cell full-corpus deltas:

| baseline | delta PQ | delta AJI | delta Dice |
|---|---:|---:|---:|
| Cellpose official cyto3 | +0.273960 | +0.313507 | +0.334254 |
| CellSAM generalist | +0.069421 | +0.093467 | +0.104125 |

Far-OOD attribution artifacts:

```text
/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/combined_summary.csv
/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/paired_delta_summary.csv
/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/interpretation.md
```

Far-OOD stage metrics:

| stage | ALL PQ | ALL AJI | ALL Dice |
|---|---:|---:|---:|
| semantic_cc | 0.165386 | 0.105394 | 0.912512 |
| raw_watershed | 0.614674 | 0.625914 | 0.911846 |
| current_proposal | 0.634858 | 0.633567 | 0.912538 |
| coarse_no_sam2 | 0.634858 | 0.633568 | 0.912538 |
| full_samcell | 0.634569 | 0.634742 | 0.911718 |

Far-OOD paired deltas:

| paired delta | mean delta PQ | median delta PQ | PQ win rate |
|---|---:|---:|---:|
| edt_watershed_over_semantic_cc | +0.449288 | +0.493635 | 0.964 |
| current_proposal_selection_over_raw_watershed | +0.020184 | +0.002954 | 0.655 |
| crop_coarse_reinsertion_over_proposal_map | -0.000000 | 0.000000 | 0.022 |
| sam2_refinement_over_coarse_no_sam2 | -0.000289 | 0.000000 | 0.309 |

Interpretation:

- In the current staged attribution, the dominant measured Far-OOD PQ gain comes from EDT/watershed over semantic connected components.
- The current proposal selection adds a smaller but positive gain.
- Crop/coarse reinsertion is effectively neutral under the measured proxy.
- SAM2 refinement is slightly negative in mean paired PQ on this Far-OOD set, so the current evidence does not support claiming SAM2 is the main source of the Far-OOD gain.
- This is a staged, interacting-module attribution, not a fully independent causal decomposition.

Final audit/report:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.json
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_audit_20260507.md
/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/active_goal_final_report_20260507.md
```

The final audit returned `complete=true`.

### 2026-05-07 full CellCosmos results split by dataset

User requested the full CellCosmos segmentation results be separated by dataset/source and metrics be reported separately.

Script:

```text
scripts/split_full_cellcosmos_results_by_dataset_20260507.py
```

Server outputs:

```text
metrics: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/by_dataset_20260507
split result links: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/results_by_dataset_20260507
```

Important files:

```text
metrics/by_dataset_20260507/all_models_by_dataset_metrics.csv
metrics/by_dataset_20260507/all_models_by_dataset_metrics.md
metrics/by_dataset_20260507/source_counts.csv
metrics/by_dataset_20260507/split_artifact_counts.csv
metrics/by_dataset_20260507/<source>/model_metrics.csv
metrics/by_dataset_20260507/<source>/<method>_per_image.csv
results_by_dataset_20260507/<source>/manifest.csv
results_by_dataset_20260507/<source>/<method>/labels/
results_by_dataset_20260507/<source>/<method>/overlays/
```

The split result directories use symlinks to existing predictions/overlays instead of copying large files. Verification passed with `missing_label_links=0`.

Source counts:

| source | n |
|---|---:|
| cellpose | 540 |
| dsb2018 | 670 |
| livecell | 1000 |
| pannuke | 7558 |
| tissuenet | 7009 |
| ALL | 16777 |

Per-source label/per-image checks passed for all three methods:

```text
cellpose: 540 labels and 540 per-image rows per method
dsb2018: 670 labels and 670 per-image rows per method
livecell: 1000 labels and 1000 per-image rows per method
pannuke: 7558 labels and 7558 per-image rows per method
tissuenet: 7009 labels and 7009 per-image rows per method
```

Per-source PQ/AJI/Dice table:

| source | method | n | PQ | AJI | Dice |
|---|---|---:|---:|---:|---:|
| cellpose | Cellpose official cyto3 | 540 | 0.718888 | 0.731799 | 0.904112 |
| cellpose | CellSAM generalist | 540 | 0.648705 | 0.652983 | 0.876153 |
| cellpose | SAM-Cell refine final | 540 | 0.778777 | 0.802897 | 0.950298 |
| dsb2018 | Cellpose official cyto3 | 670 | 0.749831 | 0.760935 | 0.885728 |
| dsb2018 | CellSAM generalist | 670 | 0.710074 | 0.725736 | 0.876941 |
| dsb2018 | SAM-Cell refine final | 670 | 0.831707 | 0.859338 | 0.957776 |
| livecell | Cellpose official cyto3 | 1000 | 0.653305 | 0.636270 | 0.898118 |
| livecell | CellSAM generalist | 1000 | 0.322264 | 0.264849 | 0.614239 |
| livecell | SAM-Cell refine final | 1000 | 0.610366 | 0.596366 | 0.922992 |
| pannuke | Cellpose official cyto3 | 7558 | 0.249934 | 0.217175 | 0.378016 |
| pannuke | CellSAM generalist | 7558 | 0.430055 | 0.394497 | 0.634315 |
| pannuke | SAM-Cell refine final | 7558 | 0.574958 | 0.593369 | 0.807926 |
| tissuenet | Cellpose official cyto3 | 7009 | 0.310519 | 0.275449 | 0.582057 |
| tissuenet | CellSAM generalist | 7009 | 0.662320 | 0.673364 | 0.900023 |
| tissuenet | SAM-Cell refine final | 7009 | 0.609482 | 0.611020 | 0.904561 |

### 2026-05-07 native SAM2 prompt-matched eval50 baseline

Purpose:

- Address reviewer concern that native SAM2 was only evaluated as automatic masks.
- Add a small prompt-matched baseline using the same SAM-Cell proposal boxes and coarse masks as prompts to frozen SAM2.
- This is a supplementary prompt-fair diagnostic, not a new main method or full-corpus baseline.

Script:

```text
scripts/run_sam2_prompt_matched_baseline_20260507.py
```

Protocol:

- Dataset: balanced eval50 from `outputs/benchmark_splits_large/eval_250_server_paths.csv`, 10 images per source.
- Config: final accepted SAM-Cell config `/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml`.
- Prompt mode: `box_mask`.
- SAM-Cell semantic/proposal code is used only to create proposal boxes and coarse masks.
- Disabled coarse fallback and SAM-Cell `choose_instance` candidate acceptance.
- Kept minimal assembly only: empty-mask removal, duplicate suppression, and pixel competition.

Artifacts:

```text
server: /backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/baseline_sam2_prompt_matched_20260507_eval50
local stats: /home/taotao/sam_cell/outputs/sam2_prompt_matched_eval50_20260507
```

Key files:

```text
summary.csv
per_image.csv
report.md
run_manifest.json
samcell_refine_final_same50_summary.csv
prompt_matched_same50_comparison.csv
prompt_matched_same50_comparison.md
```

Same-50 comparison:

| source | method | n | PQ | AJI | Dice |
|---|---|---:|---:|---:|---:|
| ALL | SAM2 prompt-matched box+mask | 50 | 0.630938 | 0.629811 | 0.877933 |
| ALL | same proposals before SAM2 | 50 | 0.645019 | 0.644211 | 0.892967 |
| ALL | SAM-Cell refine final | 50 | 0.644897 | 0.644737 | 0.892558 |
| cellpose | SAM2 prompt-matched box+mask | 10 | 0.689956 | 0.693006 | 0.909890 |
| dsb2018 | SAM2 prompt-matched box+mask | 10 | 0.801499 | 0.829593 | 0.929133 |
| livecell | SAM2 prompt-matched box+mask | 10 | 0.600163 | 0.577510 | 0.908864 |
| pannuke | SAM2 prompt-matched box+mask | 10 | 0.521766 | 0.533171 | 0.779487 |
| tissuenet | SAM2 prompt-matched box+mask | 10 | 0.541307 | 0.515777 | 0.862289 |

Interpretation:

- On this balanced eval50 subset, native SAM2 with the same box+coarse-mask prompts is weaker than both the pre-SAM2 proposal map and the final SAM-Cell output.
- The result supports the Far-OOD attribution conclusion that SAM2 refinement is not the dominant source of improvement in the current pipeline.
- Because this is only 50 images, use it as a reviewer-response diagnostic rather than a full main-table claim.

### 2026-05-09 CellCosmos core-domain vs far-domain model comparison

User requested a horizontal comparison of CellSAM, Cellpose, StarDist, native SAM2, HoVer-Net, and SAM-Cell on CellCosmos core-domain and far-domain splits.

Artifacts:

```text
outputs/core_far_model_comparison_20260509/core_far_model_comparison.csv
outputs/core_far_model_comparison_20260509/core_far_model_comparison.md
outputs/core_far_model_comparison_20260509/core_far_model_comparison_with_official_cellpose.csv
outputs/core_far_model_comparison_20260509/core_far_model_comparison_with_official_cellpose.md
scripts/build_core_far_model_comparison_20260509.py
```

Split definition:

- Core-domain: frozen `pannuke_core_test` (`n=336`).
- Far-domain: frozen `far_ood_test` (`n=1795`, non-PanNuke sources).
- Metrics: mean per-image PQ/AJI/Dice using the project evaluator convention.

Main comparison:

| model | core PQ | core AJI | core Dice | far PQ | far AJI | far Dice |
|---|---:|---:|---:|---:|---:|---:|
| CellSAM generalist | 0.430049 | 0.397525 | 0.629841 | 0.637605 | 0.641439 | 0.873047 |
| Cellpose cyto3, PanNuke-finetuned | 0.620718 | 0.615648 | 0.791060 | 0.024681 | 0.018660 | 0.055102 |
| StarDist, PanNuke-trained | 0.626118 | 0.620731 | 0.799360 | 0.022308 | 0.018220 | 0.042769 |
| Native SAM2 automatic dense | 0.058126 | 0.019259 | 0.290695 | 0.181334 | 0.120016 | 0.595004 |
| HoVer-Net fast PanNuke | 0.549858 | 0.561091 | 0.817125 | 0.005054 | 0.004639 | 0.008586 |
| SAM-Cell refine final | 0.575995 | 0.596006 | 0.809390 | 0.634569 | 0.634742 | 0.911718 |

Supplementary Cellpose distinction:

- Official Cellpose cyto3 is not core-domain finetuned. On `pannuke_core_test`, PQ/AJI/Dice = `0.231988/0.197069/0.358094`; on `far_ood_test`, `0.412207/0.387019/0.660719`.
- For the Core-vs-Far domain-shift table, the main Cellpose row uses `cellpose_pannuke_finetune_cyto3` because it matches the core-domain supervised baseline setup.

Interpretation:

- PanNuke-domain supervised baselines are strongest on the core PanNuke split, with StarDist and Cellpose around PQ `0.62`.
- These same PanNuke-domain supervised baselines collapse on Far-OOD, showing poor cross-domain generalization.
- SAM-Cell is competitive on core-domain and is the most stable across the two splits.
- On Far-OOD, CellSAM has slightly higher PQ/AJI than SAM-Cell (`0.637605/0.641439` vs `0.634569/0.634742`), while SAM-Cell has higher Dice (`0.911718` vs `0.873047`).
- Native SAM2 automatic masks and PanNuke HoVer-Net are not competitive under this automatic evaluation setting.

### 2026-05-09 thesis source-domain consistency check

The current thesis draft `毕业论文明审 -胡锦涛.docx` contains a protocol inconsistency:

- Section 3.3.3 states that the progressive OOD protocol is built with `Cellpose` as the source domain. It also describes TissueNet/DSB2018 as near-OOD and PanNuke/LIVECell as far-OOD relative to Cellpose.
- Section 3.4.1 and Table 3-5 state that Cellpose is trained on the `PanNuke` core domain and then evaluated on Far-OOD.
- The actual reproduced Core/Far experiment uses `pannuke_train`, `pannuke_core_test`, and `far_ood_test` (`non-PanNuke`), so the implemented protocol is PanNuke-core, not Cellpose-source.

Decision:

- Do not keep both claims in the thesis.
- If using the current reproduced Core/Far tables, revise the thesis protocol to say `PanNuke` is the core/source domain for the single-domain domain-shift experiment.
- Treat official Cellpose cyto3 as a separate public/generalist comparator, not as the same row as the PanNuke-finetuned Cellpose domain-shift baseline.
- If the thesis must preserve `Cellpose` as the source domain, the Core/Far experiments and tables must be regenerated with Cellpose-source training/test and distance-defined near/far domains. Current PanNuke-core results cannot be used to support that exact protocol.

### 2026-05-10 chapter 2 real-data figure replacements

User requested replacing Chapter 2.6.2 quantitative comparison figures and Chapter 2.6.4 fake ablation with real project data.

Inspected local thesis/drawing code:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/the3_datasat_get
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图
毕业论文明审 -胡锦涛.docx
```

Findings:

- Existing 2.6.2 plotting code used hard-coded simulated error arrays and only compared Cellpose/SAM-Cell.
- Existing 2.6.4 text/tables used synthetic crop-expansion and prompt-combination ablation values.
- Current real data supports replacing 2.6.2 with Cellpose official cyto3, CellSAM generalist, and SAM-Cell refine final on full CellCosmos 16777.
- Current real data supports replacing 2.6.4 with Far-OOD staged module attribution and prompt-matched native SAM2 diagnostic, not with unsupported Box-only/Mask-only claims.

New script:

```text
scripts/plot_chapter2_real_figures_20260510.py
```

Run command used:

```text
MPLCONFIGDIR=/tmp/mpl_samcell_ch2 /home/taotao/anaconda3/envs/SAM-Cell/bin/python scripts/plot_chapter2_real_figures_20260510.py
```

Reason for env:

- Base conda Matplotlib is broken due to NumPy ABI mismatch.
- `/home/taotao/anaconda3/envs/SAM-Cell/bin/python` has compatible NumPy/Pandas/Matplotlib.

Output directory:

```text
outputs/chapter2_real_figures_20260510
```

Windows-side synced copy:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter2_real_figures_20260510
```

Sync status:

- Completed on 2026-05-10 20:51 CST.
- Local output file count: `25`.
- Windows-side synced file count: `25`.

Style update on 2026-05-11 19:50 CST:

- `fig_2_09` to `fig_2_12` were regenerated with a lighter thesis-style palette.
- Main method colors now use Cellpose `#F8766D`, CellSAM `#00BFC4`, and SAM-Cell `#7CAE00`.
- Delta bars in `fig_2_11` use lighter fills `#FBB4AE` and `#B3E2CD`.
- Bar value annotations in `fig_2_09` and `fig_2_11` are horizontal rather than vertical.
- `fig_2_12` label offsets were adjusted to avoid overlap between nearby `TissueNet` and `ALL` points.
- The updated PNG/PDF files were copied to the Windows-side synced directory.

Key files:

```text
fig_2_09_cellcosmos_error_by_source.png/.pdf
fig_2_10_error_transition_three_models.png/.pdf
fig_2_11_samcell_delta_pq_by_source.png/.pdf
fig_2_12_pairwise_pq_parity.png/.pdf
fig_2_14_farood_stage_ablation_metrics.png/.pdf
fig_2_15_farood_stage_pq_heatmap.png/.pdf
fig_2_16_farood_module_delta_pq.png/.pdf
fig_2_17_prompt_matched_sam2_diagnostic.png/.pdf
figure_index.md
section_replacement_notes.md
source_model_metrics_used_for_2_6_2.csv
farood_stage_metrics_used_for_2_6_4.csv
farood_paired_delta_used_for_2_6_4.csv
```

2.6.2 ALL metrics used:

| method | n | PQ | AJI | Dice |
|---|---:|---:|---:|---:|
| Cellpose cyto3 | 16777 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM | 16777 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell | 16777 | 0.608306 | 0.618288 | 0.865723 |

2026-05-11 full reproduction audit and F1 update:

- Audit script added: `scripts/audit_full_cellcosmos_repro_20260511.py`.
- Audit report copied locally:
  - `outputs/audit_full_cellcosmos_repro_20260511/audit_full_cellcosmos_repro_20260511.md`
  - `outputs/audit_full_cellcosmos_repro_20260511/audit_full_cellcosmos_repro_20260511.json`
- The audit checked the full 16777 manifest, image/mask paths, label counts, per-image row counts, summary re-aggregation, expected prediction file names, source alignment, and 50 sampled per-image recomputations from prediction label + GT mask with the repository evaluator.
- Audit result: no missing image/mask paths, each of Cellpose official cyto3 / CellSAM generalist / SAM-Cell refine final has 16777 labels and 16777 per-image rows, summary re-aggregation diff is zero or numeric roundoff, and sampled recomputation mismatches are 0.
- SAM-Cell full run uses final config `/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml`, extending `sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml` and `sam_cell_global_adaptive_selector_v2_workstation2.yaml`.
- SAM-Cell semantic experts in the audited full run:
  - Dataset621 universal boundary: `/backup/taotao_work/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d`, folds 0-4, `checkpoint_final.pth`, foreground classes `[1, 2]`, boundary class `2`.
  - Dataset512 Cellpose-style branch: `/backup/taotao_work/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d`, folds 0-4, `checkpoint_final.pth`, foreground class `[1]`, enabled only for Cellpose-source images.
  - It does not use Dataset622 in the final full-corpus result.
- Cellpose official baseline uses `pretrained_model=cyto3`, `diameter=0`; this is the public official cyto3 baseline, not a CellCosmos-finetuned Cellpose model.
- CellSAM baseline uses `bbox_threshold=0.4`, `grayscale_mode=repeat`, `use_wsi=False`; final manifest has cached/resumed records because earlier outputs were reused, but the audit found complete files and metric consistency.
- New F1/PQ/AJI/Dice table and group plot script: `scripts/plot_full_cellcosmos_f1_pq_aji_dice_20260511.py`.
- Local outputs:
  - `outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511/full_cellcosmos_f1_pq_aji_dice_summary.csv`
  - `outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511/full_cellcosmos_f1_pq_aji_dice_summary.md`
  - `outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511/fig_full_cellcosmos_f1_pq_aji_dice_grouped.png`
  - `outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511/fig_full_cellcosmos_f1_pq_aji_dice_grouped.pdf`
- Windows-side synced copy: `/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter2_full_metrics_f1_pq_aji_dice_20260511`.

2.6.2 ALL metrics with F1:

| method | n | F1 | PQ | AJI | Dice |
|---|---:|---:|---:|---:|---:|
| Cellpose cyto3 | 16777 | 0.456724 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM | 16777 | 0.701177 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell | 16777 | 0.746555 | 0.608306 | 0.618288 | 0.865723 |

Caveat for wording:

- On ALL, SAM-Cell is better than CellSAM and Cellpose cyto3 on F1/PQ/AJI/Dice.
- By source, SAM-Cell is not strictly best on every source/metric: TissueNet has higher CellSAM PQ/AJI/F1, while SAM-Cell has higher TissueNet Dice. LIVECell has Cellpose cyto3 higher than SAM-Cell on PQ/AJI/F1, while SAM-Cell has higher Dice.
- Thesis wording should claim stronger overall and broad cross-domain performance, not universal per-dataset/per-metric dominance.

2026-05-11 update for Chapter 2.6.2 figure numbering:

- User clarified that 2.6.2 should be described as five source-dataset comparisons, not a single CellCosmos-only comparison.
- Updated `scripts/plot_full_cellcosmos_f1_pq_aji_dice_20260511.py` to generate a full figure set for F1/PQ/AJI/Dice:
  - `fig_2_09_five_dataset_four_metrics_grouped.png/.pdf`: grouped four-metric bars for Cellpose, DSB2018, LIVECell, PanNuke, TissueNet, and pooled ALL.
  - `fig_2_10_samcell_metric_delta_heatmap.png/.pdf`: SAM-Cell metric deltas versus Cellpose cyto3 and CellSAM.
  - `fig_2_11_best_model_by_metric_map.png/.pdf`: best model per dataset and metric.
  - `fig_2_12_overall_and_macro_summary.png/.pdf`: pooled ALL versus equal-weight five-dataset macro average.
- Added figure index and replacement text:
  - `outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511/figure_index_2_6_2_multimetric.md`
  - `outputs/chapter2_full_metrics_f1_pq_aji_dice_20260511/section_2_6_2_multimetric_replacement_text.md`
- Synced all updated 2.6.2 files to:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter2_full_metrics_f1_pq_aji_dice_20260511
```

2026-05-11 refinement for 2.6.2 Fig. 2-10 to Fig. 2-12:

- The first multi-metric replacements for Fig. 2-10/2-11/2-12 were judged too redundant with Fig. 2-9.
- Replaced them with higher-information error-oriented figures, following the older PQ-only error transition / delta / parity logic but extended to F1/PQ/AJI/Dice:
  - `fig_2_10_multimetric_error_transition.png/.pdf`: horizontal transition plot of mean error across the four metrics, where mean error is `mean(1 - metric)`.
  - `fig_2_11_error_reduction_breakdown.png/.pdf`: metric-wise error-reduction decomposition against Cellpose cyto3 and CellSAM; colored dots are metrics, black diamonds are four-metric means.
  - `fig_2_12_best_baseline_parity_four_metrics.png/.pdf`: four-panel parity against the stronger of Cellpose cyto3 and CellSAM for each source-metric pair.
- Updated `figure_index_2_6_2_multimetric.md` and `section_2_6_2_multimetric_replacement_text.md` accordingly.
- Older generated files named `fig_2_10_samcell_metric_delta_heatmap`, `fig_2_11_best_model_by_metric_map`, and `fig_2_12_overall_and_macro_summary` may still exist in the output directory but should not be used as the thesis 2.6.2 figures.
- 2026-05-11 21:56 CST style cleanup:
  - Fig. 2-10 legend moved from lower-right to upper-right with a white background to avoid overlapping the data.
  - Fig. 2-12 point text annotations were removed; only the top color legend remains.
  - Regenerated PNG/PDF locally and synced to the Windows-side drawing directory.

2026-05-12 Chapter 2.6.3 qualitative figure:

- Added script: `scripts/plot_chapter2_qualitative_2_6_3_20260512.py`.
- Purpose: generate a real qualitative visualization panel matching the 2.6.3 text about cross-domain microscopy scenes, visual segmentation quality, and error-correction behavior.
- Figure output:
  - `outputs/chapter2_qualitative_2_6_3_20260512/fig_2_13_qualitative_error_correction_panel.png`
  - `outputs/chapter2_qualitative_2_6_3_20260512/fig_2_13_qualitative_error_correction_panel.pdf`
- Supporting files:
  - `outputs/chapter2_qualitative_2_6_3_20260512/fig_2_13_selected_samples.csv`
  - `outputs/chapter2_qualitative_2_6_3_20260512/section_2_6_3_qualitative_notes.md`
- Windows-side synced copy:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter2_qualitative_2_6_3_20260512
```

- Figure design: five rows for PanNuke, TissueNet, DSB2018, LIVECell, and Cellpose; five columns for raw image, GT, Cellpose cyto3, CellSAM, and SAM-Cell. Overlays are generated from real full-corpus predictions and GT masks.
- PanNuke row was changed to `pannuke_fold3_1370.png` because it better matches the 2.6.3 "dense H&E nuclei" description than the initial sparse crop.
- Recommended one-line caption: `图 2-13 不同显微成像场景下 Cellpose、CellSAM 与 SAM-Cell 的实例分割可视化对比。`

### 2026-05-12 Chapter 3.3.3 PanNuke-core protocol rewrite and Fig. 3-11

User noted that the earlier 3.3.3 PanNuke-core revision was not polished enough and that Fig. 3-11 had not been redrawn.

Decision:

- Keep 3.3.3 consistent with the reproduced Chapter 3 experiments: the protocol is PanNuke-core, not Cellpose-source.
- Use a two-level pressure-test protocol:
  - PanNuke core/source domain: `pannuke_train` n=1341 and `pannuke_core_test` n=336.
  - Far-OOD target pool: `far_ood_test` n=1795, all non-PanNuke images.
- Far-OOD source composition from the frozen manifests:
  - TissueNet 1357
  - LIVECell 149
  - Cellpose 147
  - DSB2018 142

New script:

```text
scripts/plot_chapter3_pannuke_core_protocol_20260512.py
```

Outputs:

```text
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_protocol.png
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_protocol.pdf
outputs/chapter3_pannuke_core_protocol_20260512/section_3_3_3_pannuke_core_replacement_text.md
```

Windows-side synced copy:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter3_pannuke_core_protocol_20260512
```

Recommended caption:

```text
图 3-11 基于 PanNuke 核心域的 CellCosmos 跨域泛化评估协议。
```

2.6.4 replacement conclusions:

- Far-OOD staged attribution shows the dominant gain comes from EDT+watershed over semantic connected components: mean paired delta PQ `+0.449288`, win rate `0.964`.
- Proposal selection adds a smaller positive gain: mean delta PQ `+0.020184`, win rate `0.655`.
- Coarse reinsertion is nearly neutral.
- SAM2 refinement is not the dominant Far-OOD gain source in the current measured proxy: mean delta PQ `-0.000289`, win rate `0.309`.
- Prompt-matched native SAM2 eval50 is weaker than the same proposals before SAM2: PQ `0.630938` vs `0.645019`; SAM-Cell same50 is `0.644897`.
- Do not claim Box+Mask prompt superiority unless a real Box-only/Mask-only prompt ablation is run later.

## Key Local Files

Configs:

```text
configs/sam_cell_cellcosmos_boundary_fold01_best.yaml
configs/sam_cell_universal_boundary.yaml
configs/sam_cell_universal_boundary_final.yaml
configs/sam_cell_universal_boundary_fold01_best.yaml
configs/sam_cell_universal_boundary_fold01_final.yaml
configs/sam_cell_universal_boundary_workstation2.yaml
configs/sam_cell_multi_expert_dual.yaml
configs/sam_cell_multi_expert_dual_ranked.yaml
configs/sam_cell_multi_expert_cellpose_gate.yaml
configs/sam_cell_multi_expert_cellpose_gate_dataset622_workstation2.yaml
configs/sam_cell_multi_expert_cellpose_gate_dataset622_ranked_workstation2.yaml
configs/sam_cell_multi_expert_cellpose_gate_dataset622_interior_workstation2.yaml
```

Scripts:

```text
scripts/build_cellcosmos_boundary_nnunet.py
scripts/build_universal_boundary_nnunet.py
scripts/run_workstation2_cellcosmos_training.sh
scripts/monitor_workstation2_training.sh
scripts/auto_eval_universal_fold01.sh
scripts/summarize_universal_fold01_eval.py
scripts/diagnose_instance_errors.py
scripts/train_proposal_ranker.py
scripts/search_proposal_ranker_threshold.py
scripts/run_server_dataset622_proposal_diagnosis.sh
scripts/run_server_dataset622_ranker_train.sh
scripts/sweep_proposal_generation_params.py
scripts/diagnose_gt_cell_semantic_marker.py
scripts/summarize_gt_cell_diagnosis.py
```

Evaluation outputs:

```text
outputs/auto_eval_universal_fold01
outputs/benchmark_splits_large/eval_25_balanced.csv
outputs/benchmark_splits_large/eval_250.csv
outputs/benchmark_splits_large/compare_cellcosmos_fold01_best_eval25
outputs/benchmark_splits_large/compare_universal_5fold_best_eval25
outputs/benchmark_splits_large/compare_universal_5fold_final_eval25
outputs/benchmark_splits_large/compare_universal_5fold_final_eval250
outputs/benchmark_splits_large/diagnosis_universal_5fold_final_eval250
outputs/multi_expert/smoke_dual_limit1
outputs/proposal_ranker_dual_smoke
outputs/proposal_ranker_dual
outputs/benchmark_splits_large/search_multi_expert_ranker_threshold_eval25
outputs/benchmark_splits_large/search_cellpose_gate_ranker_threshold_eval25_low
outputs/benchmark_splits_large/search_cellpose_gate_t035_eval250_cellpose
outputs/benchmark_splits_large/compare_multi_expert_dual_ranked_eval25
outputs/benchmark_splits_large/compare_multi_expert_cellpose_gate_eval25
outputs/benchmark_splits_large/compare_multi_expert_cellpose_gate_eval250
outputs/benchmark_splits_large/diagnosis_multi_expert_cellpose_gate_eval250
```

### 2026-05-12 Fig. 3-11 PanNuke-centered distance-axis revision

User asked whether Fig. 3-11 could use a one-dimensional OOD distance-axis style similar to the earlier Cellpose-source figure, but the current Chapter 3 protocol must remain PanNuke-core.

Decision:

- Do not reuse the old `3.4.3.py` Cellpose-source distances; that would contradict the PanNuke-core 3.3.3 rewrite.
- Use a PanNuke-centered SAM2 feature-center cosine distance axis computed from `CellCosmos_Core_3500` features.
- Keep all non-PanNuke sources as one frozen Far-OOD test split; the distance gradient is explanatory only and does not create new train/test splits.

Computed PanNuke-center cosine distances:

| target source | distance to PanNuke | coreset feature n | Far-OOD test n |
|---|---:|---:|---:|
| TissueNet | 0.069150104 | 1357 | 1357 |
| DSB2018 | 0.076163171 | 142 | 142 |
| Cellpose | 0.086250532 | 147 | 147 |
| LIVECell | 0.113091595 | 149 | 149 |

Updated script:

```text
scripts/plot_chapter3_pannuke_core_protocol_20260512.py
```

Primary outputs:

```text
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_protocol.png
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_protocol.pdf
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_distance_axis.png
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_distance_axis.pdf
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_distance_values.csv
outputs/chapter3_pannuke_core_protocol_20260512/section_3_3_3_pannuke_core_replacement_text.md
```

The old flowchart-style version is retained as:

```text
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_flowchart.png
outputs/chapter3_pannuke_core_protocol_20260512/fig_3_11_pannuke_core_ood_flowchart.pdf
```

Synced Windows-side copy:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter3_pannuke_core_protocol_20260512
```

Recommended caption:

```text
图 3-11 基于 PanNuke 核心域与 SAM2 特征中心余弦距离的 CellCosmos 跨域泛化评估协议。
```

### 2026-05-12 Chapter 3.4.1 Table 3-5 Cellpose cross-domain data

User requested the data for Table 3-5: Cellpose under the CellCosmos cross-domain evaluation paradigm.

Raw server summaries were copied from:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_iid_finetune_cyto3/iid_val/summary_by_source.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_official_cyto3/iid_val/summary_by_source.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_official_cyto3/pannuke_core_test/summary_by_source.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_official_cyto3/far_ood_test/summary_by_source.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_pannuke_finetune_cyto3/pannuke_core_test/summary_by_source.csv
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/metrics/cellpose_pannuke_finetune_cyto3/far_ood_test/summary_by_source.csv
```

Builder:

```text
scripts/build_chapter3_table_3_5_cellpose_cross_domain_20260512.py
```

Outputs:

```text
outputs/chapter3_table_3_5_cellpose_cross_domain_20260512/table_3_5_cellpose_cross_domain_compact_thesis.csv
outputs/chapter3_table_3_5_cellpose_cross_domain_20260512/table_3_5_cellpose_cross_domain_compact_thesis.md
outputs/chapter3_table_3_5_cellpose_cross_domain_20260512/table_3_5_cellpose_cross_domain_summary.csv
outputs/chapter3_table_3_5_cellpose_cross_domain_20260512/table_3_5_cellpose_cross_domain_summary.md
outputs/chapter3_table_3_5_cellpose_cross_domain_20260512/table_3_5_cellpose_pannuke_finetune_farood_source_breakdown.csv
outputs/chapter3_table_3_5_cellpose_cross_domain_20260512/table_3_5_cellpose_pannuke_finetune_farood_source_breakdown.md
```

Windows-side synced copy:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter3_table_3_5_cellpose_cross_domain_20260512
```

Recommended Table 3-5 main rows:

Compact thesis-facing version:

| 评估基准设定 | 测试集物理分布状态 | 锚点网络 | 测试集全景质量PQ |
|---|---|---|---:|
| 传统随机混合基准 | I.I.D | Cellpose（自主训练 500 Epochs） | 0.6092 |
| CellCosmos 单源域基准 | Far-OOD | Cellpose（PanNuke 核心域训练） | 0.0247 |
| CellCosmos 通用跨域基准 | Far-OOD | Cellpose（官方 cyto3 预训练模型） | 0.4122 |

Expanded provenance version:

| model setting | training domain | test paradigm | n | F1 | PQ | AJI | Dice | Source macro PQ |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Cellpose official cyto3 | public cyto3 pretrained | PanNuke core/source test | 336 | 0.3130 | 0.2320 | 0.1971 | 0.3581 | 0.2320 |
| Cellpose official cyto3 | public cyto3 pretrained | non-PanNuke Far-OOD test | 1795 | 0.5623 | 0.4122 | 0.3870 | 0.6607 | 0.6122 |
| Cellpose cyto3 + IID finetune | mixed-source iid_train | random mixed-domain IID validation | 697 | 0.7607 | 0.6092 | 0.5992 | 0.8180 | 0.6242 |
| Cellpose cyto3 + PanNuke finetune | PanNuke train only | PanNuke core/source test | 336 | 0.7575 | 0.6207 | 0.6156 | 0.7911 | 0.6207 |
| Cellpose cyto3 + PanNuke finetune | PanNuke train only | non-PanNuke Far-OOD test | 1795 | 0.0352 | 0.0247 | 0.0187 | 0.0551 | 0.0577 |

Interpretation:

- Mixed-source IID finetuning and PanNuke in-domain testing both give high Cellpose scores.
- The same PanNuke-only supervised Cellpose model collapses on non-PanNuke Far-OOD, supporting the Chapter 3 claim that random mixed validation can hide domain-specific overfitting.
- Official cyto3 is not comparable to PanNuke-finetuned as a source-domain supervised baseline because it was not trained only on the PanNuke core split; keep it as a public generalist reference.

### 2026-05-12 Fig. 3-12 real Cellpose 500-epoch loss curves

User requested the real loss curve for Fig. 3-12, replacing the old simulated `3.4_loss_virtul.py` curve.

Raw logs copied from server:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/logs/cellpose_iid_finetune_cyto3_train.log
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501/logs/cellpose_pannuke_finetune_cyto3_train.log
```

Builder:

```text
scripts/plot_chapter3_cellpose_loss_fig3_12_20260512.py
```

Outputs:

```text
outputs/chapter3_cellpose_loss_fig3_12_20260512/fig_3_12_cellpose_500epoch_real_loss_comparison.png
outputs/chapter3_cellpose_loss_fig3_12_20260512/fig_3_12_cellpose_500epoch_real_loss_comparison.pdf
outputs/chapter3_cellpose_loss_fig3_12_20260512/fig_3_12_cellpose_iid_500epoch_real_loss.png
outputs/chapter3_cellpose_loss_fig3_12_20260512/fig_3_12_cellpose_iid_500epoch_real_loss.pdf
outputs/chapter3_cellpose_loss_fig3_12_20260512/fig_3_12_cellpose_real_loss_points.csv
outputs/chapter3_cellpose_loss_fig3_12_20260512/fig_3_12_cellpose_real_loss_notes.md
outputs/chapter3_cellpose_loss_fig3_12_20260512/raw/
```

Windows-side synced copy:

```text
/mnt/d/N E T S/nnUNETV2/nnUNet-master/画图/chapter3_cellpose_loss_fig3_12_20260512
```

Recommended thesis figure:

```text
fig_3_12_cellpose_500epoch_real_loss_comparison.png
```

Caveat:

- Cellpose logs do not print every epoch. Both real training runs are configured with `n_epochs=500`, but each log contains 51 loss points from epoch 0 to 490 and then a final checkpoint save after training.
- Use `fig_3_12_cellpose_iid_500epoch_real_loss.png` only if the text specifically discusses the traditional random mixed benchmark row.

## Rules For Future Work

- Do not rely on semantic Dice alone; use instance PQ/AJI/F1 and source-level win rate.
- Do not claim all-source superiority: the 250-image benchmark supports overall and non-Cellpose superiority over Cellpose, but Cellpose-source images still underperform Cellpose.
- Do not claim CellSAM-level performance until a direct CellSAM comparison or reproduced public benchmark supports it.
- Treat Cellpose-style images as the main known failure domain.
- Keep Dataset620 as an ablation, Dataset621 as the current main training dataset.
- Prefer source-balanced sampling over raw natural dataset proportions.
- Avoid training/evaluation leakage: keep `outputs/benchmark_splits_large/eval_250.csv` excluded from training.
- Do not store passwords in this file.
