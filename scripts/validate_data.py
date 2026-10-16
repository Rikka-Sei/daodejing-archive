#!/usr/bin/env python3
"""校验 data/ 下的全部数据：结构、编号、残缺区间、来源追溯、原始文件哈希，影像与文本单位的关联，以及对读表与逐行释文。

用法：python3 scripts/validate_data.py [--root 仓库根目录]
有任何问题时退出码为 1。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alignment as al  # noqa: E402


def load_schema(root: Path, name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((root / "schema" / name).read_text(encoding="utf-8")))


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def schema_errors(validator: Draft202012Validator, doc, where: str):
    for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(根)"
        yield f"{where}: {loc}: {e.message}"


def check_alignment(root: Path, witnesses: set[str]) -> tuple[list[str], int]:
    """对读表与逐行释文（data/alignment/）：版本都已登记、文件名与章号相符、两者互相对得上。

    没有这个目录就跳过。返回 (问题清单, 章数)。
    """
    base = root / al.OUT
    if not base.exists():
        return [], 0
    problems: list[str] = []

    def read(name: str):
        try:
            return json.loads((base / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            problems.append(f"{al.OUT}/{name}: 读不了（{e}）")
            return None

    versions = read("versions.json")
    for name in ("equivalents.json", "glyphs.json", "study.json"):
        read(name)
    ids: set[str] = set()
    for v in versions if isinstance(versions, list) else []:
        vid = v.get("id") if isinstance(v, dict) else None
        if not isinstance(vid, str):
            problems.append(f"{al.OUT}/versions.json: 有一项没有 id")
        elif vid in ids:
            problems.append(f"{al.OUT}/versions.json: id 重复 {vid}")
        elif vid not in witnesses:
            problems.append(f"{al.OUT}/versions.json: {vid} 不是已登记的版本 id")
        else:
            ids.add(vid)
    if not ids:
        return problems + [f"{al.OUT}/versions.json: 没有任何可用的版本"], 0

    for p in sorted((base / "chapters").glob("*.json")):
        try:
            n = json.loads(p.read_text(encoding="utf-8"))["chapter"]
        except (OSError, ValueError, KeyError, TypeError) as e:
            problems.append(f"{al.OUT}/chapters/{p.name}: 读不了（{e!r}）")
            continue
        if not isinstance(n, int) or p.stem != f"{n:03d}":
            problems.append(f"{al.OUT}/chapters/{p.name}: 文件名应是章号的三位数字，里面写的是第 {n} 章")
    try:
        chapters, lines = al.load(root)
        problems += [f"{al.OUT}: {x}" for x in al.verify(chapters, lines, known=ids)]
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
        problems.append(f"{al.OUT}: 对读表或逐行释文的结构不对（{type(e).__name__}: {e}）")
        return problems, 0
    return problems, len(chapters)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    root = Path(ap.parse_args().root)
    data = root / "data"
    problems: list[str] = []

    # 版本登记表
    reg_path = data / "witnesses.yaml"
    if not reg_path.exists():
        print("缺少 data/witnesses.yaml", file=sys.stderr)
        return 1
    witnesses = {w["id"] for w in yaml.safe_load(reg_path.read_text(encoding="utf-8"))["witnesses"]}

    # 来源
    src_validator = load_schema(root, "source.schema.json")
    sources: dict[str, dict] = {}
    for p in sorted((data / "sources").glob("*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        errs = list(schema_errors(src_validator, doc, str(p.relative_to(root))))
        problems += errs
        if errs:
            continue
        sources[doc["id"]] = doc
        for w in doc["witnesses"]:
            if w not in witnesses:
                problems.append(f"{p.name}: 引用了未登记的版本 {w}")
        if doc["retrieval"]["status"] == "fetched":
            if not doc["retrieval"].get("files"):
                problems.append(f"{p.name}: 状态为 fetched 但没有登记任何原始文件")
            if doc["license"]["status"] == "unknown":
                problems.append(f"{p.name}: 已抓取但授权状态仍是 unknown，先确认授权再入库")
        for f in doc["retrieval"].get("files", []):
            fp = root / f["path"]
            if not fp.exists():
                problems.append(f"{p.name}: 原始文件不存在 {f['path']}")
            elif sha256_of(fp) != f["sha256"]:
                problems.append(f"{p.name}: 原始文件哈希不符 {f['path']}（文件被改动？）")

    # 文本单位
    unit_validator = load_schema(root, "unit.schema.json")
    total = 0
    for p in sorted((data / "witnesses").glob("*.jsonl")):
        wid = p.stem
        if wid not in witnesses:
            problems.append(f"{p.name}: 文件名不是已登记的版本 id")
        seen: set[str] = set()
        expect = 1
        for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            where = f"{p.name}:{ln}"
            try:
                u = json.loads(line)
            except ValueError as e:
                problems.append(f"{where}: 不是合法 JSON（{e}）")
                continue
            errs = list(schema_errors(unit_validator, u, where))
            problems += errs
            if errs:
                continue
            total += 1
            if u["witness"] != wid:
                problems.append(f"{where}: witness 字段 {u['witness']} 与文件名不一致")
            if u["id"] in seen:
                problems.append(f"{where}: id 重复 {u['id']}")
            seen.add(u["id"])
            want = f"{wid}.{expect:03d}"
            if u["id"] != want:
                problems.append(f"{where}: id 应为 {want}，实为 {u['id']}（编号必须连续、按阅读顺序）")
            expect += 1
            n = len(u["text"])
            for d in u.get("damage", []):
                if not (0 <= d["start"] < d["end"] <= n):
                    problems.append(f"{where}: damage 区间 [{d['start']},{d['end']}) 超出 text 长度 {n}")
            for m in u.get("marks", []):
                if "offset" in m and m["offset"] > n:
                    problems.append(f"{where}: mark 偏移 {m['offset']} 超出 text 长度 {n}")
            ref = u["source_ref"]
            src = sources.get(ref["source"])
            if src is None:
                problems.append(f"{where}: 来源 {ref['source']} 未登记")
                continue
            if wid not in src["witnesses"]:
                problems.append(f"{where}: 来源 {ref['source']} 并未声明提供版本 {wid}")
            raw = ref.get("raw_file")
            if raw is None:
                problems.append(f"{where}: 缺少 raw_file，无法追溯到原始抓取文件")
            elif raw not in {f["path"] for f in src["retrieval"].get("files", [])}:
                problems.append(f"{where}: raw_file {raw} 没有在来源 {ref['source']} 中登记哈希")

    # 影像
    plate_validator = load_schema(root, "plate.schema.json")
    unit_ids: set[str] = set()
    for p in (data / "witnesses").glob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                unit_ids.add(json.loads(line)["id"])
            except (ValueError, KeyError, TypeError):
                pass  # 上面已报告
    plates = 0
    seen_files: set[object] = set()
    for p in sorted((data / "plates").glob("*.jsonl")):
        wid = p.stem
        if wid not in witnesses:
            problems.append(f"{p.name}: 文件名不是已登记的版本 id")
        for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            where = f"plates/{p.name}:{ln}"
            try:
                rec = json.loads(line)
            except ValueError as e:
                problems.append(f"{where}: 不是合法 JSON（{e}）")
                continue
            errs = list(schema_errors(plate_validator, rec, where))
            problems += errs
            if errs:
                continue
            plates += 1
            if rec["witness"] != wid:
                problems.append(f"{where}: witness 字段 {rec['witness']} 与文件名不一致")
            # 同一张图只登记一次；整页图上逐简裁出的块（带 crop）按“图 + 块”算，块要在图内、同一块不重复
            key = (rec["file"], tuple(rec["crop"])) if "crop" in rec else rec["file"]
            if key in seen_files:
                problems.append(f"{where}: 图片重复登记 {rec['file']}")
            seen_files.add(key)
            if "crop" in rec:
                if rec["kind"] != "slip-plate":
                    problems.append(f"{where}: 只有单简图版（slip-plate）可以带 crop")
                left, top, w, h = rec["crop"]
                img = root / rec["file"]
                if img.exists():
                    from PIL import Image  # 只在有裁块时用到

                    with Image.open(img) as im:
                        if w <= 0 or h <= 0 or left + w > im.width or top + h > im.height:
                            problems.append(f"{where}: crop {rec['crop']} 超出图片范围 {im.width}×{im.height}")
            src = sources.get(rec["source"])
            if src is None:
                problems.append(f"{where}: 来源 {rec['source']} 未登记")
            elif rec["file"] not in {f["path"] for f in src["retrieval"].get("files", [])}:
                problems.append(f"{where}: 图片 {rec['file']} 没有在来源 {rec['source']} 中登记哈希")
            for uid in rec["units"]:
                if uid not in unit_ids:
                    problems.append(f"{where}: 关联的文本单位 {uid} 不存在")
                elif not uid.startswith(wid + "."):
                    problems.append(f"{where}: 文本单位 {uid} 不属于版本 {wid}")

    # 对读表与逐行释文
    align_problems, chapters = check_alignment(root, witnesses)
    problems += align_problems

    for pr in problems:
        print("✗", pr, file=sys.stderr)
    print(f"检查了 {len(sources)} 个来源、{total} 条文本单位、{plates} 张影像、{chapters} 章对读表："
          f"{'发现 %d 个问题' % len(problems) if problems else '全部通过'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
