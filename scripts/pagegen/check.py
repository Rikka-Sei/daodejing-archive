"""生成后检查：站内相对链接（含样式里的 url()）必须指向存在的文件；带锚点的链接，目标页面里必须有这个 id。"""
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

HREF = re.compile(r'(?:href|src)="([^"]+)"|url\(([^)"\']+)\)')
ID = re.compile(r'\bid="([^"]+)"')


def _ids(path: Path, cache: dict) -> set:
    if path not in cache:
        cache[path] = set(ID.findall(path.read_text(encoding="utf-8")))
    return cache[path]


def check_links(out_root: Path) -> list:
    problems, cache = [], {}
    for page in sorted(out_root.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        rel = page.relative_to(out_root)
        for attr, css in HREF.findall(text):
            ref = attr or css
            u = urlparse(ref)
            if u.scheme or u.netloc:
                continue
            target = page if not u.path else (page.parent / unquote(u.path))
            if not target.exists():
                problems.append(f"{rel}: {ref} 指向的文件不存在")
                continue
            frag = unquote(u.fragment)
            if frag and target.suffix == ".html":
                ids = _ids(target, cache)
                # 数据版里 #<版本id> 由脚本映射到 w-<版本id>
                if frag not in ids and f"w-{frag}" not in ids:
                    problems.append(f"{rel}: {ref} 的锚点 #{frag} 在目标页面里不存在")
    return problems
