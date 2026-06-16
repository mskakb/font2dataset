



# REVIEW: done

"""
Pipeline: orchestrates batch generation of character images across fonts.

Integrates charset selection, rendering, and dataset writing into a single
workflow. Supports parallel processing via ThreadPoolExecutor with proper
error handling and progress tracking.
"""

import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace as dc_replace
from pathlib import Path

import yaml

from tqdm import tqdm

from fontTools.ttLib import TTFont

from .charset import build_charset
from .renderer import FontRenderer, RenderConfig
from .writer import DatasetWriter, WriterConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for batch dataset generation.

    Attributes:
        charset: Character set specification (preset name, Unicode range, or literal).
        font_dir: Directory containing TTF/OTF font files.
        output_dir: Output directory for images and metadata.
        render: Rendering configuration (image size, colors, etc.).
        writer: Output format configuration (PNG, SDF, etc.).
        workers: Number of parallel worker threads.
        recursive: Search font_dir recursively for font files.
    """
    charset: str | list[str]
    font_dir: str | Path | list[str | Path]
    output_dir: str | Path = "./output"
    render: RenderConfig = field(default_factory=RenderConfig)
    writer: WriterConfig = field(default_factory=WriterConfig)
    workers: int = 4
    recursive: bool = False


@dataclass
class FontResult:
    """Result of processing a single font."""
    font_path: str
    images_written: int
    charset_skipped: list[str]
    render_skipped: list[str]


@dataclass
class PipelineResult:
    """Result of the entire pipeline execution."""
    total_images: int
    font_results: list[FontResult]
    failed_fonts: list[str]
    parquet_path: Path
    elapsed_seconds: float


def _font_meta(font_path: Path) -> tuple[str, str]:
    """Return (family, style) from a font's name table.

    Name ID 1 = Font Family, Name ID 2 = Font Subfamily (Regular/Bold/…).
    Falls back to empty string if a record is absent.
    """
    tt = TTFont(str(font_path), lazy=True)
    names = tt["name"]

    def _get(name_id: int) -> str:
        rec = names.getName(name_id, 3, 1, 0x0409) or names.getName(name_id, 1, 0, 0)
        return rec.toUnicode() if rec else ""

    family, style = _get(1), _get(2)
    tt.close()
    return family, style


def _save_config(config: "PipelineConfig", output_dir: Path) -> None:
    """Persist the effective config to output_dir/config.yaml for reproducibility."""
    d = {
        "charset": config.charset,
        "font_dir": [str(d) for d in config.font_dir] if isinstance(config.font_dir, list) else str(config.font_dir),
        "output_dir": str(config.output_dir),
        "image_size": list(config.render.image_size),
        "font_size": config.render.font_size,
        "background": config.render.background,
        "foreground": config.render.foreground,
        "padding": config.render.padding,
        "overflow": config.render.overflow,
        "min_font_size": config.render.min_font_size,
        "bbox_method": config.render.bbox_method,
        "workers": config.workers,
        "recursive": config.recursive,
        "save_png": config.writer.save_png,
        "binarize_method": config.writer.binarize_method,
        "binarize_threshold": config.writer.binarize_threshold,
        "sdf_format": config.writer.sdf_format,
        "sdf_max_dist": config.writer.sdf_max_dist,
        "sdf_binarize_method": config.writer.sdf_binarize_method,
        "sdf_binarize_threshold": config.writer.sdf_binarize_threshold,
    }
    with open(output_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(d, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _collect_fonts(font_dir: str | Path | list[str | Path], recursive: bool = False) -> list[Path]:
    """Collect and sort font files deterministically from one or more directories."""
    dirs = [font_dir] if not isinstance(font_dir, list) else font_dir
    pattern = "**/*" if recursive else "*"
    fonts = [
        p
        for d in dirs
        for p in Path(d).glob(pattern)
        if p.is_file() and p.suffix.lower() in {".ttf", ".otf"}
    ]
    return sorted(set(fonts), key=lambda p: p.name)


def _process_font(
    font_path: Path,
    config: PipelineConfig,
    writer: DatasetWriter,
) -> FontResult:
    """Process a single font: render characters and write to dataset.

    Args:
        font_path: Path to the font file.
        config: Pipeline configuration.
        writer: Shared DatasetWriter instance (thread-safe).

    Returns:
        FontResult with counts and skip lists.

    Raises:
        Any exception encountered during rendering or writing.
    """
    # Filter charset by font glyphs
    chars, charset_skipped = build_charset(config.charset, font_path=font_path)

    logger.debug("Processing font: %s (%d chars, %d skipped by charset)",
                 font_path.name, len(chars), len(charset_skipped))

    # Extract font metadata once per font
    font_family, font_style = _font_meta(font_path)

    # Render and write
    renderer = FontRenderer(str(font_path), config.render)
    render_skipped = []
    images_written = 0

    for char in chars:
        image = renderer.render(char)
        if image is None:
            render_skipped.append(char)
            continue

        writer.write(char, image, str(font_path), index=0,
                     font_family=font_family, font_style=font_style)
        images_written += 1

    if charset_skipped:
        logger.debug("Font %s: %d chars have no glyph: %s",
                     font_path.name,
                     len(charset_skipped),
                     "".join(charset_skipped[:20]) + ("..." if len(charset_skipped) > 20 else ""))

    if render_skipped:
        logger.debug("Font %s: %d chars failed to render (overflow=skip)",
                     font_path.name, len(render_skipped))

    logger.debug("Font %s: wrote %d images", font_path.name, images_written)

    return FontResult(
        font_path=str(font_path),
        images_written=images_written,
        charset_skipped=charset_skipped,
        render_skipped=render_skipped,
    )


def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """Execute the dataset generation pipeline.

    Processes all fonts in config.font_dir in parallel, rendering characters
    and writing images + metadata. Handles errors gracefully per Pipeline Rule ②.

    Args:
        config: Pipeline configuration.

    Returns:
        PipelineResult with statistics and output path.
    """
    start_time = time.time()

    # Clean output_dir to prevent stale images from prior runs
    output_dir = Path(config.output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
        logger.info("Cleared existing output directory: %s", output_dir)
    output_dir.mkdir(parents=True)
    _save_config(config, output_dir)

    # Collect fonts in deterministic order
    fonts = _collect_fonts(config.font_dir, recursive=config.recursive)
    logger.info("Starting pipeline: %d fonts, %d workers, charset=%r",
                len(fonts), config.workers, config.charset)

    if not fonts:
        logger.warning("No fonts found in %s", config.font_dir)
        return PipelineResult(
            total_images=0,
            font_results=[],
            failed_fonts=[],
            parquet_path=Path(),
            elapsed_seconds=time.time() - start_time,
        )

    # Initialize writer (inherit SDF/PNG settings; override output_dir from pipeline)
    writer_config = dc_replace(config.writer, output_dir=config.output_dir)
    all_results = []
    failed_fonts = []

    with DatasetWriter(writer_config) as writer:
        # Process fonts in parallel
        with ThreadPoolExecutor(max_workers=config.workers) as executor:
            futures = {
                executor.submit(_process_font, font_path, config, writer): font_path
                for font_path in fonts
            }

            for future in tqdm(as_completed(futures), total=len(futures),
                              desc="Processing fonts"):
                font_path = futures[future]
                try:
                    result = future.result()
                    all_results.append(result)
                except Exception as e:
                    logger.error("Font processing failed: %s — %s",
                                font_path.name, e, exc_info=True)
                    failed_fonts.append(str(font_path))

        # Finalize: convert JSONL to Parquet
        parquet_path = writer.finalize()

    # Summarize
    total_images = sum(r.images_written for r in all_results)
    elapsed = time.time() - start_time

    logger.info("Pipeline complete: %d images, %d failed fonts, %.1f sec, parquet=%s",
                total_images, len(failed_fonts), elapsed, parquet_path)

    return PipelineResult(
        total_images=total_images,
        font_results=all_results,
        failed_fonts=failed_fonts,
        parquet_path=parquet_path,
        elapsed_seconds=elapsed,
    )
