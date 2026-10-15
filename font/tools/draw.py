"""手绘 6 个字：按字形摆笔画，写出 font/glyphs/uXXXXX.svg。

改字形就改这里的坐标（1000×1000 字身框，y 向下，基线在 y=880），再运行：python3 font/tools/draw.py
也可以直接用矢量软件改 SVG；构建（font/build.py）只认 SVG。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from glyphlib import write_svg  # noqa: E402
from parts import Strokes, bai, cong, kou_frame, mu, plain_shu, tun, wang  # noqa: E402
from strokes import W_V, heng, pie, shu, shu_qie, shu_zhe  # noqa: E402


def zi_dui() -> Strokes:
    """𠂤 U+200A4：丿加一个框，框里两道内横（自 的写法，丿更斜）。"""
    return bai(195, 805, 205, 955, inner=2)


def ce() -> Strokes:
    """𠕁 U+20541：冂里套卄。上横与框相接，四道竖，次横在顶横下；右外竖出钩。"""
    top, mid, foot = 210, 372, 935
    out: Strokes = [
        ('ce-left', shu_qie(150, top - 50, foot)),
        ('ce-right', shu_zhe(850, top - 15, foot, gou=True)),
        ('ce-top', heng(180, 830, top, dun=False)),
        ('ce-in1', shu(365, top - 15, foot, head=False)),
        ('ce-in2', shu(570, top - 15, foot, head=False)),
        ('ce-mid', heng(180, 830, mid, dun=False)),
    ]
    return out


def chi_shan() -> Strokes:
    """𠚕 U+20695：凵里叠两个从，中间一横；两边的竖比里面的横长出一截。"""
    return [
        ('wall-left', shu(190, 275, 955)),
        ('wall-right', shu(745, 275, 955)),
        ('bar-mid', heng(220, 780, 445, dun=False)),
        ('bar-bottom', heng(220, 780, 866, dun=False)),
        *[(f'up-{k}', d) for k, d in cong(265, 735, 50, 395)],
        *[(f'low-{k}', d) for k, d in cong(265, 735, 485, 835)],
    ]


def bai_mu() -> Strokes:
    """𣐩 U+23429：上白下木。"""
    return [*bai(270, 730, 130, 450, inner=1), *mu(90, 910, 485, 958)]


def wang_tun() -> Strokes:
    """𤤀 U+24900：左王右屯。"""
    return [*wang(45, 415, 140, 905), *tun(450, 955, 50, 935)]


def wu_kou() -> Strokes:
    """𭇁 U+2D1C1：上 𫝀（丿、一、竖折、一）下口。"""
    return [
        ('xi-pie', pie(400, 60, 333, 488, head=112, tip=14, right=(0.08, -0.04, 0.32, 0.64), left=(0.18, 0.24, 0.62, 0.50))),
        ('xi-top', heng(187, 690, 266, dun=False)),
        ('xi-shu', shu_zhe(706, 251, 490)),
        ('xi-bottom', heng(110, 882, 490)),
        *[(f'kou-{k}', d) for k, d in kou_frame(230, 770, 567, 940, [864])],
    ]


GLYPHS = {
    0x200A4: ('𠂤', zi_dui),
    0x20541: ('𠕁', ce),
    0x20695: ('𠚕', chi_shan),
    0x23429: ('𣐩', bai_mu),
    0x24900: ('𤤀', wang_tun),
    0x2D1C1: ('𭇁', wu_kou),
}


def main() -> None:
    out = HERE.parent / 'glyphs'
    out.mkdir(exist_ok=True)
    for cp, (ch, fn) in GLYPHS.items():
        write_svg(out / f'u{cp:05X}.svg', fn(), title=f'{ch} U+{cp:04X}')
        print(f'u{cp:05X}.svg')


if __name__ == '__main__':
    main()
