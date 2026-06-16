#!/usr/bin/env python3

# REVIEW: done

"""
CLI entry point for font2dataset: Generate character images from font files.

Usage:
  python script/generate.py --config config/default.yaml
  python script/generate.py --font-dir ./fonts --charset hiragana --output-dir ./output
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

from font2dataset.pipeline import PipelineConfig, run_pipeline
from font2dataset.renderer import RenderConfig
from font2dataset.writer import WriterConfig


def _config_from_dict(d: dict) -> PipelineConfig:
    """Convert flat YAML dict to nested PipelineConfig."""
    render = RenderConfig(
        image_size=tuple(d.get("image_size", (64, 64))),
        font_size=d.get("font_size", 48),
        background=d.get("background", "white"),
        foreground=d.get("foreground", "black"),
        padding=d.get("padding", 4),
        overflow=d.get("overflow", "skip"),
        min_font_size=d.get("min_font_size", 8),
        bbox_method=d.get("bbox_method", "textbbox"),
    )
    writer = WriterConfig(
        save_png=d.get("save_png", True),
        sdf_format=d.get("sdf_format", "none"),
        sdf_max_dist=d.get("sdf_max_dist", 10.0),
    )
    return PipelineConfig(
        charset=d["charset"],
        font_dir=d["font_dir"],
        output_dir=d.get("output_dir", "./output"),
        render=render,
        writer=writer,
        workers=d.get("workers", 4),
        recursive=d.get("recursive", False),
    )


def _load_config(path: str | Path) -> dict:
    """Load YAML configuration file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate character image dataset from font files."
    )
    parser.add_argument(
        "--config",
        type=str,
        help="YAML configuration file path",
    )
    parser.add_argument(
        "--font-dir",
        type=str,
        help="Override font directory",
    )
    parser.add_argument(
        "--charset",
        type=str,
        help="Override character set specification",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Override output directory",
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Override number of parallel workers",
    )
    parser.add_argument(
        "--sdf-format",
        choices=["none", "npy", "png", "both"],
        help="SDF output format (default: none)",
    )
    parser.add_argument(
        "--sdf-max-dist",
        type=float,
        help="SDF clipping distance in pixels (default: 10.0)",
    )
    parser.add_argument(
        "--no-png",
        action="store_true",
        help="Skip saving regular PNG images (useful with --sdf-format)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG level logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        # Load base configuration from YAML or use empty dict
        if args.config:
            logger.info("Loading configuration from %s", args.config)
            config_dict = _load_config(args.config)
        else:
            logger.info("Using default configuration")
            config_dict = {}

        # Override with CLI arguments
        if args.font_dir:
            config_dict["font_dir"] = args.font_dir
        if args.charset:
            config_dict["charset"] = args.charset
        if args.output_dir:
            config_dict["output_dir"] = args.output_dir
        if args.workers:
            config_dict["workers"] = args.workers
        if args.sdf_format:
            config_dict["sdf_format"] = args.sdf_format
        if args.sdf_max_dist is not None:
            config_dict["sdf_max_dist"] = args.sdf_max_dist
        if args.no_png:
            config_dict["save_png"] = False

        # Validate required fields
        if "charset" not in config_dict:
            parser.error("--charset is required (not in config file or CLI)")
        if "font_dir" not in config_dict:
            parser.error("--font-dir is required (not in config file or CLI)")

        # Convert to PipelineConfig
        config = _config_from_dict(config_dict)

        logger.info("Starting pipeline...")
        logger.debug("Config: %s", config)

        # Run pipeline
        result = run_pipeline(config)

        # Report results
        logger.info("=" * 60)
        logger.info("Pipeline completed successfully")
        logger.info("  Total images:      %d", result.total_images)
        logger.info("  Failed fonts:      %d", len(result.failed_fonts))
        logger.info("  Parquet file:      %s", result.parquet_path)
        logger.info("  Elapsed time:      %.1f seconds", result.elapsed_seconds)
        logger.info("=" * 60)

        if result.failed_fonts:
            logger.warning("Failed fonts: %s", ", ".join(result.failed_fonts))

        return 0

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
