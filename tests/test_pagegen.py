"""scripts/pagegen 的测试：只用占位字符，不含真实释文。"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from pagegen import check, cli, corpus, fonts, llms  # noqa: E402
from pagegen.textutil import colophon, common_id, facts, label_text, license_label, mark_damage, split_name  # noqa: E402


class TextUtil(unittest.TestCase):
    def test_label_text(self):
        self.assertEqual(label_text({"unit_type": "slip", "unit_no": "12"}), "简12")
        self.assertEqual(label_text({"unit_type": "chapter", "unit_no": "38"}), "第38章")
        self.assertEqual(label_text({"unit_type": "slip", "unit_no": "2背"}), "简2背")

    def test_common_id(self):
        self.assertEqual(common_id(["guodian-jia", "guodian-yi", "guodian-bing"]), "guodian")
        self.assertEqual(common_id(["w-a", "w-b"]), "w")
        self.assertEqual(common_id(["beida"]), "beida")
        self.assertEqual(common_id(["x-a", "y-b"]), "x-a")        # 没有共同前缀：取第一个

    def test_split_name(self):
        self.assertEqual(split_name("甲书《占位》甲组"), ("甲书", "甲组"))
        self.assertEqual(split_name("乙书《占位》"), ("乙书", "全本"))
        self.assertEqual(split_name("丙书"), ("丙书", "全本"))

    def test_mark_damage_escapes_and_wraps(self):
        out = mark_damage("甲<乙>丙丁", [{"kind": "missing", "start": 1, "end": 3}])
        self.assertEqual(out, '甲<span class="d-missing">&lt;乙</span>&gt;丙丁')

    def test_license_label(self):
        self.assertEqual(license_label({"status": "cc", "name": "CC BY-SA 4.0"}), "CC BY-SA 4.0")
        self.assertEqual(license_label({"status": "public-domain", "name": None}), "来源未标明，按可收录处理")
        self.assertEqual(license_label({"status": "unknown"}), "来源未标明")
        self.assertEqual(license_label(None), "来源未标明")

    def test_colophon_and_facts(self):
        w = {"excavated": {"year": 1993, "month": 10, "place": "某地"}, "slips": {"count": 39}}
        self.assertEqual(colophon(w), "1993年10月出土于某地；存简39枚。")
        self.assertEqual(dict(facts(w)), {"出土 / 入藏": "1993 年 10 月 · 某地", "简数": "39 枚"})


def make_corpus(root: Path):
    (root / "witnesses").mkdir(parents=True)
    (root / "plates").mkdir()
    (root / "sources").mkdir()
    (root / "witnesses.yaml").write_text(
        "witnesses:\n"
        "  - {id: w-a, name: 甲书《占位》甲组, excavated: {year: 2000, place: 某地}}\n"
        "  - {id: w-b, name: 甲书《占位》乙组}\n"
        "  - {id: w-c, name: 乙书}\n", encoding="utf-8")
    for wid, kind in (("w-a", "slip"), ("w-b", "slip"), ("w-c", "chapter")):
        rows = [{"id": f"{wid}.00{i}", "witness": wid, "unit_type": kind, "unit_no": str(i), "text": "甲乙丙",
                 "source_ref": {"source": "s"}, "status": "unverified",
                 "damage": [{"kind": "missing", "start": 1, "end": 2}]} for i in (1, 2)]
        (root / "witnesses" / f"{wid}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    plates = {"w-a": [("slip-plate", "a1.jpg"), ("page", "a2.jpg")], "w-b": [("photo", "b1.jpg")]}
    for wid, rows in plates.items():
        (root / "plates" / f"{wid}.jsonl").write_text("\n".join(json.dumps(
            {"file": f"data/images/{f}", "witness": wid, "source": "s", "kind": k, "locator": f"占位 第 {i} 页",
             "units": [f"{wid}.001"]}, ensure_ascii=False) for i, (k, f) in enumerate(rows, 1)), encoding="utf-8")
    (root / "sources" / "s.yaml").write_text(
        "id: s\ntitle: 占位来源\nurl: https://example.test/s\nwitnesses: [w-a]\n"
        "license: {status: cc, name: CC0, evidence: 占位依据}\nnotes: 占位备注\n"
        "retrieval: {status: fetched, date: '2026-01-02', files: [{path: data/raw/s/x.html, sha256: 0123456789abcdef0123}]}\n",
        encoding="utf-8")
    (root / "sources" / "t.yaml").write_text(
        "id: t\ntitle: 另一来源\nwitnesses: [w-a]\nlicense: {status: public-domain, name: null}\nretrieval: {status: pending}\n",
        encoding="utf-8")


class Model(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        make_corpus(Path(self.tmp.name) / "a")
        self.c = corpus.load_corpus("a", str(Path(self.tmp.name) / "a"), {"title": "占位书"})

    def test_groups_hold_each_documents_own_witnesses(self):
        self.assertEqual(self.c.title, "占位书")
        self.assertEqual([(g.name, g.id, [w.label for w in g.witnesses], g.single) for g in self.c.groups],
                         [("甲书", "w", ["甲组", "乙组"], False), ("乙书", "w-c", ["全本"], True)])

    def test_witness_title(self):
        self.assertEqual([w.title for w in self.c.witnesses], ["甲书 甲组", "甲书 乙组", "乙书"])

    def test_cover_plate_prefers_photo_then_page_then_slip(self):
        g = self.c.groups[0]
        self.assertEqual(g.cover_plate()["file"], "data/images/b1.jpg")       # 乙组有实物照片，优先于甲组的图版
        self.assertEqual(g.plates, 3)
        self.assertIsNone(self.c.groups[1].cover_plate())                      # 没有影像
        g.witnesses[1].plates.clear()
        self.assertEqual(g.cover_plate()["file"], "data/images/a2.jpg")       # 没有照片就取整页图版
        g.witnesses[0].plates.pop(1)
        self.assertEqual(g.cover_plate()["file"], "data/images/a1.jpg")

    def test_sources_of_witness(self):
        self.assertEqual([s["id"] for s in self.c.sources_of(self.c.witnesses[0])], ["s", "t"])
        self.assertEqual(self.c.sources_of(self.c.witnesses[1]), [])


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = Path(self.tmp.name)
        make_corpus(tmp / "a")
        make_corpus(tmp / "b")
        self.out = tmp / "out"
        corpora = [corpus.load_corpus("a", str(tmp / "a"), {"title": "典籍甲", "subtitle": "甲乙", "license_note": "占位授权说明"}),
                   corpus.load_corpus("b", str(tmp / "b"), {"title": "典籍乙"})]
        cli.build(corpora, self.out, base_url="https://example.test/x/", thumbnails=False)

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_files_generated(self):
        for f in ["index.html", "llms.txt", "llms-full.txt", "a/index.html", "a/data.html", "a/w-a.html",
                  "a/w-a.txt", "a/w-a.jsonl", "a/w-all.txt", "a/w-all.jsonl", "b/w-c.html", "b/data.html"]:
            self.assertTrue((self.out / f).exists(), f)
        self.assertFalse((self.out / "a" / "w-c-all.txt").exists())          # 只有一个本的文献没有合集

    def test_root_is_cover_of_first_corpus(self):
        root = self.read("index.html")
        self.assertIn("<h1>典籍甲</h1>", root)
        self.assertIn('href="a/w-a.html"', root)      # 文献卡片指向第一个本
        self.assertIn('id="preface"', root)           # 凡例

    def test_cover_has_one_card_per_document_and_lists_its_witnesses(self):
        text = self.read("a/index.html")
        self.assertEqual(text.count('<article class="doc">'), 2)                  # 甲书、乙书
        self.assertIn('<span class="t">甲书</span><span class="m">2 个版本 · 4 条释文 · 3 张影像</span>', text)
        self.assertIn('<div class="subs"><a href="w-a.html">甲组</a><a href="w-b.html">乙组</a></div>', text)
        self.assertIn('<span class="t">乙书</span><span class="m">2 条释文</span>', text)   # 只有一个本：不写版本数，没有子项
        self.assertEqual(text.count('class="subs"'), 1)
        self.assertIn('<span class="ph">甲</span>', text)                          # 不生成缩略图时用文字占位

    def test_cover_has_no_numbering_or_sources(self):
        text = self.read("a/index.html")
        for s in ("第一部分", "卷一", "卷三", 'id="sources"', '<span class="t">来源与授权</span>'):     # 来源与授权在各本页面里
            self.assertNotIn(s, text)
        self.assertIn("3 个版本 · 6 条释文 · 3 张影像", text)

    def test_cover_preface_generated_from_data(self):
        text = self.read("a/index.html")
        self.assertIn("释文照录来源，不改字", text)      # 没给 preface：用通用体例
        self.assertIn("只核对过一个来源", text)         # 全部 unverified，按数据补
        self.assertIn("SHA-256", text)

    def test_corpus_preface_replaces_generic_but_keeps_status_lines(self):
        c = corpus.load_corpus("a", str(Path(self.tmp.name) / "a"), {"preface": ["自拟的体例。"], "preface_extra": ["追加。"]})
        from pagegen.render import book
        items = book.preface_items(c)
        self.assertEqual(items[:2], ["自拟的体例。", "追加。"])
        self.assertNotIn("释文照录来源，不改字", "".join(items))
        self.assertIn("SHA-256", items[-1])

    def test_sidebar_tree_nests_each_documents_witnesses(self):
        page = self.read("a/w-b.html")
        self.assertIn('<details class="dir" data-g="w" open>', page)              # 甲书：文件夹
        self.assertIn('<span class="t">甲书</span>', page)
        self.assertIn('<a class="lk" href="w-a.html"><span class="t">甲组</span></a>', page)
        self.assertIn('<div class="item leaf on"><a class="lk" href="w-b.html" aria-current="page">', page)   # 当前本
        self.assertIn('<a class="lk" href="w-c.html"><svg', page)                  # 乙书只有一个本：直接一项，带文件图标
        self.assertNotIn('data-g="w-c"', page)
        self.assertNotIn("卷", page.split("<script>")[0].split("</style>")[1])      # 页面正文里没有“卷N”

    def test_sidebar_row_menu_offers_downloads(self):
        page = self.read("a/w-b.html")
        self.assertIn('href="w-a.txt" download="甲书-甲组.txt"', page)
        self.assertIn('href="w-a.jsonl" download="甲书-甲组.jsonl"', page)
        self.assertIn('href="w-all.txt" download="甲书-全部.txt"', page)           # 文件夹行：整部文献的合集
        self.assertIn("下载全部释文（.txt）", page)
        self.assertIn('href="w-c.txt" download="乙书.txt"', page)
        self.assertEqual(page.count('class="more"'), 4)                           # 一个文件夹 + 三个本
        self.assertIn('id="pop"', page)

    def test_download_paths_follow_the_page_location(self):
        self.assertIn('href="a/w-a.txt" download="甲书-甲组.txt"', self.read("index.html"))   # 站点根的封面
        self.assertIn('href="a/w-all.jsonl"', self.read("index.html"))

    def test_downloads_content(self):
        src = Path(self.tmp.name) / "a" / "witnesses"
        self.assertEqual(self.read("a/w-a.jsonl"), (src / "w-a.jsonl").read_text(encoding="utf-8") + "\n")
        self.assertEqual(self.read("a/w-all.jsonl"), self.read("a/w-a.jsonl") + self.read("a/w-b.jsonl"))
        text = self.read("a/w-all.txt")
        self.assertTrue(text.startswith("# 甲书\n"))
        self.assertIn("## 甲书《占位》甲组", text)
        self.assertIn("## 甲书《占位》乙组", text)
        self.assertLess(text.index("甲组"), text.index("乙组"))

    def test_volume_page_has_pager_and_search(self):
        page = self.read("a/w-b.html")
        self.assertIn("上一本", page)
        self.assertIn("下一本", page)
        self.assertIn('id="q"', page)
        self.assertIn('<a class="prev" href="w-a.html"><small>上一本</small>甲书 甲组</a>', page)
        self.assertNotIn("上一本", self.read("a/w-a.html"))      # 第一个本没有上一本
        self.assertNotIn("下一本", self.read("a/w-c.html"))      # 最后一个本没有下一本

    def test_crumb_follows_the_documents_own_levels(self):
        self.assertIn('<a href="index.html">典籍甲</a><span class="sep">›</span><span>甲书</span><span class="sep">›</span><b>乙组</b>',
                      self.read("a/w-b.html"))
        self.assertIn('<span class="sep">›</span><b>乙书</b></nav>', self.read("a/w-c.html"))   # 单个本：不多一级

    def test_corpus_switcher_only_when_multiple(self):
        page = self.read("a/w-a.html")
        self.assertIn('href="../b/index.html"', page)
        self.assertIn('class="sb-label">典籍<', page)

    def test_sidebar_switches_between_reading_and_data_view(self):
        page = self.read("a/w-b.html")
        self.assertIn('href="data.html#w-b"', page)         # 读到哪个本，数据版就落在哪个本
        self.assertIn('href="../llms.txt"', page)
        self.assertIn('id="to-read" class="on"', page)                      # 当前在哪种版式，哪个键亮
        self.assertIn('id="to-data" class="on"', self.read("a/data.html"))

    def test_search_box_scope(self):
        self.assertIn('data-go="data.html"', self.read("a/index.html"))      # 封面：带词去数据版
        self.assertNotIn("data-go", self.read("a/w-a.html"))                 # 本页：就地过滤
        self.assertNotIn("data-go", self.read("a/data.html"))

    def test_tools_follow_page_kind(self):
        cover, volume = self.read("a/index.html"), self.read("a/w-a.html")
        self.assertIn('data-k="theme"', cover)
        self.assertNotIn('data-k="layout"', cover)                           # 封面没有释文可排版
        for k in ("layout", "plates", "theme"):
            self.assertIn(f'data-k="{k}"', volume)

    def test_every_page_has_an_inline_favicon(self):                          # 否则浏览器会去请求 /favicon.ico，得到 404
        for rel in ("index.html", "a/index.html", "a/w-a.html", "a/data.html"):
            self.assertIn('<link rel="icon" href="data:image/svg+xml,%3Csvg', self.read(rel))

    def test_only_pages_with_text_get_the_wide_column(self):
        self.assertIn('<div class="content wide">', self.read("a/w-a.html"))
        self.assertIn('<div class="content wide">', self.read("a/data.html"))
        self.assertIn('<div class="content">', self.read("a/index.html"))

    def test_facts_fold_only_when_there_are_facts(self):
        fold = '<span class="t">版本信息</span>'
        self.assertIn(fold, self.read("a/w-a.html"))                          # w-a 登记了出土信息
        self.assertNotIn(fold, self.read("a/w-b.html"))

    def test_each_witness_page_shows_its_own_sources_and_license(self):
        fold = '<span class="t">来源与授权</span>'
        page = self.read("a/w-a.html")
        self.assertIn(fold, page)
        self.assertIn("占位来源", page)
        self.assertIn("2 个来源 · CC0、未标明", page)                           # 授权概要：各来源的授权名去重，没登记的记作未标明
        self.assertIn("占位授权说明", page)                                    # 授权说明来自典籍的设置
        self.assertIn("授权：CC0；抓取于 2026-01-02", page)
        self.assertIn("授权：来源未标明，按可收录处理；仅登记，未抓取", page)
        self.assertIn("<dt>授权依据</dt><dd>占位依据</dd>", page)               # 授权依据、备注、原始文件收在来源下面的折叠里
        self.assertIn("<dt>备注</dt><dd>占位备注</dd>", page)
        self.assertIn('href="https://github.com/Rikka-Sei/daodejing-archive/blob/main/data/raw/s/x.html"', page)
        self.assertIn("SHA-256 <code>0123456789ab…</code>", page)
        for rel in ("a/w-b.html", "a/w-c.html"):                              # 没有登记来源的本不显示
            self.assertNotIn(fold, self.read(rel))

    def test_data_page_has_all_versions_with_their_own_sources(self):
        page = self.read("a/data.html")
        for wid in ("w-a", "w-b", "w-c"):
            self.assertIn(f'id="w-{wid}"', page)
            self.assertIn(f'data-w="{wid}"', page)                             # 目录里每个本都能切换
        self.assertIn('id="q"', page)
        self.assertEqual(page.count('<span class="t">来源与授权</span>'), 1)    # 只有 w-a 登记了来源
        self.assertEqual(page.count("<p>"), page.count('<div class="u" '))        # 无属性的 <p> 只用于释文（字体子集按此区分释文与界面文字）
        self.assertNotIn('id="sources"', page)

    def test_llms_txt_format_and_base_url(self):
        text = self.read("llms.txt")
        self.assertTrue(text.startswith("# 典籍\n\n> "))
        self.assertIn("(https://example.test/x/a/w-a.txt)", text)
        self.assertIn("## 典籍甲", text)
        self.assertIn("## Optional", text)
        self.assertIn("[简1] 甲乙丙", self.read("llms-full.txt"))

    def test_links_resolve(self):
        self.assertEqual(check.check_links(self.out), [])

    def test_link_check_detects_missing_file_and_anchor(self):
        (self.out / "a" / "w-a.txt").unlink()
        self.assertTrue(any("w-a.txt" in p for p in check.check_links(self.out)))
        text = self.read("a/w-b.html")
        (self.out / "a" / "w-b.html").write_text(
            text.replace("</main>", '<a href="index.html#nope">x</a></main>'), encoding="utf-8")
        self.assertTrue(any("#nope" in p for p in check.check_links(self.out)))

    def test_link_check_covers_css_urls(self):
        page = self.out / "a" / "w-b.html"
        page.write_text(self.read("a/w-b.html").replace("</style>", "@font-face{src:url(../fonts/none.woff2)}</style>"),
                        encoding="utf-8")
        self.assertTrue(any("none.woff2" in p for p in check.check_links(self.out)))

    def test_witness_txt_lists_only_its_sources(self):
        c = corpus.load_corpus("a", str(Path(self.tmp.name) / "a"))
        self.assertIn("占位来源（授权：CC0） https://example.test/s", llms.witness_txt(c, c.witnesses[0]))
        self.assertIn("另一来源（授权：来源未标明，按可收录处理）", llms.witness_txt(c, c.witnesses[0]))
        self.assertNotIn("占位来源", llms.witness_txt(c, c.witnesses[1]))


class SingleCorpus(unittest.TestCase):
    def test_single_corpus_hides_switcher_and_titles_llms_by_book(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_corpus(tmp / "a")
            cli.build([corpus.load_corpus("a", str(tmp / "a"), {"title": "占位书"})], tmp / "out", thumbnails=False)
            self.assertNotIn('class="sb-label">典籍<', (tmp / "out" / "a" / "w-a.html").read_text(encoding="utf-8"))
            self.assertTrue((tmp / "out" / "llms.txt").read_text(encoding="utf-8").startswith("# 占位书\n"))


FAKE_FILES = [{"file": "s-400.woff2", "family": "sans", "weight": 400},
              {"file": "s-500.woff2", "family": "sans", "weight": 500},
              {"file": "f-400.woff2", "family": "serif", "weight": 400}]


class Fonts(unittest.TestCase):
    """用假的字体清单测机制：引用、复制、用字统计与覆盖提示。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "fonts-src"
        self.dir.mkdir()
        manifest = {"chars": "甲乙", "unavailable": "丙", "files": FAKE_FILES, "licenses": ["OFL.txt"]}
        (self.dir / "fonts.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        for name in [f["file"] for f in FAKE_FILES] + ["OFL.txt"]:
            (self.dir / name).write_bytes(name.encode())
        for patch in (mock.patch.object(fonts, "DIR", self.dir), mock.patch.object(fonts, "MANIFEST", self.dir / "fonts.json")):
            patch.start()
            self.addCleanup(patch.stop)

    def test_faces_and_preload_use_path_to_site_root(self):
        css = fonts.faces_css("../")
        self.assertIn('font-family:"DG Sans";font-weight:400;font-style:normal;font-display:swap;src:url(../fonts/s-400.woff2)', css)
        self.assertIn('font-family:"DG Serif";font-weight:400', css)
        self.assertEqual(css.count("@font-face"), 3)
        links = fonts.preload_links("")
        self.assertIn('href="fonts/s-400.woff2"', links)
        self.assertIn('href="fonts/f-400.woff2"', links)
        self.assertNotIn("s-500", links)                                           # 只提前加载每页都用的两个

    def test_no_manifest_means_system_fonts(self):
        with mock.patch.object(fonts, "MANIFEST", self.dir / "none.json"):
            self.assertEqual((fonts.faces_css(""), fonts.preload_links("")), ("", ""))
            self.assertEqual(fonts.uncovered({"甲"}), ("", ""))

    def test_copy_fonts_brings_files_licenses_and_manifest(self):
        out = Path(self.tmp.name) / "site"
        fonts.copy_fonts(out)
        self.assertEqual(sorted(p.name for p in (out / "fonts").iterdir()),
                         ["OFL.txt", "f-400.woff2", "fonts.json", "s-400.woff2", "s-500.woff2"])

    def test_visible_text_counts_what_is_drawn(self):
        page = ('<style>/* 注释甲 */a:before{content:"、"}</style><p>乙<b>丙</b></p><input placeholder="搜索">'
                '<img alt="替代" src="x.jpg" title="不画"><script>/* 注释丁 */ x("命中&lt;")</script>')
        text = fonts.visible_text(page)
        for ch in "乙丙搜索替代命中、":
            self.assertIn(ch, text)
        for ch in "注释甲丁不画<>":
            self.assertNotIn(ch, text.replace("命中<", ""))                          # 注释、标签、不会画出的属性不计

    def test_uncovered_splits_new_chars_from_unavailable_ones(self):
        self.assertEqual(fonts.uncovered({"甲", "乙", "丙", "丁", "戊"}), ("丁戊", "丙"))

    def test_build_ships_fonts_and_links_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_corpus(tmp / "a")
            out = tmp / "out"
            cli.build([corpus.load_corpus("a", str(tmp / "a"), {"title": "占位书"})], out, thumbnails=False)
            self.assertTrue((out / "fonts" / "s-400.woff2").exists())
            self.assertIn("url(../fonts/s-400.woff2)", (out / "a" / "w-a.html").read_text(encoding="utf-8"))
            self.assertIn("url(fonts/s-400.woff2)", (out / "index.html").read_text(encoding="utf-8"))    # 站点根的封面
            self.assertEqual(check.check_links(out), [])
            notes = cli.font_notes(out)
            self.assertTrue(any("不在固定字体里" in n for n in notes))               # 页面用到的字远多于假清单里的几个
            self.assertTrue(any("丙" in n for n in notes))

    def test_font_notes_without_fonts_point_to_the_script(self):
        with mock.patch.object(fonts, "MANIFEST", self.dir / "none.json"):
            self.assertIn("make_fonts.py", cli.font_notes(Path(self.tmp.name))[0])


@unittest.skipUnless(fonts.MANIFEST.exists(), "尚未生成固定字体")
class PinnedFonts(unittest.TestCase):
    def test_files_match_manifest(self):
        m = fonts.manifest()
        self.assertTrue(m["files"])
        for f in m["files"]:
            data = (fonts.DIR / f["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), f["sha256"], f["file"])
            self.assertEqual(len(data), f["bytes"])
        for name in m["licenses"]:
            self.assertIn("SIL OPEN FONT LICENSE", (fonts.DIR / name).read_text(encoding="utf-8").upper())
        self.assertFalse(set(m["chars"]) & set(m["unavailable"]))


class RealData(unittest.TestCase):
    def test_real_corpus_builds_and_links_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cli.main([d, "--no-thumbs"]), 0)
            self.assertIn("<h1>道德经</h1>", (Path(d) / "index.html").read_text(encoding="utf-8"))
            page = (Path(d) / "laozi" / "guodian-jia.html").read_text(encoding="utf-8")
            self.assertIn('<details class="dir" data-g="guodian" open>', page)     # 郭店楚简：三个本
            self.assertIn('data-g="mawangdui"', page)                              # 马王堆帛书：两个本
            self.assertNotIn('data-g="beida"', page)                               # 北大：只有一个本，直接一项
            self.assertTrue((Path(d) / "laozi" / "guodian-all.txt").exists())


if __name__ == "__main__":
    unittest.main()
