"""固定字体：随站点输出子集字体，并检查站点用字是否都在子集里。

字体文件在 assets/fonts/，由 scripts/make_fonts.py 生成（思源黑体、思源宋体，SIL OFL 1.1，来源与哈希记在 fonts.json）。
页面只用 @font-face 引用这几个文件，不依赖观看者机器上装了什么字体；子集里没有的字，浏览器逐字回退到系统字体。
"""
import html
import json
import re
import shutil
from pathlib import Path

DIR = Path(__file__).resolve().parent / "assets" / "fonts"
MANIFEST = DIR / "fonts.json"
FAMILY = {"sans": "DG Sans", "serif": "DG Serif"}   # CSS 里的字体族名
PRELOAD = (("sans", 400), ("serif", 400))            # 每页都用到的两个字重，提前加载
_BLOCKS = re.compile(r"<(style|script)\b[^>]*>(.*?)</\1>", re.S)
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_TAGS = re.compile(r"<[^>]+>")
_UNIT_P = re.compile(r"<p>.*?</p>", re.S)                       # 释文正文（不带 class 的 <p>）：只用宋体 400
_NOTES = re.compile(r'<div class="note">.*?</div>', re.S)       # 来源附带的注释：黑体 400
_SHOWN_ATTRS = re.compile(r'\b(?:placeholder|alt)="([^"]*)"')   # 属性值里会画出来的文字：输入框提示、图片加载失败时的替代文字


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}


def faces_css(to_root: str) -> str:
    """@font-face 规则。to_root 是本页到站点根的相对路径。"""
    return "".join(
        f'@font-face{{font-family:"{FAMILY[f["family"]]}";font-weight:{f["weight"]};font-style:normal;font-display:swap;'
        f'src:url({to_root}fonts/{f["file"]}) format("woff2")}}' for f in manifest().get("files", []))


def preload_links(to_root: str) -> str:
    files = {(f["family"], f["weight"]): f["file"] for f in manifest().get("files", [])}
    return "".join(f'<link rel="preload" href="{to_root}fonts/{files[k]}" as="font" type="font/woff2" crossorigin>'
                   for k in PRELOAD if k in files)


def copy_fonts(out_root: Path) -> None:
    """把字体文件、授权文本和清单复制到站点的 fonts/。"""
    m = manifest()
    if not m:
        return
    dest = out_root / "fonts"
    dest.mkdir(parents=True, exist_ok=True)
    names = [f["file"] for f in m["files"]] + list(m.get("licenses", [])) + [MANIFEST.name]
    for name in names:
        shutil.copyfile(DIR / name, dest / name)


def visible_text(page: str, units: bool = True, notes: bool = True) -> str:
    """页面上会画出来的文字：标签之间的正文，输入框提示和图片替代文字，以及样式、脚本里（去掉注释）的字符串，
    脚本会往页面里写字（如“本页命中”），样式会给序号加“、”。units、notes 为 False 时分别不含释文正文、来源注释。"""
    if not units:
        page = _UNIT_P.sub("", page)
    if not notes:
        page = _NOTES.sub("", page)
    shown = [m.group(2) for m in _BLOCKS.finditer(page)]
    shown = [_COMMENT.sub("", t) for t in shown]
    shown += _SHOWN_ATTRS.findall(page)
    return html.unescape(_TAGS.sub("", _BLOCKS.sub("", page)) + "".join(shown))


def site_chars(out_root: Path, units: bool = True, notes: bool = True) -> set:
    chars = set()
    for page in out_root.rglob("*.html"):
        chars.update(visible_text(page.read_text(encoding="utf-8"), units, notes))
    return {c for c in chars if not c.isspace() and c.isprintable()}


def uncovered(chars: set) -> tuple:
    """(需要重新生成子集的字, 字体本身没有、只能用系统字体显示的字)。"""
    m = manifest()
    if not m:
        return "", ""
    known = set(m["chars"]) | set(m["unavailable"])
    fresh = "".join(sorted(c for c in chars if c not in known))
    return fresh, m["unavailable"]
