import base64
import io
import math
import os
from fontTools import subset
from fontTools.ttLib import TTFont

# Palette constants
BG1 = "#1a0b3a"
BG2 = "#0e0620"
PURPLE = "#9955e7"
LIGHT = "#c9a8ff"
PALE = "#efe4ff"
DIM = "#7a5fb0"
DEEP = "#4b2a8a"

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bricolage-bold.ttf")

_font = None
_cmap = None
_upem = None
_hmtx = None


def _get_font_data():
    global _font, _cmap, _upem, _hmtx
    if _font is None:
        _font = TTFont(FONT_PATH)
        _cmap = _font.getBestCmap()
        _upem = _font["head"].unitsPerEm
        _hmtx = _font["hmtx"]
    return _cmap, _upem, _hmtx


def xml_escape(text: str) -> str:
    """Escapes XML entities (&, <, >)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_width(text: str, size: float) -> float:
    """Exact width in px from the font's hmtx advance widths and unitsPerEm."""
    cmap, upem, hmtx = _get_font_data()
    total = 0
    for char in text:
        cp = ord(char)
        glyph_name = cmap.get(cp, ".notdef")
        advance, _ = hmtx[glyph_name]
        total += advance
    return round(total * size / upem, 2)


def font_css(text: str) -> str:
    """Subset bricolage-bold.ttf to characters in text, returning <style> with base64 TTF."""
    options = subset.Options()
    options.notdef_glyph = True
    font = subset.load_font(FONT_PATH, options)
    subsetter = subset.Subsetter(options=options)
    chars = set(text) | {" "}
    subsetter.populate(text="".join(chars))
    subsetter.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        f"<style>"
        f"@font-face{{font-family:'Bri';src:url(data:font/ttf;base64,{b64}) format('truetype');}}"
        f"text{{font-family:'Bri',sans-serif;}}"
        f"</style>"
    )


def cube(cx: float, cy: float, s: float, top: str, left: str, right: str) -> str:
    """Returns SVG for an isometric cube centered at cx, cy with edge size s."""
    dx = s * 0.8660254037844386
    dy = s * 0.5
    p_center = f"{cx:.2f},{cy:.2f}"
    p_top = f"{cx:.2f},{cy - s:.2f}"
    p_bottom = f"{cx:.2f},{cy + s:.2f}"
    p_top_left = f"{cx - dx:.2f},{cy - dy:.2f}"
    p_top_right = f"{cx + dx:.2f},{cy - dy:.2f}"
    p_bot_left = f"{cx - dx:.2f},{cy + dy:.2f}"
    p_bot_right = f"{cx + dx:.2f},{cy + dy:.2f}"

    top_poly = f'<polygon points="{p_center} {p_top_right} {p_top} {p_top_left}" fill="{top}"/>'
    left_poly = f'<polygon points="{p_center} {p_top_left} {p_bot_left} {p_bottom}" fill="{left}"/>'
    right_poly = f'<polygon points="{p_center} {p_bottom} {p_bot_right} {p_top_right}" fill="{right}"/>'
    return f"{top_poly}\n{left_poly}\n{right_poly}"


def svg(
    w: int,
    h: int,
    body: str,
    text_for_font: str = "",
    extra_defs: str = "",
    extra_css: str = "",
    card_attrs: str = "",
) -> str:
    """Returns the full SVG string with card gradient, glow filter, font style, and rounded card."""
    style_tag = font_css(text_for_font) if text_for_font else ""
    extra_style = f"<style>{extra_css}</style>" if extra_css else ""

    defs_content = (
        f'<linearGradient id="card-grad" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="{BG1}"/>'
        f'<stop offset="100%" stop-color="{BG2}"/>'
        f"</linearGradient>\n"
        f'<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feGaussianBlur stdDeviation="3" result="blur"/>'
        f'<feMerge>'
        f'<feMergeNode in="blur"/>'
        f'<feMergeNode in="SourceGraphic"/>'
        f"</feMerge>"
        f"</filter>\n"
        f"{extra_defs}"
    )

    card_rect = (
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="18" '
        f'fill="url(#card-grad)" stroke="{PURPLE}" stroke-opacity="0.4" stroke-width="1.5">'
        f"{card_attrs}</rect>"
        if card_attrs
        else f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="18" '
        f'fill="url(#card-grad)" stroke="{PURPLE}" stroke-opacity="0.4" stroke-width="1.5"/>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
        f"<defs>\n{defs_content}\n</defs>\n"
        f"{style_tag}\n"
        f"{extra_style}\n"
        f"{card_rect}\n"
        f"{body}\n"
        f"</svg>"
    )


if __name__ == "__main__":
    assert text_width("test", 30) > 0
    c = cube(50, 50, 10, LIGHT, PURPLE, DEEP)
    assert c.count("<polygon") == 3
    print("common.py self-check passed")
