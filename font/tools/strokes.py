"""宋体笔画的画法：每个函数画一笔，返回 SVG 路径（1000 单位的字身框，y 向下）。

笔画粗细、顿角、收笔的尺寸，是对思源宋体 Regular（400）的白 木 王 屯 口 等字量得的：
横 30，竖 66，横的右端有三角形的顿角，竖头有小钩，竖脚向左收圆。
这里的每一笔都是按这些尺寸现画的，不是从思源宋体里抠下来的轮廓。
"""

from __future__ import annotations

T_H = 30  # 横画粗
W_V = 66  # 竖画粗


def n(v: float) -> str:
    s = f'{v:.1f}'
    return s[:-2] if s.endswith('.0') else s


def pt(x: float, y: float) -> str:
    return f'{n(x)},{n(y)}'


def path(*segs: str) -> str:
    return ' '.join(segs) + ' Z'


def heng(x0: float, x1: float, yc: float, *, dun: bool = True) -> str:
    """横。x0 起笔，x1 收笔处顿角的最右端，yc 笔画中线。dun=False 是两头平齐的内横。"""
    top, bot = yc - T_H / 2, yc + T_H / 2
    if not dun:
        return path(f'M{pt(x0, top)}', f'L{pt(x1, top)}', f'L{pt(x1, bot)}', f'L{pt(x0, bot)}')
    return path(
        f'M{pt(x0, top)}',
        f'L{pt(x1 - 148, top)}',
        f'L{pt(x1 - 95, top - 65)}',
        f'C{pt(x1 - 70, top - 47)} {pt(x1 - 35, top - 18)} {pt(x1, top + 13)}',
        f'Q{pt(x1 - 3, bot)} {pt(x1 - 27, bot)}',
        f'L{pt(x0 + 8, bot)}',
    )


def _foot(xr: float, y1: float, xl: float) -> list[str]:
    """竖脚：右边缘向左收成圆角，脚底平。"""
    return [
        f'L{pt(xr, y1 - 27)}',
        f'Q{pt(xr, y1 - 22)} {pt(xr - 8, y1 - 15.5)}',
        f'Q{pt(xr - 16, y1 - 9)} {pt(xr - 28, y1 - 4.5)}',
        f'Q{pt(xr - 40, y1)} {pt(xr - 53, y1)}',
        f'L{pt(xl, y1)}',
    ]


def shu(xl: float, y0: float, y1: float, *, w: float = W_V, head: bool = True) -> str:
    """竖：左缘 xl，从 y0（头尖）到 y1（脚底），竖头有向右的小钩（head=False 则头是平的，接在横下），竖脚收圆。"""
    xr = xl + w
    top = (
        [
            f'M{pt(xl, y0)}',
            f'L{pt(xl + 102, y0 + 12)}',
            f'Q{pt(xl + 101, y0 + 22)} {pt(xl + 93.5, y0 + 29)}',
            f'Q{pt(xl + 86, y0 + 36)} {pt(xr, y0 + 39)}',
        ]
        if head
        else [f'M{pt(xl, y0)}', f'L{pt(xr, y0)}']
    )
    return path(*top, *_foot(xr, y1, xl))


def shu_qie(xl: float, y0: float, y1: float, *, w: float = W_V) -> str:
    """竖，竖头斜切（框的左竖：与上面的横相接，起笔处向右下斜切）。y0 是切口最高处。"""
    xr = xl + w
    return path(
        f'M{pt(xl, y0)}',
        f'L{pt(xl + 73, y0 + 35)}',
        f'L{pt(xr, y0 + 35)}',
        *_foot(xr, y1, xl),
    )


def _gou_foot(xl: float, xr: float, y1: float, gou: float = 78) -> list[str]:
    """竖钩的脚：竖到底，向左出钩，钩尖朝上。"""
    return [
        f'L{pt(xr, y1 - 24)}',
        f'Q{pt(xr, y1 - 4)} {pt(xr - 24, y1 - 2)}',
        f'Q{pt(xl - gou * 0.35, y1)} {pt(xl - gou * 0.62, y1 - 36)}',
        f'L{pt(xl - gou * 0.46, y1 - 34)}',
        f'Q{pt(xl - 4, y1 - 38)} {pt(xl, y1 - 56)}',
    ]


def shu_zhe(xr: float, ytop: float, y1: float, *, w: float = W_V + 3, gou: bool = False) -> str:
    """框的右竖连顶上的横折：横的顿角收在竖头，竖脚收圆（gou=True 则竖脚出钩）。xr 是竖的右缘，ytop 是顶横的上缘。"""
    xl = xr - w
    return path(
        f'M{pt(xr - 81, ytop)}',
        f'L{pt(xr - 40, ytop - 48)}',
        f'L{pt(xr + 53, ytop + 23)}',
        f'Q{pt(xr + 46, ytop + 30)} {pt(xr + 18, ytop + 44)}',
        f'Q{pt(xr + 8, ytop + 47)} {pt(xr, ytop + 48)}',
        *(_gou_foot(xl, xr, y1) if gou else _foot(xr, y1, xl)),
        f'L{pt(xl, ytop)}',
    )


