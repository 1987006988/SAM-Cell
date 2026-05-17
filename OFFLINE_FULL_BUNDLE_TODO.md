# Offline Full Bundle TODO

Current status: partial-offline runnable package.

Included now:

- Full SAM-Cell source code.
- Final SAM-Cell packaged config with relative paths.
- Proposal ranker joblib.
- SAM2 large checkpoint.
- nnU-Net Dataset621 and Dataset512 final fold checkpoints.
- nnU-Net and SAM2 source trees needed by the packaged config.
- Full CellCosmos images and masks: 16,777 images plus 16,777 masks.
- Five-image real smoke dataset and a ground-truth-as-prediction evaluation fixture.
- Metric summaries, figures, manifests, provenance docs, and one-click verification scripts.

Still needed for a complete offline reproduction archive:

- Full baseline weights/checkpoints for Cellpose fine-tuned variants, CellSAM, StarDist, and HoVer-Net if those exact trained baselines must be rerun without network or server access.
- Full prediction label directories and overlay directories for every baseline and SAM-Cell run if exact metric re-audits must avoid recomputing predictions.
- A frozen binary conda/venv image or container if users must run without creating an environment from `environment.yml`.
- Optional full nnU-Net raw/preprocessed training folders if users must retrain the semantic experts from scratch.

Approximate local sizes observed during packaging:

- packaged SAM-Cell key weights: about 3.9 GB total package before full CellCosmos copy.
- CellCosmos images: about 2.4 GB.
- CellCosmos masks: about 167 MB.
- full package after weights plus images/masks: about 6.4 GB.

Expected cost to become full-offline-runnable:

- Add several GB to tens of GB for all baseline weights and prediction directories, depending on which overlays and intermediate probability caches are preserved.
- Add more disk if storing conda/venv or container images.
- Re-run `scripts/verify_package.sh` and `scripts/run_all_smoke.sh` after every addition.
