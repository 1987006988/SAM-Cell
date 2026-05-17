from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RuntimeConfig:
    device: str = "cuda"
    seed: int = 42


@dataclass
class ImageConfig:
    force_rgb: bool = True
    normalize_mode: str = "none"
    lower_percentile: float = 1.0
    upper_percentile: float = 99.0
    output_uint8: bool = True


@dataclass
class SemanticConfig:
    name: str = "default"
    enabled: bool = True
    source_name: str | None = None
    backend: str = "nnunet"
    nnunet_repo: str | None = "/home/taotao/nnUNet"
    nnunet_model_dir: str = "/mnt/d/N E T S/nnUNet/nnUNetFrame/nnUNet_results/Dataset512_CellPose/nnUNetTrainer__nnUNetPlans__2d"
    nnunet_folds: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    checkpoint_name: str = "checkpoint_final.pth"
    foreground_threshold: float = 0.5
    foreground_class_indices: list[int] = field(default_factory=lambda: [1])
    boundary_class_index: int | None = None
    proposal_thresholds: list[float] | None = None
    min_foreground_area: int = 20
    fill_holes: bool = True
    closing_radius: int = 1
    grayscale_mode: str = "luminance"
    prob_cache_dir: str | None = None
    enabled_sources: list[str] | None = None
    disabled_sources: list[str] | None = None


@dataclass
class ProposalRankerConfig:
    enabled: bool = False
    model_path: str | None = None
    keep_threshold: float = 0.5
    top_k: int | None = None
    enabled_sources: list[str] | None = None
    disabled_sources: list[str] | None = None


@dataclass
class WatershedConfig:
    edt_sigma: float = 1.0
    marker_method: str = "h_maxima"
    h_maxima: float = 0.15
    h_maxima_values: list[float] | None = None
    peak_threshold_rel: float = 0.2
    min_distance_factor: float = 0.45
    min_marker_distance: int = 3
    min_instance_area: int = 20
    max_instance_area: int | None = None
    proposal_duplicate_iou_threshold: float = 0.85
    boundary_suppression_weight: float = 0.0
    boundary_additive_weight: float = 0.0
    boundary_smoothing_sigma: float = 0.0
    share_boundary_across_experts: bool = False
    marker_rescue_enabled: bool = False
    marker_rescue_area_factor: float = 1.35
    marker_rescue_min_component_area: int = 80
    marker_rescue_min_distance_factor: float = 0.55
    marker_rescue_peak_threshold_rel: float = 0.08
    marker_rescue_max_markers: int = 128


@dataclass
class ProposalRepairConfig:
    enabled: bool = False
    split_enabled: bool = False
    split_min_area_factor: float = 2.2
    split_min_area_absolute: int = 120
    split_max_compactness: float = 0.65
    split_h_maxima_values: list[float] | None = None
    split_peak_threshold_rel: float = 0.2
    split_min_distance_factor: float = 0.35
    split_min_marker_distance: int = 3
    split_max_children: int = 6
    split_min_child_area: int = 10
    split_min_child_area_fraction: float = 0.0
    split_min_child_mean_fg_prob: float = 0.0
    split_min_child_parent_fg_delta: float = -1.0
    split_min_child_compactness: float = 0.0
    split_min_covered_fraction: float = 0.85
    split_keep_parent: bool = False
    set_selector_enabled: bool = False
    set_selector_iou_threshold: float = 0.55
    set_selector_containment_threshold: float = 0.75
    set_selector_center_distance_factor: float = 0.35
    set_selector_score_margin: float = 0.02


@dataclass
class ExternalProposalConfig:
    enabled: bool = False
    label_dir: str | None = None
    suffix: str = "_cp_masks.tif"
    mode: str = "augment"
    source_name: str = "external"
    min_area: int | None = None
    max_area: int | None = None
    duplicate_iou_threshold: float = 0.85
    coarse_score: float = 0.95
    min_internal_uncovered_fraction: float = 0.0
    min_internal_uncovered_pixels: int = 0
    internal_min_area: int | None = None
    internal_max_area: int | None = None
    internal_min_mean_fg_prob: float = 0.0
    max_internal_additions: int | None = None
    max_internal_additions_ratio: float | None = None
    internal_selector_model: str | None = None
    internal_selector_threshold: float = 0.5
    external_selector_model: str | None = None
    external_selector_keep_threshold: float = 0.05


