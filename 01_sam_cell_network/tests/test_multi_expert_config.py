from __future__ import annotations

import numpy as np

from sam_cell.config import load_config
from sam_cell.config import SAMCellConfig, SemanticConfig
from sam_cell.pipeline import SAMCellPipeline
from sam_cell.proposals.internal_selector import proposal_features
from sam_cell.proposals.regions import InstanceProposal, merge_duplicate_proposals


def _proposal(source: str, rank_score: float, area: int = 25) -> InstanceProposal:
    mask = np.zeros((16, 16), dtype=bool)
    mask[2:7, 2:7] = True
    return InstanceProposal(
        id=1,
        bbox_xyxy=(2, 2, 7, 7),
        mask=mask,
        area=area,
        centroid_xy=(4.0, 4.0),
        mean_fg_prob=0.5,
        source=source,
        rank_score=rank_score,
    )


def test_multi_expert_config_loads_sources() -> None:
    cfg = load_config("configs/sam_cell_multi_expert_dual.yaml")
    assert [expert.name for expert in cfg.semantic_experts] == ["universal_boundary", "cellpose_style"]
    assert [expert.source_name for expert in cfg.semantic_experts] == ["universal_boundary", "cellpose_style"]
    assert cfg.proposal_ranker.enabled is False

    ranked = load_config("configs/sam_cell_multi_expert_dual_ranked.yaml")
    assert ranked.proposal_ranker.enabled is True
    assert ranked.proposal_ranker.model_path == "outputs/proposal_ranker_dual/proposal_ranker.joblib"


def test_merge_duplicate_proposals_prefers_rank_score() -> None:
    low = _proposal("external_cellpose", 0.1)
    high = _proposal("universal_boundary", 0.9)
    merged = merge_duplicate_proposals([low, high], iou_threshold=0.5)
    assert len(merged) == 1
    assert merged[0].source == "universal_boundary"
    assert merged[0].rank_score == 0.9


def test_proposal_features_include_proposal_source() -> None:
    proposal = _proposal("cellpose_style", 0.0)
    fg_prob = np.ones((16, 16), dtype=np.float32)
    features = proposal_features(proposal, [], fg_prob, "cellpose_001.png")
    assert features["source"] == "cellpose"
    assert features["proposal_source"] == "cellpose_style"


def test_multi_expert_proposal_generation_preserves_sources() -> None:
    cfg = SAMCellConfig()
    cfg.semantic_experts = [
        SemanticConfig(name="a", source_name="expert_a", foreground_threshold=0.5, proposal_thresholds=[0.5]),
        SemanticConfig(name="b", source_name="expert_b", foreground_threshold=0.5, proposal_thresholds=[0.5]),
    ]
    cfg.watershed.min_instance_area = 4
    cfg.watershed.marker_method = "h_maxima"
    cfg.watershed.proposal_duplicate_iou_threshold = 0.95
    cfg.proposal_ranker.enabled = False
    pipeline = SAMCellPipeline.__new__(SAMCellPipeline)
    pipeline.cfg = cfg
    pipeline.semantic_experts = cfg.semantic_experts
    pipeline._proposal_ranker_payload = None
    pipeline._proposal_ranker_model_path = None

    a = np.zeros((32, 32), dtype=np.float32)
    b = np.zeros((32, 32), dtype=np.float32)
    a[4:12, 4:12] = 0.9
    b[20:28, 20:28] = 0.9
    result = pipeline._generate_multi_expert_proposals(
        {
            "expert_a": {"fg_prob": a, "boundary_prob": None},
            "expert_b": {"fg_prob": b, "boundary_prob": None},
        },
        image_id="toy_001",
    )
    proposals = result[4]
    sources = {proposal.source for proposal in proposals}
    assert sources == {"expert_a", "expert_b"}
    assert result[6].sum() == 128


def test_semantic_expert_source_gate() -> None:
    cfg = SAMCellConfig()
    cfg.semantic_experts = [
        SemanticConfig(name="universal", source_name="universal"),
        SemanticConfig(name="cellpose_style", source_name="cellpose_style", enabled_sources=["cellpose"]),
    ]
    pipeline = SAMCellPipeline.__new__(SAMCellPipeline)
    pipeline.cfg = cfg
    pipeline.semantic_experts = cfg.semantic_experts

    assert [item.name for item in pipeline._active_semantic_experts("cellpose_001")] == ["universal", "cellpose_style"]
    assert [item.name for item in pipeline._active_semantic_experts("dsb2018_001")] == ["universal"]


def test_proposal_ranker_source_gate() -> None:
    cfg = SAMCellConfig()
    cfg.proposal_ranker.enabled = True
    cfg.proposal_ranker.enabled_sources = ["cellpose"]
    pipeline = SAMCellPipeline.__new__(SAMCellPipeline)
    pipeline.cfg = cfg

    assert pipeline._proposal_ranker_enabled_for_image("cellpose_001")
    assert not pipeline._proposal_ranker_enabled_for_image("tissuenet_001")
