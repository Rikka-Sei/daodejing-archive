"""tt24h/daodejing（CC0）对齐表的解析、拼回与核对。import_alignment.py 与 validate_data.py 共用本模块。

tt24h 给出两样东西：
  - 排版数据（*.typ）：每章每个版本一条记录 "第N章&版本标记&格&格…"，同章各版本的格数相同、同列对齐。
    一格写作 [正文][通行字或标记][尾注框][行号或断句]，含义见各 .typ 文件头部的"格式说明"。
  - 实录（实录-*.txt）：各底本照简、照行的原文，每行末尾〚L…〛是简号或行号。
对齐表按王弼本分章，同一章里各本句子的顺序可能与底本不同（▩…▦ 之间，🅰🅱🅲 标出底本顺序）。
本模块把对齐表按底本顺序拼回去，逐字对上实录；对不上就报错，不写任何文件。

一个格在本仓库里写成 JSON：空格写 ""；只有正文的格写成字符串；其余写成对象，键如下（没有的不写）：
  t 正文        f 标记：残（只存部分字迹）、衍（衍文）、脱（脱文，t 为空）、补（整理者补的脱文，t 是补上的字）、占（占位）
  r 通行字      c 正确字（讹字的纠正）      n 尾注框（边线字母，见 tt24h 的格式说明）
  l 简号或行号  p 断句标点（只有校订本有）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAW = "data/raw/tt24h-daodejing/v0.1.3"
OUT = "data/alignment"
SOURCE = "tt24h-daodejing"
CHAPTERS = 81

# 对读表的行序与 tt24h 的表格一致。id 是版本登记表里的 id，label 是 .typ 里的版本标记，short 是页面上行首的简称，
# unit 是实录里一行的性质（简或帛书一行），line_prefix 用来把郭店实录按甲乙丙拆开。
VERSIONS = [
    {"id": "jiaoding", "label": "校订", "short": "校订", "typ": "校订本.typ"},
    {"id": "wangbi", "label": "弼本", "short": "王弼", "typ": "王弼本.typ", "transcript": "实录-王弼本.txt"},
    {"id": "beida", "label": "北大", "short": "北大", "typ": "北大本.typ", "transcript": "实录-北大汉简.txt", "unit": "slip"},
    {"id": "mawangdui-jia", "label": "帛甲", "short": "帛甲", "typ": "帛书甲本.typ", "transcript": "实录-帛书甲本.txt", "unit": "silk-line"},
    {"id": "mawangdui-yi", "label": "帛乙", "short": "帛乙", "typ": "帛书乙本.typ", "transcript": "实录-帛书乙本.txt", "unit": "silk-line"},
    {"id": "guodian-jia", "label": "郭甲", "short": "郭甲", "typ": "郭店本.typ", "transcript": "实录-郭店楚简.txt", "unit": "slip", "line_prefix": "甲"},
    {"id": "guodian-yi", "label": "郭乙", "short": "郭乙", "typ": "郭店本.typ", "transcript": "实录-郭店楚简.txt", "unit": "slip", "line_prefix": "乙"},
    {"id": "guodian-bing", "label": "郭丙", "short": "郭丙", "typ": "郭店本.typ", "transcript": "实录-郭店楚简.txt", "unit": "slip", "line_prefix": "丙"},
]
BY_LABEL = {v["label"]: v for v in VERSIONS}
BY_ID = {v["id"]: v for v in VERSIONS}

# 实录之外用到的 tt24h 文件：通行字规则、造字码位、尾注、概述与参考书目
EQUIV_FILE = "共用通行字.typ"
GLYPH_FILE = "字符.typ"
NOTES_FILE = "尾注和补充行号.typ"
OVERVIEW_FILE = "概述和参考书目等.typ"

ORDER_MARKS = "▩▦🅰🅱🅲🅳🅴"   # 句序标记：整理者加的，实录里没有
BLOCK_LABELS = tuple("🅰🅱🅲🅳🅴")
GAP = "〼"                    # 多个连续的 □，不计数量
FLAG_OF_MID = {"衍文": "衍", "脱文": "脱", "占位": "占"}
MID_OF_FLAG = {v: k for k, v in FLAG_OF_MID.items()}
DIGITS = {c: i for i, c in enumerate("零一二三四五六七八九")}


class AlignmentError(Exception):
    """数据对不上。"""


# ── 章键 ────────────────────────────────────────────────────

def chapter_key(key: str) -> tuple[int, str]:
    """'第十九章' → (19, '')；'第六十四章B' → (64, 'B')。"""
    m = re.fullmatch(r"第([零一二三四五六七八九十]+)章([A-Z]?)", key)
    if not m:
        raise AlignmentError(f"看不懂的章键：{key}")
    s = m.group(1)
    if "十" in s:
        a, _, b = s.partition("十")
        n = (DIGITS[a] if a else 1) * 10 + (DIGITS[b] if b else 0)
    else:
        n = DIGITS[s]
    return n, m.group(2)


# ── 格 ──────────────────────────────────────────────────────

def _balanced(s: str) -> bool:
    depth = 0
    for ch in s:
        depth += ch == "〚"
        depth -= ch == "〛"
        if depth < 0:
            return False
    return depth == 0


def parse_cell(raw: str) -> dict:
    """tt24h 的一格 → {t, f, r, c, n, l, p}。没有的项不写；空格得到 {}。"""
    if raw == "":
        return {}
    if not raw.startswith("["):
        return {"t": raw}
    parts = raw[1:-1].split("][") if raw.endswith("]") else []
    if len(parts) != 4:
        raise AlignmentError(f"格不是 [][][][] 的形式：{raw}")
    t, mid, note, last = parts
    cell: dict = {}
    m = re.fullmatch(r"〚F(.+)〛", t, re.S)
    if m and _balanced(m.group(1)):
        cell["f"] = "残"
        t = m.group(1)
    if mid.startswith("补文："):
        if t:
            raise AlignmentError(f"补文格不应再有正文：{raw}")
        cell["f"] = "补"
        t = mid[len("补文："):]
        mid = ""
    elif mid in FLAG_OF_MID:
        if "f" in cell:
            raise AlignmentError(f"一格上有两个标记：{raw}")
        cell["f"] = FLAG_OF_MID[mid]
        mid = ""
    if t:
        cell = {"t": t, **cell}
    if mid:
        r = re.fullmatch(r"（(.+)）", mid, re.S)
        c = re.fullmatch(r"〈(.+)〉", mid, re.S)
        if r:
            cell["r"] = r.group(1)
        elif c:
            cell["c"] = c.group(1)
        else:
            raise AlignmentError(f"第二段不是（通行字）、〈正确字〉或已知标记：{raw}")
    if note:
        if not note.startswith("📝"):
            raise AlignmentError(f"尾注框应以📝起始：{raw}")
        cell["n"] = note[1:]
    if last:
        m = re.fullmatch(r"〚L(.+)〛", last, re.S)
        if m:
            cell["l"] = m.group(1)
        else:
            cell["p"] = last
    return cell


def cell_raw(cell: dict) -> str:
    """parse_cell 的逆运算，写成 tt24h 的规范形式 [][][][]；用来核对解析没有丢信息。"""
    t, f = cell.get("t", ""), cell.get("f")
    mid = ""
    if f == "残":
        t = f"〚F{t}〛"
    elif f == "补":
        mid, t = f"补文：{t}", ""
    elif f in MID_OF_FLAG:
        mid = MID_OF_FLAG[f]
    if "r" in cell:
        mid = f"（{cell['r']}）"
    elif "c" in cell:
        mid = f"〈{cell['c']}〉"
    note = f"📝{cell['n']}" if "n" in cell else ""
    last = f"〚L{cell['l']}〛" if "l" in cell else cell.get("p", "")
    return f"[{t}][{mid}][{note}][{last}]"


def canonical_raw(raw: str) -> str:
    """tt24h 的一格写成规范形式：空格和只有一个字的格都补成 [][][][]。"""
    if raw == "":
        return "[][][][]"
    return raw if raw.startswith("[") else f"[{raw}][][][]"


def token_of(cell: dict) -> str | None:
    """这一格在实录里对应的记号；实录里没有的格（脱文、补文、占位、句序标记、空格）返回 None。"""
    t = cell.get("t", "")
    if not t or cell.get("f") in ("脱", "补", "占") or t in ORDER_MARKS:
        return None
    return f"〚F{t}〛" if cell.get("f") == "残" else t


def tokenize(s: str) -> list[str]:
    """一行实录切成记号：一个字，或一个〚…〛（可嵌套）。"""
    toks, i = [], 0
    while i < len(s):
        if s[i] == "〚":
            depth, j = 0, i
            while j < len(s):
                depth += s[j] == "〚"
                depth -= s[j] == "〛"
                if depth == 0:
                    break
                j += 1
            if depth != 0:
                raise AlignmentError(f"〚〛不成对：{s}")
            toks.append(s[i:j + 1])
            i = j + 1
        else:
            toks.append(s[i])
            i += 1
    return toks


def cell_json(cell: dict):
    """空格写 ""，只有正文的格写成字符串，其余写成对象。"""
    if not cell:
        return ""
    if list(cell) == ["t"]:
        return cell["t"]
    return {k: cell[k] for k in ("t", "f", "r", "c", "n", "l", "p") if k in cell}


def cell_from_json(x) -> dict:
    if x == "":
        return {}
    return {"t": x} if isinstance(x, str) else x


# ── 对齐表（.typ） ──────────────────────────────────────────

def _body(text: str, name: str) -> str:
    if "*/" not in text:
        raise AlignmentError(f"{name}: 找不到文件头部说明的结尾 */")
    return "\n".join(l for l in text[text.index("*/") + 2:].splitlines() if not l.lstrip().startswith("//"))


def read_records(path: Path) -> list[tuple[str, str, list[str]]]:
    """返回 [(章键, 版本标记, [格的原始字符串…])]；章键如 '第一章'、'第六十四章A'。"""
    out = []
    for r in re.findall(r'"([^"]*)"', _body(path.read_text(encoding="utf-8"), path.name)):
        parts = r.split("&")
        if len(parts) < 3:
            raise AlignmentError(f"{path.name}: 记录太短：{r[:30]}")
        out.append((parts[0], parts[1], parts[2:]))
    return out


def slip_order(items: list[dict], key: str) -> list[dict]:
    """实录把写在简背的篇题（"2背"）排在该简正面之前；按简牍本身的顺序改排到同一枚简的正面（"2正"）之后。

    key 是简号所在的字段。简背找不到对应正面时报 ValueError。
    """
    def no(x):
        return x.get(key) or ""
    backs = {no(x)[:-1]: x for x in items if no(x).endswith("背")}
    out = []
    for x in items:
        if no(x).endswith("背"):
            continue
        out.append(x)
        if no(x).endswith("正") and no(x)[:-1] in backs:
            out.append(backs.pop(no(x)[:-1]))
    if backs:
        raise ValueError(f"简背找不到对应的正面：{sorted(backs)}")
    return out


def physical_order(cells: list[tuple[int, dict]]) -> list[tuple[int, dict]]:
    """把 ▩…▦ 里的句子按 🅰🅱🅲 标出的底本顺序排回去，返回底本顺序的 (列, 格)。"""
    out, i = [], 0
    while i < len(cells):
        if cells[i][1].get("t") != "▩":
            out.append(cells[i])
            i += 1
            continue
        j = i + 1
        while j < len(cells) and cells[j][1].get("t") != "▦":
            j += 1
        if j == len(cells):
            raise AlignmentError("▩ 没有对应的 ▦")
        head, segs, cur = [], [], None
        for c in cells[i + 1:j]:
            if c[1].get("t") in BLOCK_LABELS:
                cur = [c]
                segs.append(cur)
            elif cur is None:
                head.append(c)
            else:
                cur.append(c)
        segs.sort(key=lambda s: BLOCK_LABELS.index(s[0][1]["t"]))
        out.extend(head)
        for s in segs:
            out.extend(s)
        i = j + 1
    return out


# ── 实录 ────────────────────────────────────────────────────

def read_transcript(path: Path) -> tuple[dict, list[dict]]:
    """返回 (头部信息, 各行)。一行是 {no 简号或行号, text 原文, tokens, line 在文件里的行号, heading}。

    头部取【底本】【参照书】【与参照书差异】三项。王弼本的实录里夹着"一章"这样的章名行（没有〚L〛），标为 heading。
    """
    text = path.read_text(encoding="utf-8")
    end = text.index("*/")
    info: dict[str, str] = {}
    cur = None
    for ln in text[:end].splitlines():
        ln = re.sub(r"^[\s*]*", "", ln).strip()
        m = re.match(r"【([^】]+)】：?(.*)", ln)
        if m:
            cur = m.group(1)
            info[cur] = m.group(2).strip()
        elif cur and ln and not ln.startswith("/"):
            info[cur] = (info[cur] + "\n" + ln).strip()
    keep = {k: v for k, v in info.items() if k in ("底本", "参照书", "与参照书差异")}
    lines = []
    first = text[:end + 2].count("\n") + 1
    for no, raw in enumerate(text[end + 2:].split("\n"), first):
        if not raw:
            continue
        m = re.search(r"〚L([^〛]*)〛$", raw)
        body = raw[:m.start()] if m else raw
        heading = m is None and re.fullmatch(r"[一二三四五六七八九十]+章", body) is not None
        lines.append({"no": m.group(1) if m else None, "text": body, "tokens": tokenize(body), "line": no, "heading": heading})
    return keep, lines


# ── 把对齐表对上实录 ────────────────────────────────────────

def match_chapter(cells: list[tuple[int, dict]], P: list[str], p: int, line_end: dict[str, int]):
    """从 P[p] 起逐字对这一章（cells 已是底本顺序）。成功返回 (结束位置, [(列, 起, 止)])，否则 None。

    〼 代表任意个 □（实录里也可能出现〼本身）；它后面紧跟的单个 □ 格要留出来。
    格上有行号时，该处必须正好是实录里这一行的行尾。
    """
    phys = [(col, cell, token_of(cell)) for col, cell in cells]
    phys = [x for x in phys if x[2] is not None]
    q, refs = p, []
    for k, (col, cell, tok) in enumerate(phys):
        ln = cell.get("l")
        if tok == GAP:
            r = 0
            while q + r < len(P) and P[q + r] in ("□", GAP):
                r += 1
            need, j = 0, k + 1
            while j < len(phys) and phys[j][2] == "□":
                need += 1
                j += 1
            take = max(0, r - need)
            if ln in line_end and q <= line_end[ln] <= q + r:
                take = line_end[ln] - q
            refs.append((col, q, q + take))
            q += take
        else:
            if q >= len(P) or P[q] != tok:
                return None
            refs.append((col, q, q + 1))
            q += 1
        if ln is not None and ln in line_end and q != line_end[ln]:
            return None
    return q, refs


def resolve(chapters: dict[str, list[tuple[int, dict]]], P: list[str], line_end: dict[str, int], who: str):
    """按实录顺序排出各章，返回 [(章键, [(列, 起, 止)])]；有一处对不上或有歧义就报错。"""
    left, p, order = set(chapters), 0, []
    while left and p < len(P):
        cands = [(key, res) for key in left if (res := match_chapter(chapters[key], P, p, line_end))]
        if not cands:
            raise AlignmentError(f"{who}: 实录第 {p} 个记号起（{''.join(P[p:p + 12])}…）对不上任何一章，已对上 {len(order)} 章")
        if len(cands) > 1:
            raise AlignmentError(f"{who}: 实录第 {p} 个记号起有 {len(cands)} 章都对得上：{sorted(k for k, _ in cands)}")
        key, (q, refs) = cands[0]
        order.append((key, refs))
        left.discard(key)
        p = q
    if left or p != len(P):
        raise AlignmentError(f"{who}: 实录没有用完或还有章没对上（剩 {sorted(left)}，实录用到 {p}/{len(P)}）")
    return order


def line_refs(order, lines: list[dict]) -> list[list]:
    """每一行实录的对应关系：[[章, [列…]]]，或带郭店六十四章分段的 [章, [列…], 'A']。每个记号对一列。"""
    where: dict[int, tuple[int, str, int]] = {}
    for key, refs in order:
        n, part = chapter_key(key)
        for col, a, b in refs:
            for i in range(a, b):
                where[i] = (n, part, col)
    out, pos = [], 0
    for line in lines:
        spans: list[list] = []
        for i in range(pos, pos + len(line["tokens"])):
            n, part, col = where[i]
            if spans and spans[-1][0] == n and (spans[-1][2] if len(spans[-1]) == 3 else "") == part:
                spans[-1][1].append(col)
            else:
                spans.append([n, [col]] + ([part] if part else []))
        pos += len(line["tokens"])
        out.append(spans)
    return out


# ── 尾注 ────────────────────────────────────────────────────

def clean_typst(s: str) -> str:
    """尾注是 Typst 标记：#IDS("…") 取括号里的字，#box 取方括号里的字，\\[ \\] 还原成 [ ]。"""
    s = re.sub(r'#IDS\("([^"]*)"\)', r"\1", s)
    s = re.sub(r"#box\([^)]*\)\[([^\]]*)\]", r"\1", s)
    return s.replace("\\[", "[").replace("\\]", "]").strip()


