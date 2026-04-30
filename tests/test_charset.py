"""Tests for charset.py module."""

import pytest

from font2dataset.charset import (
    build_charset,
    filter_by_font,
    from_range,
    get_preset,
)


class TestGetPreset:
    """Tests for get_preset() function."""

    def test_preset_digits(self):
        """Digits preset contains 0-9."""
        chars = get_preset("digits")
        assert chars == [str(i) for i in range(10)]

    def test_preset_uppercase(self):
        """Uppercase preset contains A-Z."""
        chars = get_preset("uppercase")
        assert len(chars) == 26
        assert chars[0] == "A"
        assert chars[-1] == "Z"

    def test_preset_hiragana(self):
        """Hiragana preset is non-empty."""
        chars = get_preset("hiragana")
        assert len(chars) > 0
        assert "あ" in chars

    def test_preset_unknown_raises_keyerror(self):
        """Unknown preset name raises KeyError."""
        with pytest.raises(KeyError):
            get_preset("unknown_preset_xyz")


class TestFromRange:
    """Tests for from_range() function."""

    def test_unicode_range_uppercase(self):
        """Range U+0041-U+005A should return A-Z (26 chars)."""
        chars = from_range(0x0041, 0x005A + 1)  # +1 for inclusive stop
        assert len(chars) == 26
        assert chars[0] == "A"
        assert chars[-1] == "Z"

    def test_unicode_range_digits(self):
        """Range U+0030-U+0039 should return 0-9."""
        chars = from_range(0x0030, 0x0039 + 1)
        assert len(chars) == 10
        assert chars == [str(i) for i in range(10)]

    def test_empty_range(self):
        """Range with stop <= start should return empty list."""
        chars = from_range(0x0041, 0x0041)
        assert chars == []


class TestBuildCharset:
    """Tests for build_charset() function."""

    def test_preset_name(self):
        """Build charset from preset name."""
        chars, skipped = build_charset("digits")
        assert len(chars) == 10
        assert skipped == []

    def test_unicode_range_string(self):
        """Build charset from Unicode range string."""
        chars, skipped = build_charset("U+0041-U+005A")
        assert len(chars) == 26
        assert chars[0] == "A"
        assert skipped == []

    def test_literal_string(self):
        """Build charset from literal character string."""
        chars, skipped = build_charset("ABC")
        assert chars == ["A", "B", "C"]
        assert skipped == []

    def test_list_input_single_preset(self):
        """Build charset from list with single preset."""
        chars, skipped = build_charset(["uppercase"])
        assert len(chars) == 26

    def test_list_input_mixed(self):
        """Build charset from list with mixed specs."""
        chars, skipped = build_charset(["digits", "ABC"])
        # Should have 10 digits + ABC, with A,B,C potentially overlapping
        assert "0" in chars
        assert "A" in chars

    def test_deduplication(self):
        """Overlapping specs should deduplicate."""
        chars_ascii, _ = build_charset("ascii")
        chars_mixed, _ = build_charset(["ascii", "digits"])
        # digits is subset of ascii, so no additional chars
        assert len(chars_mixed) == len(chars_ascii)

    def test_with_font_path_without_glyphs(self):
        """Filter charset by font glyphs (non-existent chars)."""
        # Aclonica is English font, so hiragana should be skipped
        chars, skipped = build_charset("hiragana", font_path="./fonts/Aclonica-Regular.ttf")
        # All hiragana should be in skipped
        assert len(skipped) > 0

    def test_with_font_path_with_glyphs(self):
        """Charset with glyphs present in font."""
        chars, skipped = build_charset("uppercase", font_path="./fonts/Aclonica-Regular.ttf")
        # Uppercase letters should be supported
        assert len(chars) > 0


class TestFilterByFont:
    """Tests for filter_by_font() function."""

    def test_supported_and_skipped(self, font_path):
        """Filter returns (supported, skipped) tuple."""
        test_chars = ["A", "B", "あ", "い"]
        supported, skipped = filter_by_font(test_chars, font_path)
        # A and B should be supported in Aclonica
        assert "A" in supported
        assert "B" in supported
        # Japanese hiragana should be skipped
        assert "あ" in skipped
        assert "い" in skipped

    def test_all_supported(self, font_path):
        """All ASCII chars in font should be supported."""
        test_chars = list("ABCDEF")
        supported, skipped = filter_by_font(test_chars, font_path)
        assert len(supported) == 6
        assert len(skipped) == 0

    def test_all_skipped(self, font_path):
        """All non-matching chars should be skipped."""
        test_chars = ["あ", "い", "う"]  # hiragana
        supported, skipped = filter_by_font(test_chars, font_path)
        assert len(supported) == 0
        assert len(skipped) == 3
