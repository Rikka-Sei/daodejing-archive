/**
 * 逐章对读表与逐行释文（tt24h/daodejing 整理，放在 data/alignment/）。
 *
 * 对读表按王弼本分章，同一章里各本同列对齐；逐行释文是各底本照简、照行的原文，每个字指向对读表里的一格。
 * 本文件的函数除 loadAlignment 外都是纯函数，不读写文件。
 */
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { esc } from './html';

/** 格上的标记：残（只存部分字迹）、衍（衍文）、脱（脱文，没有字）、补（整理者补的字）、占（占位） */
export type Flag = '残' | '衍' | '脱' | '补' | '占';

/** 对读表的一格。t 正文；r 通行字；c 正确字（讹字的纠正）；n 尾注框；l 简号或行号；p 断句标点（只有校订本有）。 */
export interface Cell {
  t: string;
  f?: Flag;
  r?: string;
  c?: string;
  n?: string;
  l?: string;
  p?: string;
}

/** 一个版本在一章里的一行。郭店六十四章分成几段，各段是带 part 的几行。 */
export interface Row {
  version: string;
  part?: string;
  cells: Cell[];
}

export interface Chapter {
  n: number;
  columns: number;
  rows: Row[];
  notes: string[];
}

/** 一简或一行：text 里 〚…〛 是造字或残字记号；refs 逐字指向对读表，[章, [列…], 分段?]。 */
export interface Line {
  no: string;
  text: string;
  refs: ([number, number[]] | [number, number[], string])[];
}

export interface Version {
  id: string;
  label: string;
  /** 行首的简称，如“王弼” */
  short: string;
  transcript?: string;
  base?: string;
  reference?: string;
  differences?: string;
  unit?: string;
}

export interface Equivalents {
  /** 含这些字的列不判定共用通行字 */
  fail: string[];
  /** 视作空 */
  blank: string[];
  /** 每组里的字视同相等，首字是代表 */
  same: string[][];
}

export interface Study {
  overview: string[];
  legend: { title: string; paragraphs: string[] }[];
  references: string[];
}

/** 对读表里的符号：句读符、分章圆点、缺字、句序标记。它们不是文字，不参与比较。 */
export const MARK_CHARS = new Set(Array.from('∟＝●■◍▁◯□〼▩▦🅰🅱🅲🅳🅴'));

export function cellOf(raw: string | Partial<Cell>): Cell {
  return typeof raw === 'string' ? { t: raw } : { t: '', ...raw };
}

/** 一行实录切成记号：一个字，或一个〚…〛（可嵌套）。 */
export function tokenize(s: string): string[] {
  const cs = Array.from(s);
  const out: string[] = [];
  for (let i = 0; i < cs.length; ) {
    if (cs[i] !== '〚') {
      out.push(cs[i++]);
      continue;
    }
    let depth = 0;
    let j = i;
    for (; j < cs.length; j++) {
      if (cs[j] === '〚') depth++;
      else if (cs[j] === '〛') depth--;
      if (depth === 0) break;
    }
    if (depth !== 0) throw new Error(`〚〛不成对：${s}`);
    out.push(cs.slice(i, j + 1).join(''));
    i = j + 1;
  }
  return out;
}

export interface Glyph {
  /** 页面上画出来的字 */
  text: string;
  /** 残字：只存部分字迹 */
  damaged: boolean;
}

/** 记号 → 显示用的字：〚F字〛是残字；〚⿰月□〛一类造字序列换成补充字体里的码位，查不到就原样写出。 */
export function glyphOf(token: string, glyphs: ReadonlyMap<string, number>): Glyph {
  const damaged = /^〚F([\s\S]+)〛$/u.exec(token);
  if (damaged) return { text: glyphOf(damaged[1], glyphs).text, damaged: true };
  const cp = token.startsWith('〚') ? glyphs.get(token) : undefined;
  return { text: cp ? String.fromCodePoint(cp) : token, damaged: false };
}

/** 一段文字里的记号都换成显示用的字（造字序列换成补充字体里的码位，残字去掉标记）。 */
export function showText(s: string, glyphs: ReadonlyMap<string, number>): string {
  return tokenize(s)
    .map((t) => glyphOf(t, glyphs).text)
    .join('');
}

/**
 * 一行实录的 HTML：每个字一个 <span>，data-k 是“章.列”，点选后据此到对读表里查别的本。
 * href 非空时，在每一章开头插入一个章次标记（数字由样式画出，复制文字时不会带上）。
 */
export function lineHtml(line: Line, glyphs: ReadonlyMap<string, number>, href?: (n: number) => string): string {
  const where: [number, number][] = [];
  const starts = new Set<number>();
  for (const [ch, cols] of line.refs) {
    starts.add(where.length);
    for (const col of cols) where.push([ch, col]);
  }
  return tokenize(line.text)
    .map((tok, i) => {
      const g = glyphOf(tok, glyphs);
      const cls = ['c'];
      if (g.damaged) cls.push('d-part');
      if (tok === '□' || tok === '〼') cls.push('d-missing');
      else if (MARK_CHARS.has(g.text)) cls.push('mk');
      const at = where[i] ? ` data-k="${where[i][0]}.${where[i][1]}"` : '';
      const head = href && starts.has(i) && where[i] ? `<a class="cm" href="${esc(href(where[i][0]))}" data-n="${where[i][0]}" aria-label="第 ${where[i][0]} 章"></a>` : '';
      return `${head}<span class="${cls.join(' ')}"${at}>${esc(g.text)}</span>`;
    })
    .join('');
}

