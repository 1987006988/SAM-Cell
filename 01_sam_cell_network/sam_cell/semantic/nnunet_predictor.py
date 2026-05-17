from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

from sam_cell.semantic.base import SemanticPredictor


def _insert_path(path: str | None) -> None:
    if path and path not in sys.path:
        sys.path.insert(0, path)


def rgb_to_grayscale(image: np.ndarray, mode: str = "luminance") -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.float32)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError(f"Expected HWC RGB image, got {image.shape}")
    img = image.astype(np.float32, copy=False)
    if mode == "max":
        return img[:, :, :3].max(axis=2)
    if mode == "first":
        return img[:, :, 0]
    if mode == "mean":
        return img[:, :, :3].mean(axis=2)
    if mode == "luminance":
        return 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
    raise ValueError(f"Unknown grayscale_mode: {mode}")


class NnUNetSemanticPredictor(SemanticPredictor):
    def __init__(
        self,
        model_dir: str | Path,
        folds: list[int] | tuple[int, ...],
        checkpoint_name: str,
        device: str = "cuda",
        nnunet_repo: str | None = None,
        grayscale_mode: str = "luminance",
        foreground_class_indices: list[int] | tuple[int, ...] = (1,),
        boundary_class_index: int | None = None,
    ) -> None:
        _insert_path(nnunet_repo)
        import torch
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

        self.grayscale_mode = grayscale_mode
        self.foreground_class_indices = tuple(int(i) for i in foreground_class_indices)
        self.boundary_class_index = None if boundary_class_index is None else int(boundary_class_index)
        self.predictor = nnUNetPredictor(
            device=torch.device(device),
            verbose=False,
            allow_tqdm=False,
            perform_everything_on_device=(device == "cuda"),
        )
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning, message=".*torch.load.*weights_only.*")
            self.predictor.initialize_from_trained_model_folder(
                str(model_dir),
                tuple(folds),
                checkpoint_name,
            )

    def _predict_raw(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        gray = rgb_to_grayscale(image, self.grayscale_mode)
        nnunet_input = gray.astype(np.float32, copy=False)[None, None, :, :]
        return self.predictor.predict_single_npy_array(
            nnunet_input,
            {"spacing": (999, 1, 1)},
            save_or_return_probabilities=True,
        )

    def predict_structure(self, image: np.ndarray) -> dict[str, np.ndarray | None]:
        seg, prob = self._predict_raw(image)
        if prob.ndim != 4 or prob.shape[0] < 2:
            return {"fg_prob": np.asarray(seg[0] > 0, dtype=np.float32), "boundary_prob": None}

        valid_fg = [idx for idx in self.foreground_class_indices if 0 <= idx < prob.shape[0]]
        if valid_fg:
            fg = np.zeros(prob.shape[2:], dtype=np.float32)
            for idx in valid_fg:
                fg += prob[idx, 0].astype(np.float32, copy=False)
            fg = np.clip(fg, 0.0, 1.0)
        else:
            fg = np.asarray(seg[0] > 0, dtype=np.float32)

        boundary = None
        if self.boundary_class_index is not None and 0 <= self.boundary_class_index < prob.shape[0]:
            boundary = np.clip(prob[self.boundary_class_index, 0].astype(np.float32, copy=False), 0.0, 1.0)
        return {"fg_prob": fg, "boundary_prob": boundary}

    def predict_proba(self, image: np.ndarray) -> np.ndarray:
        return self.predict_structure(image)["fg_prob"]
