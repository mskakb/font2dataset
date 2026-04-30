"""Tests for pipeline.py module."""

from pathlib import Path

import pytest

from font2dataset.pipeline import PipelineConfig, run_pipeline
from font2dataset.renderer import RenderConfig


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_minimal_config(self):
        """Minimal config with required fields."""
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
        )
        assert config.charset == "digits"
        assert config.font_dir == "./fonts"
        assert config.output_dir == "./output"
        assert config.workers == 4

    def test_full_config(self):
        """Full config with all fields specified."""
        render = RenderConfig(image_size=(128, 128))
        config = PipelineConfig(
            charset="uppercase",
            font_dir="./fonts",
            output_dir="./custom_output",
            render=render,
            workers=2,
        )
        assert config.charset == "uppercase"
        assert config.render.image_size == (128, 128)
        assert config.workers == 2


class TestRunPipeline:
    """Tests for run_pipeline() function."""

    def test_empty_font_directory(self, tmp_path):
        """Pipeline with no fonts returns empty result."""
        empty_dir = tmp_path / "empty_fonts"
        empty_dir.mkdir()
        output_dir = tmp_path / "output"

        config = PipelineConfig(
            charset="digits",
            font_dir=str(empty_dir),
            output_dir=str(output_dir),
            workers=1,
        )
        result = run_pipeline(config)

        assert result.total_images == 0
        assert result.font_results == []
        assert result.failed_fonts == []
        assert result.elapsed_seconds >= 0

    def test_single_font_generation(self, tmp_path):
        """Pipeline with one font generates images."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=1,
        )
        result = run_pipeline(config)

        # Should generate images
        assert result.total_images > 0
        assert len(result.font_results) > 0
        assert result.parquet_path.exists()

    def test_pipeline_creates_images_directory(self, tmp_path):
        """Pipeline creates images/ subdirectory."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=1,
        )
        run_pipeline(config)

        images_dir = Path(output_dir) / "images"
        assert images_dir.exists()

    def test_pipeline_creates_parquet_file(self, tmp_path):
        """Pipeline creates metadata.parquet."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=1,
        )
        result = run_pipeline(config)

        parquet_path = Path(output_dir) / "metadata.parquet"
        assert parquet_path.exists()
        assert result.parquet_path == parquet_path

    def test_pipeline_generates_png_files(self, tmp_path):
        """Pipeline creates PNG image files."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=1,
        )
        run_pipeline(config)

        images_dir = Path(output_dir) / "images"
        png_files = list(images_dir.glob("*.png"))
        assert len(png_files) > 0

    def test_pipeline_result_has_elapsed_time(self, tmp_path):
        """Pipeline result includes elapsed time."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=1,
        )
        result = run_pipeline(config)

        assert result.elapsed_seconds > 0

    def test_reproducibility_same_config(self, tmp_path):
        """Two runs with same config generate same filenames."""
        charset = "digits"
        font_dir = "./fonts"

        output1 = tmp_path / "output1"
        config1 = PipelineConfig(
            charset=charset,
            font_dir=font_dir,
            output_dir=str(output1),
            workers=1,
        )
        result1 = run_pipeline(config1)

        output2 = tmp_path / "output2"
        config2 = PipelineConfig(
            charset=charset,
            font_dir=font_dir,
            output_dir=str(output2),
            workers=1,
        )
        result2 = run_pipeline(config2)

        # Both runs should generate same total images
        assert result1.total_images == result2.total_images

        # File names should be identical (though in different dirs)
        images1 = sorted([f.name for f in (output1 / "images").glob("*.png")])
        images2 = sorted([f.name for f in (output2 / "images").glob("*.png")])
        assert images1 == images2

    def test_pipeline_with_multiple_workers(self, tmp_path):
        """Pipeline works with multiple workers."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=2,
        )
        result = run_pipeline(config)

        assert result.total_images > 0
        assert result.parquet_path.exists()

    def test_font_result_contains_metrics(self, tmp_path):
        """FontResult includes images_written and skip counts."""
        output_dir = tmp_path / "output"
        config = PipelineConfig(
            charset="digits",
            font_dir="./fonts",
            output_dir=str(output_dir),
            workers=1,
        )
        result = run_pipeline(config)

        assert len(result.font_results) > 0
        for font_result in result.font_results:
            assert hasattr(font_result, "font_path")
            assert hasattr(font_result, "images_written")
            assert hasattr(font_result, "charset_skipped")
            assert hasattr(font_result, "render_skipped")
            assert isinstance(font_result.images_written, int)
