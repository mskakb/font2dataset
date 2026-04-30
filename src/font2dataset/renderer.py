from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass
class RenderConfig:
    image_size: tuple[int, int] = (64, 64)  # (H, W)
    font_size: int = 48
    background: str = "white"
    foreground: str = "black"
    padding: int = 4


class FontRenderer:
    def __init__(self, font_path: str | Path, config: RenderConfig | None = None):
        self.font_path = Path(font_path)
        self.config = config or RenderConfig()
        self._font = ImageFont.truetype(str(self.font_path), self.config.font_size)

    def render(self, char: str) -> Image.Image:
        """1文字を描画してPIL Imageとして返す。"""
        cfg = self.config
        h, w = cfg.image_size
        img = Image.new("RGB", (w, h), color=cfg.background)
        draw = ImageDraw.Draw(img)

        bbox = draw.textbbox((0, 0), char, font=self._font)
        char_w = bbox[2] - bbox[0]
        char_h = bbox[3] - bbox[1]

        x = (w - char_w) // 2 - bbox[0]
        y = (h - char_h) // 2 - bbox[1]

        draw.text((x, y), char, font=self._font, fill=cfg.foreground)
        return img

    def render_batch(self, chars: list[str]) -> list[tuple[str, Image.Image]]:
        """複数文字を一括描画する。(char, image) のリストを返す。"""
        return [(c, self.render(c)) for c in chars]
