#!/usr/bin/env python3
"""生成站点用的固定字体子集（WOFF2）：思源黑体、思源宋体，SIL OFL 1.1。

先把站点生成一遍，统计页面上实际出现的字，再从固定来源的字体里裁出这些字，存到 scripts/pagegen/assets/fonts/。
来源文件按 URL + SHA-256 固定，下载后先校验；子集的哈希和覆盖的字记在 fonts.json。
新增典籍、页面出现新字后重新运行即可（站点生成时会提示哪些字不在子集里）。

依赖：pip install fonttools brotli
用法：scripts/make_fonts.py [--corpus ID=目录 ...] [--cache 目录]
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fontTools  # noqa: E402
from fontTools import subset, ttLib  # noqa: E402
from fontTools.varLib import instancer  # noqa: E402

from pagegen import cli, fonts  # noqa: E402
from pagegen.corpus import load_corpus  # noqa: E402

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


def used_chars(corpora) -> dict:
    """页面用字，按用在哪里分三档（都加上常用标点）：
    all 全部；text 去掉释文正文（黑体 400：界面、识语、注释）；ui 再去掉注释（500 字重：标题与界面）。
    释文只用宋体 400，所以其余字体的子集小得多。"""
    with tempfile.TemporaryDirectory() as d:
        cli.build(corpora, Path(d), thumbnails=False, ship_fonts=False)      # 只为统计用字，不依赖现有字体文件
        extra = set(EXTRA)
        return {"all": fonts.site_chars(Path(d)) | extra,
                "text": fonts.site_chars(Path(d), units=False) | extra,
                "ui": fonts.site_chars(Path(d), units=False, notes=False) | extra}


def subset_options(flavor=None) -> "subset.Options":
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
    font = ttLib.TTFont(src)
    sub = subset.Subsetter(subset_options())
    sub.populate(text=chars)
    sub.subset(font)
    font = instancer.instantiateVariableFont(font, {"wght": weight}, inplace=True)
    font.flavor = "woff2"
    font.save(str(out))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", action="append", metavar="ID=目录", help="收录一部典籍，可重复；默认同 build_page.py")
    ap.add_argument("--cache", default=os.path.expanduser("~/.cache/daodejing-archive/fonts"), help="来源字体的缓存目录")
    args = ap.parse_args(argv)

    corpora = [load_corpus(cid, path, meta) for cid, path, meta in cli.parse_specs(args.corpus)]
    pools = used_chars(corpora)
    wanted = pools["all"]
    fonts.DIR.mkdir(parents=True, exist_ok=True)
    files, sources, covered = [], [], None
    for family, s in SOURCES.items():
        src = fetch(s["url"], s["sha256"], Path(args.cache))
        (fonts.DIR / s["license_file"]).write_bytes(fetch(s["license_url"], s["license_sha256"], Path(args.cache)).read_bytes())
        cmap = ttLib.TTFont(src, lazy=True).getBestCmap()
        have = {c for c in wanted if ord(c) in cmap}
        covered = have if covered is None else covered & have      # 黑体、宋体共有的字
        for weight in WEIGHTS:
            scope, key = SCOPE[(family, weight)]
            pool = have & pools[key]
            name = f"{s['slug']}-{weight}.woff2"
            make_subset(src, weight, "".join(sorted(pool)), fonts.DIR / name)
            data = (fonts.DIR / name).read_bytes()
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
    (fonts.MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(f["bytes"] for f in files)
    for f in files:
        print(f"{f['file']:26s} {f['bytes'] / 1024:7.0f} KB")
    print(f"共 {total / 1024:.0f} KB；覆盖 {len(covered)} 字；字体里没有 {len(manifest['unavailable'])} 字："
          f"{manifest['unavailable'] or '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
