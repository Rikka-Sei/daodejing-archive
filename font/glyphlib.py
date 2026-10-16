"""SVG 手绘字形 → 字体轮廓：读 SVG 里的各条笔画，合并成一个轮廓，转成 CFF（PostScript）的三次曲线。"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pathops
from fontTools.misc.psCharStrings import T2CharString
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path

SVG_NS = '{http://www.w3.org/2000/svg}'
ASCENT = 880  # 字身框：基线以上 880，以下 120（与思源宋体一致）
EM = 1000


def read_strokes(svg: str | Path) -> list[tuple[str, str]]:
    """读出 SVG 里所有 <path> 的 (id, d)。"""
    root = ET.parse(svg).getroot()
    return [(p.get('id') or '', p.get('d') or '') for p in root.iter(f'{SVG_NS}path') if p.get('d')]


def _union(parts: list[pathops.Path]) -> pathops.Path:
    acc = pathops.Path()
    for p in parts:
        acc = pathops.op(acc, p, pathops.PathOp.UNION, fix_winding=True)
    return acc



def outline(strokes: list[str]) -> pathops.Path:
    """SVG 路径（y 向下）合并成一个轮廓，翻成字体坐标（y 向上，基线在 880 处）。
    上下一翻，轮廓方向也跟着反了，所以再反过来：外框逆时针、内框顺时针，是 CFF（PostScript）要的方向。"""
    merged = _union([_path(d) for d in strokes])
    out = pathops.Path()
    merged.draw(TransformPen(ReverseContourPen(out.getPen()), (1, 0, 0, -1, 0, ASCENT)))
    return out


def to_charstring(strokes: list[str], private=None, global_subrs=None) -> T2CharString:
    """手绘笔画 → CFF 字形（字宽 1000，不带 hinting；hinting 由 build.py 统一加）。"""
    pen = T2CharStringPen(EM, None)
    outline(strokes).draw(pen)
    return pen.getCharString(private=private, globalSubrs=global_subrs)


def _path(d: str) -> pathops.Path:
    p = pathops.Path()
    parse_path(d, p.getPen())
    return p


def write_svg(file: str | Path, strokes: list[tuple[str, str]], *, title: str) -> None:
    """写出手绘字形的 SVG：1000×1000 的字身框，基线在 y=880，每笔一条 <path>。"""
    body = '\n'.join(f'  <path id="{i}" d="{d}"/>' for i, d in strokes)
    Path(file).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="500" height="500">\n'
        f'  <title>{title}</title>\n'
        f'  <line x1="0" y1="{ASCENT}" x2="1000" y2="{ASCENT}" stroke="#c33" stroke-width="1" fill="none"/>\n'
        f'{body}\n</svg>\n',
        encoding='utf-8',
    )
