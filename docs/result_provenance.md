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
