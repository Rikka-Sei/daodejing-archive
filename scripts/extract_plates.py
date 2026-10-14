#!/usr/bin/env python3
"""从扫描本 PDF 中原样抽出图版页的内嵌 JPEG，存到 data/images/，并生成 data/plates/<版本>.jsonl。

用法：python3 scripts/extract_plates.py <PDF 所在目录>
PDF 不进仓库（整本书含现代释文、论文），只抽图版页；抽取用 poppler 的 pdfimages -j，
JPEG 字节不经重新编码。PDF 的 SHA-256 必须与下表一致，防止用错版本。
"""
import hashlib
import json
import re
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
        # 第 16–44 页原大图版，第 45–119 页放大图版，第 120–123 页简背；每页收哪几枚简见 BEIDA_SLIPS
        "pages": [(p, "beida", None) for p in range(16, 124)],
    },
    {
        "pdf": "长沙马王堆汉墓简帛集成  1_13896076.pdf",
        "sha256": "1e4e6686084b8367fda760ebfea64e04e125c2dc2f062aefe94d8974c5dce010",
        "source": "mawangdui-jicheng-2014",
        # 册1 整理图版：第 115–122 页为老子甲本（书页 95–102），第 162–169 页为老子乙本（书页 142–149）
        "pages": [(p, "mawangdui-jia", None) for p in range(115, 123)]
                 + [(p, "mawangdui-yi", None) for p in range(162, 170)],
    },
]

# 北大本每页图版下方印的简号（按页面从右到左），逐页目读核对过。
# 简号与 data/witnesses/beida.jsonl 的 unit_no 一致；简背图版的"一：2"等是残片编号，对应到该简。
BEIDA_SLIPS = {
    16: ["1", "2正", "2背", "3", "4", "5", "6", "7"],
    **{16 + i: [str(n) for n in range(8 * i, 8 * i + 8)] for i in range(1, 7)},  # 17–22：8–55
    23: [str(n) for n in range(56, 64)],
    24: [str(n) for n in range(64, 71)],
    25: [str(n) for n in range(71, 79)],
    26: [str(n) for n in range(79, 86)],
    **{27 + i: [str(n) for n in range(86 + 8 * i, 94 + 8 * i)] for i in range(4)},  # 27–30：86–117
    31: [str(n) for n in range(118, 124)],
    32: ["124正", "124背"] + [str(n) for n in range(125, 131)],
    **{33 + i: [str(n) for n in range(131 + 8 * i, 139 + 8 * i)] for i in range(11)},  # 33–43：131–218
    44: ["219", "220", "221"],
    45: ["1", "2正", "2背"],
    **{46 + i: [str(n) for n in range(3 + 3 * i, 6 + 3 * i)] for i in range(40)},  # 46–85：3–122
    86: ["123"],
    87: ["124正", "124背", "125"],
    **{88 + i: [str(n) for n in range(126 + 3 * i, 129 + 3 * i)] for i in range(32)},  # 88–119：126–221
    120: ["1", "6", "8", "11", "21"],
    121: ["23", "31", "40", "49", "52", "70"],
    122: ["82", "83", "95", "97", "99", "108"],
    123: ["118", "120", "148", "153", "154", "214"],
}

# 马王堆每页图版下方印的帛书行号（逐页目读核对过），行号与 tt24h 实录一致。
# 甲本：页 → (起行, 止行)；第 122 页左端另有《五行》第 1–4 行。
# 乙本：每段帛书分上下两页印，页 → (起行, 止行, "上"或"下")。
MAWANGDUI_LINES = {
    "mawangdui-jia": {115: (1, 22), 116: (23, 44), 117: (45, 66), 118: (67, 88),
                      119: (89, 108), 120: (109, 130), 121: (131, 152), 122: (153, 169)},
    "mawangdui-yi": {162: (1, 16, "上"), 163: (1, 16, "下"), 164: (17, 40, "上"), 165: (17, 40, "下"),
                     166: (41, 64, "上"), 167: (41, 64, "下"), 168: (65, 78, "上"), 169: (65, 78, "下")},
}
# 行号到通行本章号的对应取自 tt24h 的排版数据（每章一段，段内〚L…〛是行尾）
BOSHU_TYP = {"mawangdui-jia": "data/raw/tt24h-daodejing/v0.1.3/帛书甲本.typ",
             "mawangdui-yi": "data/raw/tt24h-daodejing/v0.1.3/帛书乙本.typ"}

