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


def _gou_foot(xl: float, xr: float, y1: float) -> list[str]:
    """竖钩的脚（冊 的横折钩）：竖到底向左下圆转，钩向左平平地拖出一截，钩尖朝左上。y1 是钩底。"""
    return [
        f'L{pt(xr, y1 - 94)}',
        f'C{pt(xr, y1 - 50)} {pt(xr - 30, y1 - 4)} {pt(xr - 94, y1)}',
        f'C{pt(xr - 95, y1 - 15)} {pt(xr - 103, y1 - 41)} {pt(xr - 110, y1 - 48)}',
        f'C{pt(xr - 119, y1 - 57)} {pt(xr - 152, y1 - 68)} {pt(xr - 178, y1 - 72)}',
        f'L{pt(xr - 178, y1 - 88)}',
        f'L{pt(xr - 85, y1 - 81)}',
        f'Q{pt(xl, y1 - 81)} {pt(xl, y1 - 102)}',
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
    k: float = 1.0,
) -> str:
    """撇：(xa, ya) 是头部左上角，(xe, ye) 是收笔尖的中心。头部带斜切的顶，向下渐细，收笔平切。
    plain=True 是接在别的笔画里的撇（如木），起笔是平的，宽 head。right、left 是右、左两条边的曲线比例。
    k 是笔画的轻重系数：小部件里的撇要比正文里的细，头部的斜切随之缩小。"""
    a = (xa, ya)
    b = (xa + head, ya) if plain else (xa + head, ya + 26 * k)
    r0 = b if plain else (xa + head * 0.67, ya + 47 * k)
    tr = (xe + tip / 2, ye)
    tl = (xe - tip / 2, ye)
    rc1, rc2 = _ctl(r0, tr, right or PIE_R)
    lc1, lc2 = _ctl(tl, a, left or PIE_L)
    return path(
        f'M{pt(*a)}',
        f'L{pt(*b)}',
        *([] if plain else [f'Q{pt(b[0] - 5 * k, ya + 47 * k)} {pt(*r0)}']),
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
    k: float = 1.0,
) -> str:
    """捺：从 (xa, ya) 细笔起，渐粗，到 (xe, ye) 出尖，再向左下收出脚（foot 是脚相对尖的位移）。k 是笔画的轻重系数。"""
    s1 = (xa + 16 * k, ya)
    s2 = (xa - 6 * k, ya + 7 * k)
    tip = (xe, ye)
    tip2 = (xe - 3 * k, ye + 10 * k)
    ft = (xe + foot[0] * k, ye + foot[1] * k)
    uc1, uc2 = _ctl(s1, tip, upper or NA_U)
    lc1, lc2 = _ctl(ft, s2, lower or NA_L)
    return path(
        f'M{pt(*s1)}',
        f'C{pt(*uc1)} {pt(*uc2)} {pt(*tip)}',
        f'L{pt(*tip2)}',
        f'Q{pt(tip2[0] - 22 * k, tip2[1] + 2 * k)} {pt(ft[0] + 15 * k, ft[1] - 30 * k)}',
        f'Q{pt(ft[0] + 4 * k, ft[1] - 20 * k)} {pt(*ft)}',
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
    k: float = 1.0,
) -> str:
    """短捺（从 的左人：捺画短，到底圆收）。(xs, ys) 细笔起，(xe, ye) 是圆头的中心。k 是笔画的轻重系数。"""
    s1 = (xs, ys)
    s2 = (xs - w * k, ys + 7 * k)
    u = (xe + 16 * k, ye - 38 * k)
    b = (xe - 31 * k, ye + 6 * k)
    l0 = (xe - 51 * k, ye - 11 * k)
    uc1, uc2 = _ctl(s1, u, upper)
    lc1, lc2 = _ctl(l0, s2, lower)
    return path(
        f'M{pt(*s1)}',
        f'C{pt(*uc1)} {pt(*uc2)} {pt(*u)}',
        f'C{pt(u[0] - 1 * k, u[1] + 22 * k)} {pt(xe + 8 * k, ye + 4 * k)} {pt(*b)}',
        f'C{pt(b[0] - 12 * k, b[1])} {pt(l0[0] + 2 * k, l0[1] + 12 * k)} {pt(*l0)}',
        f'C{pt(*lc1)} {pt(*lc2)} {pt(*s2)}',
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


def ti(xa: float, ya: float, xe: float, ye: float) -> str:
    """提：(xa, ya) 是起笔顿头的左上角，向右上挑出，(xe, ye) 是笔尖的上缘。起笔粗、笔尖细，如 王 作偏旁时的末笔。"""
    dx, dy = xe - xa, ye - ya
    return path(
        f'M{pt(xa, ya)}',
        f'Q{pt(xa + 0.4 * dx, ya + 0.33 * dy)} {pt(xe, ye)}',
        f'L{pt(xe + 3, ye + 14)}',
        f'L{pt(xa + 57, ya + 57)}',
        f'Q{pt(xa + 54, ya + 66)} {pt(xa + 35, ya + 82)}',
    )


def shu_wan_gou_r(xl: float, y0: float, ybot: float, xr: float, yhook: float) -> str:
    """右旁的竖弯钩（沌 纯 的屯）：竖到底圆转成平的横，末端竖直向上出一个细钩。
    xl 竖的左缘，y0 竖头尖，ybot 横的下缘，xr 钩脚最右处，yhook 钩尖的高度。"""
    xs = xl + 65
    return path(
        f'M{pt(xl, y0)}',
        f'L{pt(xl + 101, y0 + 12)}',
        f'Q{pt(xl + 100, y0 + 22)} {pt(xl + 85, y0 + 30)}',
        f'Q{pt(xl + 76, y0 + 37)} {pt(xs, y0 + 39)}',
        f'L{pt(xs, ybot - 95)}',
        f'Q{pt(xs, ybot - 61)} {pt(xs + 48, ybot - 61)}',
        f'L{pt(xr - 184, ybot - 61)}',
        f'Q{pt(xr - 99, ybot - 62)} {pt(xr - 85, ybot - 66)}',
        f'Q{pt(xr - 73, ybot - 72)} {pt(xr - 64, ybot - 110)}',
        f'Q{pt(xr - 55, ybot - 150)} {pt(xr - 47, yhook)}',
        f'L{pt(xr - 34, yhook)}',
        f'L{pt(xr - 31, ybot - 70)}',
        f'Q{pt(xr, ybot - 58)} {pt(xr, ybot - 41)}',
        f'Q{pt(xr, ybot - 10)} {pt(xr - 186, ybot)}',
        f'L{pt(xl + 102, ybot)}',
        f'Q{pt(xl, ybot)} {pt(xl, ybot - 78)}',
    )


def xie_shu(xt: float, yt: float, xb: float, yb: float, *, w: float = 70) -> str:
    """斜竖（吾 的 五 里那一笔）：笔直、粗细不变地向左下斜，头上有竖的小钩，脚平收在横上。
    (xt, yt) 是头的左上角，(xb, yb) 是脚的左下角，w 是水平方向的宽。"""
    s = (xb - xt) / (yb - yt)  # 每向下一个单位，向左（负）挪多少
    return path(
        f'M{pt(xt, yt)}',
        f'L{pt(xt + 102, yt + 12)}',
        f'Q{pt(xt + 101, yt + 22)} {pt(xt + 93.5, yt + 29)}',
        f'Q{pt(xt + 86, yt + 36)} {pt(xt + w + s * 39, yt + 39)}',
        f'L{pt(xb + w, yb)}',
        f'L{pt(xb, yb)}',
    )