def read_notes(path: Path) -> tuple[dict[int, list[str]], dict[int, dict[str, str]]]:
    """返回 (尾注: 章号 → [注…], 补充行号: 章号 → {版本标记: '12内'})。"""
    text = path.read_text(encoding="utf-8")
    i_sup, i_note = text.index("H字典-补充行号H"), text.index("H字典-尾注H")
    supplement: dict[int, dict[str, str]] = {}
    for m in re.finditer(r'"(第[^"]+章)":\(([^)]*)\)', text[i_sup:i_note]):
        supplement[chapter_key(m.group(1))[0]] = {
            k: re.sub(r"[\[\]]", "", v) for k, v in re.findall(r'"([^"]+)":"([^"]*)"', m.group(2))}
    notes: dict[int, list[str]] = {}
    for m in re.finditer(r'"(第[^"]+章)":\(\s*(.*?)\n  \),?', text[i_note:], re.S):
        items, depth, cur, i, blk = [], 0, "", 0, m.group(2)
        while i < len(blk):
            c = blk[i]
            if c == "\\" and depth >= 1:
                cur += blk[i:i + 2]
                i += 2
                continue
            if c == "[":
                depth += 1
                if depth == 1:
                    cur = ""
                    i += 1
                    continue
            elif c == "]":
                depth -= 1
                if depth == 0:
                    items.append(clean_typst(cur))
                    i += 1
                    continue
            if depth >= 1:
                cur += c
            i += 1
        notes[chapter_key(m.group(1))[0]] = items
    return notes, supplement