WITNESS_DIR = {"guodian-jia": "jia", "guodian-yi": "yi", "guodian-bing": "bing", "beida": "beida",
               "mawangdui-jia": "jia", "mawangdui-yi": "yi"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def beida_kind(page: int) -> str:
    return "原大图版" if page <= 44 else "放大图版" if page <= 119 else "简背图版"


def cn_number(s: str) -> int:
    digits = dict(zip("一二三四五六七八九", range(1, 10)))
    if "十" not in s:
        return digits[s]
    tens, ones = s.split("十")
    return (digits[tens] if tens else 1) * 10 + (digits[ones] if ones else 0)


def boshu_line_chapters(witness: str) -> dict[str, list[int]]:
    """行号 → 该行涉及的通行本章号，按帛书上的先后。一行跨两章时两章都算。"""
    typ = (ROOT / BOSHU_TYP[witness]).read_text(encoding="utf-8")
    lines: dict[str, list[int]] = {}
    pending: list[int] = []
    for element, chapter in re.findall(r'"(第([一二三四五六七八九十]+)章&[^"]*)"', typ):
        ch = cn_number(chapter)
        pending.append(ch)
        for m in re.finditer(r"〚L([^〛]+)〛", element):
            line = lines.setdefault(m.group(1), [])
            line += [c for c in pending if c not in line]
            pending = [ch] if re.search(r"[^\s&\[\]]", element[m.end():]) else []
    return lines


def mawangdui_units(witness: str, page: int) -> list[str]:
    """一页图版涉及的章，按帛书上的先后排列。"""
    ids = {}
    for line in (ROOT / "data" / "witnesses" / f"{witness}.jsonl").read_text(encoding="utf-8").splitlines():
        u = json.loads(line)
        ids[int(u["unit_no"])] = u["id"]
    line_chapters = boshu_line_chapters(witness)
    lo, hi, *half = MAWANGDUI_LINES[witness][page]
    out: list[str] = []
    for n in range(lo, hi + 1):
        for ch in line_chapters[f"{n}{half[0] if half else ''}"]:
            if ids[ch] not in out:
                out.append(ids[ch])
    return out


def page_label(witness: str, page: int) -> str:
    if witness == "beida":
        return beida_kind(page)
    lo, hi, *half = MAWANGDUI_LINES[witness][page]
    name = "老子甲本" if witness == "mawangdui-jia" else "老子乙本"
    return f"{name}整理图版，第 {lo}–{hi} 行" + (f"{half[0]}半" if half else "")


def beida_units() -> dict[str, str]:
    """unit_no → unit id。简背残片挂到该简正面那一条（"2""124"挂到"2正""124正"）。"""
    ids = {}
    for line in (ROOT / "data" / "witnesses" / "beida.jsonl").read_text(encoding="utf-8").splitlines():
        u = json.loads(line)
        ids[u["unit_no"]] = u["id"]
    return ids


def main() -> None:
    beida = beida_units()
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
                "locator": f"{scan['pdf']} 第 {page} 页" + ("" if slip else f"（{page_label(witness, page)}）"),
                "units": [f"{witness}.{slip:03d}"] if slip
                else [beida[n] for n in BEIDA_SLIPS[page]] if witness == "beida"
                else mawangdui_units(witness, page),
            }
            plates.setdefault(witness, []).append(rec)
    for witness, recs in plates.items():
        path = ROOT / "data" / "plates" / f"{witness}.jsonl"
        path.parent.mkdir(exist_ok=True)
        # 别的来源（如 Commons 照片）的记录不是本脚本生成的，原样保留在后面
        mine = {s["source"] for s in SCANS}
        others = [line for line in path.read_text(encoding="utf-8").splitlines()
                  if line.strip() and json.loads(line)["source"] not in mine] if path.exists() else []
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
                        + "".join(line + "\n" for line in others), encoding="utf-8")
        print(f"{witness}: {len(recs)} 张")


if __name__ == "__main__":
    main()
