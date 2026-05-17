# SAM-Cell Full Inference And Far-OOD Attribution Report

Audit complete: True

## Full CellCosmos 16777 Metrics

| method | n | PQ | AJI | Dice |
|---|---:|---:|---:|---:|
| cellpose_official_cyto3 | 16777 | 0.334346 | 0.304780 | 0.531469 |
| cellsam_generalist | 16777 | 0.538885 | 0.524821 | 0.761598 |
| samcell_refine_final | 16777 | 0.608306 | 0.618288 | 0.865723 |

## SAM-Cell Delta On Full CellCosmos

| baseline | delta PQ | delta AJI | delta Dice |
|---|---:|---:|---:|
| cellpose_official_cyto3 | 0.273960 | 0.313507 | 0.334254 |
| cellsam_generalist | 0.069421 | 0.093467 | 0.104125 |

## Far-OOD Attribution

| stage | ALL PQ | ALL AJI | ALL Dice |
|---|---:|---:|---:|
| semantic_cc | 0.165386 | 0.105394 | 0.912512 |
| raw_watershed | 0.614674 | 0.625914 | 0.911846 |
| current_proposal | 0.634858 | 0.633567 | 0.912538 |
| coarse_no_sam2 | 0.634858 | 0.633568 | 0.912538 |
| full_samcell | 0.634569 | 0.634742 | 0.911718 |

## Far-OOD Paired Deltas

| delta | mean delta PQ | median delta PQ | PQ win rate |
|---|---:|---:|---:|
| crop_coarse_reinsertion_over_proposal_map | -0.000000 | 0.000000 | 0.022 |
| current_proposal_selection_over_raw_watershed | 0.020184 | 0.002954 | 0.655 |
| edt_watershed_over_semantic_cc | 0.449288 | 0.493635 | 0.964 |
| sam2_refinement_over_coarse_no_sam2 | -0.000289 | 0.000000 | 0.309 |

## Answer

Within the staged current-method attribution, the largest mean paired per-image PQ gain on Far-OOD comes from `edt_watershed_over_semantic_cc` with mean delta PQ 0.449288. This indicates the dominant measured contribution is that stage, while earlier/later modules should be interpreted as interacting components rather than independent causal effects.
