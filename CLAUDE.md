# font2dataset

A tool for generating image datasets for OCR and character recognition from TTF/OTF font files.
/ TTF/OTFなどのフォントファイルからOCR・文字認識用の画像データセットを生成するツール。

## Purpose / 目的

Batch-generate character images from font files to create training data for OCR and
character recognition models. Supports multilingual character sets including Japanese
(hiragana, katakana, kanji).
/ フォントファイルを使って文字画像を大量生成し、OCRモデルや文字認識モデルの学習データを作成する。

## Directory Structure / ディレクトリ構成

```
font2dataset/
├── src/
│   └── font2dataset/
│       ├── __init__.py
│       ├── renderer.py      # character image rendering from fonts
│       ├── charset.py       # character set definition and management
│       ├── augment.py       # image augmentation (noise, rotation, etc.)
│       ├── writer.py        # dataset output (folder / HuggingFace)
│       └── pipeline.py      # integrates the above into a batch pipeline
├── config/
│   └── default.yaml         # default configuration
├── notebooks/               # learning notebooks
├── script/
│   └── generate.py          # CLI entry point
├── main.py
└── pyproject.toml
```

## Key Components / 主要コンポーネント

### renderer.py
- Renders character images from font files using Pillow
- Parameterises font size, background colour, foreground colour, and padding
- Handles overflow via `skip` / `shrink` / `scale` modes

### charset.py
- Defines character sets (ASCII, hiragana, katakana, CJK, etc.)
- Accepts preset names, Unicode range strings (`"U+XXXX-U+YYYY"`), or literal strings
- Filters characters by font glyph coverage via `filter_by_font`
- Note: `jis_level1` is **not** a built-in preset; use `cjk_common` or provide a literal list.

### augment.py
- Augmentations: random rotation, noise, blur, etc.
- Probability and intensity controlled via config YAML

### writer.py
- Output layout: **flat** — all images under `output/images/`, index file alongside.
- File naming: `{unicode_hex}_{font_stem}_{index}.png`
  (e.g. `3042_NotoSansJP-Regular_000.png`)
- Record format: **JSONL during generation** (streaming append), converted to **Parquet on completion**.
- Minimum record fields per image:
  ```json
  {"file": "3042_NotoSansJP-Regular_000.png", "char": "あ", "unicode": "U+3042", "codepoint": 12354, "font_path": "fonts/NotoSansJP-Regular.ttf"}
  ```
- Does **not** store font attribute metadata (family name, weight, license, etc.)
- HuggingFace `datasets` format: future work (priority 7).

### pipeline.py
- Processes all combinations of charset × fonts × augmentations
- Progress via `tqdm`; parallel execution via `concurrent.futures`

## Configuration File / 設定ファイル (config/default.yaml)

```yaml
charset: hiragana          # preset name, "U+XXXX-U+YYYY", or literal string
font_dir: ./fonts          # directory containing font files
image_size: [64, 64]       # output image size (H, W)
font_size: 48              # font size (px)
background: white          # background colour
foreground: black          # foreground colour
padding: 4                 # padding around the glyph
overflow: skip             # skip | shrink | scale
output_dir: ./output       # output destination
output_format: folder      # folder | huggingface
augmentation:
  enabled: false
  rotation_max: 5.0
  noise_std: 0.02
  seed: 42                 # random seed for reproducibility
workers: 4                 # parallel worker count
```

## Dependencies / 依存ライブラリ

| Library | Purpose |
|---------|---------|
| Pillow | Image rendering |
| fonttools | Glyph existence check |
| datasets | HuggingFace format output |
| tqdm | Progress bar |
| pyyaml | Config file loading |
| numpy | Noise generation, etc. |

## Implementation Status / 実装状況

| Priority | Module | Status |
|----------|--------|--------|
| 1 | `charset.py` | ✅ Done |
| 2 | `renderer.py` | ✅ Done |
| 3 | `writer.py` | ✅ Done |
| 4 | `pipeline.py` | Not started |
| 5 | `config/default.yaml` + CLI | Not started |
| 6 | `augment.py` | Not started |
| 7 | HuggingFace datasets output | Not started |

## Usage Example (after completion) / 使用例（完成後）

```bash
# Generate with default config
python script/generate.py --config config/default.yaml

# Override font directory and charset
python script/generate.py --font-dir ./myfonts --charset hiragana
```

## Review Status Convention

Every source file carries a status header immediately after any module-level docstring.
/ 各ソースファイルはモジュールdocstringの直後にステータスヘッダを持つ。

```python
# REVIEW: pending   # human-written, not yet reviewed by Claude / 人手で作成、未レビュー
# REVIEW: done      # reviewed and approved by Claude / Claudeレビュー済み
```

Rules / 規則:
- New files written by hand start with `# REVIEW: pending`.
- After a Claude review pass, the header is updated to `# REVIEW: done`.
- Files with no header are treated as `pending`.

## Language Convention

- **Code** (identifiers, docstrings, type hints): English only.
- **Comments and Markdown**: English as the primary language; Japanese may be added as supplementary annotation. / コメントやMarkdownは英語を主体とし、補助的に日本語を追記してよい。
- **Notebook output** (plot titles, axis labels, print statements): English only.

## Pipeline Rules

### ① Reproducibility / 再現性の保証
Given the same config file and the same font directory, dataset generation must always
produce the same output. Any stochastic step (e.g. augmentation) must accept an explicit
random seed via the config.
/ 同じ設定ファイルと同じフォントディレクトリを与えれば、常に同じデータセットが生成されること。
乱数を使う処理はシードを設定ファイルで指定可能にする。

### ② Batch Failure Policy / バッチ処理の障害方針
Individual rendering failures (missing glyph, corrupt font, etc.) are logged and skipped.
The pipeline must not abort on a single failure.
/ 個別のレンダリング失敗はログに記録してスキップする。パイプライン全体は止めない。

### ③ Config as Single Source of Truth / 設定ファイルが唯一の真実
All generation parameters (image size, font size, charset, etc.) must come from the config
file. Do not hardcode parameter values in pipeline or rendering code.
/ 画像サイズ・フォントサイズ・文字集合などのパラメータはすべて設定ファイル経由で指定する。コード内にハードコードしない。

### ④ Output File Naming / 出力ファイルの命名規則
Generated image filenames must be unique and traceable. Use the format:
```
{unicode_hex}_{font_stem}_{index}.png
```
Example: `3042_NotoSansJP-Regular_000.png` → U+3042 (あ), font file `NotoSansJP-Regular.ttf`, index 0.
/ ファイル名から Unicode・フォント・連番を追跡できるようにする。

## Dataset Design Policy

- **No metadata management.** Font attribute metadata (family name, weight, license, etc.)
  is not stored by this tool. Metadata management is left to the repository user.
  / フォントのメタデータ管理はこのツールでは行わない。管理はリポジトリ利用者に委ねる。
- **Font file traceability.** Each generated image record must store the path (or filename)
  of the font file used for rendering, so the source can be traced later.
  / 生成画像には描画に使用したフォントファイルのパス（またはファイル名）を必ず記録する。

## Notes / 注意事項

- Be mindful of font file licences — they affect whether the generated dataset can be distributed.
  / フォントファイルのライセンスに注意（生成データセットの配布可否に影響）。
- CJK character sets contain thousands to tens of thousands of characters; estimate memory
  and disk usage in advance. / CJK文字は数千〜数万文字あるため、メモリとディスクの見積もりを事前に行う。
- Characters without a glyph are skipped; the skip list is written to the log.
  / グリフが存在しない文字はスキップし、スキップリストをログに出力する。
