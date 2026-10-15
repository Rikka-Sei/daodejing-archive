"""手绘 6 个字：按字形摆笔画，写出 font/glyphs/uXXXXX.svg。

这里是字形的唯一源头。改字形就改这里（或 parts.py、strokes.py）的坐标（1000×1000 字身框，y 向下，基线在 y=880），
再运行 python3 font/tools/draw.py 重写 SVG。SVG 是生成的产物，供构建（font/build.py）读取、供人在矢量软件里查看，
不要手改：tests/test_font.py 会核对 SVG 与这里的输出逐字相同。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from glyphlib import write_svg  # noqa: E402
from parts import Strokes, bai_top, cong_top, kou_frame, mu_bottom, tun_right, wang_left, yi  # noqa: E402
from strokes import heng, pie, shu, shu_qie, shu_zhe, xie_shu  # noqa: E402


def zi_dui() -> Strokes:
    """𠂤 U+200A4：丿下 㠯（一道左竖，右边上下两个框，横折分开写），同 追 師 的右旁。丿 的位置对照 自。"""
    x0, xu, yh = 210, 778, 178
    return [
        *yi(x0, xu, 836, yh, 955),
        (
            'pie',
            pie(x0 + 0.43 * (xu - x0), yh - 145, x0 + 0.36 * (xu - x0), yh + 40, head=95.2, tip=6, k=0.85,
                right=(0.08, -0.04, 0.32, 0.64), left=(0.18, 0.24, 0.62, 0.50)),
        ),
    ]


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
    """𠚕 U+20695：凵里叠两个从，中间一横；两边的竖比里面的横长出一截。从 用字头的扁从（对照 怂）。"""
    return [
        ('wall-left', shu(135, 200, 955)),
        ('wall-right', shu(799, 200, 955)),
        ('bar-mid', heng(165, 835, 440, dun=False)),
        ('bar-bottom', heng(165, 835, 866, dun=False)),
        *[(f'up-{k}', d) for k, d in cong_top(232, 770, 48, 400)],
        *[(f'low-{k}', d) for k, d in cong_top(232, 770, 474, 828)],
    ]


def bai_mu() -> Strokes:
    """𣐩 U+23429：上白下木，比例对照 臬（自 下木）。"""
    return [*bai_top(220, 790, 111, 582), *mu_bottom(53, 948.5, 536.5, 959.5)]


def wang_tun() -> Strokes:
    """𤤀 U+24900：左王右屯，王 对照 珅 的左旁，屯 对照 纯 的右旁（稍收窄让出王）。"""
    return [*wang_left(29.5, 395, 153.5, 848), *tun_right(422, 969, 45, 940)]


def wu_kou() -> Strokes:
    """𭇁 U+2D1C1：上 𫝀（斜竖、一、横折、长横）下口，即 吾 去掉首横；斜竖从顶上起笔。
    参考字 吾（tools/fit.py 的 wu_kou）；斜竖按 吾 的轮廓点量取，因为没有首横压着，加上竖头、向上伸到顶。"""
    return [
        ('xi-shu', xie_shu(405, 50, 301, 488)),
        ('xi-top', heng(159.5, 711, 284.5, dun=False)),
        ('xi-zhe', shu_zhe(736, 277.5, 495)),
        ('xi-bottom', heng(44, 963, 488)),
        *[(f'kou-{k}', d) for k, d in kou_frame(206, 799, 577, 955, [875])],
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
