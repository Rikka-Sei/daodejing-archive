"""命令行入口与流程编排。

站点结构（每部典籍一个目录 <id>/）：
  index.html            阅读版封面：文献卡片、凡例
  <本>.html             阅读版的一个本
  data.html             数据版：所有版本一页，跨版本检索
  <本>.txt / .jsonl     纯文本释文、释文数据（与仓库里的 jsonl 逐字相同）
  <文献>-all.txt / .jsonl  有多个本的文献的合集
  thumbs/               影像缩略图
站点根的 index.html 是第一部典籍的封面；llms.txt、llms-full.txt、fonts/（固定字体）也在根目录。
"""
import argparse
from pathlib import Path

import yaml

from . import fonts, llms
from .check import check_links
from .corpus import load_corpus
from .render import Ctx, book, data_view
from .thumbs import Thumbs

PRESETS = Path(__file__).resolve().parent / "presets"
# 本仓库 data/ 的展示信息在 presets/laozi.yaml；其他典籍用目录里的 corpus.yaml。
DEFAULT_CORPORA = [("laozi", "data", yaml.safe_load((PRESETS / "laozi.yaml").read_text(encoding="utf-8")))]

DESCRIPTION = """生成静态站点：阅读版（封面、凡例、每个本一页）、数据版、纯文本与 jsonl 下载、llms.txt。
一部典籍 = 一个目录（结构同 data/），可含 corpus.yaml 写标题、副题、简介、凡例。"""


def build(corpora, out_root: Path, base_url: str = "", thumbnails: bool = True, ship_fonts: bool = True) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    all_thumbs = {}
    for c in corpora:
        out_dir = out_root / c.id
        out_dir.mkdir(parents=True, exist_ok=True)
        all_thumbs[c.id] = thumbs = Thumbs(out_dir, thumbnails)
        ctx = Ctx(to_root="../", cdir="")
        llms.write_downloads(c, out_dir)
        for w in c.witnesses:
            (out_dir / f"{w.id}.html").write_text(book.volume(c, w, corpora, ctx, thumbs), encoding="utf-8")
        (out_dir / "index.html").write_text(book.cover(c, corpora, ctx, thumbs), encoding="utf-8")
        (out_dir / "data.html").write_text(data_view.data_page(c, corpora, ctx, thumbs), encoding="utf-8")
    first = corpora[0]
    (out_root / "index.html").write_text(
        book.cover(first, corpora, Ctx(to_root="", cdir=f"{first.id}/"), all_thumbs[first.id]), encoding="utf-8")
    llms.write_llms(corpora, out_root, base_url.rstrip("/"))
    if ship_fonts:
        fonts.copy_fonts(out_root)
    (out_root / ".nojekyll").write_text("", encoding="utf-8")


def parse_specs(values):
    if not values:
        return DEFAULT_CORPORA
    return [tuple(v.split("=", 1)) + ({},) for v in values]


def font_notes(out_root: Path) -> list:
    """站点用字与固定字体的对照：提示要不要重新生成子集，以及只能靠系统字体显示的字。"""
    if not fonts.manifest():
        return ["没有固定字体（scripts/pagegen/assets/fonts/），页面用系统字体；先运行 scripts/make_fonts.py"]
    fresh, system = fonts.uncovered(fonts.site_chars(out_root))
    notes = []
    if fresh:
        notes.append(f"{len(fresh)} 个字不在固定字体里，暂用系统字体显示：{fresh}；重新运行 scripts/make_fonts.py 可收进子集")
    if system:
        notes.append(f"{len(system)} 个字固定字体本身没有，由系统字体显示：{system}")
    return notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument("out", nargs="?", default="site", help="输出目录，默认 site")
    ap.add_argument("--corpus", action="append", metavar="ID=目录", help="收录一部典籍，可重复；默认 laozi=data")
    ap.add_argument("--base-url", default="", help="llms.txt 里链接用的站点根地址，默认相对链接")
    ap.add_argument("--no-thumbs", action="store_true", help="不生成缩略图，只放原图链接")
    args = ap.parse_args(argv)

    corpora = [load_corpus(cid, path, meta) for cid, path, meta in parse_specs(args.corpus)]
    out_root = Path(args.out).resolve()
    build(corpora, out_root, args.base_url, not args.no_thumbs)
    for c in corpora:
        print(f"{c.title}：{len(c.witnesses)} 个版本，{c.totals[0]} 条文本，{c.totals[1]} 张影像")
    for note in font_notes(out_root):
        print("字体：", note)
    problems = check_links(out_root)
    for p in problems:
        print("链接检查：", p)
    print(f"已生成 {out_root}" + (f"（{len(problems)} 个链接问题）" if problems else "，链接检查通过"))
    return 1 if problems else 0
