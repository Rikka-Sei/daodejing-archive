"""页面公共部分：外壳、顶栏开关、侧栏与目录树、图标、单条释文、整页图版、来源。"""
import html
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .. import fonts
from ..textutil import facts, label_text, license_label, mark_damage, unit_label
from ..thumbs import full_url

e = html.escape
ASSETS = Path(__file__).resolve().parent.parent / "assets"
CSS = (ASSETS / "style.css").read_text(encoding="utf-8")
JS = (ASSETS / "app.js").read_text(encoding="utf-8")
REPO_URL = "https://github.com/Rikka-Sei/daodejing-archive"
LEGEND = "灰色为残缺字，括号内为整理者的读法；释文照录来源，未经复核。"

# 线条图标，24×24 网格，描边由样式统一设置
ICONS = {
    "panel": '<rect x="3.5" y="5" width="17" height="14" rx="3"/><path d="M9.5 5v14"/>',
    "search": '<circle cx="10.8" cy="10.8" r="6.3"/><path d="m20 20-4.7-4.7"/>',
    "book": '<path d="M12 6.8C10.3 5.4 7.8 4.9 3.8 5.1v12.6c4-.2 6.5.3 8.2 1.7 1.7-1.4 4.2-1.9 8.2-1.7V5.1c-4-.2-6.5.3-8.2 1.7Z"/><path d="M12 6.8v12.6"/>',
    "list": '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><path d="M4.2 6.5h.1M4.2 12h.1M4.2 17.5h.1" stroke-width="2.4"/>',
    "table": '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><path d="M3.5 10h17M10 10v9"/>',
    "chev": '<path d="m9.5 6 6 6-6 6"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "books": '<rect x="4" y="4" width="4.5" height="16" rx="1"/><rect x="10.5" y="4" width="4.5" height="16" rx="1"/><path d="m17.2 5.3 3.6.9-3.2 13.3-3.6-.9"/>',
    "folder": '<path d="M3.5 7.5a2 2 0 0 1 2-2h3.3l2.2 2.3h7.5a2 2 0 0 1 2 2v7.7a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V7.5Z"/>',
    "folder-open": '<path d="M4.5 17.5v-10a2 2 0 0 1 2-2h2.3l2.2 2.3h6a2 2 0 0 1 2 2V10"/><path d="m3.7 18.1 2-6.3a1.5 1.5 0 0 1 1.4-1h13.2a1.1 1.1 0 0 1 1.05 1.45l-1.8 5.6a2 2 0 0 1-1.9 1.4H5.4a1.6 1.6 0 0 1-1.7-1.15Z"/>',
    "file": '<path d="M7 3.5h6.3l5.2 5.2V19a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5Z"/><path d="M13.2 3.7v5h5"/>',
    "more": '<path d="M5.5 12h.1M12 12h.1M18.5 12h.1" stroke-width="2.6"/>',
    "download": '<path d="M12 4.5v10.2m0 0 4-4m-4 4-4-4"/><path d="M5 19.5h14"/>',
}
SEP = '<span class="sep">›</span>'
# 标签页图标：内嵌 SVG，省得浏览器去请求 favicon.ico
FAVICON = "data:image/svg+xml," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="6" fill="#cc7c5e"/>'
    f'<g fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS["book"]}</g></svg>')


def icon(name: str, cls: str = "") -> str:
    return f'<svg class="ic {cls}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def seg(key: str, title: str, options) -> str:
    buttons = "".join(f'<button type="button" data-k="{key}" data-v="{v}">{label}</button>' for v, label in options)
    return f'<div class="seg" role="group" aria-label="{title}" title="{title}">{buttons}</div>'


SEG_THEME = seg("theme", "外观", [("auto", "自动"), ("light", "浅"), ("dark", "深")])
TOOLS = (seg("layout", "释文排版", [("h", "横排"), ("v", "竖排")])
         + seg("plates", "单简图版与整页图版", [("on", "影像"), ("off", "纯文")]) + SEG_THEME)