def note_boxes(rows: list[dict]) -> list[list[tuple[int, int]]]:
    """尾注框是连成片的一块格子（可跨版本、跨列）。返回各块的 [(行序号, 列)]，块按（最左列, 最上行）排序。"""
    mark = {(ri, ci) for ri, row in enumerate(rows) for ci, c in enumerate(row["cells"]) if "n" in c}
    seen: set = set()
    comps = []
    for k in sorted(mark, key=lambda x: (x[1], x[0])):
        if k in seen:
            continue
        stack, comp = [k], []
        seen.add(k)
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if nb in mark and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp, key=lambda x: (x[1], x[0])))
    comps.sort(key=lambda comp: (min(c for _, c in comp), min(r for r, _ in comp)))
    return comps


# ── 共用通行字规则、造字码位、参考书目 ──────────────────────

def _tuple_after(text: str, name: str) -> str:
    start = text.index(f"#let {name} = (") + len(f"#let {name} = (")
    depth, j = 1, start
    while depth:
        depth += text[j] == "("
        depth -= text[j] == ")"
        j += 1
    return text[start:j - 1]


def read_equivalents(path: Path) -> dict:
    """共用通行字的判定规则：fail 含这些字的列不判定；blank 视作空；same 每组里的字视同相等。"""
    text = path.read_text(encoding="utf-8")

    def strs(s: str) -> list[str]:
        return re.findall(r'"([^"]*)"', s)

    return {
        "fail": strs(_tuple_after(text, "I数组-规则视同测试失败I")),
        "blank": strs(_tuple_after(text, "I数组-规则视同空字符串I")),
        "same": [strs(g) for g in re.findall(r"\(([^()]*)\)", _tuple_after(text, "I数组-规则视同相等I"))],
    }


