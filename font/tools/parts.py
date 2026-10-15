"""部件的画法：把笔画按字形摆起来。

同一个部件在字头、字底、偏旁里写法不同，所以部件按部位命名（wang_left 是左旁的王，mu_bottom 是字底的木……）。
每个部件的落点，是对思源宋体里**同一部件在同一部位**的参考字逐笔拟合的（参考字写在各函数的说明里，
拟合方法见 tools/fit.py）；落点记在参考字的坐标里，再按给定的字框线性映射过去。
横竖的粗细、顿角和收笔不随字框缩放；撇捺在缩小的部件里按缩小比例的平方根减轻（系数 k）。
"""

from __future__ import annotations

from strokes import (
    heng,
    na,
    na_duan,
    pie,
    plain_shu,
    shu,
    shu_duan,
    shu_qie,
    shu_tail,
    shu_wan_gou,
    shu_zhe,
    ti,
)

Strokes = list[tuple[str, str]]  # (笔画名, SVG 路径)


class Box:
    """参考框 → 目标框的线性映射。"""

    def __init__(self, ref: tuple[float, float, float, float], to: tuple[float, float, float, float]):
        (self.rx0, self.ry0, rx1, ry1), (self.tx0, self.ty0, tx1, ty1) = ref, to
        self.kx = (tx1 - self.tx0) / (rx1 - self.rx0)
        self.ky = (ty1 - self.ty0) / (ry1 - self.ry0)

    def x(self, v: float) -> float:
        return self.tx0 + (v - self.rx0) * self.kx

    def y(self, v: float) -> float:
        return self.ty0 + (v - self.ry0) * self.ky


