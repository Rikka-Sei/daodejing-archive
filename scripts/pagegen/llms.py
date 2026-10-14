"""纯文本释文、jsonl 数据下载与 llms.txt（https://llmstxt.org 格式）。"""
import json
from pathlib import Path

from .render import REPO_URL
from .textutil import UNIT_WORD, colophon, label_text, license_label

NOTE = "释文照录来源，未经复核。□ 表示残缺字；括号内为整理者的读法。"


def witness_txt(corpus, wit, level: int = 1) -> str:
    """一个本的纯文本。level 为标题级别，合集里把各本降一级。"""
    w, h = wit.meta, "#" * level
    lines = [f"{h} {w['name']}", "", f"> {colophon(w)}", "", NOTE, ""]
    lines += [f"[{label_text(u)}] {u['text']}" for u in wit.units]
    lines += ["", f"{h}# 来源", ""]
    for s in corpus.sources_of(wit):
        lines.append(f"- {s['title']}（授权：{license_label(s.get('license'))}）" + (f" {s['url']}" if s.get("url") else ""))
    return "\n".join(lines) + "\n"


def group_txt(corpus, group) -> str:
    """一部文献下所有本的合集。"""
    parts = [f"# {group.name}\n"] + [witness_txt(corpus, w, level=2) for w in group.witnesses]
    return "\n".join(parts)


def witness_jsonl(wit) -> str:
    """释文数据：与仓库里的 jsonl 逐字相同；没有源文件时按解析结果重写。"""
    if wit.file and wit.file.exists():
        text = wit.file.read_text(encoding="utf-8")
    else:
        text = "".join(json.dumps(u, ensure_ascii=False) + "\n" for u in wit.units)
    return text if text.endswith("\n") else text + "\n"


def group_jsonl(group) -> str:
    return "".join(witness_jsonl(w) for w in group.witnesses)


def write_downloads(corpus, out_dir: Path) -> None:
    """每个本一份 .txt 和 .jsonl；多个本的文献另有合集 <文献id>-all.txt / .jsonl。"""
    for w in corpus.witnesses:
        (out_dir / f"{w.id}.txt").write_text(witness_txt(corpus, w), encoding="utf-8")
        (out_dir / f"{w.id}.jsonl").write_text(witness_jsonl(w), encoding="utf-8")
    for g in corpus.groups:
        if not g.single:
            (out_dir / f"{g.id}-all.txt").write_text(group_txt(corpus, g), encoding="utf-8")
            (out_dir / f"{g.id}-all.jsonl").write_text(group_jsonl(g), encoding="utf-8")


def write_llms(corpora, out_root: Path, base: str = "") -> None:
    def link(rel):
        return f"{base}/{rel}" if base else rel

    title = corpora[0].title if len(corpora) == 1 else "典籍"
    head = [f"# {title}", "",
            "> 典籍的释文、影像索引与来源登记。释文照录来源，未经复核；每条文本可追溯到登记了 SHA-256 的原始文件。",
            "", "释文中 □ 表示残缺字；括号内为整理者的读法；符号照抄来源。授权与来源见各本页面顶部的“来源与授权”。", ""]
    lines, full = list(head), list(head)
    for c in corpora:
        heading = c.title if len(corpora) > 1 else "版本"
        lines += [f"## {heading}", "", f"{c.subtitle}。", ""]
        full += [f"## {heading}", ""]
        for wit in c.witnesses:
            w = wit.meta
            lines.append(f"- [{w['name']}]({link(f'{c.id}/{wit.id}.txt')}): "
                         f"{len(wit.units)}{UNIT_WORD[wit.units[0]['unit_type']]}。{colophon(w)}")
            body = (out_root / c.id / f"{wit.id}.txt").read_text(encoding="utf-8")
            full.append(body.replace("# ", "### ", 1).replace("\n## 来源", "\n#### 来源", 1))
        lines += ["", f"- [{c.title}（阅读版）]({link(f'{c.id}/index.html')}): 封面、凡例、目录，每本一页，释文可横排或竖排",
                  f"- [{c.title}（数据版）]({link(f'{c.id}/data.html')}): 所有版本一页，可跨版本检索", ""]
    lines += ["## Optional", "", f"- [完整释文合集]({link('llms-full.txt')}): 全部典籍的释文，单个文本文件",
              f"- [数据仓库]({REPO_URL}): 原始文件、元数据与校验脚本", ""]
    (out_root / "llms.txt").write_text("\n".join(lines), encoding="utf-8")
    (out_root / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")
