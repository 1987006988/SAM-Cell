# Prompt-Matched SAM2 Same-50 Comparison

| source | method | n | PQ | AJI | Dice |
|---|---|---:|---:|---:|---:|
| ALL | sam2_prompt_matched_box_mask | 50 | 0.630938 | 0.629811 | 0.877933 |
| ALL | same_proposals_before_sam2 | 50 | 0.645019 | 0.644211 | 0.892967 |
| ALL | samcell_refine_final_same50 | 50 | 0.644897 | 0.644737 | 0.892558 |
| cellpose | sam2_prompt_matched_box_mask | 10 | 0.689956 | 0.693006 | 0.909890 |
| cellpose | same_proposals_before_sam2 | 10 | 0.696170 | 0.696649 | 0.920401 |
| cellpose | samcell_refine_final_same50 | 10 | 0.696404 | 0.697254 | 0.920369 |
| dsb2018 | sam2_prompt_matched_box_mask | 10 | 0.801499 | 0.829593 | 0.929133 |
| dsb2018 | same_proposals_before_sam2 | 10 | 0.809963 | 0.838804 | 0.935867 |
| dsb2018 | samcell_refine_final_same50 | 10 | 0.809972 | 0.838838 | 0.935873 |
| livecell | sam2_prompt_matched_box_mask | 10 | 0.600163 | 0.577510 | 0.908864 |
| livecell | same_proposals_before_sam2 | 10 | 0.615452 | 0.596945 | 0.926647 |
| livecell | samcell_refine_final_same50 | 10 | 0.615185 | 0.597137 | 0.925949 |
| pannuke | sam2_prompt_matched_box_mask | 10 | 0.521766 | 0.533171 | 0.779487 |
| pannuke | same_proposals_before_sam2 | 10 | 0.533347 | 0.545164 | 0.787987 |
| pannuke | samcell_refine_final_same50 | 10 | 0.533025 | 0.545358 | 0.787838 |
| tissuenet | sam2_prompt_matched_box_mask | 10 | 0.541307 | 0.515777 | 0.862289 |
| tissuenet | same_proposals_before_sam2 | 10 | 0.570161 | 0.543495 | 0.893933 |
| tissuenet | samcell_refine_final_same50 | 10 | 0.569900 | 0.545097 | 0.892762 |
