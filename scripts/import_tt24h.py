#!/usr/bin/env python3
"""把 tt24h/daodejing（CC0）的北大汉简实录按简切分，写入 data/witnesses/beida.jsonl。

用法：python3 scripts/import_tt24h.py
只读取 data/raw/tt24h-daodejing/ 下已登记哈希的文件，不联网。

实录每行末尾的〚L…〛是简号（"2背"、"2正"这类原样保留在 unit_no），按它切分；
text 去掉简号标记和换行，其余照抄，只做一处机械处理：
  - 残字〚F字〛去掉外层记号，只留该字，残字范围记入 damage（uncertain）。
造字用的〚⿰…〛序列原样保留，一个〚…〛代表一个字。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = {"source": "tt24h-daodejing", "raw": "data/raw/tt24h-daodejing/v0.1.3/实录-北大汉简.txt"}
SYMBOLS = {"＝": "repeat", "◍": "section-mark", "〼": "other"}


def parse_slip(raw: str) -> tuple[str, list[dict], list[dict]]:
    """返回 (text, marks, damage)。"""
    text, damage, marks = "", [], []
    for m in re.finditer(r"〚F([^〚〛]+)〛|〚[^〛]+〛|.", raw):
        if m.group(1):
            damage.append({"kind": "uncertain", "start": len(text), "end": len(text) + len(m.group(1))})
            text += m.group(1)
        else:
            text += m.group(0)
    depth = 0
    for i, ch in enumerate(text):
        depth += ch == "〚"
        depth -= ch == "〛"
        if depth == 0 and ch in SYMBOLS:
            marks.append({"type": SYMBOLS[ch], "as_source": ch, "offset": i})
    damage += [{"kind": "missing", "start": m.start(), "end": m.end()} for m in re.finditer(r"□+", text)]
    damage.sort(key=lambda d: d["start"])
    return text, marks, damage


def beida() -> list[dict]:
    page = (ROOT / SRC["raw"]).read_text(encoding="utf-8")
    body = page[page.index("*/") + 2:]
    units = []
    for ln, line in enumerate(body.splitlines(), page[:page.index("*/")].count("\n") + 1):
        if not line.strip():
            continue
        m = re.fullmatch(r"(.+)〚L([^〛]+)〛", line)
        if not m:
            sys.exit(f"第 {ln} 行没有以简号结尾：{line}")
        text, marks, damage = parse_slip(m.group(1))
        u = {
            "id": f"beida.{len(units) + 1:03d}",
            "witness": "beida",
            "unit_type": "slip",
            "unit_no": m.group(2),
            "text": text,
            "source_ref": {"source": SRC["source"], "raw_file": SRC["raw"], "locator": f"第 {ln} 行"},
            "status": "unverified",
        }
        if marks:
            u["marks"] = marks
        if damage:
            u["damage"] = damage
        units.append(u)
    nos = [u["unit_no"] for u in units]
    expect = [str(n) for n in range(1, 222)]
    got = [re.sub(r"正$", "", n) for n in nos if not n.endswith("背")]
    if got != expect:
        sys.exit(f"简号不是 1–221 连续：{got[:5]}…")
    return units


def main() -> None:
    units = beida()
    path = ROOT / "data" / "witnesses" / "beida.jsonl"
    path.write_text("".join(json.dumps(u, ensure_ascii=False) + "\n" for u in units), encoding="utf-8")
    print(f"beida: {len(units)} 条")


if __name__ == "__main__":
    main()
