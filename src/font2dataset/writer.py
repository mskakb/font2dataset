# REVIEW: done

"""
Write generated character images and metadata to disk.

Coordinates image file I/O and metadata recording (JSONL + Parquet).
Implements context manager protocol for clean setup/teardown.
Thread-safe for concurrent calls to write().
"""

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import pyarrow as pa
import pyarrow.parquet as pq
from PIL.Image import Image


@dataclass
class WriterConfig:
    """Configuration for dataset output."""
    output_dir: str | Path


class DatasetWriter:
    """Write rendered character images and metadata records to disk.

    Manages:
    - Image file output (PNG format in a flat `images/` subdirectory)
    - Metadata recording (JSONL with streaming append, Parquet on finalization)
    - Context manager lifecycle (open on enter, close on exit)
    """

    def __init__(self, config: WriterConfig) -> None:
        """Initialize writer with output directory configuration."""
        self._config = config
        self._output_dir = Path(config.output_dir)
        self._images_dir = self._output_dir / "images"
        self._jsonl_path = self._output_dir / "metadata.jsonl"
        self._jsonl_file = None
        self._lock = threading.Lock()

    def open(self) -> None:
        """Create output directories and open JSONL file for writing.

        Overwrites existing metadata.jsonl (ensures reproducibility on re-run).
        Images directory is created with exist_ok=True.
        """
        self._images_dir.mkdir(parents=True, exist_ok=True)
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
            Generated filename (e.g., "3042_NotoSansJP-Regular_000.png")

        Raises:
            IOError: If image save or JSONL write fails
            ValueError: If char is not a single character
        """
        if len(char) != 1:
            raise ValueError(f"Expected single character, got {char!r}")

        # Generate filename
        unicode_hex = f"{ord(char):04x}"
        font_stem = Path(font_path).stem
        index_str = f"{index:03d}"
        filename = f"{unicode_hex}_{font_stem}_{index_str}.png"

        # Save image (thread-safe: unique filename per char/font/index)
        image_path = self._images_dir / filename
        image.save(image_path, format="PNG")

        # Record metadata (requires lock: shared JSONL file)
        codepoint = ord(char)
        record = {
            "file": filename,
            "char": char,
            "unicode": f"U+{codepoint:04X}",
            "codepoint": codepoint,
            "font_path": str(font_path),
            "font_family": font_family,
            "font_style": font_style,
        }
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
        # Read JSONL records
        records = []
        with open(self._jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        # Convert to Parquet
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
