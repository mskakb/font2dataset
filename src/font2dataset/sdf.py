# REVIEW: done
"""Signed Distance Field (SDF) utilities for font images."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

try:
    import torch as _torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


def binary_image_to_sdf(
    image: np.ndarray,
    max_dist: float = 10.0,
) -> np.ndarray:
    """Convert a font image to a Signed Distance Field (SDF).

    Pixels with value < 0.5 are treated as stroke; >= 0.5 as background.
    This matches the default renderer output (black stroke on white background,
    normalized to [0, 1]).

    Args:
        image: Grayscale or RGB image as a float32 numpy array in [0, 1].
               Shape (H, W), (1, H, W), or (3, H, W).
        max_dist: Clipping distance in pixels. Raw SDF values beyond ±max_dist
                  are clipped before mapping to [0, 1].

    Returns:
        SDF image as float32 ndarray in [0, 1] with the same shape as input:
          - stroke interior (far from contour): → 1.0
          - background (far from contour):      → 0.0
          - contour boundary:                   ≈ 0.5
    """
    arr = np.asarray(image, dtype=np.float32)

    squeezed = arr.ndim == 3
    if squeezed:
        arr2d = arr[0] if arr.shape[0] == 1 else arr.mean(axis=0)
    else:
        arr2d = arr

    stroke_mask = arr2d < 0.5

    if stroke_mask.all():
        sdf_01 = np.ones_like(arr2d, dtype=np.float32)
    elif (~stroke_mask).all():
        sdf_01 = np.zeros_like(arr2d, dtype=np.float32)
    else:
        dist_in = distance_transform_edt(stroke_mask).astype(np.float32)
        dist_out = distance_transform_edt(~stroke_mask).astype(np.float32)
        sdf_raw = dist_in - dist_out
        sdf_01 = (np.clip(sdf_raw / max_dist, -1.0, 1.0) + 1.0) / 2.0

    if squeezed:
        sdf_01 = sdf_01[np.newaxis]

    return sdf_01


def sdf_to_binary(
    sdf: np.ndarray,
    threshold: float = 0.5,
    sharpness: float | None = None,
) -> np.ndarray:
    """Threshold an SDF image to recover a binary image.

    Args:
        sdf: SDF image in [0, 1] as produced by binary_image_to_sdf.
        threshold: Pixels above this become stroke (0), others become background (1).
                   Default 0.5 corresponds to the zero-crossing of the raw SDF.
        sharpness: If given, applies soft sigmoid: sigmoid((threshold - sdf) * sharpness)
                   instead of a hard threshold. Values 20–50 give near-binary output.
                   Requires torch; raises ImportError if torch is not installed.

    Returns:
        Image in [0, 1]. Hard threshold: binary {0.0, 1.0}. Soft: continuous [0, 1].

    Raises:
        ImportError: If sharpness is given but torch is not installed.
    """
    if sharpness is not None:
        if not _TORCH_AVAILABLE:
            raise ImportError(
                "sharpness requires torch. Install torch or use sharpness=None for hard threshold."
            )
        t = _torch.from_numpy(np.asarray(sdf, dtype=np.float32))
        return _torch.sigmoid((threshold - t) * sharpness).numpy()

    arr = np.asarray(sdf, dtype=np.float32)
    return (arr <= threshold).astype(np.float32)
