"""字库 font/：笔画库、SVG 读取、合并进字体、改名、拟合工具，以及登记的 6 个手绘字。

构建用一个很小的合成字体当“上游”，不下载思源宋体；真正的上游字体由 npm run fonts 生成时核对哈希。
运行：python3 -m unittest tests.test_font（需要 fonttools、skia-pathops、pyyaml）
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'font'))
sys.path.insert(0, str(ROOT / 'font' / 'tools'))

import build as fontbuild  # noqa: E402
import draw  # noqa: E402
import fit  # noqa: E402
import glyphlib  # noqa: E402
import parts  # noqa: E402
import strokes  # noqa: E402
from fontTools.fontBuilder import FontBuilder  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402


def square(x0, y0, x1, y1):
    pen = TTGlyphPen(None)
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()
    return pen.glyph()


def fake_upstream(path: Path) -> Path:
    """合成的“上游”：.notdef、国、A；有 vmtx（竖排度量），带 Noto 风格的名字。"""
    fb = FontBuilder(1000, isTTF=True)
    order = ['.notdef', 'uni56FD', 'A']
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({0x56FD: 'uni56FD', 0x41: 'A'})
    fb.setupGlyf({'.notdef': square(50, 0, 450, 700), 'uni56FD': square(99, -78, 944, 821), 'A': square(40, 0, 560, 700)})
    fb.setupHorizontalMetrics({g: (1000, 50) for g in order})
    fb.setupHorizontalHeader(ascent=880, descent=-120)
    fb.setupVerticalMetrics({g: (1000, 59) for g in order})
    fb.setupVerticalHeader(ascent=500, descent=-500)
    fb.setupNameTable(
        {
            'familyName': 'Noto Serif SC',
            'styleName': 'Regular',
            'copyright': '(c) Adobe',
            'trademark': 'Noto is a trademark of Google Inc.',
            'licenseDescription': 'This Font Software is licensed under the SIL Open Font License, Version 1.1.',
        }
    )
    fb.setupOS2(usWeightClass=400)
    fb.setupPost()
    fb.save(path)
    return path


def rects(*boxes):
    """几个矩形笔画的 SVG 路径"""
    return [f'M{a},{b} L{c},{b} L{c},{d} L{a},{d} Z' for a, b, c, d in boxes]


class StrokeTest(unittest.TestCase):
    def test_every_stroke_is_a_closed_path_within_the_em_box(self):
        samples = [
            strokes.heng(100, 900, 500),
            strokes.heng(100, 900, 500, dun=False),
            strokes.shu(400, 100, 900),
            strokes.shu(400, 100, 900, head=False),
            strokes.shu_qie(200, 100, 900),
            strokes.shu_zhe(800, 200, 900),
            strokes.shu_zhe(800, 200, 900, gou=True),
            strokes.pie(400, 100, 300, 500),
            strokes.na(500, 300, 900, 800),
            strokes.na_duan(300, 400, 480, 730),
            strokes.shu_wan_gou(620, 45, 940, 965, 730),
            strokes.plain_shu(170, 150, 735),
            strokes.ti(30, 770, 380, 660),
            strokes.xie_shu(405, 50, 300, 490),
            strokes.shu_tail(160, 320, 650),
            strokes.shu_duan(750, 330, 720),
        ]
        for d in samples:
            self.assertTrue(d.startswith('M') and d.endswith('Z'), d)
            g = glyphlib.to_glyph([d])
            self.assertGreater(g.numberOfContours, 0, d)

    def test_stroke_weight_matches_regular(self):
        """横 30、竖 66：量自思源宋体 Regular，别随手改"""
        self.assertEqual((strokes.T_H, strokes.W_V), (30, 66))

    def test_union_merges_overlapping_strokes_into_one_contour(self):
        g = glyphlib.to_glyph(rects((100, 100, 500, 130), (280, 100, 320, 600)))
        self.assertEqual(g.numberOfContours, 1)

    def test_svg_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'u.svg'
            glyphlib.write_svg(f, [('a', 'M0,0 L10,0 L10,10 Z'), ('b', 'M20,20 L30,20 L30,30 Z')], title='甲')
            self.assertEqual([i for i, _ in glyphlib.read_strokes(f)], ['a', 'b'])

    def test_y_axis_is_flipped_around_the_baseline(self):
        g = glyphlib.to_glyph(rects((0, 0, 100, 100)))  # SVG 里在字身框顶部
        g.recalcBounds(None)
        self.assertEqual((g.yMin, g.yMax), (780, 880))


class FitTest(unittest.TestCase):
    def test_overlap_is_area_of_intersection_over_union(self):
        a, b = (glyphlib._path(d) for d in rects((0, 0, 100, 100), (50, 0, 150, 100)))
        self.assertAlmostEqual(fit.iou(a, a), 1.0)
        self.assertAlmostEqual(fit.iou(a, b), 1 / 3)
        self.assertEqual(fit.iou(a, glyphlib._path(rects((200, 0, 300, 100))[0])), 0.0)

    def test_reference_contours_are_flipped_like_the_svgs(self):
        with tempfile.TemporaryDirectory() as tmp:
            font = fit.reference_font(fake_upstream(Path(tmp) / 'up.ttf'))
            (c,) = fit.contours(font, '国')
        self.assertEqual(tuple(round(v) for v in c.bounds), (99, 880 - 821, 944, 880 + 78))

    def test_climbing_recovers_a_shifted_stroke(self):
        target = glyphlib._path(strokes.shu(300, 100, 800))
        x, best = fit.climb(lambda v: strokes.shu(*v), [280, 130, 760], target, [1, 1, 1])
        self.assertGreater(best, 0.99)
        self.assertEqual([round(v) for v in x], [300, 100, 800])

    def test_every_registered_stroke_draws(self):
        for name, (ch, specs) in fit.SPECS.items():
            for s in specs:
                self.assertEqual(len(s.init), len(s.scale), f'{name}.{s.name}')
                self.assertGreater(fit.drawn(s.model(s.init)).area, 0, f'{name}.{s.name}')


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.upstream = fake_upstream(self.dir / 'up.ttf')
        (self.dir / 'g').mkdir()
        glyphlib.write_svg(self.dir / 'g/u20000.svg', [(f's{i}', d) for i, d in enumerate(rects((100, 100, 900, 130), (480, 100, 520, 900)))], title='甲')
        self.cfg = {
            'family': 'TestSong',
            'style': 'Regular',
            'version': '0.1.0',
            'vendor': 'TEST',
            'designer': 'me',
            'upstream': {'name': 'Noto Serif SC', 'weight': 400},
            'glyphs': [{'cp': 0x20000, 'char': '𠀀', 'svg': 'g/u20000.svg'}],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, **over):
        cfg = {**self.cfg, **over}
        return fontbuild.build(self.upstream, self.dir / 'out.ttf', cfg, root=self.dir)

    def test_glyph_is_added_with_cmap_and_metrics(self):
        f = TTFont(self.dir / 'out.ttf') if self.build() else None
        g = f.getBestCmap()[0x20000]
        self.assertEqual(g, 'u20000')
        self.assertEqual(f['hmtx'][g][0], 1000)
        glyph = f['glyf'][g]
        glyph.recalcBounds(f['glyf'])
        self.assertEqual(f['hmtx'][g][1], glyph.xMin)
        # 竖排：与“国”共用同一个字符原点（国 tsb 59 + yMax 821 = 880）
        self.assertEqual(f['vmtx'][g], (1000, 880 - glyph.yMax))

    def test_original_glyphs_are_untouched(self):
        self.build()
        f = TTFont(self.dir / 'out.ttf')
        self.assertEqual(f.getBestCmap()[0x56FD], 'uni56FD')
        self.assertEqual(f['maxp'].numGlyphs, 4)

    def test_renamed_and_license_kept(self):
        self.build()
        n = TTFont(self.dir / 'out.ttf')['name']
        self.assertEqual(n.getDebugName(1), 'TestSong')
        self.assertEqual(n.getDebugName(4), 'TestSong Regular')
        self.assertEqual(n.getDebugName(6), 'TestSong-Regular')
        for i in (1, 3, 4, 6):
            self.assertNotIn('Noto', n.getDebugName(i))
        self.assertIsNone(n.getDebugName(7))  # 上游的商标声明不沿用
        self.assertIn('SIL Open Font License', n.getDebugName(13))
        self.assertIn('Adobe', n.getDebugName(0))

    def test_same_input_gives_same_bytes(self):
        self.build()
        a = (self.dir / 'out.ttf').read_bytes()
        self.build()
        self.assertEqual(a, (self.dir / 'out.ttf').read_bytes())

    def test_refuses_a_codepoint_the_upstream_already_has(self):
        with self.assertRaises(SystemExit) as cm:
            self.build(glyphs=[{**self.cfg['glyphs'][0], 'cp': 0x56FD}])
        self.assertIn('已经有了', str(cm.exception))

    def test_refuses_a_changed_upstream(self):
        with self.assertRaises(SystemExit) as cm:
            self.build(upstream={**self.cfg['upstream'], 'sha256': '0' * 64})
        self.assertIn('校验失败', str(cm.exception))

    def test_refuses_an_svg_without_strokes(self):
        (self.dir / 'g/u20000.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        with self.assertRaises(SystemExit):
            self.build()


class RegisteredGlyphsTest(unittest.TestCase):
    cfg = fontbuild.load_config()

    def test_six_glyphs_each_with_an_svg(self):
        self.assertEqual([g['char'] for g in self.cfg['glyphs']], list('𠂤𠕁𠚕𣐩𤤀𭇁'))
        for g in self.cfg['glyphs']:
            self.assertEqual(ord(g['char']), g['cp'])
            self.assertEqual(g['svg'], f"glyphs/u{g['cp']:05X}.svg")
            self.assertTrue((ROOT / 'font' / g['svg']).exists(), g['svg'])
            self.assertTrue(g['refs'].strip(), f"{g['char']} 没有登记参考字")

    def test_svgs_are_what_draw_py_produces(self):
        """SVG 与 draw.py 同步：只改了其中一边就会失败"""
        with tempfile.TemporaryDirectory() as tmp:
            for cp, (ch, fn) in draw.GLYPHS.items():
                f = Path(tmp) / f'u{cp:05X}.svg'
                glyphlib.write_svg(f, fn(), title=f'{ch} U+{cp:04X}')
                self.assertEqual(f.read_text(encoding='utf-8'), (ROOT / 'font/glyphs' / f.name).read_text(encoding='utf-8'), f.name)

    def test_outlines_sit_inside_the_em_box_with_room_to_spare(self):
        for g in self.cfg['glyphs']:
            glyph = glyphlib.to_glyph([d for _, d in glyphlib.read_strokes(ROOT / 'font' / g['svg'])])
            glyph.recalcBounds(None)
            self.assertGreaterEqual(glyph.xMin, 20, g['char'])
            self.assertLessEqual(glyph.xMax, 980, g['char'])
            self.assertGreaterEqual(glyph.yMin, -100, g['char'])
            self.assertLessEqual(glyph.yMax, 860, g['char'])
            self.assertGreater(glyph.yMax - glyph.yMin, 700, g['char'])  # 与正文的字一样高

    def test_parts_scale_positions_but_not_stroke_weight(self):
        """部件压扁挤窄，笔画仍和正文一样粗：横笔画的纵向厚度不变"""
        for yt, yb in ((50, 900), (50, 400)):
            g = glyphlib.to_glyph([d for _, d in parts.wang_left(50, 450, yt, yb) if _ == 'wang-heng1'])
            g.recalcBounds(None)
            # 顶横上缘到下缘：顿角之外的横身厚 30，顿角最高 65 + 13
            self.assertLess(g.yMax - g.yMin, 110)

    def test_license_names_the_derivative_and_the_original(self):
        text = (ROOT / 'font/OFL.txt').read_text(encoding='utf-8')
        for needle in ('Google Inc.', 'Adobe', 'Rikka-Sei', 'SIL OPEN FONT LICENSE Version 1.1', 'DaoSong'):
            self.assertIn(needle, text)


if __name__ == '__main__':
    unittest.main()
