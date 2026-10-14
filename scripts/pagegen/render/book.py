"""阅读版：封面（文献卡片与凡例）和每个本一页。"""
from ..textutil import UNIT_NOUN
from ..thumbs import COVER_WIDTH
from .common import (LEGEND, REPO_URL, SEG_THEME, SEP, e, facts_fold, gallery, icon, read_side, shell, sources_fold,
                     unit)

GENERIC_PREFACE = [
    "释文照录来源，不改字，不校勘：通假字、异体字、隶定字形和符号都保持原样。",
    "灰色为残缺字，括号内为整理者的读法；点选图版缩略图可看原图。",
    "各本的版本信息、来源与授权，收在该本页面顶部的折叠栏里；侧栏目录每一项右侧的“⋯”可下载释文与数据。",
]


def preface_items(c) -> list:
    """凡例：体例部分取 corpus 的 preface，没有就用通用的，再追加 preface_extra；
    释文是否复核、能否追溯，是数据的状态，由这里按数据补在最后。"""
    items = list(c.preface or GENERIC_PREFACE) + list(c.preface_extra)
    n_units = c.totals[0]
    pending = sum(1 for w in c.witnesses for u in w.units if u.get("status") != "double-checked")
    if pending == n_units:
        items.append("全部释文目前只核对过一个来源，尚未经第二个独立来源复核，引用前请对照影像或原书。")
    elif pending:
        items.append(f"其中 {pending} 条释文尚未经第二个独立来源复核。")
    items.append("每条释文都能追溯到登记了 SHA-256 的原始文件。")
    return items


def doc_card(c, g, ctx, thumbs) -> str:
    """封面上的一张文献卡片：实物影像、名称、概况；有几个本，就列几个。"""
    plate = g.cover_plate()
    thumb = thumbs.get(plate["file"], COVER_WIDTH) if plate else None
    pic = (f'<img loading="lazy" src="{e(ctx.cdir + thumb)}" alt="">' if thumb
           else f'<span class="ph">{e(g.name[:1])}</span>')
    units = sum(len(w.units) for w in g.witnesses)
    meta = [f"{len(g.witnesses)} 个版本"] if not g.single else []
    meta.append(f"{units} 条释文")
    if g.plates:
        meta.append(f"{g.plates} 张影像")
    subs = "" if g.single else (
        '<div class="subs">' + "".join(f'<a href="{ctx.cdir}{w.id}.html">{e(w.label)}</a>' for w in g.witnesses) + "</div>")
    return (f'<article class="doc"><a class="cov" href="{ctx.cdir}{g.first.id}.html"><span class="pic">{pic}</span>'
            f'<span class="tx"><span class="t">{e(g.name)}</span><span class="m">{" · ".join(meta)}</span></span></a>{subs}</article>')


def cover(c, corpora, ctx, thumbs) -> str:
    first = c.witnesses[0]
    n_units, n_plates = c.totals
    stats = [f"{len(c.witnesses)} 个版本", f"{n_units} 条释文"] + ([f"{n_plates} 张影像"] if n_plates else [])
    content = (
        f'<div class="hero"><div class="eyebrow">{e(c.subtitle)}</div><h1>{e(c.title)}</h1><p class="sub">{e(c.intro)}</p>'
        f'<div class="actions"><a class="btn pri" href="{ctx.cdir}{first.id}.html">开始阅读</a>'
        f'<a class="btn" href="{ctx.data}">数据版</a></div><div class="stats">{" · ".join(stats)}</div></div>'
        f'<div class="docs">{"".join(doc_card(c, g, ctx, thumbs) for g in c.groups)}</div>'
        f'<section id="preface" class="sec"><h2>凡例</h2><ol class="preface">'
        + "".join(f"<li>{e(t)}</li>" for t in preface_items(c)) + "</ol></section>"
        f'<div class="foot"><a href="{REPO_URL}">原始数据在 GitHub</a></div>')
    return shell(ctx, c.title, f"{c.subtitle}。{c.intro}", read_side(c, corpora, ctx, on_cover=True),
                 f"<b>{e(c.title)}</b>", content, tools=SEG_THEME)


def volume(c, w, corpora, ctx, thumbs) -> str:
    i = c.witnesses.index(w)
    prev_w = c.witnesses[i - 1] if i else None
    next_w = c.witnesses[i + 1] if i + 1 < len(c.witnesses) else None
    noun = UNIT_NOUN[w.units[0]["unit_type"]]
    chips = "".join(f'<a href="#{e(u["id"])}">{e(u["unit_no"])}</a>' for u in w.units)
    jump = (f'<details class="fold jump"{" open" if len(w.units) <= 60 else ""}><summary><span class="t">跳转到{noun}</span>'
            f'{icon("chev", "chev")}</summary><div class="body chips">{chips}</div></details>')

    def pager(x, cls, label):
        return f'<a class="{cls}" href="{ctx.cdir}{x.id}.html"><small>{label}</small>{e(x.title)}</a>'

    nav = "".join([pager(prev_w, "prev", "上一本") if prev_w else "", pager(next_w, "next", "下一本") if next_w else ""])
    content = (
        f'<h1>{e(w.meta["name"])}</h1>{facts_fold(w)}{sources_fold(c, w)}'
        f'<div class="legend">{LEGEND}</div>{jump}'
        f'<div class="units">{"".join(unit(u, w, thumbs) for u in w.units)}</div>{gallery(w, thumbs)}'
        f'<nav class="pager">{nav}</nav>')
    where = f'<b>{e(w.group)}</b>' if w.label == "全本" else f'<span>{e(w.group)}</span>{SEP}<b>{e(w.label)}</b>'
    crumb = f'<a href="{ctx.cover}">{e(c.title)}</a>{SEP}{where}'
    return shell(ctx, f'{w.meta["name"]} · {c.title}', f'{w.meta["name"]}的释文与影像',
                 read_side(c, corpora, ctx, current=w.id, data_href=f"{ctx.data}#{e(w.id)}"), crumb, content, wide=True)
