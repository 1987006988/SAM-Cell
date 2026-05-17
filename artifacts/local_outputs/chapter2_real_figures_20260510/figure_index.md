# Chapter 2 Real-Data Figure Index

Generated from real SAM-Cell project outputs, not synthetic placeholders.

## 2.6.2 Quantitative Comparison

- `fig_2_09_cellcosmos_error_by_source.png`: Error = 1 - PQ by source for Cellpose cyto3, CellSAM, and SAM-Cell.
- `fig_2_10_error_transition_three_models.png`: Dataset-wise error transition across the three models.
- `fig_2_11_samcell_delta_pq_by_source.png`: SAM-Cell PQ delta relative to Cellpose and CellSAM.
- `fig_2_12_pairwise_pq_parity.png`: Pairwise PQ parity scatter against Cellpose and CellSAM.

Full CellCosmos ALL metrics:

| method | n | PQ | AJI | Dice |
|---|---:|---:|---:|---:|
| Cellpose cyto3 | 16777 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM | 16777 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell | 16777 | 0.608306 | 0.618288 | 0.865723 |

## 2.6.4 Ablation Replacement

- `fig_2_14_farood_stage_ablation_metrics.png`: staged module ablation on Far-OOD.
- `fig_2_15_farood_stage_pq_heatmap.png`: source-wise Far-OOD PQ heatmap over stages.
- `fig_2_16_farood_module_delta_pq.png`: paired module contribution in mean delta PQ.
- `fig_2_17_prompt_matched_sam2_diagnostic.png`: prompt-matched native SAM2 diagnostic.

Interpretation for 2.6.4: the dominant measured Far-OOD gain comes from EDT+watershed after the semantic foreground prior; proposal selection adds a smaller positive gain; coarse reinsertion is nearly neutral; SAM2 refinement is not the dominant contributor under the current measured proxy.
