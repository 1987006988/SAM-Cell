from __future__ import annotations

from copy import deepcopy
import random
from pathlib import Path

import numpy as np

from sam_cell.config import SAMCellConfig, SemanticConfig
from sam_cell.io import load_label_map
from sam_cell.postprocess.merge import pixel_competition, remove_duplicate_instances
from sam_cell.postprocess.selection import choose_instance, make_coarse_instance
from sam_cell.prompts.crop import make_adaptive_crop
from sam_cell.proposals.foreground import binarize_foreground, clean_foreground
from sam_cell.proposals.internal_selector import infer_dataset_source, load_selector, proposal_features, selector_scores
from sam_cell.proposals.regions import (
    extract_proposals,
    merge_duplicate_proposals,
    proposals_to_label_map,
)
from sam_cell.proposals.repair import select_proposal_set, split_repair_proposals
from sam_cell.proposals.separator import SeparatorProposalGenerator
from sam_cell.proposals.watershed import compute_distance, make_markers, suppress_distance_by_boundary, watershed_instances
from sam_cell.sam2_refine.predictor import SAM2Refiner
from sam_cell.semantic.nnunet_predictor import NnUNetSemanticPredictor


class SAMCellPipeline:
    def __init__(self, cfg: SAMCellConfig) -> None:
        self.cfg = cfg
        random.seed(cfg.runtime.seed)
        np.random.seed(cfg.runtime.seed)
        self.semantic_experts = [expert for expert in (cfg.semantic_experts or [cfg.semantic]) if expert.enabled]
        if not self.semantic_experts:
            raise ValueError("At least one semantic expert must be enabled")
        self.semantic_predictors = {}
        for expert in self.semantic_experts:
            if expert.backend != "nnunet":
                raise ValueError(f"Unsupported semantic backend for full pipeline: {expert.backend}")
            self.semantic_predictors[expert.name] = NnUNetSemanticPredictor(
                model_dir=expert.nnunet_model_dir,
                folds=expert.nnunet_folds,
                checkpoint_name=expert.checkpoint_name,
                device=cfg.runtime.device,
                nnunet_repo=expert.nnunet_repo,
                grayscale_mode=expert.grayscale_mode,
                foreground_class_indices=expert.foreground_class_indices,
                boundary_class_index=expert.boundary_class_index,
            )
        self.semantic = self.semantic_predictors[self.semantic_experts[0].name]
        self.refiner = None
        if cfg.sam2.enabled and cfg.sam2.prompt_modes:
            self.refiner = SAM2Refiner(cfg.sam2, device=cfg.runtime.device)
        self._selector_model_path: str | None = None
        self._selector_payload: dict | None = None
        self._external_selector_model_path: str | None = None
        self._external_selector_payload: dict | None = None
        self._proposal_ranker_model_path: str | None = None
        self._proposal_ranker_payload: dict | None = None
        self._separator_model_path: str | None = None
        self._separator_generator: SeparatorProposalGenerator | None = None

    def _apply_nested_overrides(self, obj, values: dict) -> dict:
        previous = {}
        for key, value in values.items():
            if "." in key:
                head, tail = key.split(".", 1)
                child = getattr(obj, head)
                previous[key] = self._apply_nested_overrides(child, {tail: value})[tail]
                continue
            old = getattr(obj, key)
            previous[key] = deepcopy(old)
            if isinstance(value, dict) and hasattr(old, "__dataclass_fields__"):
                previous[key] = self._apply_nested_overrides(old, value)
            else:
                setattr(obj, key, value)
        return previous

    def _restore_nested_overrides(self, obj, values: dict) -> None:
        for key, value in values.items():
            if "." in key:
                head, tail = key.split(".", 1)
                self._restore_nested_overrides(getattr(obj, head), {tail: value})
                continue
            current = getattr(obj, key)
            if isinstance(value, dict) and hasattr(current, "__dataclass_fields__"):
                self._restore_nested_overrides(current, value)
            else:
                setattr(obj, key, value)

    def _apply_source_overrides(self, image_id: str | None) -> dict:
        source = infer_dataset_source(image_id)
        overrides = self.cfg.source_overrides.get(source, {})
        return self._apply_nested_overrides(self.cfg, overrides) if overrides else {}

    def _restore_source_overrides(self, previous: dict) -> None:
        if previous:
            self._restore_nested_overrides(self.cfg, previous)

    def _expert_source(self, expert: SemanticConfig) -> str:
        if expert.source_name:
            return expert.source_name
        return "watershed" if len(self.semantic_experts) == 1 else expert.name

    def _source_allowed(
        self,
        dataset_source: str,
        enabled_sources: list[str] | None,
        disabled_sources: list[str] | None,
    ) -> bool:
        if enabled_sources is not None and dataset_source not in set(enabled_sources):
            return False
        if disabled_sources is not None and dataset_source in set(disabled_sources):
            return False
        return True

    def _active_semantic_experts(self, image_id: str | None = None) -> list[SemanticConfig]:
        dataset_source = infer_dataset_source(image_id)
        active = [
            expert
            for expert in self.semantic_experts
            if self._source_allowed(dataset_source, expert.enabled_sources, expert.disabled_sources)
        ]
        if not active:
            raise ValueError(f"No semantic expert enabled for source={dataset_source!r}")
        return active

    def _foreground_mask(
        self,
        fg_prob: np.ndarray,
        threshold: float,
        semantic_cfg: SemanticConfig | None = None,
    ) -> np.ndarray:
        cfg = semantic_cfg or self.cfg.semantic
        return clean_foreground(
            binarize_foreground(fg_prob, threshold),
            min_area=cfg.min_foreground_area,
            fill_holes=cfg.fill_holes,
            closing_radius=cfg.closing_radius,
        )

    def _predict_semantic_for_expert(
        self,
        expert: SemanticConfig,
        image: np.ndarray,
        image_id: str | None = None,
    ) -> dict[str, np.ndarray | None]:
        cache_dir = expert.prob_cache_dir
        if cache_dir and image_id:
            use_structure_cache = expert.boundary_class_index is not None
            cache_path = Path(cache_dir) / f"{image_id}.npz" if use_structure_cache else Path(cache_dir) / f"{image_id}.npy"
            if cache_path.exists():
                try:
                    cached = np.load(cache_path)
                    if isinstance(cached, np.lib.npyio.NpzFile):
                        fg_prob = cached["fg_prob"]
                        boundary_prob = cached["boundary_prob"] if "boundary_prob" in cached else None
                        cached.close()
                    else:
                        fg_prob = cached
                        boundary_prob = None
                    if fg_prob.shape == image.shape[:2]:
                        return {
                            "fg_prob": fg_prob.astype(np.float32, copy=False),
                            "boundary_prob": None if boundary_prob is None else boundary_prob.astype(np.float32, copy=False),
                        }
                except Exception as exc:
                    print(f"[semantic-cache] ignoring unreadable cache {cache_path}: {exc}", flush=True)
                    try:
                        cache_path.unlink()
                    except OSError:
                        pass
            maps = self.semantic_predictors[expert.name].predict_structure(image)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            fg_prob = maps["fg_prob"].astype(np.float32, copy=False)
            boundary_prob = maps.get("boundary_prob")
            if use_structure_cache:
                payload = {"fg_prob": fg_prob}
                if boundary_prob is not None:
                    payload["boundary_prob"] = boundary_prob.astype(np.float32, copy=False)
                np.savez_compressed(cache_path, **payload)
            else:
                np.save(cache_path, fg_prob)
            return {"fg_prob": fg_prob, "boundary_prob": boundary_prob}
        maps = self.semantic_predictors[expert.name].predict_structure(image)
        return {
            "fg_prob": maps["fg_prob"].astype(np.float32, copy=False),
            "boundary_prob": None
            if maps.get("boundary_prob") is None
            else maps["boundary_prob"].astype(np.float32, copy=False),
        }

    def _predict_all_semantics(self, image: np.ndarray, image_id: str | None = None) -> dict[str, dict[str, np.ndarray | None]]:
        return {self._expert_source(expert): self._predict_semantic_for_expert(expert, image, image_id) for expert in self._active_semantic_experts(image_id)}

    def _predict_semantic(self, image: np.ndarray, image_id: str | None = None) -> dict[str, np.ndarray | None]:
        return self._predict_semantic_for_expert(self.semantic_experts[0], image, image_id=image_id)

    def _predict_foreground(self, image: np.ndarray, image_id: str | None = None) -> np.ndarray:
        return self._predict_semantic(image, image_id=image_id)["fg_prob"]

    def _proposals_for_threshold(
        self,
        fg_prob: np.ndarray,
        threshold: float,
        boundary_prob: np.ndarray | None = None,
        semantic_cfg: SemanticConfig | None = None,
        source: str = "watershed",
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list]:
        fg_mask = self._foreground_mask(fg_prob, threshold, semantic_cfg=semantic_cfg)
        dist = compute_distance(fg_mask, sigma=self.cfg.watershed.edt_sigma)
        proposal_dist = suppress_distance_by_boundary(
            dist,
            boundary_prob,
            weight=self.cfg.watershed.boundary_suppression_weight,
            additive_weight=self.cfg.watershed.boundary_additive_weight,
            smoothing_sigma=self.cfg.watershed.boundary_smoothing_sigma,
        )
        markers = make_markers(proposal_dist, fg_mask, self.cfg.watershed)
        label_map = watershed_instances(fg_mask, proposal_dist, markers)
        proposals = extract_proposals(
            label_map,
            fg_prob,
            min_area=self.cfg.watershed.min_instance_area,
            max_area=self.cfg.watershed.max_instance_area,
            source=source,
        )
        proposals = split_repair_proposals(proposals, proposal_dist, fg_prob, self.cfg.proposal_repair)
        return fg_mask, proposal_dist, markers, label_map, proposals

    def _external_proposals(self, image_id: str | None, fg_prob: np.ndarray) -> list:
        cfg = self.cfg.external_proposals
        if not cfg.enabled:
            return []
        if not image_id:
            return []
        if not cfg.label_dir:
            raise ValueError("external_proposals.label_dir is required when external proposals are enabled")
        path = Path(cfg.label_dir) / f"{image_id}{cfg.suffix}"
        if not path.exists():
            raise FileNotFoundError(f"External proposal label not found: {path}")
        label_map = load_label_map(path)
        if label_map.shape != fg_prob.shape:
            raise ValueError(f"External proposal shape {label_map.shape} does not match image shape {fg_prob.shape}: {path}")
        proposals = extract_proposals(
            label_map,
            fg_prob,
            min_area=cfg.min_area if cfg.min_area is not None else self.cfg.watershed.min_instance_area,
            max_area=cfg.max_area,
            source=cfg.source_name,
        )
        return self._filter_external_proposals(proposals, fg_prob, image_id)

    def _external_label_path(self, image_id: str | None) -> Path | None:
        cfg = self.cfg.external_proposals
        if not cfg.enabled or not image_id:
            return None
        if not cfg.label_dir:
            raise ValueError("external_proposals.label_dir is required when external proposals are enabled")
        path = Path(cfg.label_dir) / f"{image_id}{cfg.suffix}"
        if not path.exists():
            raise FileNotFoundError(f"External proposal label not found: {path}")
        return path

    def _external_replace_fast_path(self, image: np.ndarray, image_id: str | None) -> dict | None:
        cfg = self.cfg.external_proposals
        if not (
            cfg.enabled
            and cfg.mode == "replace"
            and not cfg.external_selector_model
            and (not self.cfg.sam2.enabled or not self.cfg.sam2.prompt_modes)
        ):
            return None
        path = self._external_label_path(image_id)
        if path is None:
            return None
        label_map = load_label_map(path)
        if label_map.shape != image.shape[:2]:
            raise ValueError(f"External proposal shape {label_map.shape} does not match image shape {image.shape[:2]}: {path}")
        fg_prob = (label_map > 0).astype(np.float32)
        proposals = extract_proposals(
            label_map,
            fg_prob,
            min_area=cfg.min_area if cfg.min_area is not None else 1,
            max_area=cfg.max_area,
            source=cfg.source_name,
        )
        instances = []
        for proposal in proposals:
            x1, y1, x2, y2 = proposal.bbox_xyxy
            instances.append(
                {
                    "id": proposal.id,
                    "proposal_id": proposal.id,
                    "score": float(max(cfg.coarse_score, proposal.mean_fg_prob)),
                    "quality": 1.0,
                    "source": cfg.source_name,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "area": proposal.area,
                    "crop_box_xyxy": [x1, y1, x2, y2],
                }
            )
        return {
            "fg_prob": fg_prob,
            "fg_mask": label_map > 0,
            "distance": np.zeros(label_map.shape, dtype=np.float32),
            "markers": np.zeros(label_map.shape, dtype=np.int32),
            "proposal_label_map": label_map.astype(np.int32, copy=False),
            "proposals": proposals,
            "refined_instances": [],
            "instance_map": label_map.astype(np.int32, copy=False),
            "instances": instances,
            "crops": [],
            "selection_records": [
                {"proposal_id": proposal.id, "source": cfg.source_name, "score": float(cfg.coarse_score), "quality": 1.0}
                for proposal in proposals
            ],
        }

    def _load_internal_selector(self) -> dict | None:
        path = self.cfg.external_proposals.internal_selector_model
        if not path:
            return None
        if self._selector_payload is None or self._selector_model_path != path:
            self._selector_payload = load_selector(path)
            self._selector_model_path = path
        return self._selector_payload

    def _load_external_selector(self) -> dict | None:
        path = self.cfg.external_proposals.external_selector_model
        if not path:
            return None
        if self._external_selector_payload is None or self._external_selector_model_path != path:
            self._external_selector_payload = load_selector(path)
            self._external_selector_model_path = path
        return self._external_selector_payload

    def _proposal_ranker_enabled_for_image(self, image_id: str | None) -> bool:
        cfg = self.cfg.proposal_ranker
        if not cfg.enabled:
            return False
        dataset_source = infer_dataset_source(image_id)
        return self._source_allowed(dataset_source, cfg.enabled_sources, cfg.disabled_sources)

    def _load_proposal_ranker(self, image_id: str | None = None) -> dict | None:
        cfg = self.cfg.proposal_ranker
        path = cfg.model_path
        if not self._proposal_ranker_enabled_for_image(image_id) or not path:
            return None
        if self._proposal_ranker_payload is None or self._proposal_ranker_model_path != path:
            self._proposal_ranker_payload = load_selector(path)
            self._proposal_ranker_model_path = path
        return self._proposal_ranker_payload

    def _filter_external_proposals(self, external: list, fg_prob: np.ndarray, image_id: str | None) -> list:
        selector = self._load_external_selector()
        if selector is None or not external:
            return external
        features = [proposal_features(proposal, [], fg_prob, image_id) for proposal in external]
        scores = selector_scores(selector, features)
        keep_threshold = float(self.cfg.external_proposals.external_selector_keep_threshold)
        return [proposal for proposal, score in zip(external, scores, strict=True) if float(score) >= keep_threshold]

    def _filter_internal_proposals(self, internal: list, external: list, fg_prob: np.ndarray, image_id: str | None) -> list:
        cfg = self.cfg.external_proposals
        if not external:
            return internal

        external_union = np.zeros(fg_prob.shape, dtype=bool)
        for proposal in external:
            external_union |= proposal.mask

        scored = []
        for proposal in internal:
            uncovered = int((proposal.mask & ~external_union).sum())
            uncovered_fraction = uncovered / float(max(1, proposal.area))
            if cfg.min_internal_uncovered_fraction > 0 and uncovered_fraction < cfg.min_internal_uncovered_fraction:
                continue
            if cfg.min_internal_uncovered_pixels > 0 and uncovered < cfg.min_internal_uncovered_pixels:
                continue
            if cfg.internal_min_area is not None and proposal.area < cfg.internal_min_area:
                continue
            if cfg.internal_max_area is not None and proposal.area > cfg.internal_max_area:
                continue
            if cfg.internal_min_mean_fg_prob > 0 and proposal.mean_fg_prob < cfg.internal_min_mean_fg_prob:
                continue
            scored.append((uncovered_fraction, uncovered, proposal.mean_fg_prob, proposal.area, proposal))

        selector = self._load_internal_selector()
        if selector is not None and scored:
            features = [proposal_features(item[-1], external, fg_prob, image_id, external_union) for item in scored]
            scores = selector_scores(selector, features)
            threshold = float(cfg.internal_selector_threshold)
            rescored = []
            for score, item in zip(scores, scored, strict=True):
                if float(score) >= threshold:
                    rescored.append((float(score), *item))
            scored = rescored
            scored.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]), reverse=True)
        else:
            scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)

        limit = len(scored)
        if cfg.max_internal_additions is not None:
            limit = min(limit, int(cfg.max_internal_additions))
        if cfg.max_internal_additions_ratio is not None:
            ratio_limit = int(np.floor(len(external) * float(cfg.max_internal_additions_ratio)))
            limit = min(limit, max(0, ratio_limit))
        return [item[-1] for item in scored[:limit]]

    def _fg_prob_for_proposal(
        self,
        proposal,
        fg_prob_by_source: dict[str, np.ndarray],
        default_fg_prob: np.ndarray,
    ) -> np.ndarray:
        return fg_prob_by_source.get(proposal.source, default_fg_prob)

    def _combined_fg_prob(self, fg_prob_by_source: dict[str, np.ndarray]) -> np.ndarray:
        if not fg_prob_by_source:
            raise ValueError("No foreground probability maps available")
        maps = list(fg_prob_by_source.values())
        if len(maps) == 1:
            return maps[0]
        return np.maximum.reduce(maps).astype(np.float32, copy=False)

    def _filter_ranked_proposals(
        self,
        proposals: list,
        fg_prob_by_source: dict[str, np.ndarray],
        default_fg_prob: np.ndarray,
        image_id: str | None,
    ) -> list:
        ranker = self._load_proposal_ranker(image_id)
        if ranker is None or not proposals:
            return proposals
        features = []
        extended_features = int(ranker.get("feature_version", 1)) >= 2
        for proposal in proposals:
            fg_prob = self._fg_prob_for_proposal(proposal, fg_prob_by_source, default_fg_prob)
            feature = proposal_features(proposal, [], fg_prob, image_id, extended=extended_features)
            feature["proposal_source"] = proposal.source
            features.append(feature)
        scores = selector_scores(ranker, features)
        kept = []
        threshold = float(self.cfg.proposal_ranker.keep_threshold)
        for proposal, score in zip(proposals, scores, strict=True):
            proposal.rank_score = float(score)
            if float(score) >= threshold:
                kept.append(proposal)
        kept.sort(key=lambda proposal: (proposal.rank_score, proposal.mean_fg_prob, -proposal.area), reverse=True)
        if self.cfg.proposal_ranker.top_k is not None:
            kept = kept[: int(self.cfg.proposal_ranker.top_k)]
        return kept

    @staticmethod
    def _proposal_source_counts(proposals: list) -> dict[str, int]:
        counts: dict[str, int] = {}
        for proposal in proposals:
            source = str(getattr(proposal, "source", "unknown"))
            counts[source] = counts.get(source, 0) + 1
        return counts

    @staticmethod
    def _proposal_source_count(proposals: list, source_name: str) -> int:
        return sum(1 for proposal in proposals if str(getattr(proposal, "source", "")) == source_name)

    def _external_union_mask(self, proposals: list, shape: tuple[int, int]) -> np.ndarray | None:
        if not self.cfg.external_proposals.enabled:
            return None
        external_union = np.zeros(shape, dtype=bool)
        found = False
        for proposal in proposals:
            if proposal.source == self.cfg.external_proposals.source_name or proposal.source.startswith("external"):
                external_union |= proposal.mask
                found = True
        return external_union if found else None

    def _generate_proposals(
        self,
        fg_prob: np.ndarray,
        image_id: str | None = None,
        boundary_prob: np.ndarray | None = None,
        semantic_cfg: SemanticConfig | None = None,
        source: str = "watershed",
        include_external: bool = True,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list]:
        cfg = semantic_cfg or self.cfg.semantic
        thresholds = cfg.proposal_thresholds or [cfg.foreground_threshold]
        all_proposals = []
        debug_fg_mask = None
        debug_dist = None
        debug_markers = None
        debug_label_map = None
        for idx, threshold in enumerate(thresholds):
            fg_mask, dist, markers, label_map, proposals = self._proposals_for_threshold(
                fg_prob,
                float(threshold),
                boundary_prob=boundary_prob,
                semantic_cfg=cfg,
                source=source,
            )
            all_proposals.extend(proposals)
            if idx == 0:
                debug_fg_mask = fg_mask
                debug_dist = dist
                debug_markers = markers
                debug_label_map = label_map
        if include_external:
            external = self._external_proposals(image_id, fg_prob)
            if self.cfg.external_proposals.enabled and self.cfg.external_proposals.mode == "replace":
                all_proposals = external
            else:
                all_proposals = self._filter_internal_proposals(all_proposals, external, fg_prob, image_id)
                all_proposals.extend(external)
        all_proposals = select_proposal_set(all_proposals, self.cfg.proposal_repair)
        merged = merge_duplicate_proposals(
            all_proposals,
            iou_threshold=(
                self.cfg.external_proposals.duplicate_iou_threshold
                if self.cfg.external_proposals.enabled
                else self.cfg.watershed.proposal_duplicate_iou_threshold
            ),
        )
        combined_label_map = proposals_to_label_map(merged, fg_prob.shape)
        return debug_fg_mask, debug_dist, debug_markers, combined_label_map if merged else debug_label_map, merged

    def _generate_multi_expert_proposals(
        self,
        semantic_maps_by_source: dict[str, dict[str, np.ndarray | None]],
        image_id: str | None = None,
        image: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list, dict[str, np.ndarray], np.ndarray, dict]:
        all_proposals = []
        fg_prob_by_source: dict[str, np.ndarray] = {}
        debug_fg_mask = None
        debug_dist = None
        debug_markers = None
        debug_label_map = None
        combined_fg_mask = None
        shared_boundary_prob = (
            self._shared_boundary_prob(semantic_maps_by_source)
            if self.cfg.watershed.share_boundary_across_experts
            else None
        )

        for expert in self._active_semantic_experts(image_id):
            source = self._expert_source(expert)
            maps = semantic_maps_by_source[source]
            fg_prob = maps["fg_prob"]
            if fg_prob is None:
                continue
            fg_prob = fg_prob.astype(np.float32, copy=False)
            boundary_prob = maps.get("boundary_prob")
            if boundary_prob is None and shared_boundary_prob is not None:
                boundary_prob = shared_boundary_prob
            fg_prob_by_source[source] = fg_prob
            fg_mask, dist, markers, label_map, proposals = self._generate_proposals(
                fg_prob,
                image_id=image_id,
                boundary_prob=None if boundary_prob is None else boundary_prob.astype(np.float32, copy=False),
                semantic_cfg=expert,
                source=source,
                include_external=False,
            )
            all_proposals.extend(proposals)
            combined_fg_mask = fg_mask if combined_fg_mask is None else (combined_fg_mask | fg_mask)
            if debug_fg_mask is None:
                debug_fg_mask = fg_mask
                debug_dist = dist
                debug_markers = markers
                debug_label_map = label_map

        default_fg_prob = self._combined_fg_prob(fg_prob_by_source)
        boundary_for_separator = shared_boundary_prob if shared_boundary_prob is not None else self._shared_boundary_prob(semantic_maps_by_source)
        separator = self._separator_proposals(image, default_fg_prob, boundary_for_separator, image_id)
        external = self._external_proposals(image_id, default_fg_prob)
        separator_source = self.cfg.separator_proposals.source_name
        diagnostics = {
            "internal_generated": len(all_proposals),
            "separator_generated": len(separator),
            "external_generated": len(external),
            "internal_generated_by_source": self._proposal_source_counts(all_proposals),
        }
        if self.cfg.external_proposals.enabled and self.cfg.external_proposals.mode == "replace":
            all_proposals = external
        elif self.cfg.separator_proposals.enabled and self.cfg.separator_proposals.mode == "replace":
            all_proposals = separator
        else:
            all_proposals = self._filter_internal_proposals(all_proposals, external, default_fg_prob, image_id)
            all_proposals.extend(external)
            all_proposals.extend(separator)
        diagnostics["before_ranker"] = len(all_proposals)
        diagnostics["separator_before_ranker"] = self._proposal_source_count(all_proposals, separator_source)
        diagnostics["before_ranker_by_source"] = self._proposal_source_counts(all_proposals)
        all_proposals = self._filter_ranked_proposals(all_proposals, fg_prob_by_source, default_fg_prob, image_id)
        diagnostics["after_ranker"] = len(all_proposals)
        diagnostics["separator_after_ranker"] = self._proposal_source_count(all_proposals, separator_source)
        diagnostics["after_ranker_by_source"] = self._proposal_source_counts(all_proposals)
        all_proposals = select_proposal_set(all_proposals, self.cfg.proposal_repair)
        diagnostics["after_set_selector"] = len(all_proposals)
        diagnostics["separator_after_set_selector"] = self._proposal_source_count(all_proposals, separator_source)
        diagnostics["after_set_selector_by_source"] = self._proposal_source_counts(all_proposals)
        merged = merge_duplicate_proposals(
            all_proposals,
            iou_threshold=(
                self.cfg.external_proposals.duplicate_iou_threshold
                if self.cfg.external_proposals.enabled
                else self.cfg.watershed.proposal_duplicate_iou_threshold
            ),
        )
        diagnostics["after_merge"] = len(merged)
        diagnostics["separator_after_merge"] = self._proposal_source_count(merged, separator_source)
        diagnostics["after_merge_by_source"] = self._proposal_source_counts(merged)
        combined_label_map = proposals_to_label_map(merged, default_fg_prob.shape)
        return (
            debug_fg_mask if debug_fg_mask is not None else default_fg_prob > 0,
            debug_dist,
            debug_markers,
            combined_label_map if merged else debug_label_map,
            merged,
            fg_prob_by_source,
            combined_fg_mask if combined_fg_mask is not None else default_fg_prob > 0,
            diagnostics,
        )

    def infer(self, image: np.ndarray, image_id: str | None = None) -> dict:
        previous = self._apply_source_overrides(image_id)
        try:
            return self._infer_current_config(image, image_id=image_id)
        finally:
            self._restore_source_overrides(previous)

    def _shared_boundary_prob(self, semantic_maps_by_source: dict[str, dict[str, np.ndarray | None]]) -> np.ndarray | None:
        boundaries = [
            maps["boundary_prob"].astype(np.float32, copy=False)
            for maps in semantic_maps_by_source.values()
            if maps.get("boundary_prob") is not None
        ]
        if not boundaries:
            return None
        if len(boundaries) == 1:
            return boundaries[0]
        return np.maximum.reduce(boundaries).astype(np.float32, copy=False)

    def _separator_proposals(
        self,
        image: np.ndarray | None,
        fg_prob: np.ndarray,
        boundary_prob: np.ndarray | None,
        image_id: str | None,
    ) -> list:
        cfg = self.cfg.separator_proposals
        if not cfg.enabled:
            return []
        dataset_source = infer_dataset_source(image_id)
        if not self._source_allowed(dataset_source, cfg.enabled_sources, cfg.disabled_sources):
            return []
        if image is None:
            raise ValueError("separator_proposals require the original image")
        if self._separator_generator is None or self._separator_model_path != cfg.model_path:
            self._separator_generator = SeparatorProposalGenerator(cfg, runtime_device=self.cfg.runtime.device)
            self._separator_model_path = cfg.model_path
        return self._separator_generator.predict(image, fg_prob, boundary_prob)

    def _infer_current_config(self, image: np.ndarray, image_id: str | None = None) -> dict:
        fast = self._external_replace_fast_path(image, image_id)
        if fast is not None:
            return fast
        semantic_maps_by_source = self._predict_all_semantics(image, image_id=image_id)
        fg_mask, dist, markers, proposal_label_map, proposals, fg_prob_by_source, competition_fg_mask, proposal_diagnostics = (
            self._generate_multi_expert_proposals(
                semantic_maps_by_source,
                image_id=image_id,
                image=image,
            )
        )
        fg_prob = self._combined_fg_prob(fg_prob_by_source)
        boundary_prob = next(
            (maps.get("boundary_prob") for maps in semantic_maps_by_source.values() if maps.get("boundary_prob") is not None),
            None,
        )
        external_union = self._external_union_mask(proposals, image.shape[:2])
        if external_union is not None:
            competition_fg_mask = competition_fg_mask | external_union

        refined_instances, crops, selection_records = self._refine_and_merge_proposals(
            image,
            proposals,
            fg_prob_by_source,
            fg_prob,
        )
        instance_map, instance_metadata = pixel_competition(
            refined_instances,
            image.shape[:2],
            use_pixel_logits=self.cfg.merge.use_pixel_logits,
            fg_mask=competition_fg_mask,
            semantic_gate_dilation=self.cfg.merge.semantic_gate_dilation,
        )
        return {
            "fg_prob": fg_prob,
            "fg_prob_by_source": fg_prob_by_source,
            "boundary_prob": boundary_prob,
            "fg_mask": fg_mask,
            "distance": dist,
            "markers": markers,
            "proposal_label_map": proposal_label_map,
            "proposals": proposals,
            "refined_instances": refined_instances,
            "instance_map": instance_map,
            "instances": instance_metadata,
            "crops": crops,
            "selection_records": selection_records,
            "proposal_diagnostics": proposal_diagnostics,
        }

    def _refine_and_merge_proposals(
        self,
        image: np.ndarray,
        proposals: list,
        fg_prob_by_source: dict[str, np.ndarray],
        default_fg_prob: np.ndarray,
    ) -> tuple[list, list, list]:
        refined_instances = []
        crops = []
        selection_records = []
        for proposal in proposals:
            fg_prob = self._fg_prob_for_proposal(proposal, fg_prob_by_source, default_fg_prob)
            crop = make_adaptive_crop(image, proposal, self.cfg.crop, fg_prob=fg_prob)
            candidates = []
            if self.cfg.merge.keep_coarse_candidate:
                coarse_score = (
                    self.cfg.external_proposals.coarse_score
                    if proposal.source == self.cfg.external_proposals.source_name
                    else self.cfg.merge.coarse_score
                )
                candidates.append(
                    make_coarse_instance(
                        crop,
                        score=max(coarse_score, proposal.mean_fg_prob, proposal.rank_score),
                        logit_scale=self.cfg.sam2.mask_logit_scale,
                    )
                )
                candidates[-1].source = proposal.source if proposal.source != "watershed" else "watershed"
            if self.refiner is not None:
                for prompt_mode in self.cfg.sam2.prompt_modes:
                    refined = self.refiner.refine_one(crop, prompt_mode=prompt_mode)
                    if refined.score >= self.cfg.sam2.score_threshold:
                        candidates.append(refined)
            selected = choose_instance(candidates, crop, self.cfg.merge)
            if selected is None:
                continue
            refined_instances.append(selected)
            crops.append(crop)
            selection_records.append(
                {
                    "proposal_id": proposal.id,
                    "proposal_source": proposal.source,
                    "rank_score": float(proposal.rank_score),
                    "source": selected.source,
                    "score": selected.score,
                    "quality": selected.quality,
                }
            )

        refined_instances = remove_duplicate_instances(
            refined_instances,
            image.shape[:2],
            iou_threshold=self.cfg.merge.duplicate_iou_threshold,
        )
        return refined_instances, crops, selection_records

    def _infer_single_expert_legacy(self, image: np.ndarray, image_id: str | None = None) -> dict:
        semantic_maps = self._predict_semantic(image, image_id=image_id)
        fg_prob = semantic_maps["fg_prob"]
        boundary_prob = semantic_maps.get("boundary_prob")
        fg_mask, dist, markers, proposal_label_map, proposals = self._generate_proposals(
            fg_prob,
            image_id=image_id,
            boundary_prob=boundary_prob,
        )
        external_union = self._external_union_mask(proposals, image.shape[:2])
        competition_fg_mask = fg_mask if external_union is None else (fg_mask | external_union)

        refined_instances = []
        crops = []
        selection_records = []
        for proposal in proposals:
            crop = make_adaptive_crop(image, proposal, self.cfg.crop, fg_prob=fg_prob)
            candidates = []
            if self.cfg.merge.keep_coarse_candidate:
                coarse_score = (
                    self.cfg.external_proposals.coarse_score
                    if proposal.source == self.cfg.external_proposals.source_name
                    else self.cfg.merge.coarse_score
                )
                candidates.append(
                    make_coarse_instance(
                        crop,
                        score=max(coarse_score, proposal.mean_fg_prob),
                        logit_scale=self.cfg.sam2.mask_logit_scale,
                    )
                )
                candidates[-1].source = proposal.source if proposal.source != "watershed" else "watershed"
            if self.refiner is not None:
                for prompt_mode in self.cfg.sam2.prompt_modes:
                    refined = self.refiner.refine_one(crop, prompt_mode=prompt_mode)
                    if refined.score >= self.cfg.sam2.score_threshold:
                        candidates.append(refined)
            selected = choose_instance(candidates, crop, self.cfg.merge)
            if selected is None:
                continue
            refined_instances.append(selected)
            crops.append(crop)
            selection_records.append(
                {
                    "proposal_id": proposal.id,
                    "source": selected.source,
                    "score": selected.score,
                    "quality": selected.quality,
                }
            )

        refined_instances = remove_duplicate_instances(
            refined_instances,
            image.shape[:2],
            iou_threshold=self.cfg.merge.duplicate_iou_threshold,
        )
        instance_map, instance_metadata = pixel_competition(
            refined_instances,
            image.shape[:2],
            use_pixel_logits=self.cfg.merge.use_pixel_logits,
            fg_mask=competition_fg_mask,
            semantic_gate_dilation=self.cfg.merge.semantic_gate_dilation,
        )
        return {
            "fg_prob": fg_prob,
            "boundary_prob": boundary_prob,
            "fg_mask": fg_mask,
            "distance": dist,
            "markers": markers,
            "proposal_label_map": proposal_label_map,
            "proposals": proposals,
            "refined_instances": refined_instances,
            "instance_map": instance_map,
            "instances": instance_metadata,
            "crops": crops,
            "selection_records": selection_records,
        }