Ctl = tuple[float, float, float, float]  # 三次曲线两个控制点，按“起点到终点的向量”取比例：(fx1, fy1, fx2, fy2)


def _ctl(p0, p3, c: Ctl):
    dx, dy = p3[0] - p0[0], p3[1] - p0[1]
    return (p0[0] + dx * c[0], p0[1] + dy * c[1]), (p0[0] + dx * c[2], p0[1] + dy * c[3])


# 曲线的比例，是在思源宋体的 木 从 白 的撇捺上拟合得到的
PIE_R: Ctl = (0.0, 0.38, 0.10, 0.64)
PIE_L: Ctl = (0.0, 0.40, 0.10, 0.66)
NA_U: Ctl = (0.16, 0.46, 0.46, 0.80)
NA_L: Ctl = (0.20, 0.20, 0.82, 0.70)


def pie(
    xa: float,
    ya: float,
    xe: float,
    ye: float,
    *,
    head: float = 112,
    tip: float = 22,
    plain: bool = False,
    right: Ctl | None = None,
    left: Ctl | None = None,
) -> str:
    """撇：(xa, ya) 是头部左上角，(xe, ye) 是收笔尖的中心。头部带斜切的顶，向下渐细，收笔平切。
    plain=True 是接在别的笔画里的撇（如木），起笔是平的，宽 head。right、left 是右、左两条边的曲线比例。"""
    a = (xa, ya)
    b = (xa + head, ya) if plain else (xa + head, ya + 26)
    r0 = b if plain else (xa + head * 0.67, ya + 47)
    tr = (xe + tip / 2, ye)
    tl = (xe - tip / 2, ye)
    rc1, rc2 = _ctl(r0, tr, right or PIE_R)
    lc1, lc2 = _ctl(tl, a, left or PIE_L)
    return path(
        f'M{pt(*a)}',
        f'L{pt(*b)}',
        *([] if plain else [f'Q{pt(b[0] - 5, ya + 47)} {pt(*r0)}']),
        f'C{pt(*rc1)} {pt(*rc2)} {pt(*tr)}',
        f'L{pt(*tl)}',
        f'C{pt(*lc1)} {pt(*lc2)} {pt(*a)}',
    )


def na(
    xa: float,
    ya: float,
    xe: float,
    ye: float,
    *,
    upper: Ctl | None = None,
    lower: Ctl | None = None,
    foot: tuple[float, float] = (-70, 65),
) -> str:
    """捺：从 (xa, ya) 细笔起，渐粗，到 (xe, ye) 出尖，再向左下收出脚（foot 是脚相对尖的位移）。"""
    s1 = (xa + 16, ya)
    s2 = (xa - 6, ya + 7)
    tip = (xe, ye)
    tip2 = (xe - 3, ye + 10)
    ft = (xe + foot[0], ye + foot[1])
    uc1, uc2 = _ctl(s1, tip, upper or NA_U)
    lc1, lc2 = _ctl(ft, s2, lower or NA_L)
    return path(
        f'M{pt(*s1)}',
        f'C{pt(*uc1)} {pt(*uc2)} {pt(*tip)}',
        f'L{pt(*tip2)}',
        f'Q{pt(tip2[0] - 22, tip2[1] + 2)} {pt(ft[0] + 15, ft[1] - 30)}',
        f'Q{pt(ft[0] + 4, ft[1] - 20)} {pt(*ft)}',
        f'C{pt(*lc1)} {pt(*lc2)} {pt(*s2)}',
    )


def na_duan(
    xs: float,
    ys: float,
    xe: float,
    ye: float,
    *,
    upper: Ctl = (0.35, 0.25, 0.75, 0.55),
    lower: Ctl = (0.0, -0.3, 0.1, -0.7),
    w: float = 14,
) -> str:
    """短捺（从 的左人：捺画短，到底圆收）。(xs, ys) 细笔起，(xe, ye) 是圆头的中心。"""
    s1 = (xs, ys)
    s2 = (xs - w, ys + 7)
    u = (xe + 16, ye - 38)
    b = (xe - 31, ye + 6)
    l0 = (xe - 51, ye - 11)
    uc1, uc2 = _ctl(s1, u, upper)
    lc1, lc2 = _ctl(l0, s2, lower)
    return path(
        f'M{pt(*s1)}',
        f'C{pt(*uc1)} {pt(*uc2)} {pt(*u)}',
        f'C{pt(u[0] - 1, u[1] + 22)} {pt(xe + 8, ye + 4)} {pt(*b)}',
        f'C{pt(b[0] - 12, b[1])} {pt(l0[0] + 2, l0[1] + 12)} {pt(*l0)}',
        f'C{pt(*lc1)} {pt(*lc2)} {pt(*s2)}',
    )