def read_glyphs(path: Path) -> dict[str, str]:
    """〚…〛造字序列 → tt24h 补充字体 DaoDeJingExt 里的码位（十六进制）。"""
    text = path.read_text(encoding="utf-8")
    i = text.index("#let I数组-表意文字描述序列至码位I = (")
    out: dict[str, str] = {}
    for tok, cp in re.findall(r'\(\s*"(〚[^"]*〛)"\s*,\s*"([0-9A-Fa-f]+)"\s*\)', text[i:]):
        if tok in out:
            raise AlignmentError(f"造字序列重复：{tok}")
        out[tok] = cp.upper()
    return out


def _bracket(s: str, i: int) -> tuple[str, int]:
    """s[i] 是 '['：返回 (括号里的内容, 右括号之后的位置)，括号可嵌套。"""
    depth, j = 0, i
    while j < len(s):
        depth += s[j] == "["
        depth -= s[j] == "]"
        j += 1
        if depth == 0:
            return s[i + 1:j - 1], j
    raise AlignmentError("方括号不成对")


ROLE = "I参考书性质I"


def read_references(path: Path) -> list[str]:
    """参考书目。每条写成一句：作者，书名，出版者，年份…，【性质】；性质（底本、参照书）用【】括起。"""
    text = path.read_text(encoding="utf-8")
    i = text.index("= 参考书目")
    blk = text[i:text.index("#pagebreak", i)]
    refs = []
    for m in re.finditer(r"\+ #I参考书I\(", blk):
        depth, k = 1, m.end()
        while depth:
            depth += blk[k] == "("
            depth -= blk[k] == ")"
            k += 1
        inner = blk[m.end():k - 1]
        items, j = [], 0
        while j < len(inner):
            if inner.startswith(f"{ROLE}[", j) or inner.startswith(f"#{ROLE}[", j):
                body, j = _bracket(inner, inner.index("[", j))
                items.append(f"【{body}】")
            elif inner[j] == "[":
                body, j = _bracket(inner, j)
                items.append(re.sub(rf"#{ROLE}\[([^\]]*)\]", r"【\1】", body).strip())
            else:
                j += 1
        refs.append("，".join(x for x in items if x) + ".")
    return refs


