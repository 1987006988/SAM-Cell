# Native SAM2 Prompt-Matched Baseline

This baseline uses SAM-Cell proposals only to provide box + coarse-mask prompts to frozen SAM2.
It disables coarse fallback and SAM-Cell candidate acceptance selection.

prompt_mode: `box_mask`
n: `50`

| source | PQ | AJI | Dice |
|---|---:|---:|---:|
| ALL | 0.630938 | 0.629811 | 0.877933 |
| cellpose | 0.689956 | 0.693006 | 0.909890 |
| dsb2018 | 0.801499 | 0.829593 | 0.929133 |
| livecell | 0.600163 | 0.577510 | 0.908864 |
| pannuke | 0.521766 | 0.533171 | 0.779487 |
| tissuenet | 0.541307 | 0.515777 | 0.862289 |
