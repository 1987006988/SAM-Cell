# Active Goal Audit 20260507

Complete: True

| requirement | ok | evidence |
|---|---:|---|
| hourly watcher is present | True | session=hourly_full_postprocess_and_farood_20260507 alive=True; log=/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/logs/hourly_full_postprocess_and_farood_20260507/watch.log exists=True |
| Cellpose full PQ/AJI/Dice complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellpose_official_cyto3/metrics/summary_by_source.csv; per_image_rows=16777/16777 |
| CellSAM full PQ/AJI/Dice complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/cellsam_generalist/metrics/summary_by_source.csv; per_image_rows=16777/16777 |
| SAM-Cell full PQ/AJI/Dice complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/samcell_refine_final/summary.csv; per_image_rows=16777/16777 |
| three-model full PQ/AJI/Dice comparison exists | True | csv=/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/full_model_comparison_pq_aji_dice.csv models=['cellpose_official_cyto3', 'cellsam_generalist', 'samcell_refine_final'] md_exists=True |
| SAM-Cell full delta versus Cellpose and CellSAM exists | True | csv=/backup/taotao_work/sam_cell/experiments/cellcosmos_full_16777_20260503/metrics/full_model_comparison_20260507/samcell_delta_vs_baselines.csv baselines=['cellpose_official_cyto3', 'cellsam_generalist'] md_exists=True |
| Far-OOD attribution stage metrics complete | True | combined=/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/combined_summary.csv methods=['coarse_no_sam2', 'current_proposal', 'full_samcell', 'raw_watershed', 'semantic_cc'] farood_n=1795 interpretation_exists=True |
| Far-OOD paired-delta attribution complete | True | paired_delta=/backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/paired_delta_summary.csv deltas=['crop_coarse_reinsertion_over_proposal_map', 'current_proposal_selection_over_raw_watershed', 'edt_watershed_over_semantic_cc', 'sam2_refinement_over_coarse_no_sam2'] |
| Far-OOD coarse_no_sam2 per-stage artifacts complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/coarse_no_sam2/summary.csv; per_image_rows=1795/1795 |
| Far-OOD current_proposal per-stage artifacts complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/current_proposal/summary.csv; per_image_rows=1795/1795 |
| Far-OOD full_samcell per-stage artifacts complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/full_samcell/summary.csv; per_image_rows=1795/1795 |
| Far-OOD raw_watershed per-stage artifacts complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/raw_watershed/summary.csv; per_image_rows=1795/1795 |
| Far-OOD semantic_cc per-stage artifacts complete | True | ALL metrics present: /backup/taotao_work/sam_cell/experiments/farood_module_attribution_20260507/semantic_cc/summary.csv; per_image_rows=1795/1795 |
