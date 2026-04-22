"""
SAM2 zero-shot segmentation for seismic slices.

Design: thin wrapper around SAM2ImagePredictor that speaks seismic —
takes numpy slices, returns numpy masks. All device handling is here
so callers never touch torch.

Two modes:
  - Point prompt:  give (x, y) coordinates of features you want masked
  - Automatic:     SAM2AutomaticMaskGenerator finds everything in the image
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np


def _load_predictor(checkpoint: str | Path, device: str = "cpu"):
    """Load SAM2ImagePredictor. Lazy import keeps torch optional."""
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    checkpoint = Path(checkpoint)
    if not checkpoint.exists():
        raise FileNotFoundError(f"SAM2 checkpoint not found: {checkpoint}")

    # Derive config from checkpoint filename convention:
    #   sam2.1_hiera_tiny.pt  ->  configs/sam2.1/sam2.1_hiera_t.yaml
    #   sam2.1_hiera_small.pt ->  configs/sam2.1/sam2.1_hiera_s.yaml
    #   sam2.1_hiera_large.pt ->  configs/sam2.1/sam2.1_hiera_l.yaml
    _cfg_map = {
        "tiny":      "configs/sam2.1/sam2.1_hiera_t.yaml",
        "small":     "configs/sam2.1/sam2.1_hiera_s.yaml",
        "base_plus": "configs/sam2.1/sam2.1_hiera_b+.yaml",
        "large":     "configs/sam2.1/sam2.1_hiera_l.yaml",
    }
    stem = checkpoint.stem  # e.g. "sam2.1_hiera_tiny"
    matched = next((v for k, v in _cfg_map.items() if k in stem), None)
    if matched is None:
        raise ValueError(
            f"Cannot infer SAM2 config from checkpoint name '{stem}'. "
            f"Expected one of: {list(_cfg_map)}"
        )

    model = build_sam2(matched, str(checkpoint), device=device)
    return SAM2ImagePredictor(model)


def segment_with_points(
    rgb_image: np.ndarray,
    point_coords: Sequence[tuple[int, int]],
    checkpoint: str | Path,
    device: str = "cpu",
    point_labels: Sequence[int] | None = None,
) -> np.ndarray:
    """Run SAM2 with point prompts on a seismic slice image.

    Parameters
    ----------
    rgb_image : np.ndarray
        Shape (H, W, 3), dtype uint8. Use slice_to_rgb() to produce this.
    point_coords : sequence of (x, y) tuples
        Pixel coordinates of prompts. (x=column, y=row).
    checkpoint : path
        Path to the .pt SAM2 checkpoint file.
    device : str
        'cpu' for local testing, 'cuda' for Modal GPU.
    point_labels : sequence of int, optional
        1 = foreground (include), 0 = background (exclude).
        Defaults to all-foreground if not provided.

    Returns
    -------
    np.ndarray
        Shape (H, W), dtype bool. True where SAM predicts the feature.
        If multiple masks are returned, the highest-scoring one is kept.
    """
    import torch

    if rgb_image.ndim != 3 or rgb_image.shape[2] != 3:
        raise ValueError(f"rgb_image must be (H, W, 3), got {rgb_image.shape}")

    predictor = _load_predictor(checkpoint, device)

    coords  = np.array(point_coords, dtype=np.float32)          # (N, 2)
    labels  = np.ones(len(coords), dtype=np.int32) if point_labels is None \
              else np.array(point_labels, dtype=np.int32)

    with torch.inference_mode():
        predictor.set_image(rgb_image)
        masks, scores, _ = predictor.predict(
            point_coords=coords,
            point_labels=labels,
            multimask_output=True,
        )

    # masks: (N_masks, H, W) bool — return the highest-scoring one
    best = int(np.argmax(scores))
    return masks[best].astype(bool)


def segment_auto(
    rgb_image: np.ndarray,
    checkpoint: str | Path,
    device: str = "cpu",
    points_per_side: int = 16,
    pred_iou_thresh: float = 0.80,
    stability_score_thresh: float = 0.90,
) -> list[dict]:
    """Run SAM2 automatic mask generation — finds all features.

    Parameters
    ----------
    rgb_image : np.ndarray
        Shape (H, W, 3), dtype uint8.
    checkpoint : path
        Path to the .pt SAM2 checkpoint file.
    device : str
        'cpu' or 'cuda'.
    points_per_side : int
        Grid density for automatic prompts. Lower = faster, fewer masks.
        Default 16 is good for seismic; natural images use 32.
    pred_iou_thresh : float
        Discard masks with predicted IoU below this. Default 0.80.
    stability_score_thresh : float
        Discard masks with low stability across thresholds. Default 0.90.

    Returns
    -------
    list of dict
        Each dict has keys: 'segmentation' (H, W bool array),
        'area' (int), 'predicted_iou' (float), 'stability_score' (float).
        Sorted by area descending (largest geological feature first).
    """
    from sam2.build_sam import build_sam2
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
    import torch

    checkpoint = Path(checkpoint)
    _cfg_map = {
        "tiny": "configs/sam2.1/sam2.1_hiera_t.yaml",
        "small": "configs/sam2.1/sam2.1_hiera_s.yaml",
        "base_plus": "configs/sam2.1/sam2.1_hiera_b+.yaml",
        "large": "configs/sam2.1/sam2.1_hiera_l.yaml",
    }
    stem = checkpoint.stem
    cfg = next((v for k, v in _cfg_map.items() if k in stem), None)

    model = build_sam2(cfg, str(checkpoint), device=device)
    generator = SAM2AutomaticMaskGenerator(
        model,
        points_per_side=points_per_side,
        pred_iou_thresh=pred_iou_thresh,
        stability_score_thresh=stability_score_thresh,
    )

    with torch.inference_mode():
        masks = generator.generate(rgb_image)

    masks.sort(key=lambda m: m["area"], reverse=True)
    return masks
