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

## 注意事項

- フォントファイルのライセンスに注意（生成データセットの配布可否に影響）
- CJK文字は数千〜数万文字あるため、メモリとディスクの見積もりを事前に行う
- グリフが存在しない文字はスキップし、スキップリストをログに出力する
