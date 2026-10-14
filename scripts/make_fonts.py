#!/usr/bin/env python3
"""生成站点用的固定字体子集（WOFF2）：思源黑体、思源宋体，SIL OFL 1.1。

先构建站点（npm run build），统计 dist/ 里页面实际出现的字，再从固定来源的字体里裁出这些字，存到 public/fonts/。
来源文件按 URL + SHA-256 固定，下载后先校验；子集的哈希和覆盖的字记在 fonts.json。
新增典籍、页面出现新字后重新运行即可（构建时会提示哪些字不在子集里），然后重新构建。

依赖：pip install fonttools brotli
用法：npm run build && scripts/make_fonts.py [--site dist] [--cache 目录]
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FONT_DIR = REPO / "public" / "fonts"
MANIFEST = FONT_DIR / "fonts.json"

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
SOURCES = {
    "sans": {
        "name": "Noto Sans SC", "slug": "noto-sans-sc", "license_file": "OFL-NotoSansSC.txt",
        "url": f"{GF}/notosanssc/NotoSansSC%5Bwght%5D.ttf",
        "sha256": "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da",
        "license_url": f"{GF}/notosanssc/OFL.txt",
        "license_sha256": "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9"},
    "serif": {
        "name": "Noto Serif SC", "slug": "noto-serif-sc", "license_file": "OFL-NotoSerifSC.txt",
        "url": f"{GF}/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
        "sha256": "050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9",
        "license_url": f"{GF}/notoserifsc/OFL.txt",
        "license_sha256": "5e0da210fb04058a8c0087985d2d456b931c2579811a49655721d3cf0c36b6d6"},
}
WEIGHTS = (400, 500)
# 各字体各字重装哪些字：(说明, used_chars 里的档)。宋体 400 用于释文，要全；500 字重只用于标题和界面
SCOPE = {("sans", 400): ("界面、识语与注释用字", "text"), ("sans", 500): ("界面与标题用字", "ui"),
         ("serif", 400): ("全部用字", "all"), ("serif", 500): ("界面与标题用字", "ui")}
# 页面上没出现、但样式会生成或常用的字：ASCII、序号后的“、”、常见标点
EXTRA = "".join(chr(c) for c in range(0x20, 0x7F)) + "、。，；：？！“”‘’（）《》〈〉【】「」『』·—…›"


def fetch(url: str, sha256: str, cache: Path) -> Path:
    """下载到缓存目录并校验哈希；缓存里已有且哈希对就直接用。"""
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{sha256[:12]}-{url.rsplit('/', 1)[-1].replace('%5B', '[').replace('%5D', ']')}"
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == sha256:
        return dest
    with urllib.request.urlopen(url, timeout=300) as resp:
        data = resp.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        sys.exit(f"校验失败：{url}\n  应为 {sha256}\n  实为 {got}\n"
                 "上游文件变了。确认新版可用后，更新本脚本里固定的 SHA-256。")
    dest.write_bytes(data)
    return dest


_BLOCKS = re.compile(r"<(style|script)\b[^>]*>(.*?)</\1>", re.S)
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_TAGS = re.compile(r"<[^>]+>")
_UNIT_P = re.compile(r"<p>.*?</p>", re.S)                       # 释文正文（不带 class 的 <p>）：只用宋体 400
_NOTES = re.compile(r'<div class="note">.*?</div>', re.S)       # 来源附带的注释：黑体 400
_SHOWN_ATTRS = re.compile(r'\b(?:placeholder|alt)="([^"]*)"')   # 属性值里会画出来的文字：输入框提示、图片加载失败时的替代文字


def visible_text(page: str, units: bool = True, notes: bool = True) -> str:
    """页面上会画出来的文字：标签之间的正文，输入框提示和图片替代文字，以及样式、脚本里（去掉注释）的字符串，
    脚本会往页面里写字（如“本页命中”），样式会给序号加“、”。units、notes 为 False 时分别不含释文正文、来源注释。
    与 src/lib/verify.ts 的 visibleText 同一套规则，构建时的字体提示用的是那边。"""
    if not units:
        page = _UNIT_P.sub("", page)
    if not notes:
        page = _NOTES.sub("", page)
    shown = [_COMMENT.sub("", m.group(2)) for m in _BLOCKS.finditer(page)]
    shown += _SHOWN_ATTRS.findall(page)
    return html.unescape(_TAGS.sub("", _BLOCKS.sub("", page)) + "".join(shown))


def site_chars(site: Path, units: bool = True, notes: bool = True) -> set:
    """已构建站点用到的字：全部页面的可见文字，加上外部样式与脚本（_astro/）里的字符串。"""
    chars = set()
    for page in site.rglob("*.html"):
        chars.update(visible_text(page.read_text(encoding="utf-8"), units, notes))
    for asset in list(site.rglob("*.css")) + list(site.rglob("*.js")):
        chars.update(_COMMENT.sub("", asset.read_text(encoding="utf-8")))
    return {c for c in chars if not c.isspace() and c.isprintable()}


def used_chars(site: Path) -> dict:
    """页面用字，按用在哪里分三档（都加上常用标点）：
    all 全部；text 去掉释文正文（黑体 400：界面、识语、注释）；ui 再去掉注释（500 字重：标题与界面）。
    释文只用宋体 400，所以其余字体的子集小得多。"""
    extra = set(EXTRA)
    return {"all": site_chars(site) | extra,
            "text": site_chars(site, units=False) | extra,
            "ui": site_chars(site, units=False, notes=False) | extra}


def subset_options(flavor=None) -> "subset.Options":
    from fontTools import subset      # fonttools 只有生成子集时才用到，统计用字不依赖它

    opts = subset.Options()
    opts.flavor = flavor
    opts.layout_features = ["*"]      # 竖排用的 vert/vrt2 等一并保留
    opts.name_IDs, opts.name_languages, opts.name_legacy = ["*"], ["*"], True   # 版权与授权信息原样保留
    opts.notdef_outline = True
    opts.hinting = False
    opts.glyph_names = False
    return opts


def make_subset(src: Path, weight: int, chars: str, out: Path) -> None:
    """先在变体字体上裁出用到的字（实例化才快），再取指定字重，存成 WOFF2。"""
    from fontTools import subset, ttLib
    from fontTools.varLib import instancer

    font = ttLib.TTFont(src)
    sub = subset.Subsetter(subset_options())
    sub.populate(text=chars)
    sub.subset(font)
    font = instancer.instantiateVariableFont(font, {"wght": weight}, inplace=True)
    font.flavor = "woff2"
    font.save(str(out))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default=str(REPO / "dist"), help="已构建的站点目录，默认 dist（先运行 npm run build）")
    ap.add_argument("--cache", default=os.path.expanduser("~/.cache/daodejing-archive/fonts"), help="来源字体的缓存目录")
    args = ap.parse_args(argv)

    site = Path(args.site)
    if not any(site.rglob("*.html")):
        sys.exit(f"{site} 里没有页面，先运行 npm run build")
    import fontTools
    from fontTools import ttLib

    pools = used_chars(site)
    wanted = pools["all"]
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    files, sources, covered = [], [], None
    for family, s in SOURCES.items():
        src = fetch(s["url"], s["sha256"], Path(args.cache))
        (FONT_DIR / s["license_file"]).write_bytes(fetch(s["license_url"], s["license_sha256"], Path(args.cache)).read_bytes())
        cmap = ttLib.TTFont(src, lazy=True).getBestCmap()
        have = {c for c in wanted if ord(c) in cmap}
        covered = have if covered is None else covered & have      # 黑体、宋体共有的字
        for weight in WEIGHTS:
            scope, key = SCOPE[(family, weight)]
            pool = have & pools[key]
            name = f"{s['slug']}-{weight}.woff2"
            make_subset(src, weight, "".join(sorted(pool)), FONT_DIR / name)
            data = (FONT_DIR / name).read_bytes()
            files.append({"file": name, "family": family, "weight": weight, "scope": scope, "chars": len(pool),
                          "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        sources.append({"family": family, "name": s["name"], "url": s["url"].replace("%5B", "[").replace("%5D", "]"),
                        "sha256": s["sha256"], "license": "SIL OFL 1.1", "license_file": s["license_file"],
                        "reserved_font_name": "Source"})
    manifest = {
        "about": "站点自带的固定字体子集，由 scripts/make_fonts.py 生成；只含站点用到的字，其余字回退到系统字体。"
                 "各文件装哪些字见 files[].scope：释文只用宋体 400，所以其余文件只装界面、标题、识语等处的字。",
        "fonttools": fontTools.version,
        "chars": "".join(sorted(covered)),
        "unavailable": "".join(sorted(wanted - covered)),
        "files": files,
        "licenses": [s["license_file"] for s in SOURCES.values()],
        "sources": sources,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(f["bytes"] for f in files)
    for f in files:
        print(f"{f['file']:26s} {f['bytes'] / 1024:7.0f} KB")
    print(f"共 {total / 1024:.0f} KB；覆盖 {len(covered)} 字；字体里没有 {len(manifest['unavailable'])} 字："
          f"{manifest['unavailable'] or '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
