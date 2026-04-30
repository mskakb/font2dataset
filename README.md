# font2dataset

A tool for generating image datasets for OCR and character recognition from TTF/OTF font files.

TTF/OTFなどのフォントファイルからOCR・文字認識用の画像データセットを生成するツール。

## Features

- **Batch character image generation** from font files
- **Multilingual support**: ASCII, hiragana, katakana, CJK, Greek, Cyrillic, and custom character sets
- **Flexible rendering**: configurable image size, font size, colors, padding
- **Overflow handling**: skip, shrink, or scale glyphs that don't fit
- **Parallel processing**: multi-threaded font processing with progress tracking
- **Reproducible output**: deterministic generation with configurable random seeds
- **Structured metadata**: JSONL records converted to Parquet format
- **Thread-safe operation**: safe concurrent writes to dataset files
- **Comprehensive tests**: 65 pytest tests validating all functionality

## Installation

### Requirements
- Python 3.11+
- pip

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd font2dataset

# Install in development mode with all dependencies
pip install -e .

# (Optional) Install dev tools for testing
pip install -e ".[dev]"
```

## Quick Start

### Using the CLI

```bash
# Generate with default config
python script/generate.py --config config/default.yaml

# Override specific settings
python script/generate.py --font-dir ./fonts --charset hiragana --workers 4

# Enable verbose logging
python script/generate.py --config config/default.yaml --verbose
```

### Using Python code directly

```python
from font2dataset.pipeline import PipelineConfig, run_pipeline

config = PipelineConfig(
    charset="digits",
    font_dir="./fonts",
    output_dir="./output",
    workers=2,
)

result = run_pipeline(config)
print(f"Generated {result.total_images} images")
print(f"Output: {result.parquet_path}")
```

## Configuration

Edit `config/default.yaml` or pass CLI arguments:

```yaml
charset: ascii              # preset name, Unicode range, or literal string
font_dir: ./fonts           # directory containing TTF/OTF files
output_dir: ./output        # output directory
image_size: [64, 64]        # [height, width] in pixels
font_size: 48               # font size in pixels
background: white           # background color (PIL color name)
foreground: black           # text color
padding: 4                  # padding around glyph (pixels)
overflow: skip              # handling for oversized glyphs: skip | shrink | scale
workers: 4                  # number of parallel worker threads
```

## Character Set Specifications

Supported formats for `charset`:

### Preset names
```python
"digits"        # 0-9
"ascii"         # printable ASCII
"uppercase"     # A-Z
"lowercase"     # a-z
"hiragana"      # Japanese hiragana
"katakana"      # Japanese katakana
"cjk_common"    # Common CJK characters
"greek"         # Greek letters
"cyrillic"      # Cyrillic letters
```

### Unicode ranges
```python
"U+0041-U+005A"  # A-Z (26 characters)
```

### Literal characters
```python
"ABC123"         # specific characters as string
```

### Mixed specifications
```python
["digits", "+-*/", "U+0041-U+005A"]  # combine multiple specs
```

## Output Format

### Directory structure
```
output/
├── images/                          # all PNG files (flat)
│   ├── 0041_Font-Regular_000.png    # U+0041 'A'
│   ├── 0042_Font-Regular_000.png    # U+0042 'B'
│   └── ...
├── metadata.jsonl                   # per-image records (during generation)
└── metadata.parquet                 # final Parquet dataset (after completion)
```

### Metadata record format (JSON)
```json
{
  "file": "0041_Font-Regular_000.png",
  "char": "A",
  "unicode": "U+0041",
  "codepoint": 65,
  "font_path": "./fonts/Font-Regular.ttf"
}
```

## Project Structure

```
font2dataset/
├── src/font2dataset/          # main package
│   ├── __init__.py
│   ├── charset.py             # character set definitions
│   ├── renderer.py            # image rendering engine
│   ├── writer.py              # dataset file I/O (JSONL + Parquet)
│   └── pipeline.py            # batch processing orchestration
├── config/
│   └── default.yaml           # default configuration
├── notebooks/                 # Jupyter notebooks for learning
│   ├── 01_font_structure.ipynb
│   ├── 02_rendering.ipynb
│   ├── 03_charset.ipynb
│   ├── 04_writer.ipynb
│   └── 05_pipeline.ipynb
├── script/
│   └── generate.py            # CLI entry point
├── tests/                     # pytest test suite (65 tests)
│   ├── conftest.py
│   ├── test_charset.py
│   ├── test_renderer.py
│   ├── test_writer.py
│   ├── test_pipeline.py
│   └── test_generate.py
├── fonts/                     # sample fonts (Apache-licensed)
├── main.py                    # simple example script
├── pyproject.toml             # Python project metadata
└── README.md
```

## Testing

Run the complete test suite:

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src/font2dataset --cov-report=html

# Run specific test file
pytest tests/test_renderer.py -v

# Run specific test class
pytest tests/test_writer.py::TestDatasetWriter -v
```

## Design Principles

1. **Reproducibility**: Same config + fonts → same output (deterministic ordering)
2. **Graceful degradation**: Font failures are logged; pipeline continues
3. **Single source of truth**: All parameters come from config (no hardcoding)
4. **Traceable output**: File names encode unicode, font, and index
5. **Thread-safe**: Concurrent writes protected by locks

## Dependencies

### Core
- **Pillow** — Image rendering
- **fonttools** — Font glyph introspection
- **pyarrow** — Parquet file I/O
- **pyyaml** — Configuration file parsing
- **tqdm** — Progress bars
- **numpy** — Array operations

### Development
- **pytest** — Test framework
- **pytest-cov** — Code coverage
- **jupyter** — Interactive notebooks
- **matplotlib** — Visualization

## Examples

### Generate ASCII digits dataset

```bash
python script/generate.py \
  --charset digits \
  --font-dir ./fonts \
  --output-dir ./ascii_output
```

### Generate Japanese hiragana with multiple fonts

```bash
python script/generate.py \
  --charset hiragana \
  --font-dir ./my_fonts \
  --image-size 96 96 \
  --font-size 72 \
  --workers 4
```

### Generate custom character set

```bash
python script/generate.py \
  --charset "ABCD+-*/" \
  --font-dir ./fonts
```

## Performance

- **Rendering**: ~100-500 images/sec per font (depends on image size, font size)
- **Parallel processing**: Linear speedup up to ~4 workers (I/O bound on some systems)
- **Memory**: ~500MB for 50K images with metadata

## Limitations

- **Font glyph dependencies**: Character generation requires fonts with appropriate glyphs
- **Flat output only**: All images stored in single directory (no subdirectories)
- **Metadata scope**: Only records file path, not font family/weight/license

## Future Work

- HuggingFace datasets integration
- Image augmentation (rotation, noise, blur)
- Streaming Parquet writes
- GPU-accelerated rendering

## License

See individual font files for their licenses. Generated datasets inherit restrictions of source fonts.

## Troubleshooting

### "ModuleNotFoundError: No module named 'font2dataset'"
```bash
pip install -e .
```

### "No fonts found" warning
```bash
# Verify fonts directory exists and contains .ttf/.otf files
ls fonts/
```

### Tests fail
```bash
# Reinstall in development mode
pip install -e ".[dev]"
pytest tests/ -v
```

## Contributing

Contributions welcome! Please ensure:
- All tests pass: `pytest tests/ -v`
- Code follows existing style
- New features include tests
