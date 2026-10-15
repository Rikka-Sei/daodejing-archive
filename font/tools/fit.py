#!/usr/bin/env python3
"""拟合：在思源宋体的参考字上量出部件的落点。parts.py 里各部件的坐标就是这样量出来再取整的。

做法：从上游字体（取定字重 400）里取参考字的轮廓，每一笔对应其中一个或几个轮廓；
用 strokes.py 的笔画函数按一组参数画出这一笔，与参考轮廓求重合度（交集面积 / 并集面积），
逐个参数加减步长、步长逐级减半地爬坡，直到重合度不再升高。只量落点与曲线比例，不取用参考字的轮廓本身。

用法（上游字体与 npm run fonts 用的是同一个文件，见 font.yaml 的 upstream）：
  python3 font/tools/fit.py --upstream NotoSerifSC[wght].ttf measure 臬 吾   # 列出参考字各轮廓的范围（y 向下）
  python3 font/tools/fit.py --upstream NotoSerifSC[wght].ttf fit cong_top     # 逐笔拟合，打印参数与重合度
  python3 font/tools/fit.py --upstream NotoSerifSC[wght].ttf fit              # 拟合全部登记的部件
轮廓的序号随上游字体而定；font.yaml 按 SHA-256 固定了上游版本，换版本要重新核对 SPECS 里的序号。
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pathops
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from build import load_config, static_instance  # noqa: E402
from glyphlib import ASCENT, _path  # noqa: E402
from parts import kou_frame  # noqa: E402
from strokes import heng, na, na_duan, pie, plain_shu, shu, shu_duan, shu_tail, shu_wan_gou, shu_zhe, ti  # noqa: E402

Model = Callable[[Sequence[float]], 'str | list[str]']


# ---- 参考字的轮廓与重合度 ----


def reference_font(upstream: Path, weight: int = 400) -> TTFont:
    return static_instance(TTFont(upstream), weight)


def contours(font: TTFont, ch: str) -> list[pathops.Path]:
    """参考字的各个轮廓，换到 y 向下、基线在 ASCENT 的坐标（与 SVG 一致）。"""
    glyf = font['glyf']
    rec = RecordingPen()
    glyf[font.getBestCmap()[ord(ch)]].draw(rec, glyf)  # 直接取 glyf 里的坐标（复合字形会展开）
    out, cur = [], pathops.Path()
    pen = TransformPen(cur.getPen(), (1, 0, 0, -1, 0, ASCENT))
    for op, args in rec.value:
        getattr(pen, op)(*args)
        if op in ('closePath', 'endPath'):
            out.append(cur)
            cur = pathops.Path()
            pen = TransformPen(cur.getPen(), (1, 0, 0, -1, 0, ASCENT))
    return out


def union(paths: Sequence[pathops.Path]) -> pathops.Path:
    acc = pathops.Path()
    for p in paths:
        acc = pathops.op(acc, p, pathops.PathOp.UNION, fix_winding=True)
    return acc


def drawn(d: str | list[str]) -> pathops.Path:
    return union([_path(x) for x in ([d] if isinstance(d, str) else d)])


def iou(a: pathops.Path, b: pathops.Path) -> float:
    """重合度：交集面积 / 并集面积。1 是完全重合，0 是毫不相交。"""
    u = abs(pathops.op(a, b, pathops.PathOp.UNION, fix_winding=True).area)
    i = abs(pathops.op(a, b, pathops.PathOp.INTERSECTION, fix_winding=True).area)
    return i / u if u and i <= u else 0.0


def climb(model: Model, x0: Sequence[float], target: pathops.Path, scale: Sequence[float],
          steps: Sequence[float] = (16, 8, 4, 2, 1, 0.5), rounds: int = 4) -> tuple[list[float], float]:
    """坐标爬坡：每个参数按 步长 × scale 加减一次，重合度升高就留下；一轮没有改进就把步长减半。"""
    x = [float(v) for v in x0]

    def score(v: Sequence[float]) -> float:
        try:
            return iou(drawn(model(v)), target)
        except (ValueError, ZeroDivisionError, pathops.PathOpsError):
            return 0.0

    best = score(x)
    for st in steps:
        for _ in range(rounds):
            improved = False
            for i in range(len(x)):
                for dv in (st * scale[i], -st * scale[i]):
                    y = list(x)
                    y[i] += dv
                    s = score(y)
                    if s > best + 1e-6:
                        best, x, improved = s, y, True
            if not improved:
                break
    return x, best


# ---- 各部件的拟合登记 ----


@dataclass
class Stroke:
    name: str
    contours: list[int]  # 参考字里对应的轮廓序号（见 measure 的输出）
    model: Model
    init: list[float]  # 起始参数：目测参考字填的大致位置；形状不参与拟合的笔画，就是取定的形状
    scale: list[float]  # 每个参数的步长倍数：坐标 1，曲线比例 0.01


def _p(v):  # 撇：头左上角、尖、头宽、尖宽、轻重、右边与左边的曲线比例
    return pie(v[0], v[1], v[2], v[3], head=v[4], tip=v[5], k=v[6], right=tuple(v[7:11]), left=tuple(v[11:15]))


def _pp(v):  # 接在横下的撇（起笔平）
    return pie(v[0], v[1], v[2], v[3], head=v[4], tip=v[5], k=v[6], plain=True, right=tuple(v[7:11]), left=tuple(v[11:15]))


def _n(v):  # 捺：起笔、尖、上下两边的曲线比例、脚、轻重
    return na(v[0], v[1], v[2], v[3], upper=tuple(v[4:8]), lower=tuple(v[8:12]), foot=(v[12], v[13]), k=v[14])


def _nd(v):  # 短捺（点）
    return na_duan(v[0], v[1], v[2], v[3], upper=tuple(v[4:8]), lower=tuple(v[8:12]), w=v[12], k=v[13])


NA_SCALE = [1] * 4 + [0.01] * 8 + [1, 1, 0.01]
# 头宽、尖宽、轻重这几个参数，单凭重合度会被拟到两头（尖细成一根线、头胖得失形），所以按目测取定、不参与爬坡（步长 0）
PIE_POS = [1] * 4 + [0] * 3 + [0.01] * 8


def POS_ONLY(n: int) -> list[float]:  # noqa: N802
    """只拟合起讫四个坐标，形状参数全按起始值：从 的撇和点细而弯，放开曲线比例会被拟出鼓包和毛刺。"""
    return [1] * 4 + [0] * (n - 4)

SPECS: dict[str, tuple[str, list[Stroke]]] = {
    'cong_top': ('怂', [
        Stroke('pie1', [2], _p, [271, 37, 47, 645, 85, 20, 1.17, 0.10, 0.29, 0.10, 0.67, 0.38, 0.22, 0.68, 0.12], POS_ONLY(15)),
        Stroke('na1', [3], _nd, [327, 244, 457, 448, 0.43, 0.25, 0.82, 0.39, -0.08, 0.02, -0.66, -0.50, 18, 0.96], POS_ONLY(14)),
        Stroke('pie2', [1], _p, [639, 40, 358, 622, 94, 21.5, 0.62, 0.04, 0.48, 0.08, 0.66, 0.33, 0.26, 0.90, 0.10], POS_ONLY(15)),
        Stroke('na2', [0], _n, [647, 86, 946, 611, 0.09, 0.64, 0.51, 0.80, 0.54, 0.12, 1.08, 0.62, -63, 65, 1], NA_SCALE),
    ]),
    'mu_bottom': ('臬', [
        Stroke('heng', [0], lambda v: heng(*v), [60, 945, 617], [1, 1, 1]),
        Stroke('shu', [3], lambda v: shu(*v), [470, 540, 958], [1, 1, 1]),
        Stroke('pie', [1], _pp, [470, 640, 60, 920, 99.5, 61, 1, 0.29, 0.22, 0.25, 0.50, 0.28, 0.17, 0.40, 0.41], PIE_POS),
        Stroke('na', [2], _n, [535, 630, 962, 900, 0.23, 0.38, 0.54, 0.80, 0.32, 0.12, 0.77, 0.57, -70, 65, 1], NA_SCALE),
    ]),
    'wang_left': ('珅', [
        Stroke('heng1', [0], lambda v: heng(*v), [42, 394, 138], [1, 1, 1]),
        Stroke('heng2', [1], lambda v: heng(*v), [50, 378, 414], [1, 1, 1]),
        Stroke('ti', [2], lambda v: ti(*v), [28, 770, 383, 657], [1, 1, 1, 1]),
        Stroke('shu', [3], lambda v: plain_shu(v[0], v[1], v[2], w=v[3]), [170, 153, 746, 65], [1, 1, 1, 1]),
    ]),
    'tun_right': ('纯', [
        Stroke('heng', [3], lambda v: heng(*v), [382, 960, 203], [1, 1, 1]),
        Stroke('bar', [0], lambda v: heng(*v, dun=False), [462, 855, 638], [1, 1, 1]),
        Stroke('zuo', [1, 2], lambda v: shu_tail(*v), [424, 318, 655], [1, 1, 1]),
        Stroke('you', [5], lambda v: shu_duan(v[0], v[1], v[2], w=v[3]), [824, 319, 706, 65], [1, 1, 1, 1]),
        Stroke('shu', [4], lambda v: shu_wan_gou(*v), [621, 45, 937, 965, 730], [1, 1, 1, 1, 1]),
    ]),
    'wu_kou': ('吾', [
        Stroke('mid', [5], lambda v: heng(*v, dun=False), [155, 711, 285], [1, 1, 1]),
        Stroke('long', [3], lambda v: heng(*v), [44, 962, 488], [1, 1, 1]),
        Stroke('zhe', [6], lambda v: shu_zhe(*v), [735, 270, 493], [1, 1, 1]),
        Stroke('kou', [0, 1, 2], lambda v: [d for _, d in kou_frame(v[0], v[1], v[2], v[3], [v[4]])],
               [206, 842, 580, 960, 875], [1, 1, 1, 1, 1]),
    ]),
}


# ---- 命令 ----


def measure(font: TTFont, chars: str) -> None:
    for ch in chars:
        for i, c in enumerate(contours(font, ch)):
            x0, y0, x1, y1 = c.bounds
            print(f'{ch} {i:2d}  x {x0:5.0f}–{x1:5.0f}  y {y0:5.0f}–{y1:5.0f}')


def fit(font: TTFont, names: Sequence[str]) -> None:
    for name in names:
        ch, specs = SPECS[name]
        cs = contours(font, ch)
        print(f'{name}（参考字 {ch}）')
        for s in specs:
            x, best = climb(s.model, s.init, union([cs[i] for i in s.contours]), s.scale)
            print(f"  {s.name:6s} 重合度 {best:.3f}  参数 {', '.join(f'{v:g}' for v in (round(t, 3) for t in x))}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--upstream', required=True, type=Path, help='固定版本的 NotoSerifSC[wght].ttf')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('measure', help='列出参考字各轮廓的范围').add_argument('chars')
    sub.add_parser('fit', help='逐笔拟合登记的部件').add_argument('parts', nargs='*', choices=list(SPECS))
    a = ap.parse_args()
    want = load_config()['upstream'].get('sha256')
    if want and hashlib.sha256(a.upstream.read_bytes()).hexdigest() != want:
        print('注意：上游字体与 font.yaml 登记的哈希不同，轮廓序号可能对不上', file=sys.stderr)
    font = reference_font(a.upstream)
    if a.cmd == 'measure':
        measure(font, a.chars)
    else:
        fit(font, a.parts or list(SPECS))


if __name__ == '__main__':
    main()
