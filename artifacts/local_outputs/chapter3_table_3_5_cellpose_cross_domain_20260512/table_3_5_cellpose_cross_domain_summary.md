# Table 3-5 Cellpose under CellCosmos cross-domain evaluation

ALL is the mean over all images in the split; Source_macro is the unweighted mean over source-level rows.

|model_setting|training_domain|evaluation_paradigm|test_domain|n|F1|PQ|AJI|Dice|Source_macro_PQ|Source_macro_F1|note|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Cellpose official cyto3|public cyto3 pretrained; no CellCosmos finetune|PanNuke core/source test|PanNuke|336|0.3130|0.2320|0.1971|0.3581|0.2320|0.3130|public generalist reference; weak on PanNuke core|
|Cellpose official cyto3|public cyto3 pretrained; no CellCosmos finetune|non-PanNuke Far-OOD test|TissueNet + DSB2018 + Cellpose + LIVECell|1795|0.5623|0.4122|0.3870|0.6607|0.6122|0.7610|public generalist reference on unseen non-PanNuke domains|
|Cellpose cyto3 + IID finetune|CellCosmos mixed-source iid_train|random mixed-domain IID validation|mixed CellCosmos iid_val|697|0.7607|0.6092|0.5992|0.8180|0.6242|0.7796|random split; not a strict OOD test|
|Cellpose cyto3 + PanNuke finetune|PanNuke train only|PanNuke core/source test|PanNuke|336|0.7575|0.6207|0.6156|0.7911|0.6207|0.7575|single-source supervised in-domain performance|
|Cellpose cyto3 + PanNuke finetune|PanNuke train only|non-PanNuke Far-OOD test|TissueNet + DSB2018 + Cellpose + LIVECell|1795|0.0352|0.0247|0.0187|0.0551|0.0577|0.0792|strict cross-domain transfer after single-source training|
