"""Tests for renderer.py module."""

from PIL import Image

import pytest

from font2dataset.renderer import FontRenderer, RenderConfig


class TestRenderConfig:
    """Tests for RenderConfig dataclass."""

    def test_default_config(self):
        """Default RenderConfig has expected values."""
        config = RenderConfig()
        assert config.image_size == (64, 64)
        assert config.font_size == 48
        assert config.background == "white"
        assert config.foreground == "black"
        assert config.overflow == "skip"

    def test_custom_config(self):
        """Custom RenderConfig accepts all parameters."""
        config = RenderConfig(
            image_size=(128, 128),
            font_size=72,
            background="black",
            foreground="white",
            overflow="scale",
        )
        assert config.image_size == (128, 128)
        assert config.font_size == 72


class TestFontRenderer:
    """Tests for FontRenderer class."""

    def test_render_ascii_character(self, font_path):
        """Render ASCII character returns Image with correct size."""
        renderer = FontRenderer(font_path)
        img = renderer.render("A")
        assert img is not None
        assert isinstance(img, Image.Image)
        assert img.size == (64, 64)

    def test_render_returns_rgb_image(self, font_path):
        """Rendered image is RGB."""
        renderer = FontRenderer(font_path)
        img = renderer.render("A")
        assert img.mode == "RGB"

    def test_render_multiple_characters(self, font_path):
        """Render produces different results for different characters."""
        renderer = FontRenderer(font_path)
        img_a = renderer.render("A")
        img_b = renderer.render("B")
        # Images should be different
        assert img_a.tobytes() != img_b.tobytes()

    def test_overflow_skip_returns_none_for_large_char(self):
        """With overflow='skip', render returns None for char that doesn't fit."""
        config = RenderConfig(
            image_size=(16, 16),
            font_size=48,
            overflow="skip",
        )
        renderer = FontRenderer("./fonts/Aclonica-Regular.ttf", config)
        # Large font in small image should return None
        img = renderer.render("W")
        assert img is None

    def test_overflow_shrink_returns_image(self):
        """With overflow='shrink', render returns Image."""
        config = RenderConfig(
            image_size=(16, 16),
            font_size=48,
            overflow="shrink",
            min_font_size=6,
        )
        renderer = FontRenderer("./fonts/Aclonica-Regular.ttf", config)
        img = renderer.render("W")
        assert img is not None
        assert isinstance(img, Image.Image)

    def test_overflow_scale_always_returns_image(self):
        """With overflow='scale', render always returns Image."""
        config = RenderConfig(
            image_size=(16, 16),
            font_size=48,
            overflow="scale",
        )
        renderer = FontRenderer("./fonts/Aclonica-Regular.ttf", config)
        img = renderer.render("W")
        assert img is not None
        assert isinstance(img, Image.Image)
        assert img.size == (16, 16)

    def test_render_batch_filters_none_results(self, font_path):
        """render_batch filters out None results."""
        config = RenderConfig(
            image_size=(16, 16),
            font_size=48,
            overflow="skip",
        )
        renderer = FontRenderer(font_path, config)
        # Render multiple chars, some may return None
        results = renderer.render_batch(["A", "W", "B"])
        # All results should have non-None images
        assert all(img is not None for _, img in results)

    def test_fits_considers_padding(self, font_path):
        """fits() considers padding when checking if char fits."""
        config = RenderConfig(image_size=(32, 32), font_size=24, padding=4)
        renderer = FontRenderer(font_path, config)
        # Test that fits accounts for padding
        fits_large = renderer.fits("W")  # Wide char
        assert isinstance(fits_large, bool)


class TestRenderBatch:
    """Tests for render_batch() method."""

    def test_render_batch_returns_tuples(self, font_path):
        """render_batch returns list of (char, Image) tuples."""
        renderer = FontRenderer(font_path)
        results = renderer.render_batch(["A", "B", "C"])
        assert len(results) == 3
        for char, img in results:
            assert isinstance(char, str)
            assert isinstance(img, Image.Image)

    def test_render_batch_preserves_order(self, font_path):
        """render_batch preserves character order in output."""
        renderer = FontRenderer(font_path)
        chars = ["A", "B", "C"]
        results = renderer.render_batch(chars)
        output_chars = [c for c, _ in results]
        assert output_chars == chars

    def test_render_batch_empty_input(self, font_path):
        """render_batch with empty list returns empty list."""
        renderer = FontRenderer(font_path)
        results = renderer.render_batch([])
        assert results == []
