# 03_reproduced_baselines

Reproduced comparison networks and evaluation wrappers.

Included methods:

- Cellpose official cyto3, IID finetuned cyto3, and PanNuke-finetuned cyto3.
- StarDist IID and PanNuke-trained baselines.
- CellSAM generalist.
- Native SAM2 automatic dense and SAM2 prompt-matched box+mask diagnostic.
- HoVer-Net fast PanNuke through TIAToolbox.

Important caveats:

- HoVer-Net here uses official PanNuke weights, not CellCosmos finetuning.
- SAM2 prompt-matched eval50 is a supplementary prompt-fair diagnostic, not a full-corpus baseline.
- Missing or stale baseline artifacts should be refreshed with `../scripts/sync_from_server.sh`.

Key remote experiment root:

```text
/backup/taotao_work/sam_cell/experiments/cellcosmos_repro_20260501
```
