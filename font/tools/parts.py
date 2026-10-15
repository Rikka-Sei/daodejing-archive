"""部件的画法：把笔画按字形摆起来。

每个部件先按思源宋体里同一部件的位置（参考框）排好笔画的落点，再按给定的字框把落点线性映射过去；
笔画的粗细、顿角和收笔不随字框缩放，所以挤窄、压扁之后笔画仍和正文一样粗。
"""

from __future__ import annotations

from strokes import (
    W_V,
    heng,
    na,
    na_duan,
    path,
    pie,
    pt,
    shu,
    shu_duan,
    shu_qie,
    shu_tail,
    shu_wan_gou_r,
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


def plain_shu(xl: float, y0: float, y1: float, w: float = W_V + 3) -> str:
    """没有头饰、脚平收的竖，用于接在横上的内竖。"""
    return path(f'M{pt(xl, y0)}', f'L{pt(xl + w, y0)}', f'L{pt(xl + w, y1)}', f'L{pt(xl, y1)}')


def mu(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """扁的木（在字底）：横长，撇捺从横下分出、向两边舒展。x0..x1 横的起讫（含顿角），yt 竖头尖，yb 竖脚底。
    落点与曲线比例是对思源宋体 臬 的字底逐笔拟合的。"""
    b = Box((52, 537, 950, 959), (x0, yt, x1, yb))
    k = max(0.6, min(1.0, ((b.kx + b.ky) / 2) ** 0.5))
    return [
        ('mu-heng', heng(x0, x1, b.y(650))),
        ('mu-shu', shu(b.x(466), yt, yb)),
        (
            'mu-pie',
            pie(b.x(449.5), b.y(632), b.x(72), b.y(919.5), head=99.5 * k, tip=61 * k, plain=True, k=k,
                right=(0.29, 0.225, 0.25, 0.50), left=(0.36, 0.25, 0.50, 0.41)),
        ),
        (
            'mu-na',
            na(b.x(525), b.y(628), b.x(974.5), b.y(868), upper=(0.145, 0.38, 0.40, 0.66), lower=(0.34, 0.11, 0.79, 0.53), foot=(-64, 59), k=k),
        ),
    ]


def wang(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """左旁的王：两横一竖，末笔是向右上挑的提。x0..x1 是提的起讫，yt 顶横的上缘，yb 提的最低处。
    比例是对思源宋体 珅 的左旁逐笔拟合的。"""
    b = Box((29, 153, 396, 849), (x0, yt, x1, yb))
    return [
        ('wang-heng1', heng(b.x(42), b.x(396), b.y(168))),
        ('wang-heng2', heng(b.x(52), b.x(389), b.y(444))),
        ('wang-shu', plain_shu(b.x(170), b.y(153), b.y(734), w=65)),
        ('wang-ti', ti(b.x(29), b.y(767), b.x(381), b.y(657))),
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


def bai(x0: float, xr: float, yh: float, yb: float, *, inner: int = 1) -> Strokes:
    """白：丿加一个框，框里有 inner 道内横（白 1 道，自 2 道）。x0 左竖左缘，xr 右竖右缘，yh 左竖切口顶，yb 竖脚底。"""
    s = (yb - yh) / 753
    w = xr - x0
    k = max(0.6, min(1.0, s**0.5))  # 压扁的白，丿要比正文里的细小、短（臬 的字头）
    top, bottom = yh + 50, yb - 99 * min(1.0, 0.4 + 0.6 * s)
    fr = {1: [0.489], 2: [0.36, 0.64]}.get(inner) or [i / (inner + 1) for i in range(1, inner + 1)]
    bars = [top + (bottom - top) * f for f in fr] + [bottom]
    return [
        *kou_frame(x0, xr, yh, yb, bars),
        (
            'bai-pie',
            pie(x0 + 0.416 * w, yh - 156 * s**1.8, x0 + 0.348 * w, yh + 47 * s, head=115 * k, tip=6 * k, k=k,
                right=(0.08, -0.04, 0.32, 0.64), left=(0.18, 0.24, 0.62, 0.50)),
        ),
    ]


def dui(x0: float, xu: float, xl: float, yh: float, yb: float) -> Strokes:
    """𠂤：丿下一道左竖，右边上下两个框（㠯），两个横折分开写，下框比上框宽。
    x0 左竖左缘，xu、xl 上框、下框右竖的右缘，yh 左竖切口顶，yb 左竖脚底。
    上下框的比例取自思源宋体 官 追 師 里的 㠯。"""
    top = yh + 35
    h = yb - top
    ub, lt, bot = top + 0.34 * h, top + 0.575 * h, top + 0.875 * h
    k = 0.85
    return [
        ('dui-left', shu_qie(x0, yh, yb)),
        ('dui-up', shu_zhe(xu, top, top + 0.44 * h)),
        ('dui-up-top', heng(x0 + 40, xu - 20, top + 15, dun=False)),
        ('dui-up-bottom', heng(x0 + 40, xu - 40, ub, dun=False)),
        ('dui-low', shu_zhe(xl, lt - 15, yb - 3)),
        ('dui-low-top', heng(x0 + 40, xl - 20, lt, dun=False)),
        ('dui-low-bottom', heng(x0 + 40, xl - 40, bot, dun=False)),
        (
            'dui-pie',
            pie(x0 + 0.43 * (xu - x0), yh - 145, x0 + 0.36 * (xu - x0), yh + 40, head=112 * k, tip=6, k=k,
                right=(0.08, -0.04, 0.32, 0.64), left=(0.18, 0.24, 0.62, 0.50)),
        ),
    ]


def cong(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """扁的从（在字头或框里）：两个人并立，撇比正文里的从斜，左人的捺缩成一点，右人的捺短而有脚。
    (x0, x1) 是笔画最左、最右的落点，yt 撇头顶，yb 撇尖底。
    落点与曲线比例是对思源宋体 怂 的字头逐笔拟合的；缩小后笔画按缩小比例的平方根减轻，不随之细成线。"""
    b = Box((36, 37, 954, 645), (x0, yt, x1, yb))
    k = max(0.6, min(1.0, ((b.kx + b.ky) / 2) ** 0.5))
    return [
        (
            'cong-pie1',
            pie(b.x(271), b.y(37), b.x(47), b.y(645), head=85 * k, tip=20 * k, k=1.17 * k,
                right=(0.10, 0.29, 0.10, 0.67), left=(0.38, 0.22, 0.68, 0.12)),
        ),
        ('cong-na1', na_duan(b.x(327), b.y(244), b.x(457), b.y(448), upper=(0.43, 0.25, 0.82, 0.39), lower=(-0.08, 0.02, -0.66, -0.50), w=18, k=0.96 * k)),
        (
            'cong-pie2',
            pie(b.x(639), b.y(40), b.x(358), b.y(622), head=94 * k, tip=21.5 * k, k=0.62 * k,
                right=(0.04, 0.48, 0.08, 0.66), left=(0.33, 0.26, 0.90, 0.10)),
        ),
        (
            'cong-na2',
            na(b.x(675), b.y(140), b.x(951), b.y(561), upper=(0.09, 0.64, 0.60, 0.81), lower=(0.42, 0.12, 1.03, 0.62), foot=(-76, 49), k=k),
        ),
    ]


def tun(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """右旁的屯：横下两短竖夹一横，中竖下来圆转成平横，末端竖直出细钩。
    x0..x1 是横的起点到钩脚最右处，yt 中竖头尖，yb 平横的下缘。比例是对思源宋体 纯 的右旁逐笔拟合的。"""
    b = Box((384, 45, 969, 940), (x0, yt, x1, yb))
    return [
        ('tun-heng', heng(b.x(384), b.x(969), b.y(238))),
        ('tun-zuo', shu_tail(b.x(420), b.y(317), b.y(653))),
        ('tun-bar', heng(b.x(462), b.x(855), b.y(638), dun=False)),
        ('tun-you', shu_duan(b.x(824), b.y(317), b.y(706), w=62)),
        ('tun-shu', shu_wan_gou_r(b.x(620), b.y(45), b.y(940), b.x(965), b.y(730))),
    ]
