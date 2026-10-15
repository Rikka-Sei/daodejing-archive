"""validate_data.py 的测试。所用文本是明显的占位字符，不是任何真实版本的释文。"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "validate_data.py"


class ValidateData(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "schema", self.tmp / "schema")
        (self.tmp / "data" / "sources").mkdir(parents=True)
        (self.tmp / "data" / "witnesses").mkdir()
        (self.tmp / "data" / "raw" / "fake").mkdir(parents=True)
        shutil.copy(REPO / "data" / "witnesses.yaml", self.tmp / "data" / "witnesses.yaml")

        raw = self.tmp / "data" / "raw" / "fake" / "page.txt"
        raw.write_text("占位原始文件", encoding="utf-8")
        self.sha = hashlib.sha256(raw.read_bytes()).hexdigest()
        self.write_source()
        self.write_units([self.unit(1, "甲乙丙丁")])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_source(self, **over):
        doc = {
            "id": "fake", "kind": "website", "title": "占位来源", "witnesses": ["guodian-jia"],
            "license": {"status": "public-domain"},
            "retrieval": {"status": "fetched", "date": "2026-10-14",
                          "files": [{"path": "data/raw/fake/page.txt", "sha256": self.sha}]},
        }
        doc.update(over)
        (self.tmp / "data" / "sources" / "fake.yaml").write_text(
            yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

    def unit(self, n, text, **over):
        u = {"id": f"guodian-jia.{n:03d}", "witness": "guodian-jia", "unit_type": "slip",
             "unit_no": str(n), "text": text, "status": "unverified",
             "source_ref": {"source": "fake", "raw_file": "data/raw/fake/page.txt"}}
        u.update(over)
        return u

    def write_units(self, units):
        (self.tmp / "data" / "witnesses" / "guodian-jia.jsonl").write_text(
            "\n".join(json.dumps(u, ensure_ascii=False) for u in units) + "\n", encoding="utf-8")

    def run_validator(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.tmp)],
                           capture_output=True, text=True)
        self.out = r.stdout
        return r.returncode, r.stderr

    def test_valid_data_passes(self):
        code, err = self.run_validator()
        self.assertEqual(code, 0, err)

    def test_gap_in_numbering_fails(self):
        self.write_units([self.unit(1, "甲乙"), self.unit(3, "丙丁")])
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("编号必须连续", err)

    def test_damage_out_of_range_fails(self):
        self.write_units([self.unit(1, "甲乙", damage=[{"kind": "missing", "start": 1, "end": 5}])])
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("超出 text 长度", err)

    def test_modified_raw_file_fails(self):
        (self.tmp / "data" / "raw" / "fake" / "page.txt").write_text("被改动", encoding="utf-8")
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("哈希不符", err)

    def test_unknown_license_blocks_fetched_source(self):
        self.write_source(license={"status": "unknown"})
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("授权状态仍是 unknown", err)

    def test_missing_raw_file_reference_fails(self):
        u = self.unit(1, "甲乙")
        del u["source_ref"]["raw_file"]
        self.write_units([u])
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("缺少 raw_file", err)

    def test_chapter_unit_type_passes(self):
        self.write_units([self.unit(1, "甲乙", unit_type="chapter", unit_no="38")])
        code, err = self.run_validator()
        self.assertEqual(code, 0, err)

    def write_plate(self, **over):
        rec = {"file": "data/raw/fake/page.txt", "witness": "guodian-jia", "source": "fake",
               "kind": "slip-plate", "locator": "第 1 页", "units": ["guodian-jia.001"]}
        rec.update(over)
        (self.tmp / "data" / "plates").mkdir(exist_ok=True)
        (self.tmp / "data" / "plates" / "guodian-jia.jsonl").write_text(
            json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_valid_plate_passes(self):
        self.write_plate(file="data/images/fake/1.jpg")
        img = self.tmp / "data" / "images" / "fake" / "1.jpg"
        img.parent.mkdir(parents=True)
        img.write_bytes(b"\xff\xd8placeholder")
        self.write_source(retrieval={"status": "fetched", "date": "2026-10-14", "files": [
            {"path": "data/raw/fake/page.txt", "sha256": self.sha},
            {"path": "data/images/fake/1.jpg", "sha256": hashlib.sha256(img.read_bytes()).hexdigest()}]})
        code, err = self.run_validator()
        self.assertEqual(code, 0, err)

    def test_plate_with_unknown_unit_fails(self):
        self.write_plate(file="data/images/fake/1.jpg", units=["guodian-jia.099"])
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("guodian-jia.099 不存在", err)

    def test_plate_file_without_hash_fails(self):
        self.write_plate(file="data/images/fake/unregistered.jpg")
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("没有在来源 fake 中登记哈希", err)

    def test_unknown_unit_type_fails(self):
        self.write_units([self.unit(1, "甲乙", unit_type="page")])
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("unit_type", err)

    # ── 对读表与逐行释文（data/alignment/） ──

    def write_alignment(self):
        """占位的对读表：81 章，每章两列、两个版本（王弼本、郭店甲），郭店甲有逐行释文，两者一致。"""
        base = self.tmp / "data" / "alignment"
        (base / "chapters").mkdir(parents=True)
        (base / "lines").mkdir()
        versions = [{"id": "wangbi", "label": "弼本", "short": "王弼"},
                    {"id": "guodian-jia", "label": "郭甲", "short": "郭甲", "unit": "slip"}]
        for name, doc in [("versions.json", versions), ("equivalents.json", {"fail": [], "blank": [], "same": []}),
                          ("glyphs.json", {}), ("study.json", {"overview": [], "legend": [], "references": []})]:
            (base / name).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        for n in range(1, 82):
            rows = [{"version": "wangbi", "cells": ["甲", "乙"]},
                    {"version": "guodian-jia", "cells": ["甲", {"t": "乙", "l": str(n)}]}]
            (base / "chapters" / f"{n:03d}.json").write_text(
                json.dumps({"chapter": n, "columns": 2, "rows": rows, "notes": []}, ensure_ascii=False), encoding="utf-8")
        lines = [{"no": str(n), "text": "甲乙", "refs": [[n, [0, 1]]]} for n in range(1, 82)]
        (base / "lines" / "guodian-jia.jsonl").write_text(
            "\n".join(json.dumps(l, ensure_ascii=False) for l in lines) + "\n", encoding="utf-8")
        return base

    def edit_json(self, path, change):
        doc = json.loads(path.read_text(encoding="utf-8"))
        change(doc)
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def test_alignment_passes_and_is_counted(self):
        self.write_alignment()
        code, err = self.run_validator()
        self.assertEqual(code, 0, err)
        self.assertIn("81 章对读表", self.out)

    def test_alignment_is_optional(self):
        code, err = self.run_validator()
        self.assertEqual(code, 0, err)
        self.assertIn("0 章对读表", self.out)

    def test_alignment_version_must_be_registered(self):
        base = self.write_alignment()
        self.edit_json(base / "versions.json", lambda v: v.append({"id": "nope", "label": "无", "short": "无"}))
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("nope 不是已登记的版本 id", err)

    def test_alignment_rows_must_use_listed_versions(self):
        base = self.write_alignment()
        self.edit_json(base / "versions.json", lambda v: v.pop())
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("guodian-jia", err)
        self.assertIn("不是已知的版本", err)

    def test_alignment_file_name_must_match_the_chapter(self):
        base = self.write_alignment()
        self.edit_json(base / "chapters" / "005.json", lambda c: c.update(chapter=6))
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("005.json: 文件名应是章号的三位数字", err)

    def test_alignment_needs_all_81_chapters(self):
        base = self.write_alignment()
        (base / "chapters" / "081.json").unlink()
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("缺第 81 章", err)

    def test_alignment_transcript_must_match_the_table(self):
        base = self.write_alignment()
        self.edit_json(base / "chapters" / "003.json", lambda c: c["rows"][1]["cells"].__setitem__(0, "丙"))
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("对到第 3 章第 0 列", err)

    def test_alignment_unreadable_file_fails(self):
        base = self.write_alignment()
        (base / "glyphs.json").write_text("{", encoding="utf-8")
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("glyphs.json: 读不了", err)

    def test_alignment_malformed_table_is_reported_not_crashed(self):
        base = self.write_alignment()
        (base / "chapters" / "001.json").write_text(json.dumps({"chapter": 1}), encoding="utf-8")
        code, err = self.run_validator()
        self.assertEqual(code, 1)
        self.assertIn("结构不对", err)
        self.assertNotIn("Traceback", err)


class RealData(unittest.TestCase):
    def test_repository_data_passes(self):
        r = subprocess.run([sys.executable, "-I", str(SCRIPT), "--root", str(REPO)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("81 章对读表：全部通过", r.stdout)


if __name__ == "__main__":
    unittest.main()
