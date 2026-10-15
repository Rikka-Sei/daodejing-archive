"""scripts/alignment.py 与 scripts/import_alignment.py 的测试。所用文本是明显的占位字符，不是任何真实版本的释文。
最后两组读仓库里的 data/alignment/ 与 tt24h 原始文件：只核对结构、一致与能否原样重新生成，不测字句。
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import alignment as al  # noqa: E402
import import_alignment  # noqa: E402

# (tt24h 的写法, 解析出的格)
CELLS = [
    ("", {}),
    ("甲", {"t": "甲"}),
    ("[甲][][][]", {"t": "甲"}),
    ("[〚F甲〛][][][]", {"t": "甲", "f": "残"}),
    ("[〚F〚⿰甲乙〛〛][][][]", {"t": "〚⿰甲乙〛", "f": "残"}),
    ("[][脱文][][]", {"f": "脱"}),
    ("[甲][衍文][][]", {"t": "甲", "f": "衍"}),
    ("[][占位][][]", {"f": "占"}),
    ("[][补文：甲][][]", {"t": "甲", "f": "补"}),
    ("[甲][（乙）][][]", {"t": "甲", "r": "乙"}),
    ("[甲][〈乙〉][][]", {"t": "甲", "c": "乙"}),
    ("[甲][][📝丙][]", {"t": "甲", "n": "丙"}),
    ("[甲][][][〚L12〛]", {"t": "甲", "l": "12"}),
    ("[甲][][][，]", {"t": "甲", "p": "，"}),
    ("[〚F甲〛][（乙）][📝丙][〚L3〛]", {"t": "甲", "f": "残", "r": "乙", "n": "丙", "l": "3"}),
]


class Cells(unittest.TestCase):
    def test_parse_and_write_back(self):
        for raw, cell in CELLS:
            with self.subTest(raw=raw):
                self.assertEqual(al.parse_cell(raw), cell)
                self.assertEqual(al.cell_raw(cell), al.canonical_raw(raw))  # 解析不丢信息

    def test_bad_cells(self):
        for raw, why in [
            ("[甲][][]", "[][][][]"),
            ("[甲][乙][][]", "第二段"),
            ("[甲][][丙][]", "📝"),
            ("[甲][补文：乙][][]", "补文格"),
            ("[〚F甲〛][衍文][][]", "两个标记"),
        ]:
            with self.subTest(raw=raw), self.assertRaises(al.AlignmentError) as cm:
                al.parse_cell(raw)
            self.assertIn(why, str(cm.exception))

    def test_json_form(self):
        self.assertEqual(al.cell_json({}), "")
        self.assertEqual(al.cell_json({"t": "甲"}), "甲")
        self.assertEqual(list(al.cell_json({"p": "，", "l": "1", "r": "乙", "f": "残", "t": "甲"})), ["t", "f", "r", "l", "p"])
        for raw, cell in CELLS:
            self.assertEqual(al.cell_from_json(al.cell_json(cell)), cell)

    def test_which_cells_appear_in_the_transcript(self):
        self.assertEqual(al.token_of({"t": "甲"}), "甲")
        self.assertEqual(al.token_of({"t": "甲", "f": "残"}), "〚F甲〛")
        self.assertEqual(al.token_of({"t": "□"}), "□")
        for cell in [{}, {"f": "脱"}, {"t": "甲", "f": "补"}, {"f": "占"}, {"t": "▩"}, {"t": "🅰"}]:
            self.assertIsNone(al.token_of(cell), cell)


class Keys(unittest.TestCase):
    def test_chapter_key(self):
        for key, want in [("第一章", (1, "")), ("第九章", (9, "")), ("第十章", (10, "")), ("第十九章", (19, "")),
                          ("第二十章", (20, "")), ("第六十四章B", (64, "B")), ("第八十一章", (81, ""))]:
            self.assertEqual(al.chapter_key(key), want, key)
        for bad in ["第章", "一章", "第一章ab", "第百章"]:
            with self.assertRaises(al.AlignmentError, msg=bad):
                al.chapter_key(bad)

    def test_tokenize(self):
        self.assertEqual(al.tokenize("甲〚F乙〛〚⿰丙〚⿱丁戊〛〛𠀀"), ["甲", "〚F乙〛", "〚⿰丙〚⿱丁戊〛〛", "𠀀"])
        with self.assertRaises(al.AlignmentError):
            al.tokenize("甲〚⿰乙")


class Order(unittest.TestCase):
    def cells(self, *ts):
        return [(i, {"t": t}) for i, t in enumerate(ts)]

    def test_sentences_back_in_the_order_of_the_original(self):
        # ▩…▦ 之间的句子按 🅰🅱 排回底本顺序；▩ ▦ 本身不留
        got = al.physical_order(self.cells("甲", "▩", "🅱", "乙", "🅰", "丙", "▦", "丁"))
        self.assertEqual([c for c, _ in got], [0, 4, 5, 2, 3, 7])

    def test_unchanged_without_marks(self):
        cells = self.cells("甲", "乙", "丙")
        self.assertEqual(al.physical_order(cells), cells)

    def test_unclosed_block(self):
        with self.assertRaises(al.AlignmentError):
            al.physical_order(self.cells("▩", "🅰", "甲"))


class Matching(unittest.TestCase):
    def chapter(self, s, **last):
        return [(i, {"t": t, **last.get(str(i), {})}) for i, t in enumerate(s)]

    def test_resolve_orders_chapters_by_the_transcript(self):
        chapters = {"第二章": self.chapter("丁戊"), "第一章": self.chapter("甲乙丙")}
        order = al.resolve(chapters, list("甲乙丙丁戊"), {}, "测试")
        self.assertEqual(order, [("第一章", [(0, 0, 1), (1, 1, 2), (2, 2, 3)]), ("第二章", [(0, 3, 4), (1, 4, 5)])])

    def test_what_each_line_points_to(self):
        order = [("第一章", [(0, 0, 1), (1, 1, 2), (2, 2, 3)]), ("第二章", [(0, 3, 4), (1, 4, 5)]), ("第六十四章B", [(0, 5, 6)])]
        lines = [{"tokens": list("甲乙")}, {"tokens": list("丙丁戊")}, {"tokens": list("己")}]
        self.assertEqual(al.line_refs(order, lines), [[[1, [0, 1]]], [[1, [2]], [2, [0, 1]]], [[64, [0], "B"]]])

    def test_gap_stands_for_any_number_of_missing(self):
        # 〼 代表任意个 □，但它后面紧跟的单个 □ 格要留出来
        chapter = self.chapter("甲〼乙")
        self.assertEqual(al.match_chapter(chapter, list("甲□□□乙"), 0, {}), (5, [(0, 0, 1), (1, 1, 4), (2, 4, 5)]))
        chapter = self.chapter("甲〼□乙")
        self.assertEqual(al.match_chapter(chapter, list("甲□□□乙"), 0, {}), (5, [(0, 0, 1), (1, 1, 3), (2, 3, 4), (3, 4, 5)]))

    def test_line_end_must_agree(self):
        chapter = self.chapter("甲乙", **{"0": {"l": "1"}})
        self.assertIsNotNone(al.match_chapter(chapter, list("甲乙"), 0, {"1": 1}))
        self.assertIsNone(al.match_chapter(chapter, list("甲乙"), 0, {"1": 2}))

    def test_no_match_is_an_error(self):
        with self.assertRaises(al.AlignmentError) as cm:
            al.resolve({"第一章": self.chapter("甲乙")}, list("甲丙"), {}, "测试")
        self.assertIn("对不上任何一章", str(cm.exception))

    def test_ambiguous_match_is_an_error(self):
        with self.assertRaises(al.AlignmentError) as cm:
            al.resolve({"第一章": self.chapter("甲乙"), "第二章": self.chapter("甲乙")}, list("甲乙"), {}, "测试")
        self.assertIn("都对得上", str(cm.exception))

    def test_left_over_chapter_is_an_error(self):
        with self.assertRaises(al.AlignmentError):
            al.resolve({"第一章": self.chapter("甲乙"), "第二章": self.chapter("丙")}, list("甲乙"), {}, "测试")


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, name, text):
        p = self.tmp / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_records(self):
        p = self.write("a.typ", '/* 格式说明 "不算" */\n// "注释"\n#let H数据H = (\n  "第一章&校订&甲&[乙][][][，]&",\n  "第二章&弼本&丙",\n)\n')
        self.assertEqual(al.read_records(p), [("第一章", "校订", ["甲", "[乙][][][，]", ""]), ("第二章", "弼本", ["丙"])])
        with self.assertRaises(al.AlignmentError):
            al.read_records(self.write("b.typ", '/* x */\n"第一章&校订"'))
        with self.assertRaises(al.AlignmentError):
            al.read_records(self.write("c.typ", '"第一章&校订&甲"'))  # 没有头部说明

    def test_transcript(self):
        p = self.write("t.txt", "/*\n*\t【底本】：占位底本\n*\t【参照书】：占位参照\n*\t【别的】：不取\n*/\n甲乙〚L1〛\n一章\n丙□〚L2〛\n")
        info, lines = al.read_transcript(p)
        self.assertEqual(info, {"底本": "占位底本", "参照书": "占位参照"})
        self.assertEqual([(l["no"], l["text"], l["heading"]) for l in lines], [("1", "甲乙", False), (None, "一章", True), ("2", "丙□", False)])
        self.assertEqual(lines[2]["tokens"], ["丙", "□"])
        self.assertEqual([l["line"] for l in lines], [6, 7, 8])

    def test_equivalents(self):
        p = self.write("e.typ", '#let I数组-规则视同测试失败I = ("∟", "＝")\n#let I数组-规则视同空字符串I = ("□", "〼")\n'
                                '#let I数组-规则视同相等I = (\n  ("甲", "子"),\n  ("乙","丑","寅"),\n)\n')
        self.assertEqual(al.read_equivalents(p), {"fail": ["∟", "＝"], "blank": ["□", "〼"], "same": [["甲", "子"], ["乙", "丑", "寅"]]})

    def test_glyphs(self):
        head = "#let I数组-表意文字描述序列至码位I = (\n"
        p = self.write("g.typ", head + '  ("〚⿰甲乙〛", "e000"),\n  ("〚⿱甲乙〛", "20001"),\n)\n')
        self.assertEqual(al.read_glyphs(p), {"〚⿰甲乙〛": "E000", "〚⿱甲乙〛": "20001"})
        with self.assertRaises(al.AlignmentError):
            al.read_glyphs(self.write("h.typ", head + '  ("〚⿰甲乙〛", "E000"),\n  ("〚⿰甲乙〛", "E001"),\n)\n'))

    def test_typst_markup_in_notes(self):
        self.assertEqual(al.clean_typst('#IDS("〚⿰甲乙〛")同 #box(baseline: 1pt)[丙] \\[丁\\]'), "〚⿰甲乙〛同 丙 [丁]")

    def test_load(self):
        (self.tmp / "data/alignment/chapters").mkdir(parents=True)
        (self.tmp / "data/alignment/lines").mkdir()
        rows = [{"version": "x", "cells": [al.cell_json(c) for c in ({"t": "甲"}, {}, {"t": "乙", "f": "残", "l": "1"})]}]
        (self.tmp / "data/alignment/chapters/001.json").write_text(json.dumps({"chapter": 1, "columns": 3, "rows": rows, "notes": []}), encoding="utf-8")
        line = {"no": "1", "text": "甲〚F乙〛", "refs": [[1, [0, 2]]]}
        (self.tmp / "data/alignment/lines/x.jsonl").write_text(json.dumps(line) + "\n\n", encoding="utf-8")
        chapters, lines = al.load(self.tmp)
        self.assertEqual(chapters[1]["rows"][0]["cells"], [{"t": "甲"}, {}, {"t": "乙", "f": "残", "l": "1"}])
        self.assertEqual(lines, {"x": [line]})
        self.assertEqual(al.verify(chapters, lines, total=1, known={"x"}), [])


def tiny():
    """两章、两个版本的对读表和一个版本的逐行释文，彼此一致。"""
    chapters = {
        1: {"chapter": 1, "columns": 3, "notes": [], "rows": [
            {"version": "jiaoding", "cells": [{"t": "甲"}, {"t": "乙"}, {"t": "丙"}]},
            {"version": "x", "cells": [{"t": "甲"}, {"t": "乙"}, {"t": "丙", "l": "1"}]},
        ]},
        2: {"chapter": 2, "columns": 3, "notes": [], "rows": [
            {"version": "jiaoding", "cells": [{"t": "丁"}, {"t": "戊"}, {}]},
            {"version": "x", "cells": [{"t": "丁"}, {"t": "戊", "l": "2"}, {"f": "脱"}]},
        ]},
    }
    lines = {"x": [
        {"no": "1", "text": "甲乙丙", "refs": [[1, [0, 1, 2]]]},
        {"no": "2", "text": "丁戊", "refs": [[2, [0, 1]]]},
    ]}
    return chapters, lines


class Verify(unittest.TestCase):
    KNOWN = {"jiaoding", "x"}

    def problems(self, mutate=lambda chapters, lines: None, **kw):
        chapters, lines = tiny()
        mutate(chapters, lines)
        return al.verify(chapters, lines, total=2, known=kw.get("known", self.KNOWN))

    def test_consistent(self):
        self.assertEqual(self.problems(), [])

    def assertProblem(self, text, mutate, **kw):
        got = self.problems(mutate, **kw)
        self.assertTrue(any(text in p for p in got), f"{text!r} 不在 {got}")

    def test_missing_chapter(self):
        self.assertProblem("缺第 2 章", lambda ch, ln: ch.pop(2))

    def test_ragged_row(self):
        self.assertProblem("有 2 格，本章应是 3 格", lambda ch, ln: ch[1]["rows"][0]["cells"].pop())

    def test_unknown_version(self):
        self.assertProblem("不是已知的版本", lambda ch, ln: ch[1]["rows"][0].update(version="nope"))
        self.assertProblem("逐行释文 y: 不是已知的版本", lambda ch, ln: ln.update(y=[]))
        self.assertProblem("x: 不是已知的版本", lambda ch, ln: None, known={"jiaoding"})

    def test_duplicate_row(self):
        self.assertProblem("重复的行", lambda ch, ln: ch[1]["rows"].append(dict(ch[1]["rows"][1])))

    def test_token_differs_from_the_cell(self):
        self.assertProblem("记号 丁 对到第 1 章第 2 列", lambda ch, ln: ln["x"][0].update(text="甲乙丁"))

    def test_cell_without_a_character(self):
        self.assertProblem("对到第 2 章第 2 列，那一格是 None", lambda ch, ln: ln["x"][1].update(text="丁戊己", refs=[[2, [0, 1, 2]]]))

    def test_number_of_tokens_and_refs(self):
        self.assertProblem("2 个记号，对应关系却有 3 个", lambda ch, ln: ln["x"][0].update(text="甲乙"))

    def test_cell_nobody_points_to(self):
        self.assertProblem("被 0 个记号指向", lambda ch, ln: ln["x"][0].update(text="甲乙", refs=[[1, [0, 1]]]))

    def test_cell_pointed_to_twice(self):
        self.assertProblem("被 2 个记号指向", lambda ch, ln: ln["x"].append({"no": "3", "text": "丁", "refs": [[2, [0]]]}))

    def test_points_to_a_row_that_is_not_there(self):
        self.assertProblem("那里没有 x 这一行", lambda ch, ln: ch[2]["rows"].pop())
        self.assertProblem("第 1 章没有第 9 列", lambda ch, ln: ln["x"][0].update(refs=[[1, [0, 1, 9]]]))

    def test_duplicate_line_number(self):
        self.assertProblem("简号或行号重复", lambda ch, ln: ln["x"][1].update(no="1"))

    def test_line_number_must_sit_on_the_last_token(self):
        self.assertProblem("行号 1 不在实录里该行的最后一个记号上", lambda ch, ln: (ch[1]["rows"][1]["cells"][2].pop("l"), ch[1]["rows"][1]["cells"][1].update(l="1")))

    def test_part_of_the_chapter(self):
        # 郭店六十四章分两段：同一版本同一章有两行，行上带 part，实录指向 [章, 列, 分段]
        def mutate(ch, ln):
            ch[1]["rows"][1:] = [{"version": "x", "part": "A", "cells": [{"t": "甲"}, {"t": "乙"}, {}]}, {"version": "x", "part": "B", "cells": [{}, {}, {"t": "丙", "l": "1"}]}]
            ln["x"][0]["refs"] = [[1, [0, 1], "A"], [1, [2], "B"]]
        self.assertEqual(self.problems(mutate), [])


class RealData(unittest.TestCase):
    def test_tables_and_transcripts_agree(self):
        chapters, lines = al.load(REPO)
        self.assertEqual(sorted(chapters), list(range(1, 82)))
        self.assertEqual(al.verify(chapters, lines), [])

    def test_importer_regenerates_every_file_exactly(self):
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "import_alignment.py"), "--root", str(REPO), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("全部一致", r.stdout)


class Importer(unittest.TestCase):
    """在一份拷贝上动手脚，看导入脚本能不能发现。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / al.RAW, self.tmp / al.RAW)
        shutil.copytree(REPO / al.OUT, self.tmp / al.OUT)
        (self.tmp / "data/witnesses").mkdir()
        for wid in ("wangbi", "jiaoding"):
            shutil.copy(REPO / f"data/witnesses/{wid}.jsonl", self.tmp / f"data/witnesses/{wid}.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_importer(self, *args):
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "import_alignment.py"), "--root", str(self.tmp), *args], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def test_untouched_copy_passes(self):
        code, out, err = self.run_importer("--check")
        self.assertEqual(code, 0, err)

    def test_hand_edited_table_is_reported(self):
        path = self.tmp / al.OUT / "chapters" / "001.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"notes"', '"notes" ', 1), encoding="utf-8")
        code, out, err = self.run_importer("--check")
        self.assertEqual(code, 1)
        self.assertIn("chapters/001.json 与重新生成的结果不一致", err)

    def test_stray_file_is_reported(self):
        (self.tmp / al.OUT / "lines" / "stray.jsonl").write_text("", encoding="utf-8")
        code, out, err = self.run_importer("--check")
        self.assertEqual(code, 1)
        self.assertIn("lines/stray.jsonl", err)

    def test_changed_transcript_is_rejected_and_nothing_is_written(self):
        path = self.tmp / al.RAW / "实录-王弼本.txt"
        text = path.read_text(encoding="utf-8")
        body = text.index("*/") + 2
        i = next(i for i in range(body, len(text)) if "一" <= text[i] <= "鿿")
        path.write_text(text[:i] + "占" + text[i + 1:], encoding="utf-8")
        before = {p: p.read_bytes() for p in (self.tmp / al.OUT).rglob("*") if p.is_file()}
        code, out, err = self.run_importer()
        self.assertEqual(code, 1)
        self.assertIn("对不上", err)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.tmp / al.OUT).rglob("*") if p.is_file()})

    def test_write_mode_reproduces_the_committed_files(self):
        shutil.rmtree(self.tmp / al.OUT)
        code, out, err = self.run_importer()
        self.assertEqual(code, 0, err)
        code, out, err = self.run_importer("--check")
        self.assertEqual(code, 0, err)
        for p in (REPO / al.OUT).rglob("*"):
            if p.is_file():
                self.assertEqual(p.read_bytes(), (self.tmp / p.relative_to(REPO)).read_bytes(), p.name)

    def test_build_is_deterministic_python_api(self):
        files = import_alignment.build(self.tmp)
        self.assertEqual(len([k for k in files if "/chapters/" in k]), 81)
        self.assertIn(f"{al.OUT}/glyphs.json", files)


if __name__ == "__main__":
    unittest.main()
