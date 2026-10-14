#!/usr/bin/env python3
"""把维基文库的原始页面切分成文本单位，写入 data/witnesses/<版本>.jsonl。

用法：python3 scripts/import_wikisource.py
只读取 data/raw/ 下已登记哈希的页面，不联网。text 照抄页面上的释文，只做两处机械处理：
  - 去掉 HTML 标签和首尾空白；
  - 删除段落内的换行符（HTML 源码折行，浏览器显示为空白，不是释文内容）；
  - 郭店一枚简跨两个段落时，段落之间用一个换行符连接。

郭店（wikisource-guodian）：《老子（甲乙丙）》一节里，每枚简的释文后紧跟简号数字，按简号切分。
马王堆（wikisource-boshu）：每个通行本章节下两段，上段甲本、下段乙本，按章切分。
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

GUODIAN = {"source": "wikisource-guodian", "raw": "data/raw/wikisource-guodian/2026-10-14.html"}
BOSHU = {"source": "wikisource-boshu", "raw": "data/raw/wikisource-boshu/2026-10-14.html"}


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip().replace("\n", "")


def content_area(page: str) -> str:
    return page[page.find('mw-parser-output'):page.find('class="printfooter"')]


def damage(text: str, pattern: str = r"□+|……") -> list[dict]:
    return [{"kind": "missing", "start": m.start(), "end": m.end()} for m in re.finditer(pattern, text)]


def marks(text: str, symbols: dict[str, str]) -> list[dict]:
    """symbols：来源符号 → mark 类型。括注（……）里的符号是整理者的说明，不算。"""
    out, depth = [], 0
    for i, ch in enumerate(text):
        depth += ch == "（"
        depth -= ch == "）"
        if depth == 0 and ch in symbols:
            out.append({"type": symbols[ch], "as_source": ch, "offset": i})
    return out


def unit(witness: str, seq: int, unit_type: str, unit_no: str, text: str, src: dict, locator: str,
         symbols: dict[str, str]) -> dict:
    u = {
        "id": f"{witness}.{seq:03d}",
        "witness": witness,
        "unit_type": unit_type,
        "unit_no": unit_no,
        "text": text,
        "source_ref": {"source": src["source"], "raw_file": src["raw"], "locator": locator},
        "status": "unverified",
    }
    if m := marks(text, symbols):
        u["marks"] = m
    if d := damage(text):
        u["damage"] = d
    return u


def guodian() -> dict[str, list[dict]]:
    page = (ROOT / GUODIAN["raw"]).read_text(encoding="utf-8")
    area = content_area(page)
    start = area.find('id="老子（甲乙丙）"')
    end = area.find('class="mw-heading', start)
    paras = [strip_tags(p) for p in re.findall(r"(?s)<p>(.*?)</p>", area[start:end])]
    groups: dict[str, list[str]] = {}
    current = None
    for p in paras:
        if p in ("甲", "乙", "丙"):
            current = p
            groups[current] = []
        elif p and current:
            groups[current].append(p)
    names = {"甲": "guodian-jia", "乙": "guodian-yi", "丙": "guodian-bing"}
    out = {}
    for g, ps in groups.items():
        wid = names[g]
        # 简文可跨段落（段落是整理者的分章，不是简的边界），所以整组连起来按简号切分，
        # 段落分隔以换行符保留在 text 里
        whole = "\n".join(ps)
        units = []
        for m in re.finditer(r"(\D+?)(\d+)", whole):
            text, no = m.group(1).strip(), m.group(2)
            expect = len(units) + 1
            if int(no) != expect:
                sys.exit(f"{wid}: 简号应为 {expect}，实为 {no}")
            units.append(unit(wid, expect, "slip", no, text, GUODIAN, f"老子（甲乙丙）/{g}/简{no}",
                              {"=": "repeat"}))
        if re.sub(r"[\s\d]", "", whole[whole.rfind(units[-1]["unit_no"]):]):
            sys.exit(f"{wid}: 最后一个简号之后还有文字")
        out[wid] = units
    return out


def boshu() -> dict[str, list[dict]]:
    page = (ROOT / BOSHU["raw"]).read_text(encoding="utf-8")
    area = content_area(page)
    parts = re.split(r'<div class="mw-heading mw-heading3"><h3 id="(\d+)_-_[^"]*"', area)
    out = {"mawangdui-jia": [], "mawangdui-yi": []}
    symbols = {"﹦": "repeat", "‧": "other", "∠": "other", "∟": "other"}
    for i in range(1, len(parts), 2):
        chap, content = parts[i], parts[i + 1]
        content = re.split(r'<div class="mw-heading', content)[0]
        paras = [strip_tags(p) for p in re.findall(r"(?s)<p>(.*?)</p>", content)]
        paras = [p for p in paras if p][:2]  # 第37章后附有版权模板段落
        if len(paras) != 2:
            sys.exit(f"第{chap}章应有甲乙两段，实有 {len(paras)} 段")
        for wid, text, row in zip(out, paras, ("上段（甲本）", "下段（乙本）")):
            out[wid].append(unit(wid, len(out[wid]) + 1, "chapter", chap, text, BOSHU, f"{chap} - 章/{row}",
                                 symbols))
    return out


def main() -> None:
    target = DATA / "witnesses"
    for wid, units in {**guodian(), **boshu()}.items():
        lines = [json.dumps(u, ensure_ascii=False) for u in units]
        (target / f"{wid}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{wid}: {len(units)} 条")


if __name__ == "__main__":
    main()
