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
from parts import Strokes, bai, cong, dui, kou_frame, mu, plain_shu, tun, wang  # noqa: E402
from strokes import heng, shu, shu_qie, shu_zhe, xie_shu  # noqa: E402


def zi_dui() -> Strokes:
    """𠂤 U+200A4：丿下 㠯（一道左竖，右边上下两个框，横折分开写），同 追 師 的右旁、官 的下部。"""
    return dui(210, 778, 836, 178, 955)


def ce() -> Strokes:
    """𠕁 U+20541：冂里套卄。上横与框相接，四道竖，中横收在框里；右外竖出钩。比例对照思源宋体的 冊。"""
    return [
        ('ce-left', shu_qie(149, 93, 958)),
        ('ce-right', shu_zhe(857, 126, 956, w=65, gou=True)),
        ('ce-top', heng(190, 826, 141, dun=False)),
        ('ce-in1', shu(359, 141, 939, w=62, head=False)),
        ('ce-in2', shu(575, 141, 939, w=62, head=False)),
        ('ce-mid', heng(200, 800, 478, dun=False)),
    ]


def chi_shan() -> Strokes:
    """𠚕 U+20695：凵里叠两个从，中间一横；两边的竖比里面的横长出一截。"""
    return [
        ('wall-left', shu(135, 200, 955)),
        ('wall-right', shu(799, 200, 955)),
        ('bar-mid', heng(165, 835, 440, dun=False)),
        ('bar-bottom', heng(165, 835, 866, dun=False)),
        *[(f'up-{k}', d) for k, d in cong(232, 770, 48, 400)],
        *[(f'low-{k}', d) for k, d in cong(232, 770, 474, 828)],
    ]


def bai_mu() -> Strokes:
    """𣐩 U+23429：上白下木。"""
    return [*bai(220, 790, 111, 582, inner=1), *mu(52, 950, 537, 959)]


def wang_tun() -> Strokes:
    """𤤀 U+24900：左王右屯。"""
    return [*wang(29, 396, 153, 849), *tun(422, 969, 45, 940)]


def wu_kou() -> Strokes:
    """𭇁 U+2D1C1：上 𫝀（斜竖、一、横折、长横）下口，即 吾 去掉首横；斜竖从顶上起笔。比例对照思源宋体的 吾。"""
    return [
        ('xi-shu', xie_shu(405, 50, 301, 488)),
        ('xi-top', heng(156, 700, 287, dun=False)),
        ('xi-zhe', shu_zhe(736, 272, 488)),
        ('xi-bottom', heng(44, 965, 488)),
        *[(f'kou-{k}', d) for k, d in kou_frame(206, 799, 577, 956, [875])],
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
