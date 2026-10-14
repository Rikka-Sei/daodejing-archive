"""读取一部典籍。

一部典籍 = 一个目录，结构同本仓库 data/：witnesses.yaml、witnesses/*.jsonl、
plates/*.jsonl（可缺）、sources/*.yaml；可选 corpus.yaml 写 title、subtitle、intro、preface（凡例）、
preface_extra（追加的凡例）、license_note（授权说明）。

版本（witness）按名字归入“文献”（group）：“郭店楚简《老子》甲组”“……乙组”同属“郭店楚简”，目录里是一个文件夹，
各有几个本就列几个；只有一个本的文献直接是一项。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .textutil import common_id, split_name

ROOT = Path(__file__).resolve().parent.parent.parent
PLATE_PREFERENCE = ("photo", "page", "slip-plate")      # 封面取图：先实物照片，再整页图版，最后单简图版


@dataclass
class Witness:
    meta: dict
    units: list
    plates: list
    by_unit: dict = field(default_factory=dict)
    group: str = ""       # 所属文献，如“郭店楚简”
    label: str = ""       # 本名，如“甲组”；文献只有一个本时为“全本”
    file: Path | None = None   # 释文 jsonl 的路径，下载时原样复制

    @property
    def id(self):
        return self.meta["id"]

    @property
    def title(self) -> str:
        """目录与翻页里用的名字：“郭店楚简 甲组”；只有一个本时就是文献名。"""
        return self.group if self.label == "全本" else f"{self.group} {self.label}"


@dataclass
class Group:
    """一部文献：目录里的一个文件夹（多个本）或一项（单个本）。"""
    name: str
    witnesses: list
    id: str

    @property
    def single(self) -> bool:
        return len(self.witnesses) == 1

    @property
    def first(self) -> Witness:
        return self.witnesses[0]

    @property
    def plates(self) -> int:
        return sum(len(w.plates) for w in self.witnesses)

    def cover_plate(self):
        """封面用的影像：按 PLATE_PREFERENCE 取第一张；没有影像时为 None。"""
        for kind in PLATE_PREFERENCE:
            for w in self.witnesses:
                for p in w.plates:
                    if p["kind"] == kind:
                        return p
        return None


@dataclass
class Corpus:
    id: str
    title: str
    subtitle: str
    intro: str
    witnesses: list
    sources: list
    preface: list = field(default_factory=list)        # 凡例（体例部分），空则用通用的
    preface_extra: list = field(default_factory=list)  # 追加在通用凡例之后
    license_note: str = ""                             # 授权说明，显示在各本的“来源与授权”里
    totals: tuple = (0, 0)

    @property
    def groups(self) -> list:
        """按版本登记顺序归并同名文献。"""
        out = {}
        for w in self.witnesses:
            out.setdefault(w.group, []).append(w)
        return [Group(name, ws, common_id([w.id for w in ws])) for name, ws in out.items()]

    def sources_of(self, wit: Witness) -> list:
        return [s for s in self.sources if wit.id in (s.get("witnesses") or [])]


def _jsonl(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_corpus(cid: str, path: str, overrides: dict | None = None) -> Corpus:
    """overrides 优先于目录里的 corpus.yaml，键同 corpus.yaml。"""
    base = (ROOT / path).resolve()
    meta = _yaml(base / "corpus.yaml") if (base / "corpus.yaml").exists() else {}
    meta = {**meta, **(overrides or {})}
    reg = _yaml(base / "witnesses.yaml")
    witnesses = []
    for w in reg["witnesses"]:
        plate_file = base / "plates" / f"{w['id']}.jsonl"
        plates = _jsonl(plate_file) if plate_file.exists() else []
        by_unit = {}
        for p in plates:
            for uid in p["units"]:
                by_unit.setdefault(uid, []).append(p)
        group, label = split_name(w["name"])
        unit_file = base / "witnesses" / f"{w['id']}.jsonl"
        witnesses.append(Witness(w, _jsonl(unit_file), plates, by_unit, group=group, label=label, file=unit_file))
    c = Corpus(
        id=cid,
        title=meta.get("title") or cid,
        subtitle=meta.get("subtitle") or "",
        intro=meta.get("intro") or "释文照录来源，未经复核。",
        preface=list(meta.get("preface") or []),
        preface_extra=list(meta.get("preface_extra") or []),
        license_note=meta.get("license_note") or "各来源自身的声明见仓库中的来源记录。",
        witnesses=witnesses,
        sources=[_yaml(p) for p in sorted((base / "sources").glob("*.yaml"))],
    )
    c.totals = (sum(len(w.units) for w in witnesses), sum(len(w.plates) for w in witnesses))
    return c
