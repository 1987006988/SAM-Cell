# Environment Reproduction

Local WSL environment used during development:

```text
repo: /home/taotao/sam_cell
conda env for plotting/runtime smoke: /home/taotao/anaconda3/envs/SAM-Cell
nnU-Net local cache: /home/taotao/nnUNet/nnUNetFrame
SAM2 local source: /home/taotao/segment-anything-2
```

Remote workstation:

```text
ssh taotao@10.181.10.20
work root: /backup/taotao_work
sam-cell root: /backup/taotao_work/sam_cell
GPU: 2 x NVIDIA A100-PCIE-40GB
nnU-Net/SAM-Cell env: /backup/taotao_work/venvs/nnunet
Cellpose env: /backup/taotao_work/venvs/cellpose311
CellSAM env: /backup/taotao_work/venvs/cellsam311_shared
HoVer-Net env: /backup/taotao_work/venvs/hovernet311_shared
```

Top-level smoke scripts expose path variables and default to dry-run. Do not launch long full training unless you explicitly set the corresponding environment variables and output paths.
