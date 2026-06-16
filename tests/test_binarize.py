"""Tests for binarize.py module."""

import numpy as np
import pytest

from font2dataset.binarize import compute_threshold


class TestComputeThreshold:
    """Tests for compute_threshold registry dispatch."""

    def test_fixed_threshold_returns_value(self):
        """method='threshold' returns the configured threshold unchanged."""
        gray = np.linspace(0.0, 1.0, 256, dtype=np.float32).reshape(16, 16)
        assert compute_threshold(gray, "threshold", 0.3) == pytest.approx(0.3)

    def test_otsu_separates_bimodal_image(self):
        """Otsu returns a threshold between the two modes of a bimodal image."""
        # Half dark (~0.1), half bright (~0.9)
        gray = np.concatenate([
            np.full(500, 0.1, dtype=np.float32),
            np.full(500, 0.9, dtype=np.float32),
        ]).reshape(20, 50)
        t = compute_threshold(gray, "otsu")
        assert 0.1 < t < 0.9

    def test_otsu_ignores_threshold_arg(self):
        """Otsu computes from the image regardless of the threshold argument."""
        gray = np.concatenate([
            np.full(500, 0.2, dtype=np.float32),
            np.full(500, 0.8, dtype=np.float32),
        ]).reshape(20, 50)
        assert compute_threshold(gray, "otsu", 0.99) == compute_threshold(gray, "otsu", 0.01)

    def test_unknown_method_raises_valueerror(self):
        """An unregistered method name raises ValueError."""
        gray = np.zeros((4, 4), dtype=np.float32)
        with pytest.raises(ValueError):
            compute_threshold(gray, "nonexistent")
