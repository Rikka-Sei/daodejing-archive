"""影像缩略图。Pillow 不可用或显式关闭时返回 None，页面改为只放原图链接。"""
from pathlib import Path
from urllib.parse import quote

from .corpus import ROOT

try:
    from PIL import Image
except ImportError:
    Image = None

WIDTH = 360          # 释文旁与整页图版的缩略图
COVER_WIDTH = 720    # 封面卡片的缩略图，高分屏下仍然清楚
REPO_RAW = "https://raw.githubusercontent.com/Rikka-Sei/daodejing-archive/main/"


def full_url(rel: str) -> str:
    return REPO_RAW + quote(rel)


class Thumbs:
    def __init__(self, out_dir: Path, enabled: bool = True):
        self.out_dir = out_dir
        self.enabled = enabled and Image is not None

    def get(self, rel: str, width: int = WIDTH):
        """生成并返回相对 out_dir 的缩略图路径；width 不是默认值时文件名带上宽度。"""
        if not self.enabled:
            return None
        name = rel.replace("data/images/", "").replace("/", "__")
        if width != WIDTH:
            name = f"{Path(name).stem}@{width}.jpg"
        dst = self.out_dir / "thumbs" / name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(ROOT / rel) as im:
                im = im.convert("RGB")
                if im.width > width:
                    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
                im.save(dst, "JPEG", quality=72, optimize=True)
        return "thumbs/" + dst.name
