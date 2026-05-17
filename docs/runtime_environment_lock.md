# Runtime Environment Lock

This package includes source code and model/data artifacts, not a binary conda or virtualenv directory.

The local environment used for packaging was:

- Python: `3.10.13`
- torch: `2.5.1`
- torchvision: `0.20.1`
- numpy: `2.2.6`
- scipy: `1.15.2`
- scikit-image: `0.25.2`
- Pillow: `11.1.0`
- tifffile: `2025.2.18`
- PyYAML: `6.0.3`
- pandas: `2.3.3`
- scikit-learn: `1.7.2`
- joblib: `1.5.3`
- OpenCV: `4.13.0`

Packaged source dependencies:

- `artifacts/third_party/segment-anything-2/`
- `artifacts/third_party/nnUNet/`

Recommended setup:

```bash
conda env create -f environment.yml
conda activate sam-cell-package
bash scripts/run_all_smoke.sh
```

If the environment is already created elsewhere, set:

```bash
PYTHON_BIN=/path/to/python bash scripts/run_all_smoke.sh
```

The package scripts also auto-detect `/home/taotao/anaconda3/envs/SAM-Cell/bin/python` on the original workstation, but that path is only a convenience fallback and is not required on another machine.