def read_overview(path: Path) -> dict:
    """概述与凡例的正文段落（原文，只去掉排版标记）。"""
    text = path.read_text(encoding="utf-8")

    def paras(block: str) -> list[str]:
        out = []
        for m in re.finditer(r"#I缩进I;(.*?)(?=\n\s*\n|\Z)", block, re.S):
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            t = re.sub(r"#sub\[([^\]]*)\]", r"（\1）", t)
            t = re.sub(r'#link\("([^"]*)"\)', r"\1", t)
            out.append(t)
        return out

    i = text.index("= 概述")
    overview = paras(text[i:text.index("#v(4fr)", i)])
    j = text.index("= 凡例")
    legend = []
    for m in re.finditer(r"#I章内标题I\[([^\]]+)\]\s*\n(.*?)(?=\n#I章内标题I|\n#pagebreak|\Z)", text[j:], re.S):
        legend.append({"title": m.group(1), "paragraphs": paras(m.group(2))})
    return {"overview": overview, "legend": [x for x in legend if x["paragraphs"]]}


# ── 读取与自检 data/alignment/ ──────────────────────────────

def load(root: Path) -> tuple[dict[int, dict], dict[str, list[dict]]]:
    """读 data/alignment/ 里的对读表与逐行释文；格还原成 dict。"""
    base = root / OUT
    chapters: dict[int, dict] = {}
    for p in sorted((base / "chapters").glob("*.json")):
        ch = json.loads(p.read_text(encoding="utf-8"))
        for r in ch["rows"]:
            r["cells"] = [cell_from_json(c) for c in r["cells"]]
        chapters[ch["chapter"]] = ch
    lines = {p.stem: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
             for p in sorted((base / "lines").glob("*.jsonl"))}
    return chapters, lines