@dataclass(frozen=True)
class Ctx:
    """本页相对站点的位置。to_root：到站点根的相对路径；cdir：到本典籍目录的相对路径。"""
    to_root: str
    cdir: str

    @property
    def cover(self) -> str:
        return f"{self.cdir}index.html"

    @property
    def data(self) -> str:
        return f"{self.cdir}data.html"


def shell(ctx: Ctx, title: str, desc: str, side: str, crumb: str, content: str, tools: str = TOOLS,
          crumb_attrs: str = "", wide: bool = False) -> str:
    """wide：页面里有释文，竖排时正文栏撑满整宽。"""
    return (f'<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light dark">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="icon" href="{FAVICON}">'
            f'{fonts.preload_links(ctx.to_root)}<style>{fonts.faces_css(ctx.to_root)}{CSS}</style></head>'
            f'<body><div id="app"><aside id="side">{side}</aside>'
            f'<main><header class="top"><button type="button" class="ibtn" id="menu" aria-label="菜单">{icon("menu")}</button>'
            f'<span class="tile">{icon("book")}</span><nav class="crumb"{crumb_attrs}>{crumb}</nav>'
            f'<div class="tools">{tools}</div></header><div class="content{" wide" if wide else ""}">{content}</div></main></div>'
            f'<div id="pop" class="pop" role="menu" hidden></div><script>{JS}</script></body></html>')


def item(href: str, label: str, ic: str, on: bool = False, attrs: str = "") -> str:
    """侧栏的一行：图标 + 文字，选中时灰底。"""
    return (f'<a class="item{" on" if on else ""}" href="{href}"{attrs}>{icon(ic)}<span class="t">{label}</span></a>')


def sidebar(c, ctx, mode: str, search: str, body: str, read_href: str = "", data_href: str = "") -> str:
    """侧栏骨架：收起键、书名、阅读版/数据版切换、检索、内容、页脚。mode 为 read 或 data。"""
    read_href, data_href = read_href or ctx.cover, data_href or ctx.data
    switch = (f'<div class="mode" role="group" aria-label="阅读版与数据版">'
              f'<a id="to-read" class="{"on" if mode == "read" else ""}" href="{read_href}" title="阅读版" aria-label="阅读版">{icon("book")}</a>'
              f'<a id="to-data" class="{"on" if mode == "data" else ""}" href="{data_href}" title="数据版" aria-label="数据版">{icon("table")}</a></div>')
    return (f'<div class="sb-top"><button type="button" class="ibtn" id="sbclose" aria-label="收起侧栏">{icon("panel")}</button>'
            f'<a class="brand" href="{ctx.cover}">{e(c.title)}</a>{switch}</div>{search}{body}<div class="sb-gap"></div>'
            f'<div class="sb-foot"><a href="{REPO_URL}" target="_blank" rel="noopener">数据仓库</a>'
            f'<a href="{ctx.to_root}llms.txt">llms.txt</a></div>')


def search_box(placeholder: str, go: str = "") -> str:
    """go 非空时，回车跳转到该页（数据版）并带上检索词；否则就地过滤本页。"""
    goto = f' data-go="{e(go)}"' if go else ""
    return (f'<label class="sb-search">{icon("search")}<input id="q" type="search" placeholder="{e(placeholder)}" '
            f'aria-label="{e(placeholder)}" autocomplete="off"{goto}></label><div class="hint" id="hits"></div>')


def corpus_links(c, corpora, ctx) -> str:
    """多部典籍时，侧栏里的切换组；只有一部时不显示。"""
    if len(corpora) < 2:
        return ""
    links = "".join(item(f"{ctx.to_root}{x.id}/index.html", e(x.title), "books", on=x.id == c.id) for x in corpora)
    return f'<div class="sb-label">典籍</div>{links}'


def dl_name(text: str, ext: str) -> str:
    return f"{text.replace(' ', '-')}.{ext}"


