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
