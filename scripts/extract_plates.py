#!/usr/bin/env python3
"""从扫描本 PDF 中原样抽出图版页的内嵌 JPEG，存到 data/images/，并生成 data/plates/<版本>.jsonl。

用法：python3 scripts/extract_plates.py <PDF 所在目录>
PDF 不进仓库（整本书含现代释文、论文），只抽图版页；抽取用 poppler 的 pdfimages -j，
JPEG 字节不经重新编码。PDF 的 SHA-256 必须与下表一致，防止用错版本。
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 每本扫描本：哪几页是图版、对应哪个版本的哪枚简
SCANS = [
    {
        "pdf": "郭店楚墓竹简  老子甲.pdf",
        "sha256": "44187c206dacddf9d85bd7a5549f798aa504e8c01347ccd07cacfa84c803e792",
        "source": "jianbo-shufa-guodian-2002",
        # 第 6–44 页一页一简：甲组简 1–39
        "pages": [(p, "guodian-jia", p - 5) for p in range(6, 45)],
    },
    {
        "pdf": "郭店楚墓竹简  老子乙.丙.pdf",
        "sha256": "08c350d13b31e5adeb639bae42f1ae98b269c7d124790ba8c57f9242733a492c",
        "source": "jianbo-shufa-guodian-2002",
        # 第 5–22 页为乙组简 1–18，第 23–36 页为丙组简 1–14
        "pages": [(p, "guodian-yi", p - 4) for p in range(5, 23)]
                 + [(p, "guodian-bing", p - 22) for p in range(23, 37)],
    },
    {
        "pdf": "北京大学藏西汉竹书 2_13350360.pdf",
        "sha256": "9fb9c39253ced4a1b07bfbbb3e9476cc5d9ac1b5973301f849813b4e28d4bf17",
        "source": "beida-2012",
        # 第 16–44 页原大图版，第 45–119 页放大图版，第 120–123 页简背；未逐简对应
        "pages": [(p, "beida", None) for p in range(16, 124)],
    },
]

WITNESS_DIR = {"guodian-jia": "jia", "guodian-yi": "yi", "guodian-bing": "bing", "beida": "beida"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def beida_kind(page: int) -> str:
    return "原大图版" if page <= 44 else "放大图版" if page <= 119 else "简背图版"


def main() -> None:
    pdf_dir = Path(sys.argv[1])
    plates: dict[str, list[dict]] = {}
    for scan in SCANS:
        pdf = pdf_dir / scan["pdf"]
        if sha256(pdf) != scan["sha256"]:
            sys.exit(f"{pdf.name}: SHA-256 与登记不符，可能不是同一份扫描本")
        out_dir = ROOT / "data" / "images" / scan["source"]
        out_dir.mkdir(parents=True, exist_ok=True)
        for page, witness, slip in scan["pages"]:
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run(["pdfimages", "-j", "-f", str(page), "-l", str(page), str(pdf), f"{tmp}/x"],
                               check=True, capture_output=True)
                imgs = sorted(Path(tmp).glob("x-*"))
                if len(imgs) != 1 or imgs[0].suffix != ".jpg":
                    sys.exit(f"{pdf.name} 第 {page} 页应恰有一张 JPEG，实有 {[i.name for i in imgs]}")
                name = f"{WITNESS_DIR[witness]}-{slip:03d}.jpg" if slip else f"{WITNESS_DIR[witness]}-p{page:03d}.jpg"
                dest = out_dir / name
                shutil.copyfile(imgs[0], dest)
            rec = {
                "file": str(dest.relative_to(ROOT)),
                "witness": witness,
                "source": scan["source"],
                "kind": "slip-plate" if slip else "page",
                "locator": f"{scan['pdf']} 第 {page} 页" + ("" if slip else f"（{beida_kind(page)}）"),
                "units": [f"{witness}.{slip:03d}"] if slip else [],
            }
            plates.setdefault(witness, []).append(rec)
    for witness, recs in plates.items():
        path = ROOT / "data" / "plates" / f"{witness}.jsonl"
        path.parent.mkdir(exist_ok=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
        print(f"{witness}: {len(recs)} 张")


if __name__ == "__main__":
    main()
