# CellCosmos Core-Domain vs Far-Domain Comparison

- Core-domain split: `pannuke_core_test`.
- Far-domain split: `far_ood_test`.
- Metrics are mean per-image PQ/AJI/Dice using the project evaluator convention.

| model | core n | core PQ | core AJI | core Dice | far n | far PQ | far AJI | far Dice | far-core PQ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CellSAM generalist | 336 | 0.430049 | 0.397525 | 0.629841 | 1795 | 0.637605 | 0.641439 | 0.873047 | 0.207556 |
| Cellpose official cyto3 | 336 | 0.231988 | 0.197069 | 0.358094 | 1795 | 0.412207 | 0.387019 | 0.660719 | 0.180219 |
| Cellpose cyto3, PanNuke-finetuned | 336 | 0.620718 | 0.615648 | 0.791060 | 1795 | 0.024681 | 0.018660 | 0.055102 | -0.596036 |
| StarDist, PanNuke-trained | 336 | 0.626118 | 0.620731 | 0.799360 | 1795 | 0.022308 | 0.018220 | 0.042769 | -0.603809 |
| Native SAM2 automatic dense | 336 | 0.058126 | 0.019259 | 0.290695 | 1795 | 0.181334 | 0.120016 | 0.595004 | 0.123208 |
| HoVer-Net fast PanNuke | 336 | 0.549858 | 0.561091 | 0.817125 | 1795 | 0.005054 | 0.004639 | 0.008586 | -0.544803 |
| SAM-Cell refine final | 336 | 0.575995 | 0.596006 | 0.809390 | 1795 | 0.634569 | 0.634742 | 0.911718 | 0.058574 |

## Notes

- CellSAM generalist: public generalist; filtered from full 16777 per-image metrics
- Cellpose official cyto3: public official cyto3; not core-domain finetuned
- Cellpose cyto3, PanNuke-finetuned: core-domain supervised baseline
- StarDist, PanNuke-trained: core-domain supervised baseline
- Native SAM2 automatic dense: automatic masks, no SAM-Cell prompts
- HoVer-Net fast PanNuke: official PanNuke weights; filtered from Core3500 per-image metrics
- SAM-Cell refine final: final accepted SAM-Cell config; filtered from full 16777 metrics
