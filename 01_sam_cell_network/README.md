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
