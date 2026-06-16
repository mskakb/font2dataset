# REVIEW: done

"""
Write generated character images and metadata to disk.

Coordinates image file I/O and metadata recording (JSONL + Parquet).
Implements context manager protocol for clean setup/teardown.
Thread-safe for concurrent calls to write().
"""

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image as _PIL
from PIL.Image import Image

from .binarize import compute_threshold
from .sdf import binary_image_to_sdf


@dataclass
class WriterConfig:
    """Configuration for dataset output."""
    output_dir: str | Path = "./output"
    save_png: bool = True
    # PNG binarization (independent from SDF)
    binarize_method: Literal["none", "threshold", "otsu"] = "none"
    binarize_threshold: float = 0.5
    sdf_format: Literal["none", "npy", "png", "both"] = "none"
    sdf_max_dist: float = 10.0
    # SDF stroke-detection binarization (independent from PNG)
    sdf_binarize_method: Literal["threshold", "otsu"] = "threshold"
    sdf_binarize_threshold: float = 0.5


class DatasetWriter:
    """Write rendered character images and metadata records to disk.

    Manages:
    - Image file output (PNG format in a flat `images/` subdirectory)
    - SDF file output (npy and/or grayscale PNG in `sdf/` subdirectory)
    - Metadata recording (JSONL with streaming append, Parquet on finalization)
    - Context manager lifecycle (open on enter, close on exit)
    """

    def __init__(self, config: WriterConfig) -> None:
        """Initialize writer with output directory configuration."""
        self._config = config
        self._output_dir = Path(config.output_dir)
        self._images_dir = self._output_dir / "images"
        self._sdf_dir = self._output_dir / "sdf"
        self._jsonl_path = self._output_dir / "metadata.jsonl"
        self._jsonl_file = None
        self._lock = threading.Lock()

    def open(self) -> None:
        """Create output directories and open JSONL file for writing.

        Overwrites existing metadata.jsonl (ensures reproducibility on re-run).
        Images and sdf directories are created with exist_ok=True.
        """
        if self._config.save_png:
            self._images_dir.mkdir(parents=True, exist_ok=True)
        if self._config.sdf_format != "none":
            self._sdf_dir.mkdir(parents=True, exist_ok=True)
        self._jsonl_file = open(self._jsonl_path, "w", encoding="utf-8")

    def write(
        self,
        char: str,
        image: Image,
        font_path: str | Path,
        index: int,
        font_family: str = "",
        font_style: str = "",
    ) -> str:
        """Save one character image and record metadata.

        Args:
            char: Single character to render
            image: Rendered character as PIL Image
            font_path: Path to the font file used for rendering
            index: Sequential index for this (char, font) pair
            font_family: Font family name from the font's name table (e.g. "Noto Sans JP")
            font_style: Font subfamily name from the font's name table (e.g. "Regular")

        Returns:
            Generated PNG filename (e.g., "3042_NotoSansJP-Regular_000.png")

        Raises:
            IOError: If image save or JSONL write fails
            ValueError: If char is not a single character
        """
        if len(char) != 1:
            raise ValueError(f"Expected single character, got {char!r}")

        cfg = self._config
        unicode_hex = f"{ord(char):04x}"
        font_stem = Path(font_path).stem
        index_str = f"{index:03d}"
        stem = f"{unicode_hex}_{font_stem}_{index_str}"
        filename = f"{stem}.png"

        # Grayscale view of the original anti-aliased image (SDF always uses this)
        gray = image.convert("L")

        # Save regular PNG (optionally binarized; luminance-based, polarity-preserving)
        if cfg.save_png:
            if cfg.binarize_method != "none":
                gray01 = np.asarray(gray, dtype=np.float32) / 255.0
                t = compute_threshold(gray01, cfg.binarize_method, cfg.binarize_threshold)
                cutoff = t * 255.0
                save_image = gray.point(lambda p: 0 if p < cutoff else 255).convert("RGB")
            else:
                save_image = image
            save_image.save(self._images_dir / filename, format="PNG")

        # Save SDF (always computed from the original image, independent of PNG binarization)
        sdf_npy_file: str | None = None
        sdf_png_file: str | None = None
        if cfg.sdf_format != "none":
            arr = np.asarray(gray, dtype=np.float32) / 255.0
            sdf_t = compute_threshold(arr, cfg.sdf_binarize_method, cfg.sdf_binarize_threshold)
            sdf = binary_image_to_sdf(arr, max_dist=cfg.sdf_max_dist, binarize_threshold=sdf_t)

            if cfg.sdf_format in ("npy", "both"):
                npy_name = f"{stem}.npy"
                np.save(self._sdf_dir / npy_name, sdf)
                sdf_npy_file = npy_name

            if cfg.sdf_format in ("png", "both"):
                png_name = f"{stem}.png"
                sdf_uint8 = (sdf * 255).clip(0, 255).astype(np.uint8)
                _PIL.fromarray(sdf_uint8, mode="L").save(self._sdf_dir / png_name)
                sdf_png_file = png_name

        # Record metadata (requires lock: shared JSONL file)
        codepoint = ord(char)
        record: dict = {
            "file": filename,
            "char": char,
            "unicode": f"U+{codepoint:04X}",
            "codepoint": codepoint,
            "font_path": str(font_path),
            "font_family": font_family,
            "font_style": font_style,
        }
        if sdf_npy_file is not None:
            record["sdf_npy_file"] = sdf_npy_file
        if sdf_png_file is not None:
            record["sdf_png_file"] = sdf_png_file

        with self._lock:
            self._jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._jsonl_file.flush()

        return filename

    def finalize(self) -> Path:
        """Convert JSONL to Parquet format.

        Reads all records from metadata.jsonl and writes to metadata.parquet.
        JSONL file is not deleted.

        Returns:
            Path to the generated Parquet file

        Raises:
            IOError: If reading JSONL or writing Parquet fails
        """
        records = []
        with open(self._jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        table = pa.Table.from_pylist(records)
        parquet_path = self._output_dir / "metadata.parquet"
        pq.write_table(table, parquet_path)

        return parquet_path

    def close(self) -> None:
        """Close JSONL file handle."""
        if self._jsonl_file is not None:
            self._jsonl_file.close()
            self._jsonl_file = None

    def __enter__(self) -> "DatasetWriter":
        """Enter context manager: open JSONL and directories."""
        self.open()
        return self

    def __exit__(self, *args) -> None:
        """Exit context manager: close JSONL file.

        Note: finalize() is not called here; pipeline is responsible for
        calling it after all fonts are processed.
        """
        self.close()
