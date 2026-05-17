# Chapter 2 Figure And Ablation Replacement Notes

## 2.6.2 定量对比与性能分析

数据来源：

- `outputs/cellcosmos_full_16777_by_dataset_metrics_20260507/all_models_by_dataset_metrics.csv`
- 全量 CellCosmos，共 `16777` 张图像。
- 模型：Cellpose official cyto3、CellSAM generalist、SAM-Cell refine final。
- 指标：mean per-image PQ/AJI/Dice；图中 Error 定义为 `1 - PQ`。

建议图号：

- 图 2-9：`fig_2_09_cellcosmos_error_by_source.png`
  - 含义：不同数据源上三种模型的实例误差 `1 - PQ`，越低越好。
- 图 2-10：`fig_2_10_error_transition_three_models.png`
  - 含义：每个数据源中 Cellpose、CellSAM、SAM-Cell 的误差位置变化。
- 图 2-11：`fig_2_11_samcell_delta_pq_by_source.png`
  - 含义：SAM-Cell 相对 Cellpose 和 CellSAM 的 PQ 增益。
- 图 2-12：`fig_2_12_pairwise_pq_parity.png`
  - 含义：SAM-Cell 与两个基线的配对 PQ 散点；对角线上方表示 SAM-Cell 更优。

可写入正文的关键结果：

| model | n | PQ | AJI | Dice |
|---|---:|---:|---:|---:|
| Cellpose cyto3 | 16777 | 0.334346 | 0.304780 | 0.531469 |
| CellSAM | 16777 | 0.538885 | 0.524821 | 0.761598 |
| SAM-Cell | 16777 | 0.608306 | 0.618288 | 0.865723 |

建议表述：

在全量 CellCosmos 上，SAM-Cell 在整体 PQ、AJI 与前景 Dice 上均高于 Cellpose official cyto3 和 CellSAM generalist。按数据源拆分后，SAM-Cell 在 Cellpose、DSB2018 和 PanNuke 上取得最高 PQ；在 LIVECell 上 PQ 略低于 Cellpose，但 Dice 更高；在 TissueNet 上 PQ 略低于 CellSAM，但 Dice 仍略高。该结果说明 SAM-Cell 的优势主要体现为跨数据源稳定性和前景完整性，而不是在每一个单源数据集上都取得最高 PQ。

避免写法：

- 不要写 “SAM-Cell 在所有数据源上均超过 Cellpose/CellSAM”。
- 不要继续使用旧的模拟 Error/F1 数据。
- 不要把 CellSAM 结果写成 Cellpose 结果。

## 2.6.4 核心机制消融实验替换方案

原 2.6.4 中“裁剪膨胀因子敏感性”和“Box-only/Mask-only/Box+Mask”数值不是当前真实实验结果。建议整体替换为“模块级真实消融与 prompt-matched SAM2 诊断”。

真实数据来源：

- `outputs/chapter2_real_figures_20260510/farood_stage_metrics_used_for_2_6_4.csv`
- `outputs/chapter2_real_figures_20260510/farood_paired_delta_used_for_2_6_4.csv`
- `outputs/sam2_prompt_matched_eval50_20260507/prompt_matched_same50_comparison.csv`

建议图号：

- 图 2-14：`fig_2_14_farood_stage_ablation_metrics.png`
  - 含义：Far-OOD 上从语义连通域到完整 SAM-Cell 的阶段式消融。
- 图 2-15：`fig_2_15_farood_stage_pq_heatmap.png`
  - 含义：不同 Far-OOD 来源在各模块阶段的 PQ 热力图。
- 图 2-16：`fig_2_16_farood_module_delta_pq.png`
  - 含义：模块两两加入后的 mean paired delta PQ 与胜率。
- 图 2-17：`fig_2_17_prompt_matched_sam2_diagnostic.png`
  - 含义：使用同样 box+粗掩码提示的原生 SAM2 与 SAM-Cell proposal/final 的对照。

Far-OOD 阶段式消融 ALL 结果：

| stage | PQ | AJI | Dice |
|---|---:|---:|---:|
| Semantic connected components | 0.165386 | 0.105394 | 0.912512 |
| EDT + watershed | 0.614674 | 0.625914 | 0.911846 |
| Current proposal selection | 0.634858 | 0.633567 | 0.912538 |
| Coarse map, no SAM2 | 0.634858 | 0.633568 | 0.912538 |
| Full SAM-Cell | 0.634569 | 0.634742 | 0.911718 |

Paired module contribution：

| module delta | mean delta PQ | median delta PQ | win rate |
|---|---:|---:|---:|
| EDT + watershed over semantic CC | +0.449288 | +0.493635 | 0.964 |
| Proposal selection over raw watershed | +0.020184 | +0.002954 | 0.655 |
| Coarse reinsertion over proposal map | -0.000000 | 0.000000 | 0.022 |
| SAM2 refinement over coarse map | -0.000289 | 0.000000 | 0.309 |

Prompt-matched SAM2 eval50 ALL 结果：

| method | PQ | AJI | Dice |
|---|---:|---:|---:|
| Same proposals before SAM2 | 0.645019 | 0.644211 | 0.892967 |
| Native SAM2 box+mask prompts | 0.630938 | 0.629811 | 0.877933 |
| SAM-Cell final same50 | 0.644897 | 0.644737 | 0.892558 |

建议正文：

为避免仅从最终结果推断各模块作用，本文进一步在 Far-OOD 测试集上构建阶段式消融实验。首先，将 nnU-Net 语义前景直接连通域化作为最弱实例化基线；随后依次加入 EDT+watershed 拓扑分离、proposal 选择、粗实例图重组以及冻结 SAM2 精修模块。结果显示，仅依赖语义连通域时 PQ 为 0.1654，说明像素级前景召回虽然较高，但无法完成密集细胞的实例解耦。加入 EDT+watershed 后，PQ 大幅提升至 0.6147，paired mean delta PQ 达到 +0.4493，胜率为 96.4%，表明基于距离场的拓扑分离是当前 SAM-Cell 在远域泛化中的主要性能来源。进一步加入 proposal 选择后，PQ 提升至 0.6349，平均增益为 +0.0202，说明候选实例筛选能够带来稳定但相对较小的收益。相比之下，粗实例图重组几乎不改变整体 PQ，而冻结 SAM2 精修在当前 Far-OOD 设置下对 PQ 的平均贡献接近 0，甚至略为负值。这说明在当前实现中，SAM2 更适合作为边界修正与提示一致性模块，而不是主要的实例分离来源。

为进一步排除提示条件不公平的影响，本文补充构建了 prompt-matched SAM2 诊断实验，即使用与 SAM-Cell 相同的 proposal box 与粗掩码作为原生 SAM2 的输入提示。结果显示，原生 SAM2 box+mask prompt 在 balanced eval50 上的 PQ 为 0.6309，低于同一 proposal map 在进入 SAM2 前的 0.6450，也略低于 SAM-Cell final 的 0.6449。该结果进一步说明，当前 SAM-Cell 的主要有效机制并非简单来自 SAM2 解码器本身，而是来自前置语义场、EDT+watershed 拓扑分离和 proposal 筛选构成的结构化提示生成流程。

避免写法：

- 不要再声称 “Box+Mask 提示显著优于 Box-only/Mask-only”，除非后续真正补做该消融。
- 不要声称 “SAM2 精修是 Far-OOD 性能提升的主要来源”；当前数据不支持。
- 可以写 “SAM2 被保留为冻结式边界修正模块，但当前量化归因显示主增益来自拓扑 proposal 生成”。