def menu(ctx: Ctx, stem: str, name: str, whole: bool) -> str:
    """一行的“⋯”菜单内容，藏在该行里，点开时由脚本搬进浮层。stem 是下载文件名（不含扩展名）。"""
    all_ = "全部" if whole else ""
    shown = f"{name} 全部" if whole else name
    links = "".join(
        f'<a role="menuitem" href="{ctx.cdir}{stem}.{ext}" download="{e(dl_name(shown, ext))}">'
        f'{icon("download")}<span>下载{all_}{what}（.{ext}）</span></a>'
        for ext, what in (("txt", "释文"), ("jsonl", "数据")))
    return f'<div class="menu-src" hidden>{links}</div>'


def more_button(label: str) -> str:
    return (f'<button type="button" class="more" aria-haspopup="menu" aria-expanded="false" '
            f'aria-label="更多操作：{e(label)}" title="更多">{icon("more")}</button>')


def leaf(ctx: Ctx, g, w, current: str, data: bool, top: bool) -> str:
    """目录里的一个本。top：它自己就是一项文献（文献只有一个本），前面带文件图标。"""
    href = f"#{e(w.id)}" if data else f"{ctx.cdir}{w.id}.html"
    attrs = f' data-w="{e(w.id)}" data-name="{e(w.meta["name"])}"' if data else ""
    on = w.id == current
    cur = ' aria-current="page"' if on and not data else ""
    cnt = '<span class="cnt"></span>' if data else ""
    ic = icon("file") if top else ""
    name = g.name if top else w.label
    return (f'<div class="item leaf{" on" if on else ""}"><a class="lk" href="{href}"{attrs}{cur}>{ic}'
            f'<span class="t">{e(name)}</span>{cnt}</a>{more_button(w.title)}'
            f'{menu(ctx, w.id, w.title, whole=False)}</div>')


def tree(c, ctx: Ctx, current: str = "", data: bool = False) -> str:
    """文献目录：有几个本的文献是文件夹，各本列在里面；只有一个本的直接是一项。
    current 是当前本的 id；data 为 True 时链接是数据版页内的 #<本 id>。"""
    out = []
    for g in c.groups:
        if g.single:
            out.append(leaf(ctx, g, g.first, current, data, top=True))
            continue
        kids = "".join(leaf(ctx, g, w, current, data, top=False) for w in g.witnesses)
        out.append(
            f'<details class="dir" data-g="{e(g.id)}" open><summary class="item">{icon("folder", "f-shut")}{icon("folder-open", "f-open")}'
            f'<span class="t">{e(g.name)}</span><span class="cnt"></span>{more_button(g.name)}'
            f'{menu(ctx, f"{g.id}-all", g.name, whole=True)}</summary><div class="kids">{kids}</div></details>')
    return f'<div class="tree">{"".join(out)}</div>'


def read_side(c, corpora, ctx: Ctx, current: str = "", on_cover: bool = False, data_href: str = "") -> str:
    """阅读版侧栏：封面、凡例，再是文献目录。current 是当前本的 id。"""
    here = "" if on_cover else ctx.cover
    search = search_box("搜索全部版本", go=ctx.data) if on_cover else search_box("搜索本页释文")
    nav = item(ctx.cover, "封面", "book", on=on_cover) + item(f"{here}#preface", "凡例", "list")
    body = (f'<nav class="sb-nav">{nav}</nav>{corpus_links(c, corpora, ctx)}'
            f'<div class="sb-label">文献</div>{tree(c, ctx, current)}')
    return sidebar(c, ctx, "read", search, body, data_href=data_href)


def facts_fold(wit) -> str:
    """版本信息：折叠，收起时给出前几项的概要。"""
    rows = facts(wit.meta)
    if not rows:
        return ""
    brief = " · ".join(v for _, v in rows[:3])
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in rows)
    return (f'<details class="fold"><summary><span class="t">版本信息</span><span class="m">{e(brief)}</span>{icon("chev", "chev")}'
            f'</summary><div class="body"><dl class="facts">{dl}</dl></div></details>')