def verify(chapters: dict[int, dict], lines: dict[str, list[dict]], total: int = CHAPTERS, known=BY_ID) -> list[str]:
    """对读表和逐行释文互相核对，返回问题清单（空表示一致）：

    1. 共 total 章（第 1 章起连续），每章的各行格数相同，版本已知（known 里有），同一版本同一分段只有一行；
    2. 逐行释文属于已知的版本，简号或行号不重复，每个记号指向的格，正文正是这个记号；
    3. 对读表里每个出现在实录里的格，恰好被一个记号指向（〼 可以一个也没有，也可以对着多个□）；
    4. 格上的简号或行号，正是实录里那一行最后一个记号所在的格。
    """
    problems: list[str] = []
    rows: dict[tuple[int, str, str], dict] = {}
    for n in range(1, total + 1):
        ch = chapters.get(n)
        if ch is None:
            problems.append(f"缺第 {n} 章")
            continue
        for r in ch["rows"]:
            where = f"第 {n} 章 {r['version']}{r.get('part', '')}"
            if r["version"] not in known:
                problems.append(f"{where}: 不是已知的版本")
            key = (n, r["version"], r.get("part", ""))
            if key in rows:
                problems.append(f"{where}: 重复的行")
            rows[key] = r
            if len(r["cells"]) != ch["columns"]:
                problems.append(f"{where}: 有 {len(r['cells'])} 格，本章应是 {ch['columns']} 格")
    hit: dict[tuple[int, str, str, int], int] = {}
    last_cell: dict[tuple[str, str], tuple[int, str, int]] = {}
    for vid, ls in lines.items():
        if vid not in known:
            problems.append(f"逐行释文 {vid}: 不是已知的版本")
        seen_no: set = set()
        for line in ls:
            where = f"{vid} 第 {line['no']} 简/行"
            if line["no"] in seen_no:
                problems.append(f"{where}: 简号或行号重复")
            seen_no.add(line["no"])
            toks = tokenize(line["text"])
            if sum(len(s[1]) for s in line["refs"]) != len(toks):
                problems.append(f"{where}: {len(toks)} 个记号，对应关系却有 {sum(len(s[1]) for s in line['refs'])} 个")
                continue
            i = 0
            for s in line["refs"]:
                n, cols, part = s[0], s[1], (s[2] if len(s) > 2 else "")
                row = rows.get((n, vid, part))
                if row is None:
                    problems.append(f"{where}: 指向第 {n} 章{part}，那里没有 {vid} 这一行")
                    i += len(cols)
                    continue
                for col in cols:
                    tok = toks[i]
                    i += 1
                    if not 0 <= col < len(row["cells"]):
                        problems.append(f"{where}: 第 {n} 章没有第 {col} 列")
                        continue
                    want = token_of(row["cells"][col])
                    if want is None or (want == GAP and tok not in ("□", GAP)) or (want != GAP and want != tok):
                        problems.append(f"{where}: 记号 {tok} 对到第 {n} 章第 {col} 列，那一格是 {want!r}")
                    k = (n, vid, part, col)
                    hit[k] = hit.get(k, 0) + 1
            if line["refs"]:
                n, cols, part = line["refs"][-1][0], line["refs"][-1][1], (line["refs"][-1][2] if len(line["refs"][-1]) > 2 else "")
                last_cell[(vid, line["no"])] = (n, part, cols[-1])
    for (n, vid, part), r in rows.items():
        if vid not in lines:
            continue
        for col, cell in enumerate(r["cells"]):
            want = token_of(cell)
            if want is None:
                continue
            got = hit.get((n, vid, part, col), 0)
            if want != GAP and got != 1:
                problems.append(f"第 {n} 章 {vid}{part} 第 {col} 列（{want}）被 {got} 个记号指向，应恰好 1 个")
            # 一个〼若一个记号也没对到（它前面的章已经用掉了这段空缺），它身上的行号没法在这里核对
            if "l" in cell and got and last_cell.get((vid, cell["l"])) != (n, part, col):
                problems.append(f"第 {n} 章 {vid}{part} 第 {col} 列：行号 {cell['l']} 不在实录里该行的最后一个记号上")
    return problems
