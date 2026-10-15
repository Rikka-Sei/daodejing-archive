#!/usr/bin/env python3
"""生成 DaoSong：思源宋体 Regular 的派生字体，补上 font/glyphs/ 里手绘的字。

做法：取固定版本的 Noto Serif SC（可变字体），取定字重 400 得到静态字体；把 SVG 里的手绘轮廓转成 TrueType 曲线，
按 font.yaml 登记的码位加进去（字宽、竖排度量与同字体里的“国”一致）；再把字体族改名、写上版权与授权，存成 TTF。

用法：python3 font/build.py --upstream 上游可变字体.ttf --out DaoSong-Regular.ttf
上游字体的下载与哈希校验由调用方负责（npm run fonts 会做）；这里会再核对一次 SHA-256。
依赖（只在制作字体时用，站点构建不需要）：fonttools、skia-pathops、pyyaml。
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from glyphlib import ASCENT, read_strokes, to_glyph  # noqa: E402

EM = 1000
# 下面这些 name 条目在改名时整体换掉；其余（版权、设计者、授权等）保留
RENAMED = (1, 2, 3, 4, 6, 16, 17, 21, 22, 25)


def load_config(path: Path = HERE / 'font.yaml') -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def glyph_name(cp: int) -> str:
    return f'u{cp:05X}'


def static_instance(font: TTFont, weight: int) -> TTFont:
    """可变字体取定字重得到静态字体；本来就是静态的原样返回。"""
    if 'fvar' not in font:
        return font
    from fontTools.varLib import instancer

    return instancer.instantiateVariableFont(font, {'wght': weight}, inplace=False)


def add_glyph(font: TTFont, cp: int, glyph) -> str:
    """把字形加进字体：glyf、字宽、竖排度量、字符映射。竖排的字符原点取与“国”相同的位置。"""
    name = glyph_name(cp)
    glyph.recalcBounds(font['glyf'])
    order = font.getGlyphOrder()
    if name in order:
        raise ValueError(f'{name} 已在字体里')
    order.append(name)
    font.setGlyphOrder(order)
    font['glyf'].glyphOrder = order
    font['glyf'].glyphs[name] = glyph
    font['hmtx'][name] = (EM, glyph.xMin)
    if 'vmtx' in font:
        origin = vertical_origin(font)
        font['vmtx'][name] = (EM, origin - glyph.yMax)
    # 码位加进所有能放下的 Unicode 子表（第 12 格式覆盖全部平面；第 4 格式只有基本平面）
    placed = False
    for table in font['cmap'].tables:
        if table.isUnicode() and table.format in (12, 13) and table.platEncID in (4, 10):
            table.cmap[cp] = name
            placed = True
    if not placed:
        t = CmapSubtable.newSubtable(12)
        # 第 12 格式的表要装下全部字符，所以带上已有的映射
        t.platformID, t.platEncID, t.language, t.cmap = 3, 10, 0, {**font.getBestCmap(), cp: name}
        font['cmap'].tables.append(t)
    return name


def vertical_origin(font: TTFont) -> int:
    """竖排时字形顶端到原点的位置：用“国”的 tsb 与 yMax 之和；取不到时用 ascent 880。"""
    cmap = font.getBestCmap()
    ref = cmap.get(0x56FD)
    if ref and 'vmtx' in font:
        g = font['glyf'][ref]
        g.recalcBounds(font['glyf'])
        return font['vmtx'][ref][1] + g.yMax
    return ASCENT


def rename(font: TTFont, cfg: dict) -> None:
    """换名：字体族、全名、PostScript 名、唯一标识都换成 DaoSong；版权、设计者、授权保留并补上本项目的说明。"""
    family, style = cfg['family'], cfg['style']
    full = f'{family} {style}'
    name = font['name']
    name.names = [r for r in name.names if r.nameID not in RENAMED and not (r.nameID > 255)]
    version = f"Version {cfg['version']}"
    up = cfg['upstream']['name']
    for pid, eid, lid in ((3, 1, 0x409),):
        for nid, text in (
            (1, family),
            (2, style),
            (3, f"{cfg['version']};{cfg['vendor']};{family}-{style}"),
            (4, full),
            (6, f'{family}-{style}'),
        ):
            name.setName(text, nid, pid, eid, lid)
        name.setName(version, 5, pid, eid, lid)
        name.setName(
            f"{up} Regular 的派生字体，补绘了 {len(cfg['glyphs'])} 个生僻字（" + ''.join(g['char'] for g in cfg['glyphs']) + '）。'
            ' A modified version of Noto Serif SC Regular with hand-drawn additions.',
            10, pid, eid, lid,
        )
        name.setName(
            'Copyright 2012 Google Inc.; (c) 2017-2024 Adobe (http://www.adobe.com/); additions (c) 2026 Rikka-Sei.',
            0, pid, eid, lid,
        )
    # 商标声明里的 Noto 是 Google 的商标，派生字体不再沿用
    name.names = [r for r in name.names if r.nameID != 7]
    font['OS/2'].achVendID = cfg['vendor']
    font['OS/2'].usWeightClass = 400


def build(upstream: Path, out: Path, cfg: dict | None = None, root: Path = HERE) -> TTFont:
    cfg = cfg or load_config(root / 'font.yaml')
    want = cfg['upstream'].get('sha256')
    got = hashlib.sha256(upstream.read_bytes()).hexdigest()
    if want and got != want:
        raise SystemExit(f'上游字体校验失败：{upstream}\n  应为 {want}\n  实为 {got}')
    font = static_instance(TTFont(upstream, recalcTimestamp=False), cfg['upstream'].get('weight', 400))
    font.recalcTimestamp = False  # 修改时间沿用上游：同样的输入得到逐字节相同的字体
    have = set(font.getBestCmap())
    for g in cfg['glyphs']:
        cp = g['cp']
        if cp in have:
            raise SystemExit(f"U+{cp:04X} 上游字体里已经有了，不必再补：{g['char']}")
        strokes = [d for _, d in read_strokes(root / g['svg'])]
        if not strokes:
            raise SystemExit(f"{g['svg']} 里没有笔画")
        add_glyph(font, cp, to_glyph(strokes))
    rename(font, cfg)
    font['head'].fontRevision = float(cfg['version'].rsplit('.', 1)[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(out)
    return font


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--upstream', required=True, type=Path, help='固定版本的 NotoSerifSC[wght].ttf')
    ap.add_argument('--out', required=True, type=Path, help='生成的 TTF')
    a = ap.parse_args()
    f = build(a.upstream, a.out)
    print(f'{a.out}  {a.out.stat().st_size // 1024} KB  {len(f.getGlyphOrder())} 字形')


if __name__ == '__main__':
    main()
