"""数据版：所有版本在一页里，按版本切换，可跨版本检索。"""
from ..textutil import UNIT_WORD, colophon
from .common import (LEGEND, REPO_URL, SEP, corpus_links, e, facts_fold, gallery, icon, item, search_box, shell,
                     sidebar, sources_fold, tree, unit)


def side(c, corpora, ctx) -> str:
    nav = item("#", "总目", "list", on=True, attrs=' data-w=""')
    body = (f'<nav class="sb-nav">{nav}</nav>{corpus_links(c, corpora, ctx)}'
            f'<div class="sb-label">文献</div>{tree(c, ctx, data=True)}')
    return sidebar(c, ctx, "data", search_box("搜索全部版本"), body)


def data_page(c, corpora, ctx, thumbs) -> str:
    rows, sections = [], []
    for w in c.witnesses:
        wid, name = w.id, w.meta["name"]
        word = UNIT_WORD[w.units[0]["unit_type"]]
        rows.append(f'<a class="row" href="#{e(wid)}"><span class="bd">'
                    f'<span class="t">{e(w.title)}</span><span class="m" title="{e(colophon(w.meta))}">{len(w.units)} {word} · '
                    f'{len(w.plates)} 张影像 · {e(colophon(w.meta))}</span></span>{icon("chev")}</a>')
        sections.append(
            f'<section class="wit" id="w-{e(wid)}" hidden><h1>{e(name)}</h1>{facts_fold(w)}{sources_fold(c, w)}'
            f'<div class="legend">{LEGEND}</div>'
            f'<div class="units">{"".join(unit(u, w, thumbs) for u in w.units)}</div>{gallery(w, thumbs)}</section>')
    content = (
        f'<section id="overview"><h1>{e(c.title)}　数据版</h1><p class="lead">{e(c.subtitle)}。所有版本在同一页，可按版本切换，'
        f'检索会统计各版本的命中数。</p><div class="rows">{"".join(rows)}</div></section>' + "".join(sections)
        + f'<div class="foot">共 {len(c.witnesses)} 个版本，{c.totals[0]} 条释文，{c.totals[1]} 张影像 · '
        f'<a href="{REPO_URL}">原始数据在 GitHub</a></div>')
    base = f'<a href="{ctx.cover}">{e(c.title)}</a>{SEP}<span>数据版</span>'
    return shell(ctx, f"{c.title} · 数据版", f"{c.title}的全部版本，数据版", side(c, corpora, ctx), base, content,
                 crumb_attrs=f' id="crumb" data-base="{e(base)}"', wide=True)
