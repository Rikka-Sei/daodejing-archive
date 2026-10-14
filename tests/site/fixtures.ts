/** 测试用的占位典籍：只用占位字符，不含真实释文。结构同本仓库 data/。 */
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadCorpus, type Corpus } from '../../src/lib/corpus';

export function makeCorpusFiles(root: string, withPlates = true): void {
  for (const d of ['witnesses', 'plates', 'sources']) mkdirSync(join(root, d), { recursive: true });
  writeFileSync(
    join(root, 'witnesses.yaml'),
    [
      'witnesses:',
      '  - {id: w-a, name: 甲书《占位》甲组, excavated: {year: 2000, place: 某地}}',
      '  - {id: w-b, name: 甲书《占位》乙组}',
      '  - {id: w-c, name: 乙书}',
      '',
    ].join('\n'),
  );
  const kinds: [string, string][] = [
    ['w-a', 'slip'],
    ['w-b', 'slip'],
    ['w-c', 'chapter'],
  ];
  for (const [wid, kind] of kinds) {
    const rows = [1, 2].map((i) => ({
      id: `${wid}.00${i}`,
      witness: wid,
      unit_type: kind,
      unit_no: String(i),
      text: '甲乙丙',
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
}

/** 临时目录，用完调用 cleanup。 */
export function tempDir(): { dir: string; cleanup: () => void } {
  const dir = mkdtempSync(join(tmpdir(), 'dg-test-'));
  return { dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

/** 在 root 下建一部占位典籍并读入。 */
export function fixtureCorpus(root: string, id: string, overrides: Record<string, unknown> = {}, withPlates = true): Corpus {
  const dir = join(root, id);
  makeCorpusFiles(dir, withPlates);
  return loadCorpus(id, dir, overrides);
}
