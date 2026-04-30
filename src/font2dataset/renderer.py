# REVIEW: done
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont

# Bounding box type: (left, top, right, bottom) relative to anchor (0, 0)
BBox = tuple[int, int, int, int]


@dataclass
class RenderConfig:
    image_size: tuple[int, int] = (64, 64)  # (H, W)
    font_size: int = 48
    background: str = "white"
    foreground: str = "black"
    padding: int = 4
    overflow: Literal["skip", "shrink", "scale"] = "skip"
    min_font_size: int = 8              # lower bound for overflow="shrink" / shrink時の下限
    bbox_method: Literal["textbbox", "pixel"] = "textbbox"
    resample: Image.Resampling = Image.Resampling.LANCZOS


class FontRenderer:
    def __init__(self, font_path: str | Path, config: RenderConfig | None = None):
        self.font_path = Path(font_path)
        self.config = config or RenderConfig()
        self._font = ImageFont.truetype(str(self.font_path), self.config.font_size)

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.font_path), size)

    # ------------------------------------------------------------------
    # Bounding box
    # ------------------------------------------------------------------

    def _char_size_textbbox(
        self, char: str, font: ImageFont.FreeTypeFont
    ) -> tuple[int, int, BBox]:
        """Return ink bounds (w, h, bbox) using Pillow's textbbox()."""
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        bbox: BBox = dummy.textbbox((0, 0), char, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox

    def _char_size_pixel(
        self, char: str, font: ImageFont.FreeTypeFont
    ) -> tuple[int, int, BBox]:
        """Return ink bounds (w, h, bbox) by detecting non-background pixels.
        / 実際に描画した画像から非背景ピクセルを検出して bbox を返す。

        The returned bbox uses the same coordinate space as textbbox
        (i.e. relative to anchor (0, 0)), so it is a drop-in replacement.
        """
        # Estimate canvas size from textbbox to avoid clipping / キャンバスサイズをtextbboxで見積もる
        _, _, tb = self._char_size_textbbox(char, font)
        margin = 16
        canvas_w = max(tb[2] - tb[0], 1) + margin * 2
        canvas_h = max(tb[3] - tb[1], 1) + margin * 2

        bg_rgb = np.array(ImageColor.getrgb(self.config.background), dtype=np.uint8)
        tmp_img = Image.new("RGB", (canvas_w, canvas_h), color=self.config.background)
        draw = ImageDraw.Draw(tmp_img)
        # Place the anchor (0, 0) at canvas position (margin, margin)
        draw.text((margin - tb[0], margin - tb[1]), char, font=font, fill=self.config.foreground)

        arr = np.array(tmp_img)
        mask = ~np.all(arr == bg_rgb, axis=2)

        if not mask.any():
            return 0, 0, (0, 0, 0, 0)

        rows = np.where(np.any(mask, axis=1))[0]
        cols = np.where(np.any(mask, axis=0))[0]

        # Convert canvas coordinates back to anchor-relative coordinates
        # canvas_x = anchor_x + (margin - tb[0])  →  anchor_x = canvas_x - margin + tb[0]
        left   = int(cols[0])  - margin + tb[0]
        right  = int(cols[-1]) - margin + tb[0] + 1
        top    = int(rows[0])  - margin + tb[1]
        bottom = int(rows[-1]) - margin + tb[1] + 1

        bbox: BBox = (left, top, right, bottom)
        return right - left, bottom - top, bbox

    def _char_size(
        self, char: str, font: ImageFont.FreeTypeFont
    ) -> tuple[int, int, BBox]:
        """Dispatch to the configured bbox method."""
        if self.config.bbox_method == "pixel":
            return self._char_size_pixel(char, font)
        return self._char_size_textbbox(char, font)

    # ------------------------------------------------------------------
    # Overflow handling
    # ------------------------------------------------------------------

    def _fits_with_font(self, char: str, font: ImageFont.FreeTypeFont) -> bool:
        """Return True if the character fits within the padded image area."""
        cfg = self.config
        h, w = cfg.image_size
        char_w, char_h, _ = self._char_size(char, font)
        return char_w <= w - cfg.padding * 2 and char_h <= h - cfg.padding * 2

    def fits(self, char: str) -> bool:
        """Return True if the character fits within the padded image area.
        / padding込みの画像領域に収まるか返す。"""
        return self._fits_with_font(char, self._font)

    def _shrink_font(self, char: str) -> ImageFont.FreeTypeFont | None:
        """Find the largest font size <= font_size at which the character fits.
        / 収まる最大のフォントサイズを探して返す。見つからなければ None。"""
        for size in range(self.config.font_size - 1, self.config.min_font_size - 1, -1):
            font = self._load_font(size)
            if self._fits_with_font(char, font):
                return font
        return None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def calc_xy(
        self, char: str, font: ImageFont.FreeTypeFont | None = None
    ) -> tuple[int, int]:
        """Return the draw coordinate (x, y) that centers the character
        within the padded image area. / 文字を中央配置する描画座標を返す。"""
        cfg = self.config
        h, w = cfg.image_size
        char_w, char_h, bbox = self._char_size(char, font or self._font)
        inner_w = w - cfg.padding * 2
        inner_h = h - cfg.padding * 2
        x = cfg.padding + (inner_w - char_w) // 2 - bbox[0]
        y = cfg.padding + (inner_h - char_h) // 2 - bbox[1]
        return x, y

    def _render_scale(self, char: str) -> Image.Image:
        """Render at the natural character size, then downscale to image_size
        while preserving aspect ratio (letterbox with background fill).
        / アスペクト比を保ったまま image_size に収める。余白は background 色で埋める。"""
        cfg = self.config
        char_w, char_h, bbox = self._char_size(char, self._font)
        tmp_w = char_w + cfg.padding * 2
        tmp_h = char_h + cfg.padding * 2
        tmp_img = Image.new("RGB", (tmp_w, tmp_h), color=cfg.background)
        draw = ImageDraw.Draw(tmp_img)
        draw.text((cfg.padding - bbox[0], cfg.padding - bbox[1]), char, font=self._font, fill=cfg.foreground)

        h, w = cfg.image_size
        # Scale so the longer side fills the output / 長辺が収まるスケールを選ぶ
        scale = min(w / tmp_w, h / tmp_h)
        new_w, new_h = int(tmp_w * scale), int(tmp_h * scale)
        resized = tmp_img.resize((new_w, new_h), cfg.resample)

        out = Image.new("RGB", (w, h), color=cfg.background)
        out.paste(resized, ((w - new_w) // 2, (h - new_h) // 2))
        return out

    def render(self, char: str) -> Image.Image | None:
        """Render a single character and return a PIL Image.

        overflow="skip"   : return None if the character does not fit.
        overflow="shrink" : reduce font size until it fits; return None if
                            min_font_size is reached without success.
        overflow="scale"  : render at natural size then downscale to image_size,
                            preserving aspect ratio.
        """
        cfg = self.config
        font = self._font

        if not self.fits(char):
            if cfg.overflow == "skip":
                return None
            elif cfg.overflow == "shrink":
                font = self._shrink_font(char)
                if font is None:
                    return None
            elif cfg.overflow == "scale":
                return self._render_scale(char)

        h, w = cfg.image_size
        img = Image.new("RGB", (w, h), color=cfg.background)
        draw = ImageDraw.Draw(img)
        x, y = self.calc_xy(char, font)
        draw.text((x, y), char, font=font, fill=cfg.foreground)
        return img

    def render_batch(self, chars: list[str]) -> list[tuple[str, Image.Image]]:
        """Render multiple characters, silently skipping any that return None.
        / 複数文字を一括描画する。None になった文字はスキップする。"""
        results = []
        for c in chars:
            img = self.render(c)
            if img is not None:
                results.append((c, img))
        return results
