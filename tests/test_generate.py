"""Tests for script/generate.py CLI module."""

import sys
from pathlib import Path

import pytest

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "script"))

from generate import _config_from_dict


class TestConfigFromDict:
    """Tests for _config_from_dict() conversion function."""

    def test_minimal_config_dict(self):
        """Minimal dict with required fields converts successfully."""
        config_dict = {
            "charset": "digits",
            "font_dir": "./fonts",
        }
        config = _config_from_dict(config_dict)

        assert config.charset == "digits"
        assert config.font_dir == "./fonts"
        assert config.output_dir == "./output"  # default
        assert config.workers == 4  # default

    def test_full_config_dict(self):
        """Full dict with all fields converts correctly."""
        config_dict = {
            "charset": "uppercase",
            "font_dir": "./my_fonts",
            "output_dir": "./my_output",
            "image_size": [128, 128],
            "font_size": 72,
            "background": "black",
            "foreground": "white",
            "padding": 8,
            "overflow": "scale",
            "workers": 2,
        }
        config = _config_from_dict(config_dict)

        assert config.charset == "uppercase"
        assert config.font_dir == "./my_fonts"
        assert config.output_dir == "./my_output"
        assert config.render.image_size == (128, 128)
        assert config.render.font_size == 72
        assert config.render.background == "black"
        assert config.render.foreground == "white"
        assert config.render.padding == 8
        assert config.render.overflow == "scale"
        assert config.workers == 2

    def test_image_size_list_to_tuple(self):
        """image_size list is converted to tuple."""
        config_dict = {
            "charset": "digits",
            "font_dir": "./fonts",
            "image_size": [96, 96],
        }
        config = _config_from_dict(config_dict)

        assert config.render.image_size == (96, 96)
        assert isinstance(config.render.image_size, tuple)

    def test_missing_charset_raises_keyerror(self):
        """Missing required field 'charset' raises KeyError."""
        config_dict = {
            "font_dir": "./fonts",
        }
        with pytest.raises(KeyError):
            _config_from_dict(config_dict)

    def test_missing_font_dir_raises_keyerror(self):
        """Missing required field 'font_dir' raises KeyError."""
        config_dict = {
            "charset": "digits",
        }
        with pytest.raises(KeyError):
            _config_from_dict(config_dict)

    def test_partial_render_config(self):
        """Render config fields can be specified individually."""
        config_dict = {
            "charset": "digits",
            "font_dir": "./fonts",
            "font_size": 64,
            "background": "gray",
        }
        config = _config_from_dict(config_dict)

        # Specified values
        assert config.render.font_size == 64
        assert config.render.background == "gray"
        # Default values
        assert config.render.image_size == (64, 64)  # default
        assert config.render.foreground == "black"  # default

    def test_defaults_are_applied(self):
        """Unspecified fields get default values."""
        config_dict = {
            "charset": "ascii",
            "font_dir": "./fonts",
        }
        config = _config_from_dict(config_dict)

        assert config.output_dir == "./output"
        assert config.render.image_size == (64, 64)
        assert config.render.padding == 4
        assert config.workers == 4

    def test_charset_list_input(self):
        """charset can be a list of specs."""
        config_dict = {
            "charset": ["digits", "uppercase"],
            "font_dir": "./fonts",
        }
        config = _config_from_dict(config_dict)

        assert config.charset == ["digits", "uppercase"]

    def test_all_overflow_modes(self):
        """All overflow modes are accepted."""
        for overflow in ["skip", "shrink", "scale"]:
            config_dict = {
                "charset": "digits",
                "font_dir": "./fonts",
                "overflow": overflow,
            }
            config = _config_from_dict(config_dict)
            assert config.render.overflow == overflow
