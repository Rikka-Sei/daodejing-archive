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
    shu_wan_gou,
    shu_zhe,
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
    """木：x0..x1 横的起讫（含顿角），yt 竖头尖，yb 竖脚底。"""
    h = yb - yt
    yc = yt + 0.272 * h
    cx = (x0 + x1) / 2 - 3
    s = h / 917
    return [
        ('mu-heng', heng(x0, x1, yc)),
        ('mu-shu', shu(cx - W_V / 2, yt, yb)),
        (
            'mu-pie',
            pie(cx - 6, yc - 4, x0 + 7, yt + 811 * s, head=90, tip=21, plain=True,
                right=(0.29, 0.22, 0.25, 0.50), left=(0.28, 0.17, 0.40, 0.41)),
        ),
        ('mu-na', na(cx + 5, yc - 12, x1 + 12, yt + 729 * s, upper=(0.23, 0.38, 0.54, 0.80), lower=(0.32, 0.12, 0.77, 0.57))),
    ]


def wang(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """王：三横一竖。yt 顶横的上缘，yb 底横的下缘；x0..x1 是底横起讫（含顿角）。"""
    h = yb - yt
    sx = (x1 - x0) / 906
    cx = (x0 + x1) / 2 - 4
    return [
        ('wang-heng1', heng(x0 + 44 * sx, x0 + 858 * sx, yt + 15)),
        ('wang-heng2', heng(x0 + 87 * sx, x0 + 822 * sx, yt + 0.469 * h + 0.531 * 15)),
        ('wang-shu', plain_shu(cx - 34, yt + 15, yb - 15)),
        ('wang-heng3', heng(x0, x1, yb - 14)),
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
    top, bottom = yh + 50, yb - 99 * min(1.0, 0.4 + 0.6 * s)
    fr = [0.489] if inner == 1 else [i / (inner + 1) for i in range(1, inner + 1)]
    bars = [top + (bottom - top) * f for f in fr] + [bottom]
    return [
        *kou_frame(x0, xr, yh, yb, bars),
        (
            'bai-pie',
            pie(x0 + 0.416 * w, yh - 156 * s, x0 + 0.348 * w, yh + 47 * s, head=115, tip=6,
                right=(0.08, -0.04, 0.32, 0.64), left=(0.18, 0.24, 0.62, 0.50)),
        ),
    ]


def cong(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """从：两个人并立，左人捺短，右人捺长。(x0, x1) 是笔画最左、最右的落点，yt 撇头顶，yb 撇尖底。"""
    b = Box((36, 66, 976, 957), (x0, yt, x1, yb))
    return [
        (
            'cong-pie1',
            pie(b.x(277), b.y(66), b.x(64), b.y(944.5), head=68 * b.kx * 0.8, tip=46 * b.kx * 0.6,
                right=(0.02, 0.46, 0.10, 0.66), left=(0.50, 0.22, 0.70, 0.14)),
        ),
        ('cong-na1', na_duan(b.x(309), b.y(443), b.x(475), b.y(731), upper=(0.43, 0.25, 0.81, 0.59), lower=(-0.32, -0.06, -0.34, -0.50))),
        (
            'cong-pie2',
            pie(b.x(635), b.y(75.5), b.x(400.5), b.y(939.5), head=84 * b.kx * 0.8, tip=9.5 * b.kx,
                right=(0.04, 0.50, 0.10, 0.66), left=(0.36, 0.26, 0.70, 0.10)),
        ),
        (
            'cong-na2',
            na(b.x(662), b.y(128), b.x(968), b.y(899), upper=(0.09, 0.64, 0.51, 0.80), lower=(0.54, 0.12, 1.08, 0.62), foot=(-63, 65)),
        ),
    ]


def tun(x0: float, x1: float, yt: float, yb: float) -> Strokes:
    """屯：x0..x1 是横的起讫，yt 竖头尖，yb 竖弯钩的底。"""
    b = Box((46, 43, 954, 936), (x0, yt, x1, yb))
    return [
        ('tun-heng', heng(b.x(46), b.x(942), b.y(247))),
        ('tun-zuo', shu_tail(b.x(160), b.y(324), b.y(654))),
        ('tun-bar', heng(b.x(192), b.x(791), b.y(639.5), dun=False)),
        ('tun-you', shu_duan(b.x(759), b.y(329), b.y(717), w=65)),
        ('tun-shu', shu_wan_gou(b.x(455), b.y(43), b.y(936), b.x(948), b.y(689))),
    ]
