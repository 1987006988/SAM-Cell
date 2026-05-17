# Full CellCosmos Reproduction Audit

- root: `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503`
- manifest n: `16777`
- source counts: `{'cellpose': 540, 'dsb2018': 670, 'livecell': 1000, 'pannuke': 7558, 'tissuenet': 7009}`
- missing image paths: `0`
- missing mask paths: `0`

| method | labels | per-image | summary diff | sampled | sample mismatches | ALL PQ | ALL AJI | ALL Dice | key params/status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| cellpose_official_cyto3 | 16777 | 16777 | 1.11e-16 | 50 | 0 | 0.334346 | 0.304780 | 0.531469 | pretrained_model=cyto3; diameter=0 |
| cellsam_generalist | 16777 | 16777 | 0 | 50 | 0 | 0.538885 | 0.524821 | 0.761598 | bbox_threshold=0.4; grayscale_mode=repeat; use_wsi=False; status={'skipped': 10279, 'empty_from_blank_image': 3, 'done': 6492, 'empty_from_cellsam_none': 3} |
| samcell_refine_final | 16777 | 16777 | 0 | 50 | 0 | 0.608306 | 0.618288 | 0.865723 |  |

## Notes

- `summary diff` is the maximum absolute difference between summary CSV metrics and metrics re-aggregated from per-image CSV.
- Sample recomputation reads prediction labels and GT masks and recomputes PQ/AJI/Dice with the repository evaluator.

## SAM-Cell Config Chain

- run manifest: `/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/run_manifest_samcell_tn_refine.json`
- final config: `/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml`
- config 1: `/backup/taotao_work/sam_cell/outputs/tissuenet_refine_combo_search_20260504/sam_cell_tissuenet_refine_best_config.yaml`
- config 1 extends: `/backup/taotao_work/sam_cell/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml`
- config 2: `/backup/taotao_work/sam_cell/configs/sam_cell_global_adaptive_selector_v3_cellpose_boundary_workstation2.yaml`
- config 2 extends: `sam_cell_global_adaptive_selector_v2_workstation2.yaml`
- config 3: `/backup/taotao_work/sam_cell/configs/sam_cell_global_adaptive_selector_v2_workstation2.yaml`
- semantic expert `universal_boundary`: model_dir=`/backup/taotao_work/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d`, folds=`[0, 1, 2, 3, 4]`, checkpoint=`checkpoint_final.pth`, foreground=`[1, 2]`, boundary=`2`, enabled_sources=`None`
- semantic expert `cellpose_style`: model_dir=`/backup/taotao_work/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d`, folds=`[0, 1, 2, 3, 4]`, checkpoint=`checkpoint_final.pth`, foreground=`[1]`, boundary=`None`, enabled_sources=`['cellpose']`
- proposal ranker: enabled=`True`, model=`/backup/taotao_work/sam_cell/outputs/proposal_ranker_dual/proposal_ranker.joblib`, keep_threshold=`0.45`, enabled_sources=`['cellpose']`
- SAM prompt/model: checkpoint=`/backup/taotao_work/segment-anything-2/checkpoints/sam2_hiera_large.pt`, cfg=`sam2_hiera_l.yaml`, prompt_mode=`['box_mask']`
