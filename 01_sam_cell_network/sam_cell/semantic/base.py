from __future__ import annotations

import numpy as np


class SemanticPredictor:
    def predict_proba(self, image: np.ndarray) -> np.ndarray:
        """Return an HxW foreground probability map in [0, 1]."""
        raise NotImplementedError

    def predict_structure(self, image: np.ndarray) -> dict[str, np.ndarray | None]:
        """Return semantic maps used by proposal generation."""
        return {"fg_prob": self.predict_proba(image), "boundary_prob": None}
