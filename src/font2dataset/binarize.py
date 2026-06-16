# REVIEW: pending

"""Grayscale binarization threshold strategies (extensible registry).

Both PNG saving and SDF stroke detection reduce to the same operation:
given a grayscale image in [0, 1], decide a scalar threshold `t` such that
pixels with value < t are treated as stroke (ink) and the rest as background.

To add a new method, write a function with the signature
`(gray: np.ndarray, threshold: float) -> float` and register it in
`THRESHOLD_METHODS`.
"""

from __future__ import annotations

import numpy as np


def _fixed(gray: np.ndarray, threshold: float) -> float:
    """Return the user-specified fixed threshold (ignores the image)."""
    return threshold


def _otsu(gray: np.ndarray, threshold: float) -> float:
    """Otsu's method: maximize inter-class variance over a 256-bin histogram.

    The `threshold` argument is unused; it is accepted only to keep a uniform
    signature across registry entries. Returns a threshold in [0, 1].
    """
    hist, edges = np.histogram(gray, bins=256, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total == 0:
        return threshold

    centers = (edges[:-1] + edges[1:]) / 2.0
    w_bg = np.cumsum(hist)
    w_fg = total - w_bg
    sum_total = (hist * centers).sum()
    sum_bg = np.cumsum(hist * centers)

    valid = (w_bg > 0) & (w_fg > 0)
    mean_bg = np.where(w_bg == 0, 0.0, sum_bg / np.where(w_bg == 0, 1, w_bg))
    mean_fg = np.where(
        w_fg == 0, 0.0, (sum_total - sum_bg) / np.where(w_fg == 0, 1, w_fg)
    )
    between = np.where(valid, w_bg * w_fg * (mean_bg - mean_fg) ** 2, -1.0)
    # Right edge of the optimal background bin: pixels below it are stroke.
    idx = int(np.argmax(between))
    return float(edges[idx + 1])


# Registry: method name -> threshold function. Add new methods here.
THRESHOLD_METHODS = {"threshold": _fixed, "otsu": _otsu}


def compute_threshold(
    gray: np.ndarray,
    method: str = "threshold",
    threshold: float = 0.5,
) -> float:
    """Compute a scalar binarization threshold in [0, 1] for a grayscale image.

    Args:
        gray: Grayscale image as a numpy array in [0, 1].
        method: Strategy name; one of the keys in THRESHOLD_METHODS.
        threshold: Fixed threshold value, used by the "threshold" method.

    Returns:
        Scalar threshold in [0, 1]. Pixels below this are stroke.

    Raises:
        ValueError: If `method` is not a registered strategy.
    """
    try:
        fn = THRESHOLD_METHODS[method]
    except KeyError:
        raise ValueError(
            f"Unknown binarize method: {method!r}. "
            f"Available: {sorted(THRESHOLD_METHODS)}"
        )
    return float(fn(np.asarray(gray, dtype=np.float32), threshold))