def mu_bottom(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """字底的木（扁木）：横长，撇捺从横下分出、向两边舒展。x0..x1 横的起讫（含顿角），yt 竖头尖，yb 竖脚底。
    参考字 臬（tools/fit.py 的 mu_bottom）。"""
    b = Box((53, 536.5, 948.5, 959.5), (x0, yt, x1, yb))
    k = max(0.6, min(1.0, ((b.kx + b.ky) / 2) ** 0.5))
    return [
        ('mu-heng', heng(x0, x1, b.y(648))),
        ('mu-shu', shu(b.x(465.5), yt, yb)),
        (
            'mu-pie',
            pie(b.x(426), b.y(634.5), b.x(67.5), b.y(920), head=99.5 * k, tip=61 * k, plain=True, k=k,
                right=(0.155, 0.125, 0.20, 0.50), left=(0.32, 0.21, 0.595, 0.41)),
        ),
        (
            'mu-na',
            na(b.x(530.5), b.y(634.5), b.x(975), b.y(870), upper=(0.165, 0.48, 0.67, 0.80), lower=(0.39, 0.12, 0.785, 0.525),
               foot=(-62, 53), k=0.99 * k),
        ),
    ]


def wang_left(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """左旁的王：两横一竖，末笔是向右上挑的提。x0..x1 是提的起点到顶横的收笔，yt 竖头，yb 提的最低处。
    参考字 珅 的左旁（tools/fit.py 的 wang_left）。"""
    b = Box((29.5, 153.5, 395, 848), (x0, yt, x1, yb))
    return [
        ('wang-heng1', heng(b.x(42), b.x(395), b.y(167.5))),
        ('wang-heng2', heng(b.x(49.5), b.x(385.5), b.y(441.5))),
        ('wang-shu', plain_shu(b.x(170), b.y(153.5), b.y(735), w=65)),
        ('wang-ti', ti(b.x(29.5), b.y(766), b.x(381.5), b.y(657))),
    ]


def kou_frame(x0: float, xr: float, yh: float, yb: float, bars: list[float]) -> Strokes:
    """口式的框：左竖（头斜切）、顶横连右竖、若干内横与底横。yh 是左竖切口最高处，bars 是除顶横外各横的中线。"""
    top = yh + 35
    out: Strokes = [
        ('frame-left', shu_qie(x0, yh, yb)),
        ('frame-right', shu_zhe(xr, top, yb)),
        ('frame-top', heng(x0 + 40, xr - 20, top + 15, dun=False)),
    ]
    for i, y in enumerate(bars):
        out.append((f'frame-bar{i + 1}', heng(x0 + 40, xr - 40, y, dun=False)))
    return out


def bai_top(x0: float, xr: float, yh: float, yb: float) -> Strokes:
    """字头的白：丿加一个框，框中一横。x0 左竖左缘，xr 右竖右缘，yh 左竖切口顶，yb 竖脚底。
    框的比例对照思源宋体 臬 的字头；丿随字框压扁而变短、变细（独体 白 时 s=1）。"""
    s = (yb - yh) / 753
    w = xr - x0
    k = max(0.6, min(1.0, s**0.5))
    top, bottom = yh + 50, yb - 99 * min(1.0, 0.4 + 0.6 * s)
    return [
        *kou_frame(x0, xr, yh, yb, [top + (bottom - top) * 0.489, bottom]),
        (
            'bai-pie',
            pie(x0 + 0.416 * w, yh - 156 * s**1.8, x0 + 0.348 * w, yh + 47 * s, head=115 * k, tip=6 * k, k=k,
                right=(0.08, -0.04, 0.32, 0.64), left=(0.18, 0.24, 0.62, 0.50)),
        ),
    ]


def yi(x0: float, xu: float, xl: float, yh: float, yb: float) -> Strokes:
    """㠯（官 的下部、追 師 的右旁）：一道左竖，右边上下两个框，两个横折分开写，下框比上框宽。
    x0 左竖左缘，xu、xl 上框、下框右竖的右缘，yh 左竖切口顶，yb 左竖脚底。
    各横、各竖脚的高度比例量自思源宋体 官 追 的 㠯。"""
    top = yh + 35
    h = yb - top
    ub, lt, bot = top + 0.34 * h, top + 0.575 * h, top + 0.875 * h
    return [
        ('yi-left', shu_qie(x0, yh, yb)),
        ('yi-up', shu_zhe(xu, top, top + 0.44 * h)),
        ('yi-up-top', heng(x0 + 40, xu - 20, top + 15, dun=False)),
        ('yi-up-bottom', heng(x0 + 40, xu - 40, ub, dun=False)),
        ('yi-low', shu_zhe(xl, lt - 15, yb - 3)),
        ('yi-low-top', heng(x0 + 40, xl - 20, lt, dun=False)),
        ('yi-low-bottom', heng(x0 + 40, xl - 40, bot, dun=False)),
    ]


def cong_top(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """字头的从（扁从，也用在框里）：两个人并立，撇比独体的从斜，左人的捺缩成一点，右人的捺短而有脚。
    (x0, x1) 是笔画最左、最右处，yt 撇头顶，yb 撇尖底。参考字 怂 的字头（tools/fit.py 的 cong_top）。"""
    b = Box((36, 37, 954, 645), (x0, yt, x1, yb))
    k = max(0.6, min(1.0, ((b.kx + b.ky) / 2) ** 0.5))
    return [
        (
            'cong-pie1',
            pie(b.x(271.5), b.y(33.5), b.x(49), b.y(645), head=85 * k, tip=20 * k, k=1.17 * k,
                right=(0.10, 0.29, 0.10, 0.67), left=(0.38, 0.22, 0.68, 0.12)),
        ),
        (
            'cong-na1',
            na_duan(b.x(321), b.y(240.5), b.x(457), b.y(448.5), upper=(0.43, 0.25, 0.82, 0.39), lower=(-0.08, 0.02, -0.66, -0.50),
                    w=18, k=0.96 * k),
        ),
        (
            'cong-pie2',
            pie(b.x(637.5), b.y(41), b.x(361), b.y(619.5), head=94 * k, tip=21.5 * k, k=0.62 * k,
                right=(0.04, 0.48, 0.08, 0.66), left=(0.33, 0.26, 0.90, 0.10)),
        ),
        (
            'cong-na2',
            na(b.x(673), b.y(114), b.x(956.5), b.y(557.5), upper=(0.09, 0.64, 0.51, 0.81), lower=(0.565, 0.12, 0.92, 0.46),
               foot=(-66, 52.5), k=0.925 * k),
        ),
    ]


def tun_right(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """右旁的屯：横下两短竖夹一横，中竖下来圆转成平横，末端竖直出细钩。
    x0..x1 是横的起点到钩脚最右处，yt 中竖头尖，yb 平横的下缘。参考字 纯 的右旁（tools/fit.py 的 tun_right）。"""
    b = Box((382.5, 44.5, 966.5, 938), (x0, yt, x1, yb))
    return [
        ('tun-heng', heng(b.x(382.5), b.x(961.5), b.y(232))),
        ('tun-zuo', shu_tail(b.x(419.5), b.y(317), b.y(652.5))),
        ('tun-bar', heng(b.x(461.5), b.x(855), b.y(638), dun=False)),
        ('tun-you', shu_duan(b.x(824), b.y(318), b.y(707), w=61.5)),
        ('tun-shu', shu_wan_gou(b.x(620.5), yt, yb, x1, b.y(729.5))),
    ]