@dataclass
class SeparatorProposalConfig:
    enabled: bool = False
    model_path: str | None = None
    source_name: str = "separator"
    enabled_sources: list[str] | None = None
    disabled_sources: list[str] | None = None
    mode: str = "augment"
    device: str | None = None
    input_channels: int = 4
    base_channels: int = 32
    fg_threshold: float = 0.35
    semantic_gate_threshold: float = 0.20
    center_threshold: float = 0.25
    center_nms_min_distance: int = 3
    center_nms_radius_factor: float = 0.35
    max_seeds_per_component: int = 64
    min_area: int = 10
    max_area: int | None = None
    boundary_weight: float = 0.70
    edt_sigma: float = 0.5


@dataclass
class CropConfig:
    alpha: float = 0.2
    min_crop_size: int = 64
    max_crop_size: int = 1024
    square_crop: bool = True
    clip_to_image: bool = True


@dataclass
class SAM2Config:
    enabled: bool = True
    sam2_repo: str | None = "/home/taotao/segment-anything-2"
    checkpoint: str = "/home/taotao/segment-anything-2/checkpoints/sam2_hiera_large.pt"
    config: str = "sam2_hiera_l.yaml"
    autocast_dtype: str = "bfloat16"
    multimask_output: bool = False
    return_logits: bool = True
    prompt_modes: list[str] = field(default_factory=lambda: ["box_mask"])
    mask_prompt_size: int = 256
    mask_logit_scale: float = 10.0
    score_threshold: float = 0.0
    apply_postprocessing: bool = True


@dataclass
class MergeConfig:
    use_pixel_logits: bool = True
    duplicate_iou_threshold: float = 0.85
    min_refined_area: int = 15
    max_area_growth_ratio: float = 3.0
    min_coarse_refined_iou: float = 0.05
    semantic_gate_dilation: int = 3
    keep_coarse_candidate: bool = True
    coarse_score: float = 0.5
    accept_sam2_min_score: float = 0.0
    accept_sam2_min_coarse_iou: float = 0.15
    accept_sam2_max_area_growth_ratio: float = 3.0
    accept_sam2_min_semantic_support: float = 0.35
    semantic_support_threshold: float = 0.35


@dataclass
class OutputConfig:
    save_label_map: bool = True
    save_instance_json: bool = True
    save_overlay: bool = True
    save_debug: bool = False


@dataclass
class SAMCellConfig:
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    semantic: SemanticConfig = field(default_factory=SemanticConfig)
    semantic_experts: list[SemanticConfig] = field(default_factory=list)
    proposal_ranker: ProposalRankerConfig = field(default_factory=ProposalRankerConfig)
    watershed: WatershedConfig = field(default_factory=WatershedConfig)
    proposal_repair: ProposalRepairConfig = field(default_factory=ProposalRepairConfig)
    external_proposals: ExternalProposalConfig = field(default_factory=ExternalProposalConfig)
    separator_proposals: SeparatorProposalConfig = field(default_factory=SeparatorProposalConfig)
    crop: CropConfig = field(default_factory=CropConfig)
    sam2: SAM2Config = field(default_factory=SAM2Config)
    merge: MergeConfig = field(default_factory=MergeConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    source_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)


def _merge_dataclass(instance: Any, values: dict[str, Any]) -> Any:
    for f in fields(instance):
        if f.name not in values:
            continue
        current = getattr(instance, f.name)
        incoming = values[f.name]
        if is_dataclass(current) and isinstance(incoming, dict):
            _merge_dataclass(current, incoming)
        else:
            setattr(instance, f.name, incoming)
    return instance


def _coerce_semantic_config(value: Any) -> SemanticConfig:
    if isinstance(value, SemanticConfig):
        return value
    if not isinstance(value, dict):
        raise ValueError(f"semantic_experts entries must be mappings, got {type(value).__name__}")
    cfg = SemanticConfig()
    _merge_dataclass(cfg, value)
    return cfg


def load_config(path: str | Path | None = None) -> SAMCellConfig:
    if path is None:
        return SAMCellConfig()
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        values = yaml.safe_load(f) or {}
    if not isinstance(values, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    extends = values.pop("extends", None)
    if extends:
        base_path = Path(extends)
        if not base_path.is_absolute():
            base_path = path.parent / base_path
        cfg = load_config(base_path)
    else:
        cfg = SAMCellConfig()
    _merge_dataclass(cfg, values)
    cfg.semantic_experts = [_coerce_semantic_config(item) for item in cfg.semantic_experts]
    return cfg
