# SAM-Cell Thesis Experiment Package

Built from `/home/taotao/sam_cell` on 2026-05-12.

GitHub publication note: the local thesis bundle contains large offline assets
including SAM2/nnU-Net weights and the full 16,777-image CellCosmos copy. These
assets are intentionally excluded from normal Git history by `.gitignore`
because GitHub rejects files larger than 100 MB without a working Git LFS setup.
The online repository keeps code, configs, scripts, manifests, provenance docs,
metric tables, and smoke fixtures; restore large assets from the local bundle or
the paths recorded under `artifacts/path_index/` when full inference is needed.

This package is a partial-offline runnable and traceable delivery bundle for the SAM-Cell master's thesis experiments. It includes the final SAM-Cell code/config chain, key SAM-Cell inference weights, the SAM2 checkpoint/source, nnU-Net source/final fold checkpoints, the proposal-ranker joblib, full CellCosmos images/masks, smoke fixtures, metric summaries, figures, logs/provenance notes, and path indexes.

It does not include a binary conda/venv environment, full baseline training checkpoints, or full prediction/overlay directories for every method.

## Directory Layout

- `01_sam_cell_network/`: complete SAM-Cell source package, configs, tests, and project scripts.
- `02_cellcosmos_dataset_work/`: CellCosmos/Core3500/Full16777 dataset construction and thesis figure/table scripts.
- `03_reproduced_baselines/`: Cellpose, StarDist, CellSAM, SAM2, and HoVer-Net wrappers.
- `scripts/`: top-level one-click smoke, verification, and server-sync scripts.
- `docs/`: experiment protocol, environment, path mapping, and result provenance.
- `artifacts/`: metric summaries, figures, manifests, path indexes, packaged weights, full CellCosmos images/masks, smoke fixtures, and remote-synced small files.

## One-Click Order

```bash
cd /mnt/d/毕业数据/课题实验相关
bash scripts/verify_package.sh
bash scripts/run_all_smoke.sh
```

`verify_package.sh` checks package structure, portable config paths, key weights, the 16,777-row packaged CellCosmos manifest, and shell syntax. `run_all_smoke.sh` runs the SAM-Cell inference preflight and a real five-image label-evaluation fixture.

Create the environment before running model inference on a new machine:

```bash
conda env create -f environment.yml
conda activate sam-cell-package
bash scripts/check_runtime_env.sh
```

Run a packaged SAM-Cell one-image inference after the environment is ready:

```bash
DRY_RUN=0 DEVICE=auto bash scripts/run_packaged_samcell_inference.sh --run
```

`DEVICE=auto` uses CUDA only when `torch.cuda.is_available()` is true. For CPU-only machines, use `DEVICE=cpu`; it will be much slower.

Run full CellCosmos inference from packaged images:

```bash
IMAGE_DIR=artifacts/datasets/CellCosmos_Benchmark/images LIMIT=0 OUT_DIR=artifacts/runs/samcell_full16777 DRY_RUN=0 bash scripts/run_packaged_samcell_inference.sh --run
```

This is a long GPU job and is not launched by default.

Evaluate any existing prediction-label directory against the packaged full CellCosmos manifest:

```bash
MANIFEST_CSV=artifacts/datasets/CellCosmos_Benchmark/full_manifest_packaged.csv \
PRED_DIR=/path/to/prediction_labels \
PRED_PATTERN='{stem}.tif' \
METHOD_NAME=my_method \
OUT_DIR=artifacts/runs/my_method_eval \
DRY_RUN=0 \
bash scripts/run_baseline_eval_smoke.sh
```

## Final Audited Result

Metrics are mean per-image values.

| method | n | F1 | PQ | AJI | Dice |
|---|---:|---:|---:|---:|---:|
| Cellpose official cyto3 | 16777 | 0.456724 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM generalist | 16777 | 0.701177 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell refine final | 16777 | 0.746555 | 0.608306 | 0.618288 | 0.865723 |

Source caveat: SAM-Cell is strongest overall, but not best on every source/metric. TissueNet has higher CellSAM PQ/AJI/F1, and LIVECell has higher Cellpose PQ/AJI/F1; SAM-Cell has the strongest overall pooled result and strongest Dice.

## Included vs Not Included

Included:

- final SAM-Cell packaged config: `01_sam_cell_network/configs/sam_cell_final_packaged.yaml`
- proposal ranker: `artifacts/weights/proposal_ranker_dual/proposal_ranker.joblib`
- SAM2 large checkpoint: `artifacts/weights/sam2/checkpoints/sam2_hiera_large.pt`
- nnU-Net Dataset621 and Dataset512 final fold checkpoints under `artifacts/weights/nnunet/`
- packaged SAM2 and nnU-Net source under `artifacts/third_party/`
- full CellCosmos images/masks and relative manifest under `artifacts/datasets/CellCosmos_Benchmark/`
- five-image smoke dataset and prediction fixture under `artifacts/smoke_data/`
- environment specs: `environment.yml`, `requirements.txt`, `docs/runtime_environment_lock.md`

Not included:

- a binary conda/venv directory
- full baseline weights/checkpoints for Cellpose fine-tuned variants, CellSAM, StarDist, and HoVer-Net
- full prediction and overlay directories for every baseline/SAM-Cell run
- raw/preprocessed nnU-Net training folders needed to retrain semantic experts from scratch

See `OFFLINE_FULL_BUNDLE_TODO.md` for the remaining cost to make this a fully offline archive.
