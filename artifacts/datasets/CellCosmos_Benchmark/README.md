# Packaged CellCosmos Data

This directory contains the packaged CellCosmos image/mask corpus used by the thesis full-corpus evaluation.

- `images/`: 16,777 raw images copied from `/mnt/d/cell data/CellCosmos_Benchmark/images` on 2026-05-12.
- `masks/`: 16,777 instance-label masks copied from `/mnt/d/cell data/CellCosmos_Benchmark/masks` on 2026-05-12.
- `full_manifest_packaged.csv`: relative-path manifest pointing to the packaged `images/` and `masks/` directories.

Count check performed during packaging:

- source images: 16,777
- packaged images: 16,777
- source masks: 16,777
- packaged masks: 16,777

The package still does not include full prediction labels/overlays for every baseline; those remain indexed in `artifacts/path_index/` and `OFFLINE_FULL_BUNDLE_TODO.md`.
