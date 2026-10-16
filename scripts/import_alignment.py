#!/usr/bin/env python3
"""把 tt24h/daodejing（CC0）的对齐表与逐行释文导入 data/alignment/，并生成王弼本、校订本的章级释文。

用法：python3 scripts/import_alignment.py [--root 仓库根目录] [--check]
只读取 data/raw/tt24h-daodejing/ 下已登记哈希的文件，不联网。--check 不写文件，只检查已有的文件
是否与重新生成的结果逐字相同（有差异时退出码为 1）。

写出：
  data/alignment/versions.json        对读表里的各行（版本）：id、标记、实录文件、底本、参照书
  data/alignment/chapters/NNN.json    一章的对读表：每个版本一行格子（格的写法见 scripts/alignment.py），加尾注
  data/alignment/lines/<版本>.jsonl   各简、各行的实录原文，及每个字对应哪一章的哪一列
  data/alignment/equivalents.json     共用通行字的判定规则
  data/alignment/glyphs.json          〚…〛造字序列与补充字体码位的对应
  data/alignment/study.json           tt24h 的概述、凡例与参考书目
  data/witnesses/wangbi.jsonl         王弼本，每章一条
  data/witnesses/jiaoding.jsonl       校订本（tt24h 整理者的断句本），每章一条

对不上实录就报错退出，不写任何文件。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alignment as al  # noqa: E402
from import_tt24h import parse_slip  # noqa: E402


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def render_chapter(ch: dict) -> str:
    """一章一个文件：每个版本一行格子占一行，便于对比改动。"""
    rows = ",\n".join(
        "    " + dumps({k: v for k, v in (("version", r["version"]), ("part", r.get("part")), ("cells", [al.cell_json(c) for c in r["cells"]])) if v is not None})
        for r in ch["rows"])
    notes = ",\n".join("    " + dumps(n) for n in ch["notes"])
    return (f'{{\n  "chapter": {ch["chapter"]},\n  "columns": {ch["columns"]},\n  "rows": [\n{rows}\n  ],\n'
            f'  "notes": [{chr(10) + notes + chr(10) + "  " if notes else ""}]\n}}\n')


def render_lines(lines: list[dict]) -> str:
    return "".join(dumps({"no": l["no"], "text": l["text"], "refs": l["refs"]}) + "\n" for l in lines)


def render_map(d: dict, indent="  ") -> str:
    body = ",\n".join(f"{indent}{dumps(k)}: {dumps(v)}" for k, v in d.items())
    return "{\n" + body + "\n}\n"


def render_equivalents(e: dict) -> str:
    same = ",\n".join("    " + dumps(g) for g in e["same"])
    return ('{\n  "fail": ' + dumps(e["fail"]) + ',\n  "blank": ' + dumps(e["blank"]) + ',\n  "same": [\n' + same + "\n  ]\n}\n")


def jsonl(units: list[dict]) -> str:
    return "".join(json.dumps(u, ensure_ascii=False) + "\n" for u in units)


def build(root: Path) -> dict[str, str]:
    """返回 {相对路径: 文件内容}；数据对不上就抛 AlignmentError。"""
    raw = root / al.RAW
    typs = {fn: al.read_records(raw / fn) for fn in sorted({v["typ"] for v in al.VERSIONS})}

    # ── 对读表：章 → 各版本一行 ──
    chapters: dict[int, dict] = {n: {"chapter": n, "rows": []} for n in range(1, al.CHAPTERS + 1)}
    cells_of: dict[tuple[str, str], list[dict]] = {}     # (章键, 版本 id) → 格
    for v in al.VERSIONS:
        for key, label, cells in typs[v["typ"]]:
            if label not in al.BY_LABEL:
                raise al.AlignmentError(f"{v['typ']}: 没见过的版本标记 {label}")
            if label != v["label"]:
                continue
            n, part = al.chapter_key(key)
            if n not in chapters:
                raise al.AlignmentError(f"{v['typ']}: 章号 {n} 不在 1–{al.CHAPTERS}")
            parsed = [al.parse_cell(c) for c in cells]
            if any(al.canonical_raw(a) != al.cell_raw(b) for a, b in zip(cells, parsed)):
                raise al.AlignmentError(f"{v['typ']} {key}: 格解析后不能还原")
            row = {"version": v["id"], "cells": parsed}
            if part:
                row["part"] = part
            chapters[n]["rows"].append(row)
            cells_of[(key, v["id"])] = parsed
    for n, ch in chapters.items():
        if not ch["rows"]:
            raise al.AlignmentError(f"第 {n} 章没有任何版本")
        ch["columns"] = max(len(r["cells"]) for r in ch["rows"])
        for r in ch["rows"]:                              # tt24h 的排版把短行右侧用空格补齐
            r["cells"] += [{}] * (ch["columns"] - len(r["cells"]))
        order = {v["id"]: i for i, v in enumerate(al.VERSIONS)}
        ch["rows"].sort(key=lambda r: (order[r["version"]], r.get("part", "")))

    # ── 实录 → 各版本的简、行 ──
    lines_out: dict[str, list[dict]] = {}
    versions_meta: list[dict] = []
    for v in al.VERSIONS:
        meta = {"id": v["id"], "label": v["label"], "short": v["short"]}
        if "transcript" in v:
            meta["transcript"] = v["transcript"]
        versions_meta.append(meta)
    meta_of = {m["id"]: m for m in versions_meta}
    units_out: dict[str, list[dict]] = {}
    for fn in sorted({v["transcript"] for v in al.VERSIONS if "transcript" in v}):
        info, lines = al.read_transcript(raw / fn)
        group = [v for v in al.VERSIONS if v.get("transcript") == fn]
        keys: dict[str, list] = {}
        for v in group:
            for key, label, _ in typs[v["typ"]]:
                if label == v["label"]:
                    keys[key] = al.physical_order([(i, c) for i, c in enumerate(cells_of[(key, v["id"])])])
        body = [l for l in lines if not l["heading"]]
        P = [t for l in body for t in l["tokens"]]
        line_end: dict[str, int] = {}
        pos = 0
        for l in body:
            pos += len(l["tokens"])
            if l["no"] is not None:
                if l["no"] in line_end:
                    raise al.AlignmentError(f"{fn}: 简号或行号重复：{l['no']}")
                line_end[l["no"]] = pos
        order = al.resolve(keys, P, line_end, fn)
        refs = al.line_refs(order, body)
        for l, r in zip(body, refs):
            l["refs"] = r
        if fn == "实录-王弼本.txt":                       # 王弼本每行是一章，没有简号，用章号
            for n, l in enumerate(body, 1):
                l["no"] = str(n)
        for v in group:
            mine = al.slip_order([l for l in body if "line_prefix" not in v or (l["no"] or "").startswith(v["line_prefix"])], "no")
            lines_out[v["id"]] = mine
            meta_of[v["id"]].update({en: info[zh] for zh, en in (("底本", "base"), ("参照书", "reference"), ("与参照书差异", "differences")) if zh in info})
            meta_of[v["id"]]["unit"] = v.get("unit", "chapter")
        if fn == "实录-王弼本.txt":
            units_out["wangbi"] = wangbi_units(root, body, order)
    # 对齐表里的行号都要出现在实录里（补充行号 "12内" 的章除外：那一章整个在某一行中间）
    for ch in chapters.values():
        for r in ch["rows"]:
            for c in r["cells"]:
                if "l" in c and r["version"] in lines_out and c["l"] not in {l["no"] for l in lines_out[r["version"]]}:
                    raise al.AlignmentError(f"第 {ch['chapter']} 章 {r['version']}: 行号 {c['l']} 不在实录里")
    units_out["jiaoding"] = jiaoding_units(root, chapters)

    # ── 尾注 ──
    notes, supplement = al.read_notes(raw / al.NOTES_FILE)
    if set(notes) - set(chapters):
        raise al.AlignmentError(f"尾注里有不存在的章：{sorted(set(notes) - set(chapters))}")
    for n, ch in chapters.items():
        ch["notes"] = notes.get(n, [])
    check_supplement(chapters, lines_out, supplement)

    # ── 其余 ──
    equivalents = al.read_equivalents(raw / al.EQUIV_FILE)
    glyphs = al.read_glyphs(raw / al.GLYPH_FILE)
    check_glyphs(chapters, lines_out, units_out, glyphs)
    study = al.read_overview(raw / al.OVERVIEW_FILE)
    study["references"] = al.read_references(raw / al.OVERVIEW_FILE)
    if len(study["references"]) != 15:
        raise al.AlignmentError(f"参考书目应有 15 条，读到 {len(study['references'])} 条")

    out = {f"{al.OUT}/chapters/{n:03d}.json": render_chapter(ch) for n, ch in chapters.items()}
    for vid, ls in lines_out.items():
        out[f"{al.OUT}/lines/{vid}.jsonl"] = render_lines(ls)
    out[f"{al.OUT}/versions.json"] = "[\n" + ",\n".join("  " + dumps(m) for m in versions_meta) + "\n]\n"
    out[f"{al.OUT}/equivalents.json"] = render_equivalents(equivalents)
    out[f"{al.OUT}/glyphs.json"] = render_map(glyphs)
    out[f"{al.OUT}/study.json"] = json.dumps(study, ensure_ascii=False, indent=2) + "\n"
    for wid, units in units_out.items():
        out[f"data/witnesses/{wid}.jsonl"] = jsonl(units)

    problems = al.verify(chapters, lines_out)
    if problems:
        raise al.AlignmentError("生成的结果自检未通过：\n  " + "\n  ".join(problems[:20]))
    return out


def wangbi_units(root: Path, body: list[dict], order) -> list[dict]:
    """王弼本：实录每章一行。"""
    if [al.chapter_key(k)[0] for k, _ in order] != list(range(1, al.CHAPTERS + 1)):
        raise al.AlignmentError("王弼本实录的章次不是 1–81 依次排列")
    units = []
    for n, l in enumerate(body, 1):
        text, marks, damage = parse_slip(l["text"])
        u = {"id": f"wangbi.{n:03d}", "witness": "wangbi", "unit_type": "chapter", "unit_no": str(n), "text": text,
             "source_ref": {"source": al.SOURCE, "raw_file": f"{al.RAW}/实录-王弼本.txt", "locator": f"第 {l['line']} 行"},
             "status": "unverified"}
        if marks:
            u["marks"] = marks
        if damage:
            u["damage"] = damage
        units.append(u)
    return units


def jiaoding_units(root: Path, chapters: dict[int, dict]) -> list[dict]:
    """校订本：把一章的格连起来，加上整理者的断句；¶ 是分段，不进正文，只记位置。"""
    units = []
    for n, ch in chapters.items():
        row = next(r for r in ch["rows"] if r["version"] == "jiaoding")
        text, marks = "", []
        for c in row["cells"]:
            text += c.get("t", "")
            p = c.get("p", "")
            if p.endswith("¶"):
                text += p[:-1]
                marks.append({"type": "other", "as_source": "¶", "offset": len(text)})
            else:
                text += p
        if not text:
            raise al.AlignmentError(f"校订本第 {n} 章是空的")
        u = {"id": f"jiaoding.{n:03d}", "witness": "jiaoding", "unit_type": "chapter", "unit_no": str(n), "text": text,
             "source_ref": {"source": al.SOURCE, "raw_file": f"{al.RAW}/校订本.typ", "locator": f"第 {n} 章"},
             "status": "unverified"}
        if marks:
            u["marks"] = marks
        units.append(u)
    return units


def check_supplement(chapters, lines_out, supplement):
    """补充行号 "12内"：这一章在该版本里整个落在第 12 行中间。用实录里的对应关系核对。"""
    for n, per in supplement.items():
        for label, val in per.items():
            vid = al.BY_LABEL[label]["id"]
            want = val.replace("内", "")
            got = sorted({l["no"] for l in lines_out[vid] for s in l["refs"] if s[0] == n}, key=str)
            if got != [want]:
                raise al.AlignmentError(f"补充行号 第 {n} 章 {label} {val}：实录里这一章在 {got}")


def check_glyphs(chapters, lines_out, units_out, glyphs):
    """页面上出现的〚…〛造字序列，都要能在补充字体里找到码位。"""
    used: set[str] = set()
    for ch in chapters.values():
        for r in ch["rows"]:
            for c in r["cells"]:
                for k in ("t", "r", "c"):
                    used.update(al.tokenize(c.get(k, "")))
        for note in ch["notes"]:
            used.update(al.tokenize(note))
    for ls in lines_out.values():
        for l in ls:
            used.update(l["tokens"])
    for us in units_out.values():
        for u in us:
            used.update(al.tokenize(u["text"]))
    missing = sorted(t for t in used if t.startswith("〚") and not t.startswith("〚F") and t not in glyphs)
    if missing:
        raise al.AlignmentError(f"{len(missing)} 个造字序列在补充字体里没有码位：{missing[:8]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    try:
        out = build(root)
    except al.AlignmentError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    if args.check:
        bad = [p for p, s in out.items() if not (root / p).exists() or (root / p).read_text(encoding="utf-8") != s]
        stale = [str(p.relative_to(root)) for d in ("chapters", "lines") for p in (root / al.OUT / d).glob("*")
                 if str(p.relative_to(root)) not in out]
        for p in bad + stale:
            print(f"✗ {p} 与重新生成的结果不一致", file=sys.stderr)
        print(f"检查了 {len(out)} 个文件：{'全部一致' if not (bad or stale) else '发现 %d 处不一致' % len(bad + stale)}")
        return 1 if bad or stale else 0
    for p in [p for d in ("chapters", "lines") for p in (root / al.OUT / d).glob("*") if str(p.relative_to(root)) not in out]:
        p.unlink()
    for rel, text in out.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"写入 {len(out)} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
