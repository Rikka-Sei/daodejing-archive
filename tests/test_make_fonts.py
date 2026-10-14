"""scripts/make_fonts.py 里的用字统计测试。统计不依赖 fonttools，所以这里不需要装它。"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("make_fonts", REPO / "scripts" / "make_fonts.py")
make_fonts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_fonts)


class VisibleText(unittest.TestCase):
    def test_counts_what_is_drawn(self):
        page = ('<style>/* 注释甲 */a:before{content:"、"}</style><p>乙<b>丙</b></p><input placeholder="搜索">'
                '<img alt="替代" src="x.jpg" title="不画"><script>/* 注释丁 */ x("命中&lt;")</script>')
        text = make_fonts.visible_text(page)
        for ch in "乙丙搜索替代命中、":
            self.assertIn(ch, text)
        for ch in "注释甲丁不画<>":
            self.assertNotIn(ch, text.replace("命中<", ""))      # 注释、标签、不会画出的属性不计

    def test_tiers_drop_unit_text_and_notes(self):
        page = '<h1>标题</h1><p>释文</p><div class="note">注</div><p class="x">界面</p>'
        self.assertEqual(make_fonts.visible_text(page, units=False, notes=False), "标题界面")
        self.assertEqual(make_fonts.visible_text(page, units=False), "标题注界面")
        self.assertEqual(make_fonts.visible_text(page), "标题释文注界面")


class SiteChars(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name)
        (self.site / "a").mkdir()
        (self.site / "a" / "index.html").write_text('<h1>标 题</h1><p>释文</p><div class="note">注</div>', encoding="utf-8")
        (self.site / "_astro").mkdir()
        (self.site / "_astro" / "x.css").write_text('/* 备忘 */a:before{content:"、"}', encoding="utf-8")
        (self.site / "_astro" / "app.js").write_text('/* 备忘 */var s="本页命中";', encoding="utf-8")

    def test_pages_plus_external_styles_and_scripts(self):
        chars = make_fonts.site_chars(self.site)
        for ch in "标题释文注、本页命中":
            self.assertIn(ch, chars)
        for ch in "备忘 ":
            self.assertNotIn(ch, chars)                           # 注释与空白不计

    def test_three_tiers(self):
        pools = make_fonts.used_chars(self.site)
        self.assertIn("释", pools["all"])
        self.assertNotIn("释", pools["text"])                     # 释文只用宋体 400
        self.assertIn("注", pools["text"])
        self.assertNotIn("注", pools["ui"])                       # 500 字重不含来源注释
        self.assertIn("标", pools["ui"])
        for pool in pools.values():
            self.assertTrue(set(make_fonts.EXTRA) <= pool)        # 常用标点一律带上

    def test_requires_a_built_site(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(SystemExit) as cm:
                make_fonts.main(["--site", empty])
            self.assertIn("npm run build", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
