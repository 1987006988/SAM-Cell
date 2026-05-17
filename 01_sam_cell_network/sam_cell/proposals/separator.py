from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.segmentation import watershed

from sam_cell.proposals.regions import InstanceProposal, extract_proposals
from sam_cell.proposals.watershed import compute_distance

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover - torch is optional unless the separator is enabled
    torch = None
    nn = None


class _ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.GroupNorm(8 if out_channels >= 8 else 1, out_channels),
            nn.SiLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.GroupNorm(8 if out_channels >= 8 else 1, out_channels),
            nn.SiLU(inplace=True),
        )

    def forward(self, x):  # noqa: ANN001
        return self.net(x)


class SeparatorProposalNet(nn.Module):
    """Small U-Net that predicts fg, center, contact, and offset proposal cues."""

    def __init__(self, in_channels: int = 4, base_channels: int = 32, out_channels: int = 5) -> None:
        super().__init__()
        c = int(base_channels)
        self.enc1 = _ConvBlock(in_channels, c)
        self.enc2 = _ConvBlock(c, c * 2)
        self.enc3 = _ConvBlock(c * 2, c * 4)
        self.pool = nn.MaxPool2d(2)
        self.up2 = nn.ConvTranspose2d(c * 4, c * 2, 2, stride=2)
        self.dec2 = _ConvBlock(c * 4, c * 2)
        self.up1 = nn.ConvTranspose2d(c * 2, c, 2, stride=2)
        self.dec1 = _ConvBlock(c * 2, c)
        self.out = nn.Conv2d(c, out_channels, 1)

    def forward(self, x):  # noqa: ANN001
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        d2 = self.up2(e3)
        d2 = _match_size(d2, e2)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        d1 = self.up1(d2)
        d1 = _match_size(d1, e1)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))
        return self.out(d1)


def _match_size(x, ref):  # noqa: ANN001
    if x.shape[-2:] == ref.shape[-2:]:
        return x
    return torch.nn.functional.interpolate(x, size=ref.shape[-2:], mode="bilinear", align_corners=False)


def build_separator_input(
    image: np.ndarray,
    fg_prob: np.ndarray,
    boundary_prob: np.ndarray | None,
    fg_threshold: float,
) -> np.ndarray:
    gray = _to_gray_float(image)
    fg = np.clip(fg_prob.astype(np.float32, copy=False), 0.0, 1.0)
    boundary = np.zeros_like(fg, dtype=np.float32) if boundary_prob is None else np.clip(boundary_prob.astype(np.float32, copy=False), 0.0, 1.0)
    edt = ndi.distance_transform_edt(fg >= float(fg_threshold)).astype(np.float32)
    max_edt = float(edt.max())
    if max_edt > 0:
        edt /= max_edt
    return np.stack([gray, fg, boundary, edt.astype(np.float32, copy=False)], axis=0).astype(np.float32, copy=False)


def build_separator_targets(label_map: np.ndarray) -> dict[str, np.ndarray]:
    labels = label_map.astype(np.int32, copy=False)
    shape = labels.shape
    fg = (labels > 0).astype(np.float32)
    center = np.zeros(shape, dtype=np.float32)
    offset_y = np.zeros(shape, dtype=np.float32)
    offset_x = np.zeros(shape, dtype=np.float32)

    objects = ndi.find_objects(labels)
    for label_id, slices in enumerate(objects, start=1):
        if slices is None:
            continue
        local = labels[slices] == label_id
        if not np.any(local):
            continue
        yslice, xslice = slices
        ys, xs = np.nonzero(local)
        cy = float(ys.mean() + yslice.start)
        cx = float(xs.mean() + xslice.start)
        area = int(local.sum())
        radius = max(2.0, np.sqrt(float(area) / np.pi))
        yy, xx = np.indices(local.shape)
        local_center = np.exp(-(((yy + yslice.start - cy) ** 2 + (xx + xslice.start - cx) ** 2) / (2.0 * max(1.0, radius * 0.25) ** 2)))
        center[slices] = np.maximum(center[slices], local_center.astype(np.float32) * local)
        norm = max(1.0, radius)
        offset_y[slices][local] = (cy - (ys + yslice.start)) / norm
        offset_x[slices][local] = (cx - (xs + xslice.start)) / norm

    contact = _contact_boundary(labels).astype(np.float32)
    return {"fg": fg, "center": center, "contact": contact, "offset_y": offset_y, "offset_x": offset_x}


def _contact_boundary(labels: np.ndarray) -> np.ndarray:
    boundaries = np.zeros(labels.shape, dtype=bool)
    for dy, dx in ((1, 0), (0, 1), (1, 1), (1, -1)):
        a = labels[max(0, dy) : labels.shape[0] + min(0, dy), max(0, dx) : labels.shape[1] + min(0, dx)]
        b = labels[max(0, -dy) : labels.shape[0] - max(0, dy), max(0, -dx) : labels.shape[1] - max(0, dx)]
        diff = (a != b) & (a > 0) & (b > 0)
        target = boundaries[max(0, dy) : labels.shape[0] + min(0, dy), max(0, dx) : labels.shape[1] + min(0, dx)]
        target |= diff
    return ndi.binary_dilation(boundaries, structure=np.ones((3, 3), dtype=bool))