// ── 比较：共用通行字与差异 ──────────────────────────────────

/** 比较用的字：有通行字用（通行字），有正确字用〈正确字〉，否则是正文。规则同 tt24h 的“用于比较字”。 */
export function compareKey(c: Cell): string {
  if (c.r) return `（${c.r}）`;
  if (c.c) return `〈${c.c}〉`;
  return c.t;
}

const unwrap = (k: string) => (/^[（〈]/.test(k) ? k.slice(1, -1) : k);
const headOf = (k: string, eq: Equivalents) => eq.same.find((g) => g.includes(k))?.[0] ?? k;
/** 视同相等时的代表字 */
export const foldKey = (c: Cell, eq: Equivalents) => headOf(unwrap(compareKey(c)), eq);

export interface Shared {
  /** 共用通行字 */
  reading: string;
  /** 这一列里与它写法不同、但视同相等的字 */
  also: string[];
}

/**
 * 一列的共用通行字（规则同 tt24h 的 共用通行字.typ）：
 * 列里有句读符就不判定；去掉空与缺字后不足两个字也没有；各字（含通行字、正确字）按等同表折成同一个字，才有共用通行字。
 */
export function sharedReading(keys: string[], eq: Equivalents): Shared | null {
  if (keys.some((k) => eq.fail.includes(k))) return null;
  const solid = keys.map((k) => (eq.blank.includes(k) ? '' : k)).filter((k) => k !== '');
  if (solid.length <= 1) return null;
  const distinct = [...new Set(solid)];
  const plain = distinct.filter((k) => !/^[（〈]/.test(k));
  if (plain.length === 0) return null;
  if (new Set(distinct.map((k) => headOf(unwrap(k), eq))).size !== 1) return null;
  const group = eq.same.filter((g) => g.includes(plain[0])).flat();
  const reading = group.length === 0 ? plain[0] : [...plain].sort((a, b) => group.indexOf(a) - group.indexOf(b))[0];
  return { reading, also: [...new Set(distinct.map(unwrap))].filter((k) => k !== reading) };
}

export type ColumnKind = 'shared' | 'diff' | 'none';

/** 一列的情形：有共用通行字、用字有实质差异，或没有可比较的（只有一个字、句读符、全缺）。 */
export function columnKind(keys: string[], eq: Equivalents): { kind: ColumnKind; shared: Shared | null } {
  const shared = sharedReading(keys, eq);
  if (shared) return { kind: 'shared', shared };
  if (keys.some((k) => eq.fail.includes(k))) return { kind: 'none', shared };
  const solid = keys.filter((k) => k !== '' && !eq.blank.includes(k));
  return { kind: solid.length > 1 ? 'diff' : 'none', shared };
}

export type CellKind = 'blank' | 'tuo' | 'zhan' | 'miss' | 'mark' | 'text';

/** 一格怎么画：空格、脱文、占位、缺字、符号，或文字。 */
export function cellKind(c: Cell): CellKind {
  if (c.f === '脱') return 'tuo';
  if (c.f === '占') return 'zhan';
  if (!c.t) return 'blank';
  if (c.t === '□' || c.t === '〼') return 'miss';
  return MARK_CHARS.has(c.t) ? 'mark' : 'text';
}

export type Diff = '' | 'var' | 'diff';

/** 与校订本同一列比：用字相同为空；写法不同但视同相等（异体、通假、通行字相同）为 var；否则 diff。 */
export function diffOf(c: Cell, base: Cell, eq: Equivalents): Diff {
  if (cellKind(c) !== 'text' || c.t === base.t) return '';
  if (cellKind(base) !== 'text') return 'diff';
  return foldKey(c, eq) === foldKey(base, eq) ? 'var' : 'diff';
}

// ── 一章的版面 ──────────────────────────────────────────────

/** 同一版本的几行（郭店六十四章）并成一行；各行占的列不相交，所以直接叠起来。 */
export function mergeParts(rows: Row[]): Row[] {
  const out: Row[] = [];
  for (const r of rows) {
    const same = out.find((x) => x.version === r.version);
    if (!same) {
      out.push({ version: r.version, cells: r.cells.slice() });
      continue;
    }
    r.cells.forEach((c, i) => {
      if (cellKind(same.cells[i]) === 'blank' && cellKind(c) !== 'blank') same.cells[i] = c;
    });
  }
  return out;
}

