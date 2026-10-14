#!/usr/bin/env python3
"""校验 data/ 下的全部数据：结构、编号、残缺区间、来源追溯与原始文件哈希。

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

    for pr in problems:
        print("✗", pr, file=sys.stderr)
    print(f"检查了 {len(sources)} 个来源、{total} 条文本单位：{'发现 %d 个问题' % len(problems) if problems else '全部通过'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
