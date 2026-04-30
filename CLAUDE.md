# font2dataset

TTF/OTFなどのフォントファイルからOCR・文字認識用の画像データセットを生成するツール。

## 目的

フォントファイルを使って文字画像を大量生成し、OCRモデルや文字認識モデルの学習データを作成する。日本語（ひらがな・カタカナ・漢字）を含む多言語文字集合に対応する。

## ディレクトリ構成

```
font2dataset/
├── src/
│   └── font2dataset/
│       ├── __init__.py
│       ├── renderer.py      # フォントを使った文字画像レンダリング
│       ├── charset.py       # 文字集合の定義・管理
│       ├── augment.py       # 画像拡張（ノイズ・回転など）
│       ├── writer.py        # データセット書き出し（フォルダ / HuggingFace）
│       └── pipeline.py      # 上記を統合するパイプライン
├── config/
│   └── default.yaml         # デフォルト設定
├── script/
│   └── generate.py          # CLIエントリポイント
├── main.py
└── pyproject.toml
```

## 主要コンポーネント

### renderer.py
- `Pillow` を使ってフォントファイルから文字画像を描画
- フォントサイズ・背景色・文字色をパラメータ化
- 複数フォントを一括処理

### charset.py
- 文字集合の定義（ASCII, JIS第一水準, ひらがな, カタカナ など）
- Unicode範囲指定による動的生成
- フォントがグリフを持つか事前チェック（`fonttools` 使用）

### augment.py
- ランダム回転・ノイズ付加・ぼかしなどのオーグメンテーション
- 適用率・強度をYAMLで制御

### writer.py
- 出力形式: `label/image.png` のフォルダ構成 または HuggingFace `datasets` 形式
- メタデータ（フォント名・文字・unicode値）をJSONL/Parquetで保存

### pipeline.py
- charset × fonts × augments の全組み合わせを処理
- `tqdm` で進捗表示
- マルチプロセス対応（`concurrent.futures`）

## 設定ファイル (config/default.yaml)

```yaml
charset: jis_level1        # 使用文字集合
font_dir: ./fonts          # フォントファイルのディレクトリ
image_size: [64, 64]       # 出力画像サイズ (H, W)
font_size: 48              # フォントサイズ (px)
background: white          # 背景色
foreground: black          # 文字色
padding: 4                 # 文字周囲のパディング
output_dir: ./output       # 出力先
output_format: folder      # folder | huggingface
augmentation:
  enabled: false
  rotation_max: 5.0
  noise_std: 0.02
workers: 4                 # 並列ワーカー数
```

## 依存ライブラリ

| ライブラリ | 用途 |
|-----------|------|
| Pillow | 画像描画 |
| fonttools | グリフ存在チェック |
| datasets | HuggingFace形式出力 |
| tqdm | プログレスバー |
| pyyaml | 設定ファイル読み込み |
| numpy | ノイズ生成など |

## 実装優先順位

1. `charset.py` — 文字集合の定義（ひらがな・カタカナ・ASCII）
2. `renderer.py` — Pillowによる基本レンダリング
3. `writer.py` — フォルダ形式への書き出し
4. `pipeline.py` — 上記の統合・バッチ処理
5. `config/default.yaml` + CLIエントリポイント
6. `augment.py` — オーグメンテーション
7. HuggingFace datasets形式への対応

## 使用例 (完成後)

```bash
# デフォルト設定で生成
python script/generate.py --config config/default.yaml

# フォントディレクトリとcharsetを上書き
python script/generate.py --font-dir ./myfonts --charset ascii
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

## 注意事項

- フォントファイルのライセンスに注意（生成データセットの配布可否に影響）
- CJK文字は数千〜数万文字あるため、メモリとディスクの見積もりを事前に行う
- グリフが存在しない文字はスキップし、スキップリストをログに出力する