def _to_gray_float(image: np.ndarray) -> np.ndarray:
    arr = image.astype(np.float32, copy=False)
    if arr.ndim == 3:
        arr = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    lo = float(np.percentile(arr, 1))
    hi = float(np.percentile(arr, 99))
    if hi <= lo:
        hi = float(arr.max())
        lo = float(arr.min())
    if hi > lo:
        arr = (arr - lo) / (hi - lo)
    return np.clip(arr, 0.0, 1.0).astype(np.float32, copy=False)


class SeparatorProposalGenerator:
    def __init__(self, cfg, runtime_device: str = "cuda") -> None:  # noqa: ANN001
        if torch is None or nn is None:
            raise RuntimeError("PyTorch is required when separator_proposals.enabled=true")
        if not cfg.model_path:
            raise ValueError("separator_proposals.model_path is required when separator proposals are enabled")
        self.cfg = cfg
        self.device = torch.device(cfg.device or runtime_device)
        self.model = self._load_model(Path(cfg.model_path))

    def _load_model(self, path: Path):
        payload: Any = torch.load(path, map_location="cpu")
        state_dict = payload.get("state_dict", payload) if isinstance(payload, dict) else payload
        in_channels = int(payload.get("input_channels", self.cfg.input_channels)) if isinstance(payload, dict) else int(self.cfg.input_channels)
        base_channels = int(payload.get("base_channels", self.cfg.base_channels)) if isinstance(payload, dict) else int(self.cfg.base_channels)
        model = SeparatorProposalNet(in_channels=in_channels, base_channels=base_channels)
        model.load_state_dict(state_dict)
        model.to(self.device)
        model.eval()
        return model

    def predict(self, image: np.ndarray, fg_prob: np.ndarray, boundary_prob: np.ndarray | None) -> list[InstanceProposal]:
        model_input = build_separator_input(image, fg_prob, boundary_prob, self.cfg.fg_threshold)
        tensor = torch.from_numpy(model_input[None]).to(self.device)
        with torch.inference_mode():
            pred = self.model(tensor)[0].detach().cpu().numpy()
        sep_fg = _sigmoid(pred[0])
        center = _sigmoid(pred[1])
        contact = _sigmoid(pred[2])
        return separator_outputs_to_proposals(sep_fg, center, contact, fg_prob, self.cfg)


def separator_outputs_to_proposals(
    sep_fg: np.ndarray,
    center_prob: np.ndarray,
    contact_prob: np.ndarray,
    semantic_fg_prob: np.ndarray,
    cfg,
) -> list[InstanceProposal]:  # noqa: ANN001
    fg_mask = (sep_fg >= float(cfg.fg_threshold)) & (semantic_fg_prob >= float(cfg.semantic_gate_threshold))
    fg_mask = ndi.binary_fill_holes(fg_mask)
    fg_mask = ndi.binary_opening(fg_mask, structure=np.ones((2, 2), dtype=bool))
    if not np.any(fg_mask):
        return []
    dist = compute_distance(fg_mask, sigma=float(cfg.edt_sigma))
    markers = _markers_from_center(center_prob, fg_mask, cfg)
    if int(markers.max()) == 0:
        return []
    max_dist = float(dist.max())
    energy = dist.astype(np.float32, copy=True)
    if max_dist > 0 and float(cfg.boundary_weight) > 0:
        energy -= max_dist * float(cfg.boundary_weight) * np.clip(contact_prob.astype(np.float32, copy=False), 0.0, 1.0)
        energy[energy < 0] = 0.0
    label_map = watershed(-energy, markers, mask=fg_mask).astype(np.int32, copy=False)
    score_map = np.maximum(semantic_fg_prob.astype(np.float32, copy=False), sep_fg.astype(np.float32, copy=False))
    return extract_proposals(label_map, score_map, min_area=int(cfg.min_area), max_area=cfg.max_area, source=cfg.source_name)


def _markers_from_center(center_prob: np.ndarray, fg_mask: np.ndarray, cfg) -> np.ndarray:  # noqa: ANN001
    component_labels, n_components = ndi.label(fg_mask)
    markers = np.zeros(fg_mask.shape, dtype=np.int32)
    next_marker = 1
    for component_id in range(1, n_components + 1):
        component = component_labels == component_id
        if int(component.sum()) < int(cfg.min_area):
            continue
        slices = ndi.find_objects(component.astype(np.int32), max_label=1)[0]
        if slices is None:
            continue
        local_mask = component[slices]
        local_center = center_prob[slices].astype(np.float32, copy=False)
        area = int(local_mask.sum())
        radius = np.sqrt(float(max(1, area)) / np.pi)
        min_distance = max(int(cfg.center_nms_min_distance), int(radius * float(cfg.center_nms_radius_factor)))
        coords = peak_local_max(
            local_center,
            labels=local_mask.astype(np.uint8),
            min_distance=max(1, min_distance),
            threshold_abs=float(cfg.center_threshold),
            exclude_border=False,
            num_peaks=int(cfg.max_seeds_per_component),
        )
        if coords.size == 0:
            y, x = np.unravel_index(np.argmax(local_center * local_mask), local_center.shape)
            coords = np.asarray([[y, x]], dtype=np.int64)
        local_out = markers[slices]
        for y, x in coords:
            if not local_mask[int(y), int(x)]:
                continue
            local_out[int(y), int(x)] = next_marker
            next_marker += 1
        markers[slices] = local_out
    return markers


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))).astype(np.float32, copy=False)