def unit(u: dict, wit, thumbs) -> str:
    pre, no, suf = unit_label(u)
    label = label_text(u)
    img = ""
    for p in wit.by_unit.get(u["id"], []):
        t = thumbs.get(p["file"])
        if t and p["kind"] == "slip-plate":
            img += (f'<a class="plate" href="{full_url(p["file"])}" target="_blank" rel="noopener">'
                    f'<img loading="lazy" src="{t}" alt="{e(label)}图版"></a>')
    notes = "".join(f'<div class="note">{e(n["by"])}：{e(n["text"])}</div>' for n in u.get("notes", []))
    return (f'<div class="u" id="{e(u["id"])}"><a class="no" href="#{e(u["id"])}">{e(pre)}<span class="n">{e(no)}</span>{e(suf)}</a>'
            f'<p>{mark_damage(u["text"], u.get("damage"))}</p>{notes}{img}</div>')


def gallery(wit, thumbs) -> str:
    items = []
    for p in wit.plates:
        if p["kind"] == "slip-plate":
            continue
        t = thumbs.get(p["file"])
        loc = p["locator"]
        cap = loc.split(" 第 ", 1)[-1] if " 第 " in loc else loc
        pic = f'<img loading="lazy" src="{t}" alt="{e(cap)}">' if t else e(Path(p["file"]).name)
        items.append(f'<figure><a href="{full_url(p["file"])}" target="_blank" rel="noopener">{pic}</a>'
                     f'<figcaption>{e(cap)}</figcaption></figure>')
    return f'<div class="plates"><h3>整页图版</h3><div class="grid">{"".join(items)}</div></div>' if items else ""


def blob_url(rel: str) -> str:
    return f"{REPO_URL}/blob/main/{quote(rel)}"


def source(s: dict) -> str:
    """一个来源：题名、出版者与年份、授权与抓取情况；授权依据、备注、原始文件（含 SHA-256）收在下面的折叠里。"""
    lic, retr = s.get("license") or {}, s.get("retrieval") or {}
    fetched = retr.get("status") == "fetched"
    name = (f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["title"])}</a>'
            if s.get("url") else e(s["title"]))
    pub = "，".join(str(x) for x in (s.get("publisher"), s.get("year")) if x)
    state = f"；抓取于 {e(retr['date'])}" if fetched and retr.get("date") else "" if fetched else "；仅登记，未抓取"
    rows = []
    if lic.get("evidence"):
        rows.append(("授权依据", e(lic["evidence"])))
    if s.get("notes"):
        rows.append(("备注", e(str(s["notes"]).strip())))
    files = retr.get("files") or []
    if files:
        rows.append(("原始文件", "<br>".join(
            f'<a href="{e(blob_url(f["path"]))}" target="_blank" rel="noopener">{e(f["path"])}</a>　SHA-256 <code>{e(f["sha256"][:12])}…</code>'
            for f in files)))
    more = ("<details class=\"why\"><summary>依据与原始文件</summary><dl class=\"facts\">"
            + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl></details>") if rows else ""
    return (f"<li>{name}" + (f"　{e(pub)}" if pub else "") + f"<small>授权：{e(license_label(lic))}{state}</small>{more}</li>")


def license_brief(sources: list) -> str:
    """折叠收起时的授权概要：各来源授权名去重（一个来源写了几种授权时拆开），没登记名字的记作“未标明”。"""
    names = []
    for s in sources:
        name = (s.get("license") or {}).get("name")
        for t in (name.split("；") if name else ["未标明"]):
            if t not in names:
                names.append(t)
    return "、".join(names)


def sources_fold(c, wit) -> str:
    """这个本的来源与授权：折叠，收起时给出来源数和授权概要。"""
    ss = c.sources_of(wit)
    if not ss:
        return ""
    return (f'<details class="fold"><summary><span class="t">来源与授权</span><span class="m">{len(ss)} 个来源 · {e(license_brief(ss))}</span>'
            f'{icon("chev", "chev")}</summary><div class="body"><ol class="src">{"".join(source(s) for s in ss)}</ol>'
            f'<p class="lic">{e(c.license_note)}</p></div></details>')
