# Fig. 3-12 Cellpose 500-Epoch Real Loss Curves

These figures replace the old simulated loss curve with values parsed from the original Cellpose training logs.

## Recommended thesis figure

- `fig_3_12_cellpose_500epoch_real_loss_comparison.png`
- `fig_3_12_cellpose_500epoch_real_loss_comparison.pdf`

This comparison figure shows the two real Cellpose 500-epoch training runs used in Chapter 3:

- I.I.D mixed-domain CellCosmos training: n_train=2693, n_val=697, reported IID validation PQ=0.6092.
- PanNuke core-domain training: n_train=1269, n_val=336, reported PanNuke core PQ=0.6207 and Far-OOD PQ=0.0247.

## IID-only figure

- `fig_3_12_cellpose_iid_500epoch_real_loss.png`
- `fig_3_12_cellpose_iid_500epoch_real_loss.pdf`

Use this if the text only discusses the traditional random mixed benchmark.

## Logging caveat

Cellpose does not print every single epoch loss in these logs. The curves use the logged checkpoints only: IID has 51 logged loss points from epoch 0 to 490; PanNuke has 51 logged loss points from epoch 0 to 490. Both runs were configured with `n_epochs=500`, and the final checkpoint was saved after training.
