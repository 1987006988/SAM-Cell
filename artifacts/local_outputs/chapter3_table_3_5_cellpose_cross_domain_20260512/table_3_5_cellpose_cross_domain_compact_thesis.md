# 表 3-5 Cellpose 在 CellCosmos 跨域评估范式下的 PQ 对比

PQ 为对应测试集 ALL 行的 mean per-image PQ；完整 F1/PQ/AJI/Dice 见 summary 表。

|评估基准设定|测试集物理分布状态|锚点网络|测试集全景质量PQ|
|---|---|---|---|
|传统随机混合基准|I.I.D|Cellpose（自主训练 500 Epochs）|0.6092|
|CellCosmos 单源域基准|Far-OOD|Cellpose（PanNuke 核心域训练）|0.0247|
|CellCosmos 通用跨域基准|Far-OOD|Cellpose（官方 cyto3 预训练模型）|0.4122|
