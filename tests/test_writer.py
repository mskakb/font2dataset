"""Tests for writer.py module."""

import json
from pathlib import Path
from threading import Thread

import pyarrow.parquet as pq
import pytest
from PIL import Image

from font2dataset.writer import DatasetWriter, WriterConfig


@pytest.fixture
def test_image():
    """Create a test image."""
    return Image.new("RGB", (64, 64), color="white")


class TestWriterConfig:
    """Tests for WriterConfig dataclass."""

    def test_config_creation(self, tmp_output):
        """WriterConfig accepts output_dir."""
        config = WriterConfig(output_dir=tmp_output)
        assert config.output_dir == tmp_output


class TestDatasetWriter:
    """Tests for DatasetWriter class."""

    def test_context_manager_creates_directories(self, tmp_output, test_image):
        """Context manager creates output structure."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            assert (Path(tmp_output) / "images").exists()

    def test_write_creates_png_file(self, tmp_output, test_image):
        """write() creates PNG file with correct name."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            filename = writer.write("A", test_image, "./fonts/test.ttf", index=0)
            assert filename == "0041_test_000.png"
            assert (Path(tmp_output) / "images" / filename).exists()

    def test_filename_format_unicode_hex(self, tmp_output, test_image):
        """Filename uses lowercase unicode hex."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            # U+3042 is あ
            filename = writer.write("あ", test_image, "./fonts/font.ttf", index=0)
            assert filename.startswith("3042_")

    def test_filename_uses_font_stem(self, tmp_output, test_image):
        """Filename uses font file stem (no extension)."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            filename = writer.write("A", test_image, "/path/to/MyFont-Bold.ttf", index=0)
            assert "MyFont-Bold" in filename

    def test_filename_index_padding(self, tmp_output, test_image):
        """Index in filename is zero-padded to 3 digits."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            writer.write("A", test_image, "./fonts/test.ttf", index=0)
            writer.write("A", test_image, "./fonts/test.ttf", index=5)
            writer.write("A", test_image, "./fonts/test.ttf", index=123)

        images = list((Path(tmp_output) / "images").glob("*.png"))
        filenames = [f.name for f in images]
        assert any("_000.png" in f for f in filenames)
        assert any("_005.png" in f for f in filenames)
        assert any("_123.png" in f for f in filenames)

    def test_write_creates_jsonl_record(self, tmp_output, test_image):
        """write() appends record to metadata.jsonl."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            writer.write("A", test_image, "./fonts/test.ttf", index=0)

        jsonl_path = Path(tmp_output) / "metadata.jsonl"
        assert jsonl_path.exists()

        with open(jsonl_path) as f:
            line = f.readline()
            record = json.loads(line)

        assert record["char"] == "A"
        assert record["file"] == "0041_test_000.png"
        assert record["unicode"] == "U+0041"
        assert record["codepoint"] == 65

    def test_jsonl_record_has_all_fields(self, tmp_output, test_image):
        """JSONL record contains all required fields."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            writer.write("X", test_image, "./fonts/Font.ttf", index=3)

        jsonl_path = Path(tmp_output) / "metadata.jsonl"
        with open(jsonl_path) as f:
            record = json.loads(f.readline())

        required_fields = {"file", "char", "unicode", "codepoint", "font_path", "font_family", "font_style"}
        assert set(record.keys()) == required_fields

    def test_unicode_field_format(self, tmp_output, test_image):
        """Unicode field uses U+XXXX format."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            writer.write("Z", test_image, "./fonts/test.ttf", index=0)

        jsonl_path = Path(tmp_output) / "metadata.jsonl"
        with open(jsonl_path) as f:
            record = json.loads(f.readline())

        assert record["unicode"] == "U+005A"  # Z

    def test_finalize_creates_parquet(self, tmp_output, test_image):
        """finalize() converts JSONL to Parquet."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            writer.write("A", test_image, "./fonts/test.ttf", index=0)
            parquet_path = writer.finalize()

        assert parquet_path.exists()
        assert parquet_path.name == "metadata.parquet"

    def test_parquet_contains_jsonl_records(self, tmp_output, test_image):
        """Parquet file contains the JSONL records."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            writer.write("A", test_image, "./fonts/test.ttf", index=0)
            writer.write("B", test_image, "./fonts/test.ttf", index=1)
            parquet_path = writer.finalize()

        table = pq.read_table(str(parquet_path))
        records = table.to_pylist()
        assert len(records) == 2
        assert records[0]["char"] == "A"
        assert records[1]["char"] == "B"

    def test_write_invalid_char_raises_valueerror(self, tmp_output, test_image):
        """write() with multi-char string raises ValueError."""
        config = WriterConfig(output_dir=tmp_output)
        with DatasetWriter(config) as writer:
            with pytest.raises(ValueError):
                writer.write("AB", test_image, "./fonts/test.ttf", index=0)

    def test_rerun_overwrites_jsonl(self, tmp_output, test_image):
        """Second open() overwrites existing metadata.jsonl."""
        config = WriterConfig(output_dir=tmp_output)

        # First run
        with DatasetWriter(config) as writer:
            writer.write("A", test_image, "./fonts/test.ttf", index=0)
            writer.write("B", test_image, "./fonts/test.ttf", index=1)

        # Check first run has 2 records
        jsonl_path = Path(tmp_output) / "metadata.jsonl"
        with open(jsonl_path) as f:
            lines1 = f.readlines()
        assert len(lines1) == 2

        # Second run (should overwrite)
        with DatasetWriter(config) as writer:
            writer.write("C", test_image, "./fonts/test.ttf", index=0)

        # Check second run has only 1 record
        with open(jsonl_path) as f:
            lines2 = f.readlines()
        assert len(lines2) == 1
        record = json.loads(lines2[0])
        assert record["char"] == "C"

    def test_thread_safe_write(self, tmp_output, test_image):
        """Multiple threads can write without corrupting JSONL."""
        config = WriterConfig(output_dir=tmp_output)

        def write_chars(writer, start_char, count):
            for i in range(count):
                char = chr(ord(start_char) + i)
                writer.write(char, test_image, "./fonts/test.ttf", index=i)

        with DatasetWriter(config) as writer:
            threads = [
                Thread(target=write_chars, args=(writer, "A", 5)),
                Thread(target=write_chars, args=(writer, "F", 5)),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Check all records were written without corruption
        jsonl_path = Path(tmp_output) / "metadata.jsonl"
        with open(jsonl_path) as f:
            records = [json.loads(line) for line in f]

        assert len(records) == 10
        # All should be valid JSON
        for rec in records:
            assert "char" in rec
            assert "file" in rec
