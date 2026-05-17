# Far-OOD SAM-Cell Module Attribution

This attribution uses the frozen Far-OOD manifest and reports mean per-image metrics.

| stage | module interpretation | ALL PQ | SOURCE_MACRO PQ | ALL AJI | ALL Dice |
|---|---|---:|---:|---:|---:|
| semantic_cc | nnU-Net semantic foreground connected components | 0.165386 | 0.301609 | 0.105394 | 0.912512 |
| raw_watershed | EDT/watershed instance separation | 0.614674 | 0.642606 | 0.625914 | 0.911846 |
| current_proposal | current proposal selection/merging before SAM2 | 0.634858 | 0.694278 | 0.633567 | 0.912538 |
| coarse_no_sam2 | adaptive crop plus coarse-mask reinsertion without SAM2 | 0.634858 | 0.694278 | 0.633568 | 0.912538 |
| full_samcell | SAM2 refinement with box+mask prompts | 0.634569 | 0.694212 | 0.634742 | 0.911718 |

## PQ Deltas

| delta | ALL PQ delta | interpretation |
|---|---:|---|
| semantic_cc -> raw_watershed | 0.449288 | effect of EDT/watershed over semantic connected components |
| raw_watershed -> current_proposal | 0.020184 | effect of current proposal filtering/selection/merge |
| current_proposal -> coarse_no_sam2 | -0.000000 | effect of crop/coarse-mask reinsertion without SAM2 |
| coarse_no_sam2 -> full_samcell | -0.000289 | effect of SAM2 refinement |

## Comparator Anchor

- Cellpose official cyto3 Far-OOD ALL PQ: 0.412207
- Full SAM-Cell Far-OOD ALL PQ: 0.634569
- Full SAM-Cell minus Cellpose ALL PQ: 0.222362

## Current Evidence-Based Answer

The largest positive ALL-PQ step in this staged attribution is: effect of EDT/watershed over semantic connected components (0.449288).
Treat this as a quantitative attribution within the current method, not a causal proof independent of component interactions.

## Paired Per-Image Delta Check

| delta | mean delta PQ | median delta PQ | PQ win rate |
|---|---:|---:|---:|
| crop_coarse_reinsertion_over_proposal_map | -0.000000 | 0.000000 | 0.022 |
| current_proposal_selection_over_raw_watershed | 0.020184 | 0.002954 | 0.655 |
| edt_watershed_over_semantic_cc | 0.449288 | 0.493635 | 0.964 |
| sam2_refinement_over_coarse_no_sam2 | -0.000289 | 0.000000 | 0.309 |

Paired-delta conclusion:

- The largest mean paired per-image PQ gain is `edt_watershed_over_semantic_cc` (0.449288).
