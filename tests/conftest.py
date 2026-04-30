"""Shared test fixtures and configuration."""

from pathlib import Path

import pytest


@pytest.fixture
def font_path():
    """Path to a test font file (ASCII compatible)."""
    font = Path(__file__).parent.parent / "fonts" / "Aclonica-Regular.ttf"
    assert font.exists(), f"Test font not found: {font}"
    return str(font)


@pytest.fixture
def tmp_output(tmp_path):
    """Temporary output directory for test generation."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)
