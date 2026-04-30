# REVIEW: done
from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont

# ---------------------------------------------------------------------------
# Built-in presets
# Each value is a half-open Unicode range [start, stop), same semantics as range().
# / 各値は半開区間 [start, stop)。range() と同じ。
# ---------------------------------------------------------------------------

_PRESETS: dict[str, tuple[int, int]] = {
    "ascii":        (0x0020, 0x007F),  # printable ASCII (space … ~)
    "digits":       (0x0030, 0x003A),  # 0-9
    "uppercase":    (0x0041, 0x005B),  # A-Z
    "lowercase":    (0x0061, 0x007B),  # a-z
    "hiragana":     (0x3041, 0x3097),  # ぁ-ゖ
    "katakana":     (0x30A1, 0x30F7),  # ァ-ヶ
    "cjk_common":   (0x4E00, 0x9FA6),  # CJK Unified Ideographs (common block)
    "latin_ext":    (0x00C0, 0x0180),  # Latin Extended-A/B
    "greek":        (0x0391, 0x03CA),  # Greek (Α-Ω / α-ω)
    "cyrillic":     (0x0410, 0x0460),  # Cyrillic (А-я)
}

PRESET_NAMES: frozenset[str] = frozenset(_PRESETS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def from_range(start: int, stop: int) -> list[str]:
    """Return all characters in the Unicode range [start, stop).
    / Unicode 範囲 [start, stop) の全文字を返す。"""
    return [chr(cp) for cp in range(start, stop)]


def get_preset(name: str) -> list[str]:
    """Return the character list for a named preset.
    / 名前付きプリセットの文字リストを返す。

    Raises KeyError if the name is not registered.
    """
    if name not in _PRESETS:
        raise KeyError(f"Unknown preset {name!r}. Available: {sorted(_PRESETS)}")
    start, stop = _PRESETS[name]
    return from_range(start, stop)


def supported_codepoints(font_path: str | Path) -> set[int]:
    """Return the set of Unicode codepoints covered by the font.
    / フォントがサポートする Unicode コードポイントの集合を返す。"""
    font = TTFont(str(font_path), lazy=True)
    cmap = font.getBestCmap() or {}
    return set(cmap.keys())


def filter_by_font(
    chars: list[str],
    font_path: str | Path,
) -> tuple[list[str], list[str]]:
    """Split chars into (supported, skipped) based on font glyph coverage.
    / フォントのグリフ有無でリストを (サポート済み, スキップ) に分割する。"""
    codepoints = supported_codepoints(font_path)
    supported, skipped = [], []
    for c in chars:
        (supported if ord(c) in codepoints else skipped).append(c)
    return supported, skipped


def build_charset(
    names: str | list[str],
    font_path: str | Path | None = None,
) -> tuple[list[str], list[str]]:
    """Build a deduplicated character list from one or more preset names
    (or a custom range string ``"U+XXXX-U+YYYY"``), then optionally filter
    by font glyph coverage.
    / プリセット名（複数可）から重複なしの文字リストを組み立て、フォントでフィルタする。

    Args:
        names:      A preset name, a list of preset names, or a range string
                    like ``"U+3041-U+3097"``.
        font_path:  If provided, characters not covered by the font are removed.
                    / 指定時、フォントにグリフがない文字を除外する。

    Returns:
        (chars, skipped) — chars to use, chars removed by font filter.
        font_path が None のとき skipped は空リスト。
    """
    if isinstance(names, str):
        names = [names]

    chars: list[str] = []
    seen: set[str] = set()

    for name in names:
        if name in _PRESETS:
            candidates = get_preset(name)
        elif name.upper().startswith("U+") and "-" in name:
            # custom range string, e.g. "U+3041-U+3097" / カスタム範囲指定
            parts = name.upper().split("-")
            start = int(parts[0][2:], 16)
            stop  = int(parts[1][2:], 16) + 1
            candidates = from_range(start, stop)
        else:
            raise ValueError(
                f"Cannot parse charset spec {name!r}. "
                f"Use a preset name or a range like 'U+3041-U+3097'."
            )
        for c in candidates:
            if c not in seen:
                seen.add(c)
                chars.append(c)

    if font_path is None:
        return chars, []

    return filter_by_font(chars, font_path)
