/** 测试用的占位典籍：只用占位字符，不含真实释文。结构同本仓库 data/。 */
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadCorpus, type Corpus } from '../../src/lib/corpus';

/**
 * 占位的对读表：两章，四个版本（校订本 jiaoding、传世本 w-t、竹简 w-a 和 w-b；只有 w-a 有逐行释文）。
 * 第 1 章 6 列：第 0、3、5 列各本相同；第 1 列 w-a 写作“丑”、通行字是“乙”（异体）；第 2、4 列用字不同；
 * 第 2 章 4 列，w-b 没有这一章。等同表里甲＝子、乙＝丑。
 */
const ALIGNMENT: Record<string, unknown> = {
  'versions.json': [
    { id: 'jiaoding', label: '校订', short: '校订', unit: 'chapter' },
    { id: 'w-t', label: '传世', short: '传世', transcript: 't.txt', unit: 'chapter' },
    { id: 'w-a', label: '甲', short: '甲组', transcript: 't.txt', unit: 'slip' },
    { id: 'w-b', label: '乙', short: '乙组', unit: 'slip' },
  ],
  'equivalents.json': { fail: ['∟', '＝'], blank: ['□', '〼'], same: [['甲', '子'], ['乙', '丑']] },
  'glyphs.json': { '〚⿰甲乙〛': 'E000' },
  'study.json': {
    overview: ['占位概述一。', '占位概述二。'],
    legend: [{ title: '占位凡例', paragraphs: ['占位凡例段。'] }],
    references: ['占位书目一.', '占位书目二.'],
  },
  'chapters/001.json': {
    chapter: 1,
    columns: 6,
    rows: [
      { version: 'jiaoding', cells: ['甲', '乙', { t: '丙', p: '，' }, '丁', '戊', { t: '己', p: '。' }] },
      { version: 'w-t', cells: ['甲', '乙', '丙', '丁', '庚', '己'] },
      { version: 'w-a', cells: ['甲', { t: '丑', r: '乙' }, { t: '丙', l: '1' }, '', '□', '己'] },
      { version: 'w-b', cells: ['甲', '乙', { t: '子', f: '残' }, '丁', { f: '脱' }, '己'] },
    ],
    notes: ['占位尾注'],
  },
  'chapters/002.json': {
    chapter: 2,
    columns: 4,
    rows: [
      { version: 'jiaoding', cells: ['乙', '丙', '丁', { t: '戊', p: '。' }] },
      { version: 'w-t', cells: ['乙', '丙', '丁', '戊'] },
      { version: 'w-a', cells: ['乙', { t: '丙', l: '2' }, { t: '丁', f: '残' }, { t: '〚⿰甲乙〛', l: '3' }] },
    ],
    notes: [],
  },
};
/** 逐行释文：w-a 第 2 简跨两章，第 3 简有残字和造字 */
const LINES: Record<string, unknown[]> = {
  'w-a': [
    { no: '1', text: '甲丑丙', refs: [[1, [0, 1, 2]]] },
    { no: '2', text: '□己乙丙', refs: [[1, [4, 5]], [2, [0, 1]]] },
    { no: '3', text: '〚F丁〛〚⿰甲乙〛', refs: [[2, [2, 3]]] },
  ],
};

const json = (x: unknown) => JSON.stringify(x);

