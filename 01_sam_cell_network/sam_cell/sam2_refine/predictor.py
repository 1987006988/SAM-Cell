from __future__ import annotations

import sys
from contextlib import nullcontext
from dataclasses import dataclass

import numpy as np

from sam_cell.prompts.crop import CropRecord
from sam_cell.prompts.mask_prompt import coarse_mask_to_sam2_logits


def _insert_path(path: str | None) -> None:
    if path and path not in sys.path:
        sys.path.insert(0, path)


@dataclass
class RefinedInstance:
    proposal_id: int
    global_crop_box_xyxy: tuple[int, int, int, int]
    local_mask: np.ndarray
    local_logits: np.ndarray
    score: float
    local_box_xyxy: np.ndarray
    coarse_area: int
    source: str = "sam2"
    quality: float = 0.0


class SAM2Refiner:
    def __init__(self, cfg, device: str = "cuda") -> None:
        _insert_path(cfg.sam2_repo)
        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        self.torch = torch
        self.cfg = cfg
        self.device = device
        model = build_sam2(
            cfg.config,
            cfg.checkpoint,
            device=device,
            apply_postprocessing=cfg.apply_postprocessing,
        )
        for param in model.parameters():
            param.requires_grad_(False)
        model.eval()
        self.predictor = SAM2ImagePredictor(model)

    def _autocast_context(self):
        if self.device != "cuda":
            return nullcontext()
        dtype = self.torch.bfloat16 if self.cfg.autocast_dtype == "bfloat16" else self.torch.float16
        return self.torch.autocast("cuda", dtype=dtype)

    def refine_one(self, crop_record: CropRecord, prompt_mode: str = "box_mask") -> RefinedInstance:
        if prompt_mode not in {"box_mask", "box_only", "mask_only"}:
            raise ValueError(f"Unsupported prompt_mode: {prompt_mode}")
        mask_logits = None
        if prompt_mode in {"box_mask", "mask_only"}:
            mask_logits = coarse_mask_to_sam2_logits(
                crop_record.local_coarse_mask,
                size=self.cfg.mask_prompt_size,
                scale=self.cfg.mask_logit_scale,
            )
        x1, y1, x2, y2 = crop_record.local_box_xyxy.astype(np.float32)
        box = None
        if prompt_mode in {"box_mask", "box_only"}:
            box = np.asarray([x1, y1, max(x1, x2 - 1), max(y1, y2 - 1)], dtype=np.float32)
        with self.torch.inference_mode(), self._autocast_context():
            self.predictor.set_image(crop_record.crop_image)
            masks, scores, _low_res = self.predictor.predict(
                box=box,
                mask_input=mask_logits,
                multimask_output=self.cfg.multimask_output,
                return_logits=True,
            )
        best = int(np.argmax(scores)) if scores.size else 0
        local_logits = np.asarray(masks[best], dtype=np.float32)
        local_mask = local_logits > 0.0
        return RefinedInstance(
            proposal_id=crop_record.proposal_id,
            global_crop_box_xyxy=crop_record.crop_box_xyxy,
            local_mask=np.ascontiguousarray(local_mask),
            local_logits=np.ascontiguousarray(local_logits),
            score=float(scores[best]) if scores.size else 0.0,
            local_box_xyxy=crop_record.local_box_xyxy.copy(),
            coarse_area=crop_record.coarse_area,
            source=f"sam2_{prompt_mode}",
        )
