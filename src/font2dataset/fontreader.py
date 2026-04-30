from dataclasses import dataclass, field, asdict
from pathlib import Path

from fontTools.ttLib import TTFont


@dataclass
class FontMetadata:
    path: str
    family: str | None
    subfamily: str | None
    full_name: str | None
    version: str | None
    manufacturer: str | None
    license: str | None
    weight_class: int | None    # 100–900 (400=Regular, 700=Bold)
    width_class: int | None     # 1–9    (5=Normal)
    is_monospaced: bool
    italic_angle: float
    supported_codepoints: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("supported_codepoints")   # 大きすぎるのでJSONLには含めない
        return d


def _get_name(font: TTFont, name_id: int) -> str | None:
    """name テーブルから文字列を取得する。英語レコードを優先。"""
    record = font["name"].getName(name_id, 3, 1, 0x0409)  # Windows, BMP, English
    if record is None:
        record = font["name"].getName(name_id, 1, 0, 0)   # Mac fallback
    return record.toUnicode() if record is not None else None


def read_font_metadata(font_path: str | Path) -> FontMetadata:
    """フォントファイルからメタデータを読み取る。"""
    font_path = Path(font_path)
    font = TTFont(str(font_path), lazy=True)

    os2 = font.get("OS/2")
    post = font.get("post")
    cmap = font.getBestCmap() or {}

    return FontMetadata(
        path=str(font_path),
        family=_get_name(font, 1),
        subfamily=_get_name(font, 2),
        full_name=_get_name(font, 4),
        version=_get_name(font, 5),
        manufacturer=_get_name(font, 8),
        license=_get_name(font, 13),
        weight_class=os2.usWeightClass if os2 else None,
        width_class=os2.usWidthClass if os2 else None,
        is_monospaced=bool(post.isFixedPitch) if post else False,
        italic_angle=post.italicAngle if post else 0.0,
        supported_codepoints=list(cmap.keys()),
    )


def has_glyph(meta: FontMetadata, char: str) -> bool:
    """フォントが指定文字のグリフを持つか返す。"""
    return ord(char) in meta.supported_codepoints
