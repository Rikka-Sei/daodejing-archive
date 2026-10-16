#!/usr/bin/env python3
"""生成 DaoSong：思源宋体 Regular 的派生字体，补上 font/glyphs/ 里手绘的字。

做法：取固定版本的 Noto Serif SC Regular（Adobe 发布的静态 OTF，CFF 轮廓，带 hinting）；把 SVG 里的手绘轮廓
转成 CFF 字形，按 font.yaml 登记的码位加进去（字宽、竖排度量与同字体里的“国”一致），用 AFDKO 的 otfautohint
只给新加的字补上 hinting；再把字体族改名、写上版权与授权，存成 OTF。

用法：python3 font/build.py --upstream NotoSerifSC-Regular.otf --out DaoSong-Regular.otf
上游字体的下载与哈希校验由调用方负责（npm run fonts 会做）；这里会再核对一次 SHA-256。
依赖（只在制作字体时用，站点构建不需要）：fonttools、skia-pathops、pyyaml、afdko。
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from glyphlib import ASCENT, EM, read_strokes, to_charstring  # noqa: E402

# 下面这些 name 条目在改名时整体换掉；其余（版权、设计者、授权等）保留
RENAMED = (1, 2, 3, 4, 6, 16, 17, 21, 22, 25)
REF = 0x56FD  # 国：新字的字宽、竖排原点、所属的 CFF 私有字典（汉字那一组）都照它


def load_config(path: Path = HERE / 'font.yaml') -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _cff(font: TTFont):
    return font['CFF '].cff, font['CFF '].cff.topDictIndex[0]


def add_glyph(font: TTFont, cp: int, strokes: list[str]) -> str:
    """把字形加进字体：CFF 字形、字宽、竖排度量、字符映射。
    CID 字体（思源的 OTF 都是）里新字取一个没用过的 CID，归进“国”所在的那组私有字典；
    竖排时与“国”共用同一个字符原点。"""
    cff, top = _cff(font)
    ref = font.getBestCmap()[REF]
    order = list(font.getGlyphOrder())
    if getattr(top, 'ROS', None):
        fd = top.FDSelect[font.getGlyphID(ref)]
        private = top.FDArray[fd].Private
        name = f'cid{max(int(n[3:]) for n in order if n.startswith("cid")) + 1}'
    else:
        fd, private, name = None, top.Private, f'u{cp:05X}'
    if name in order:
        raise ValueError(f'{name} 已在字体里')
    cs = to_charstring(strokes, private, top.GlobalSubrs)
    chars = top.CharStrings
    chars.charStringsIndex.append(cs)
    chars.charStrings[name] = len(chars.charStringsIndex) - 1
    if fd is not None:
        top.FDSelect.append(fd)
        top.CIDCount = int(name[3:]) + 1
    order.append(name)
    top.charset = order
    font.setGlyphOrder(order)
    bp = BoundsPen(None)
    cs.draw(bp)
    x_min, _, _, y_max = bp.bounds
    font['hmtx'][name] = (EM, round(x_min))
    if 'vmtx' in font:
        font['vmtx'][name] = (EM, round(vertical_origin(font) - y_max))
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


def vertical_origin(font: TTFont) -> float:
    """竖排时字形顶端到原点的位置：用“国”的 tsb 与顶端之和；取不到时用 ascent 880。"""
    ref = font.getBestCmap().get(REF)
    if not ref or 'vmtx' not in font:
        return ASCENT
    bp = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[ref].draw(bp)
    return font['vmtx'][ref][1] + bp.bounds[3]


def autohint(path: Path, glyphs: list[str]) -> None:
    """用 AFDKO 的 otfautohint 只给新加的字补 hinting（上游的字原样保留 Adobe 的 hinting）。"""
    run = subprocess.run(
        ['otfautohint', '-g', ','.join(glyphs), str(path), '-o', str(path)],
        capture_output=True, text=True,
    )
    if run.returncode != 0:
        raise SystemExit(f'otfautohint 失败（需要 afdko，见 font/README.md）：\n{run.stderr or run.stdout}')


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
    # CFF 里也记着字体名（PostScript 名、全名、字体族，CID 字体各组私有字典也带着名字）
    cff, top = _cff(font)
    old = cff.fontNames[0]
    ps = f'{family}-{style}'
    cff.fontNames[0] = ps
    top.FullName, top.FamilyName = full, family
    if getattr(top, 'Notice', None):  # 同 name 表：去掉 Noto 的商标声明
        top.Notice = top.Notice.replace(' Noto is a trademark of Google Inc.', '')
    for fd in getattr(top, 'FDArray', None) or []:
        fd.FontName = fd.FontName.replace(old, ps)


def build(upstream: Path, out: Path, cfg: dict | None = None, root: Path = HERE) -> TTFont:
    cfg = cfg or load_config(root / 'font.yaml')
    want = cfg['upstream'].get('sha256')
    got = hashlib.sha256(upstream.read_bytes()).hexdigest()
    if want and got != want:
        raise SystemExit(f'上游字体校验失败：{upstream}\n  应为 {want}\n  实为 {got}')
    font = TTFont(upstream, recalcTimestamp=False)  # 修改时间沿用上游：同样的输入得到逐字节相同的字体
    if 'CFF ' not in font:
        raise SystemExit(f'上游字体要用 CFF 轮廓的 OTF（带 hinting），不是 TrueType：{upstream}')
    have = set(font.getBestCmap())
    added = []
    for g in cfg['glyphs']:
        cp = g['cp']
        if cp in have:
            raise SystemExit(f"U+{cp:04X} 上游字体里已经有了，不必再补：{g['char']}")
        strokes = [d for _, d in read_strokes(root / g['svg'])]
        if not strokes:
            raise SystemExit(f"{g['svg']} 里没有笔画")
        added.append(add_glyph(font, cp, strokes))
    rename(font, cfg)
    font['head'].fontRevision = float(cfg['version'].rsplit('.', 1)[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / 'unhinted.otf'
        font.save(work)
        autohint(work, added)
        # otfautohint 会改写 head 的修改时间；改回上游的，保证逐字节可重现
        hinted = TTFont(work, recalcTimestamp=False)
        hinted['head'].modified = font['head'].modified
        hinted.save(out)
    return TTFont(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--upstream', required=True, type=Path, help='固定版本的 NotoSerifSC-Regular.otf')
    ap.add_argument('--out', required=True, type=Path, help='生成的 OTF')
    a = ap.parse_args()
    f = build(a.upstream, a.out)
    print(f'{a.out}  {a.out.stat().st_size // 1024} KB  {len(f.getGlyphOrder())} 字形')


if __name__ == '__main__':
    main()
