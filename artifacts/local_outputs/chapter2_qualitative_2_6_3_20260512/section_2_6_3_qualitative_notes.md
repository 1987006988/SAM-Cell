# Chapter 2.6.3 Qualitative Visualization

Recommended figure:

- Fig. 2-13: `fig_2_13_qualitative_error_correction_panel.png/.pdf`

One-line caption:

图 2-13 不同显微成像场景下 Cellpose、CellSAM 与 SAM-Cell 的实例分割可视化对比。

Text replacement:

图 2-13 展示了五类代表性显微图像场景下的定性分割结果，包括 H&E 染色病理图像、组织细胞图像、低信噪比荧光图像、相差显微图像以及常规细胞培养图像。每一行对应一个来源数据集，每一列分别给出原始图像、人工标注、Cellpose cyto3、CellSAM 和 SAM-Cell 的实例掩码叠加结果。可以看到，SAM-Cell 在密集细胞、低对比度边界和跨域成像风格下通常能够保持较连续的实例轮廓，并减少粘连区域中的漏分割和过度扩张现象。该结果从视觉层面说明，语义前景引导、局部区域重构、混合提示和候选筛选机制能够在不微调 SAM2 的条件下提升复杂显微场景中的实例边界质量。
