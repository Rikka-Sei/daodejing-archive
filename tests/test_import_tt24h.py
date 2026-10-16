"""scripts/import_tt24h.py 与 alignment.slip_order 的测试：简背排到同一枚简的正面之后，仓库里的 beida.jsonl 能原样重新生成。"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import alignment as al  # noqa: E402
import import_tt24h  # noqa: E402


def u(no: str) -> dict:
    return {"unit_no": no}


class SlipOrder(unittest.TestCase):
    def test_back_follows_front(self):
        got = al.slip_order([u("2背"), u("1"), u("2正"), u("3")], "unit_no")
        self.assertEqual([x["unit_no"] for x in got], ["1", "2正", "2背", "3"])

    def test_orphan_back_fails(self):
        with self.assertRaises(ValueError):
            al.slip_order([u("5背"), u("1")], "unit_no")

    def test_repo_file_matches(self):
        units = import_tt24h.beida()
        on_disk = [json.loads(line) for line in (REPO / "data/witnesses/beida.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(units, on_disk)
        self.assertEqual([x["unit_no"] for x in units[:4]], ["1", "2正", "2背", "3"])


if __name__ == "__main__":
    unittest.main()
