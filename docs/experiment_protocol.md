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