/** 把一章的列分段，每段不超过 max 列：尽量断在句末，其次句中，断点后若紧跟一个校订本空着的列（帛书的句读记号）一并带上。 */
export function bands(base: Cell[], max = 20, min = 8): [number, number][] {
  const out: [number, number][] = [];
  let start = 0;
  while (start < base.length) {
    if (base.length - start <= max) {
      out.push([start, base.length]);
      break;
    }
    let strong = -1;
    let weak = -1;
    for (let i = start + min - 1; i < start + max; i++) {
      const p = base[i].p ?? '';
      if (/[。？；]/.test(p)) strong = i + 1;
      else if (p) weak = i + 1;
    }
    let cut = strong > 0 ? strong : weak > 0 ? weak : start + max;
    while (cut < base.length && cut < start + max && base[cut].t === '' && !base[cut].p && cut > start + min) cut++;
    out.push([start, cut]);
    start = cut;
  }
  return out;
}

/** 一章的标题：校订本第一个分句，如“道可道也”。 */
export function chapterTitle(base: Cell[], limit = 8): string {
  let s = '';
  for (const c of base) {
    if (cellKind(c) === 'text') s += c.t;
    if (c.p || Array.from(s).length >= limit) break;
  }
  return s;
}

export interface Presence {
  /** 这一章有没有这个本的行 */
  has: boolean;
  /** 行里有没有存字（不全是缺字） */
  legible: boolean;
}

// ── 读取 data/alignment/ ────────────────────────────────────

export class Alignment {
  constructor(
    public versions: Version[],
    public chapters: Chapter[],
    public lines: Map<string, Line[]>,
    public equivalents: Equivalents,
    public glyphs: Map<string, number>,
    public study: Study,
    /** 各章 JSON 的原文，网站原样提供下载，也供阅读器按需读取 */
    public chapterFiles: string[],
  ) {}

  version(id: string): Version | undefined {
    return this.versions.find((v) => v.id === id);
  }

  chapter(n: number): Chapter {
    const ch = this.chapters[n - 1];
    if (!ch) throw new Error(`没有第 ${n} 章`);
    return ch;
  }

  /** 这个本有逐行释文 */
  hasLines(id: string): boolean {
    return (this.lines.get(id)?.length ?? 0) > 0 && this.version(id)?.unit !== 'chapter';
  }

  /** 第 n 章在某个本里占哪几简或哪几行（简号或行号），按底本顺序。 */
  linesOf(id: string, n: number): string[] {
    return (this.lines.get(id) ?? []).filter((l) => l.refs.some((r) => r[0] === n)).map((l) => l.no);
  }

  /** 第 n 章里某个本的存字情况。郭店三组合并看。 */
  presence(n: number, ids: string[]): Presence {
    const rows = this.chapter(n).rows.filter((r) => ids.includes(r.version));
    const legible = rows.some((r) => r.cells.some((c) => cellKind(c) === 'text'));
    return { has: rows.length > 0, legible };
  }
}

/** 阅读器要读的公共部分（<典籍>/alignment.json）：各行的简称、共用通行字的规则、造字码位。 */
export function readerMeta(al: Alignment) {
  return {
    versions: al.versions.map((v) => ({ id: v.id, short: v.short, unit: v.unit })),
    equivalents: al.equivalents,
    glyphs: Object.fromEntries(al.glyphs),
  };
}

const readJson = <T>(path: string): T => JSON.parse(readFileSync(path, 'utf-8')) as T;
const readLines = (path: string): Line[] =>
  readFileSync(path, 'utf-8')
    .split(/\r?\n/)
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l) as Line);

/** 读 <data>/alignment/；没有这个目录就返回 null（别的典籍不一定有对读表）。 */
export function loadAlignment(dataDir: string): Alignment | null {
  const dir = join(dataDir, 'alignment');
  if (!existsSync(join(dir, 'versions.json'))) return null;
  const chapterDir = join(dir, 'chapters');
  const files = readdirSync(chapterDir)
    .filter((f) => f.endsWith('.json'))
    .sort();
  const chapterFiles = files.map((f) => readFileSync(join(chapterDir, f), 'utf-8'));
  const chapters = chapterFiles.map((text) => {
    const raw = JSON.parse(text) as { chapter: number; columns: number; rows: { version: string; part?: string; cells: (string | Partial<Cell>)[] }[]; notes: string[] };
    return {
      n: raw.chapter,
      columns: raw.columns,
      rows: raw.rows.map((r) => ({ version: r.version, ...(r.part ? { part: r.part } : {}), cells: r.cells.map(cellOf) })),
      notes: raw.notes,
    };
  });
  const lines = new Map<string, Line[]>();
  const lineDir = join(dir, 'lines');
  for (const f of readdirSync(lineDir).sort()) if (f.endsWith('.jsonl')) lines.set(f.slice(0, -'.jsonl'.length), readLines(join(lineDir, f)));
  const glyphs = new Map(Object.entries(readJson<Record<string, string>>(join(dir, 'glyphs.json'))).map(([k, hex]) => [k, parseInt(hex, 16)]));
  return new Alignment(
    readJson<Version[]>(join(dir, 'versions.json')),
    chapters,
    lines,
    readJson<Equivalents>(join(dir, 'equivalents.json')),
    glyphs,
    readJson<Study>(join(dir, 'study.json')),
    chapterFiles,
  );
}