export function makeCorpusFiles(root: string, withPlates = true, withAlignment = false): void {
  for (const d of ['witnesses', 'plates', 'sources']) mkdirSync(join(root, d), { recursive: true });
  writeFileSync(
    join(root, 'witnesses.yaml'),
    [
      'witnesses:',
      '  - {id: w-a, name: 甲书《占位》甲组, excavated: {year: 2000, place: 某地}}',
      '  - {id: w-b, name: 甲书《占位》乙组}',
      '  - {id: w-c, name: 乙书}',
      ...(withAlignment
        ? ['  - {id: w-t, name: 传世本《占位》, kind: transmitted}', '  - {id: jiaoding, name: 校订本《占位》, kind: edition}']
        : []),
      '',
    ].join('\n'),
  );
  const kinds: [string, string][] = [
    ['w-a', 'slip'],
    ['w-b', 'slip'],
    ['w-c', 'chapter'],
    ...(withAlignment ? ([['w-t', 'chapter'], ['jiaoding', 'chapter']] as [string, string][]) : []),
  ];
  for (const [wid, kind] of kinds) {
    const rows = [1, 2].map((i) => ({
      id: `${wid}.00${i}`,
      witness: wid,
      unit_type: kind,
      unit_no: String(i),
      // 校订本的释文夹着对读表的句序记号（▩），章节页的开头一段要把它去掉
      text: wid === 'jiaoding' ? '甲乙，丙▩丁。' : '甲乙丙',
      source_ref: { source: 's' },
      status: 'unverified',
      damage: [{ kind: 'missing', start: 1, end: 2 }],
    }));
    writeFileSync(join(root, 'witnesses', `${wid}.jsonl`), rows.map((r) => JSON.stringify(r)).join('\n'));
  }
  const plates: Record<string, [string, string][]> = {
    'w-a': [
      ['slip-plate', 'a1.jpg'],
      ['page', 'a2.jpg'],
    ],
    'w-b': [['photo', 'b1.jpg']],
  };
  for (const [wid, rows] of withPlates ? Object.entries(plates) : []) {
    const lines = rows.map(([kind, file], i) =>
      JSON.stringify({ file: `data/images/${file}`, witness: wid, source: 's', kind, locator: `占位 第 ${i + 1} 页`, units: [`${wid}.001`] }),
    );
    writeFileSync(join(root, 'plates', `${wid}.jsonl`), lines.join('\n'));
  }
  writeFileSync(
    join(root, 'sources', 's.yaml'),
    [
      'id: s',
      'title: 占位来源',
      'url: https://example.test/s',
      'witnesses: [w-a]',
      'license: {status: cc, name: CC0, evidence: 占位依据}',
      'notes: 占位备注',
      "retrieval: {status: fetched, date: '2026-01-02', files: [{path: data/raw/s/x.html, sha256: 0123456789abcdef0123}]}",
      '',
    ].join('\n'),
  );
  writeFileSync(
    join(root, 'sources', 't.yaml'),
    [
      'id: t',
      'title: 另一来源',
      'witnesses: [w-a]',
      'license: {status: public-domain, name: null}',
      'retrieval: {status: pending}',
      '',
    ].join('\n'),
  );
  if (!withAlignment) return;
  // 一份对照资料（study: true），以及它给出的对读表
  writeFileSync(
    join(root, 'sources', 'u.yaml'),
    [
      'id: u',
      'title: 《占位对照表》',
      'short: 对照表',
      'publisher: 占位出版者',
      'year: 2026',
      'study: true',
      'witnesses: [w-a, w-b, jiaoding]',
      'license: {status: cc, name: CC0}',
      'retrieval: {status: pending}',
      '',
    ].join('\n'),
  );
  for (const d of ['alignment/chapters', 'alignment/lines']) mkdirSync(join(root, d), { recursive: true });
  for (const [name, doc] of Object.entries(ALIGNMENT)) writeFileSync(join(root, 'alignment', name), json(doc));
  for (const [wid, lines] of Object.entries(LINES)) {
    writeFileSync(join(root, 'alignment/lines', `${wid}.jsonl`), lines.map(json).join('\n'));
  }
}

/** 临时目录，用完调用 cleanup。 */
export function tempDir(): { dir: string; cleanup: () => void } {
  const dir = mkdtempSync(join(tmpdir(), 'dg-test-'));
  return { dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

/** 在 root 下建一部占位典籍并读入。withAlignment：再加上传世本、校订本、一份对照资料和占位的对读表。 */
export function fixtureCorpus(
  root: string,
  id: string,
  overrides: Record<string, unknown> = {},
  withPlates = true,
  withAlignment = false,
): Corpus {
  const dir = join(root, id);
  makeCorpusFiles(dir, withPlates, withAlignment);
  return loadCorpus(id, dir, overrides);
}
