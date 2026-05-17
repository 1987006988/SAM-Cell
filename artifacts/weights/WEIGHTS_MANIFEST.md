# Packaged Weights Manifest

Packaged on 2026-05-12 from the local workstation after checking available disk space.

Included model artifacts:

- `proposal_ranker_dual/proposal_ranker.joblib`
  - Source: `/home/taotao/sam_cell/outputs/proposal_ranker_dual/proposal_ranker.joblib`
  - Purpose: final cellpose-source proposal ranker used by `sam_cell_final_packaged.yaml`.
- `sam2/checkpoints/sam2_hiera_large.pt`
  - Source: `/home/taotao/segment-anything-2/checkpoints/sam2_hiera_large.pt`
  - Purpose: SAM2 large image predictor checkpoint for SAM-Cell refinement.
- `nnunet/Dataset621_SAMCellUniversalBoundary/.../fold_*/checkpoint_final.pth`
  - Source: `/home/taotao/nnUNet/nnUNetFrame/nnUNet_results/Dataset621_SAMCellUniversalBoundary/nnUNetTrainer__nnUNetPlans__2d`
  - Purpose: universal boundary semantic expert.
- `nnunet/Dataset512_CellPose/.../fold_*/checkpoint_final.pth`
  - Source: `/mnt/d/N E T S/nnUNet/nnUNetFrame/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d`
  - Purpose: cellpose-style semantic expert.

Not included:

- Full baseline model training checkpoints for Cellpose, CellSAM, StarDist, HoVer-Net.
- Full prediction/overlay directories for all 16,777 images.
- Conda/venv binary environment directories.

The packaged SAM-Cell final config with relative paths is:

```text
01_sam_cell_network/configs/sam_cell_final_packaged.yaml
```
