"""分组命名、识语、标签与残缺标注。纯函数，不读写文件。"""
import html
import os
import re

UNIT_WORD = {"slip": "枚简", "silk-line": "行", "chapter": "章"}      # 数量后面：39 枚简、81 章
UNIT_NOUN = {"slip": "简", "silk-line": "行", "chapter": "章"}        # 单说一个单位：跳转到简


def unit_label(u: dict) -> tuple:
    """(前缀, 编号, 后缀)：简 1 / 第 38 章。编号单独返回，竖排时可做数字并排。"""
    if u["unit_type"] == "chapter":
        return ("第", u["unit_no"], "章")
    return ("简" if u["unit_type"] == "slip" else "行", u["unit_no"], "")


def label_text(u: dict) -> str:
    pre, no, suf = unit_label(u)
    return f"{pre}{no}{suf}"


def common_id(ids: list) -> str:
    """一组版本 id 的共同前缀（去掉结尾的连字符）：guodian-jia、guodian-yi → guodian。无共同前缀时取第一个 id。"""
    prefix = ids[0] if len(ids) == 1 else os.path.commonprefix(ids).rstrip("-_.")
    return prefix or ids[0]


def split_name(name: str) -> tuple:
    """版本名拆成 (文献名, 本名)：“郭店楚简《老子》甲组” → (“郭店楚简”, “甲组”)；无后缀时本名为“全本”。"""
    m = re.match(r"^([^《]*)《[^》]*》(.*)$", name)
    if not m:
        return name, "全本"
    group, suffix = m.group(1).strip(), m.group(2).strip()
    return (group or name), (suffix or "全本")


LICENSE_STATUS = {"public-domain": "来源未标明，按可收录处理", "cc": "知识共享", "all-rights-reserved": "保留所有权利",
                  "permission-granted": "已获许可", "unknown": "来源未标明"}


def license_label(lic: dict | None) -> str:
    """授权的一句话：登记了名字（如 CC BY-SA 4.0）就用名字，没有就按状态说。"""
    lic = lic or {}
    return lic.get("name") or LICENSE_STATUS.get(lic.get("status"), "来源未标明")


def colophon(w: dict) -> str:
    """把登记表里的事实写成一段识语，而不是字段表。"""
    ex = w.get("excavated") or {}
    parts = []
    if ex.get("year"):
        parts.append(f"{ex['year']}年" + (f"{ex['month']}月" if ex.get("month") else "") + f"出土于{ex.get('place') or ''}")
    elif ex.get("place"):
        parts.append(ex["place"])
    de = (w.get("date_estimate") or {}).get("text")
    if de:
        parts.append(de)
    sl = w.get("slips") or {}
    if sl.get("count"):
        parts.append(f"存简{sl['count']}枚")
    pub = w.get("published") or {}
    if pub:
        parts.append(f"{pub.get('year')}年收入《{pub.get('title')}》（{pub.get('publisher')}）")
    hold = (w.get("holder") or {}).get("name")
    if hold:
        parts.append(f"现藏{hold}")
    return "；".join(parts) + "。"


def facts(w: dict) -> list:
    """版本登记表里的事实，按研究者常看的顺序列成 (标签, 值)。"""
    ex = w.get("excavated") or {}
    when = ""
    if ex.get("year"):
        when = f"{ex['year']} 年" + (f" {ex['month']} 月" if ex.get("month") else "")
    sl = w.get("slips") or {}
    pub = w.get("published") or {}
    rows = [
        ("材质", " · ".join(x for x in (w.get("medium"), w.get("script")) if x)),
        ("出土 / 入藏", " · ".join(x for x in (when, ex.get("place")) if x)),
        ("年代", (w.get("date_estimate") or {}).get("text") or ""),
        ("简数", f"{sl['count']} 枚" if sl.get("count") else ""),
        ("篇章", (w.get("chapter_order") or {}).get("text") or w.get("scope") or ""),
        ("出版", f"《{pub['title']}》，{pub['publisher']}，{pub['year']}" if pub else ""),
        ("现藏", (w.get("holder") or {}).get("name") or ""),
    ]
    return [(k, v) for k, v in rows if v]


def mark_damage(text: str, damage: list | None) -> str:
    """按码点区间给残缺处加样式，其余原样转义。"""
    flags = [None] * len(text)
    for d in damage or []:
        for i in range(d["start"], min(d["end"], len(text))):
            flags[i] = d["kind"]
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and flags[j] == flags[i]:
            j += 1
        seg = html.escape(text[i:j])
        out.append(f'<span class="d-{flags[i]}">{seg}</span>' if flags[i] else seg)
        i = j
    return "".join(out)
