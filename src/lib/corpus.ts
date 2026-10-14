/**
 * 读取一部典籍。
 *
 * 一部典籍 = 一个目录，结构同本仓库 data/：witnesses.yaml、witnesses/*.jsonl、plates/*.jsonl（可缺）、
 * sources/*.yaml；可选 corpus.yaml 写 title、subtitle、intro、preface（凡例）、preface_extra（追加的凡例）、
 * license_note（授权说明）。
 *
 * 版本（witness）按名字归入“文献”（group）：“郭店楚简《老子》甲组”“……乙组”同属“郭店楚简”，
 * 目录里是一个文件夹，各有几个本就列几个；只有一个本的文献直接是一项。
 */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parse } from 'yaml';
import { commonId, splitName } from './text';
import type { Meta, Plate, Unit } from './types';

/** 仓库根目录：npm 脚本与测试都从这里运行。 */
export const ROOT = process.cwd();
/** 封面取图：先实物照片，再整页图版，最后单简图版。 */
export const PLATE_PREFERENCE = ['photo', 'page', 'slip-plate'];

export class Witness {
  constructor(
    public meta: Meta,
    public units: Unit[],
    public plates: Plate[],
    /** 文本单位 id → 对应的影像 */
    public byUnit: Map<string, Plate[]>,
    /** 所属文献，如“郭店楚简” */
    public group: string,
    /** 本名，如“甲组”；文献只有一个本时为“全本” */
    public label: string,
    /** 释文 jsonl 的路径，下载时原样复制 */
    public file: string | null,
  ) {}

  get id(): string {
    return this.meta.id;
  }

  /** 目录与翻页里用的名字：“郭店楚简 甲组”；只有一个本时就是文献名。 */
  get title(): string {
    return this.label === '全本' ? this.group : `${this.group} ${this.label}`;
  }
}

/** 一部文献：目录里的一个文件夹（多个本）或一项（单个本）。 */
export class Group {
  constructor(
    public name: string,
    public witnesses: Witness[],
    public id: string,
  ) {}

  get single(): boolean {
    return this.witnesses.length === 1;
  }

  get first(): Witness {
    return this.witnesses[0];
  }

  /** 影像张数 */
  get plates(): number {
    return this.witnesses.reduce((n, w) => n + w.plates.length, 0);
  }

  /** 封面用的影像：按 PLATE_PREFERENCE 取第一张；没有影像时为 null。 */
  coverPlate(): Plate | null {
    for (const kind of PLATE_PREFERENCE) {
      for (const w of this.witnesses) {
        for (const p of w.plates) if (p.kind === kind) return p;
      }
    }
    return null;
  }
}

export class Corpus {
  /** 按版本登记顺序归并同名文献 */
  readonly groups: Group[];
  /** [释文条数, 影像张数] */
  readonly totals: [number, number];

  constructor(
    public id: string,
    public title: string,
    public subtitle: string,
    public intro: string,
    public witnesses: Witness[],
    public sources: Meta[],
    /** 凡例（体例部分），空则用通用的 */
    public preface: string[] = [],
    /** 追加在凡例体例部分之后 */
    public prefaceExtra: string[] = [],
    /** 授权说明，显示在各本的“来源与授权”里 */
    public licenseNote: string = '',
  ) {
    const byGroup = new Map<string, Witness[]>();
    for (const w of witnesses) {
      const list = byGroup.get(w.group);
      if (list) list.push(w);
      else byGroup.set(w.group, [w]);
    }
    this.groups = [...byGroup].map(([name, ws]) => new Group(name, ws, commonId(ws.map((w) => w.id))));
    this.totals = [
      witnesses.reduce((n, w) => n + w.units.length, 0),
      witnesses.reduce((n, w) => n + w.plates.length, 0),
    ];
  }

  sourcesOf(wit: Witness): Meta[] {
    return this.sources.filter((s) => (s.witnesses ?? []).includes(wit.id));
  }

  witness(id: string): Witness | undefined {
    return this.witnesses.find((w) => w.id === id);
  }
}

function jsonl<T>(path: string): T[] {
  return readFileSync(path, 'utf-8')
    .split(/\r?\n/)
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as T);
}

function yamlFile(path: string): Meta {
  return parse(readFileSync(path, 'utf-8')) ?? {};
}

/** 读取一部典籍。path 相对仓库根目录或为绝对路径；overrides 优先于目录里的 corpus.yaml，键同 corpus.yaml。 */
export function loadCorpus(id: string, path: string, overrides: Meta = {}): Corpus {
  const base = resolve(ROOT, path);
  const corpusYaml = join(base, 'corpus.yaml');
  const meta: Meta = { ...(existsSync(corpusYaml) ? yamlFile(corpusYaml) : {}), ...overrides };
  const reg = yamlFile(join(base, 'witnesses.yaml'));
  const witnesses: Witness[] = [];
  for (const w of reg.witnesses as Meta[]) {
    const plateFile = join(base, 'plates', `${w.id}.jsonl`);
    const plates = existsSync(plateFile) ? jsonl<Plate>(plateFile) : [];
    const byUnit = new Map<string, Plate[]>();
    for (const p of plates) {
      for (const uid of p.units) {
        const list = byUnit.get(uid);
        if (list) list.push(p);
        else byUnit.set(uid, [p]);
      }
    }
    const [group, label] = splitName(w.name);
    const unitFile = join(base, 'witnesses', `${w.id}.jsonl`);
    witnesses.push(new Witness(w, jsonl<Unit>(unitFile), plates, byUnit, group, label, unitFile));
  }
  const sourceDir = join(base, 'sources');
  const sources = existsSync(sourceDir)
    ? readdirSync(sourceDir)
        .filter((f) => f.endsWith('.yaml'))
        .sort()
        .map((f) => yamlFile(join(sourceDir, f)))
    : [];
  return new Corpus(
    id,
    meta.title || id,
    meta.subtitle || '',
    meta.intro || '释文照录来源，未经复核。',
    witnesses,
    sources,
    [...(meta.preface ?? [])],
    [...(meta.preface_extra ?? [])],
    meta.license_note || '各来源自身的声明见仓库中的来源记录。',
  );
}