def shu_wan_gou(xl: float, y0: float, ybot: float, xhook: float, ytop_hook: float) -> str:
    """竖弯钩（屯、乚）：竖到底转成向右的横，末端向上出钩。
    xl 竖的左缘，y0 竖头尖，ybot 弯底的下缘，xhook 钩的右缘，ytop_hook 钩尖的高度。
    横段的长度随 xl 到 xhook 的距离伸缩（参考宽 493），钩和转弯的形状不变。"""
    xr = xl + W_V
    u = min(1.4, (xhook - xl) / 493)
    return path(
        f'M{pt(xl, y0 - 1)}',
        f'L{pt(xl + 103, y0 + 10)}',
        f'Q{pt(xl + 102, y0 + 20)} {pt(xl + 94.5, y0 + 27)}',
        f'Q{pt(xl + 87, y0 + 34)} {pt(xr, y0 + 37)}',
        f'L{pt(xr, ybot - 101)}',
        f'Q{pt(xr, ybot - 78)} {pt(xr + 25, ybot - 58)}',
        f'Q{pt(xr + 67 * u, ybot - 58)} {pt(xr + 130 * u, ybot - 58)}',
        f'L{pt(xhook - 230 * u, ybot - 58)}',
        f'Q{pt(xhook - 120, ybot - 58)} {pt(xhook - 90, ybot - 62)}',
        f'Q{pt(xhook - 73, ybot - 64)} {pt(xhook - 66, ybot - 76)}',
        f'Q{pt(xhook - 55, ybot - 120)} {pt(xhook - 45, ytop_hook + 60)}',
        f'Q{pt(xhook - 40, ytop_hook + 30)} {pt(xhook - 36, ytop_hook)}',
        f'L{pt(xhook - 22, ytop_hook)}',
        f'L{pt(xhook - 19, ybot - 72)}',
        f'Q{pt(xhook, ybot - 65)} {pt(xhook + 6, ybot - 52)}',
        f'Q{pt(xhook + 6, ybot - 34)} {pt(xhook - 24, ybot - 16)}',
        f'Q{pt(xhook - 126 * u, ybot)} {pt(xhook - 224 * u, ybot)}',
        f'L{pt(xl + 127 * u, ybot)}',
        f'Q{pt(xl + 73, ybot)} {pt(xl + 24, ybot - 16)}',
        f'Q{pt(xl, ybot - 55)} {pt(xl, ybot - 89)}',
    )


def shu_tail(xl: float, y0: float, y1: float) -> str:
    """竖（头有小钩），脚向左下拖出一个小尖尾（屯 左边的短竖）。y1 是竖脚转折处，尖尾再向下 33。"""
    xr = xl + W_V
    return path(
        f'M{pt(xl, y0)}',
        f'L{pt(xl + 100, y0 + 11)}',
        f'Q{pt(xl + 99, y0 + 21)} {pt(xl + 91, y0 + 29)}',
        f'Q{pt(xl + 83, y0 + 36)} {pt(xr, y0 + 38)}',
        f'L{pt(xr, y1)}',
        f'L{pt(xr + 8, y1)}',
        f'L{pt(xr - 16, y1 + 33)}',
        f'L{pt(xl - 33, y1 - 14)}',
        f'Q{pt(xl - 25, y1 - 22)} {pt(xl + 4, y1 - 39)}',
        f'Q{pt(xl + 10, y1 - 42)} {pt(xl + 16, y1 - 42)}',
        f'L{pt(xl, y1 - 6)}',
    )


def shu_duan(xl: float, y0: float, y1: float, *, w: float = W_V) -> str:
    """竖（头有小钩），脚平收，右下角微圆（屯 里面的短竖）。"""
    xr = xl + w
    return path(
        f'M{pt(xl, y0)}',
        f'L{pt(xl + 102, y0 + 12)}',
        f'Q{pt(xl + 101, y0 + 22)} {pt(xl + 93.5, y0 + 29)}',
        f'Q{pt(xl + 86, y0 + 36)} {pt(xr, y0 + 39)}',
        f'L{pt(xr, y1 - 22)}',
        f'Q{pt(xr, y1 - 18)} {pt(xr - 15, y1 - 7)}',
        f'Q{pt(xr - 40, y1)} {pt(xr - 53, y1)}',
        f'L{pt(xl, y1)}',
    )
