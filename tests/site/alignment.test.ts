/**
 * 对读表（src/lib/alignment.ts）：记号切分、显示用的字、共用通行字与差异、版面分段、读取。
 * 单元测试只用占位字符，不含真实释文；最后一组读 data/alignment/，只核对结构与互相的一致，不测字句。
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import {
  Alignment,
  type Cell,
  type Equivalents,
  MARK_CHARS,
  bands,
  cellKind,
  cellOf,
  chapterTitle,
  columnKind,
  compareKey,
  diffOf,
  foldKey,
  glyphOf,
  lineHtml,
  loadAlignment,
  mergeParts,
  sharedReading,
  showText,
  tokenize,
} from '../../src/lib/alignment';
import { fixtureCorpus, tempDir } from './fixtures';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

/** 甲乙丙丁、戊己、庚辛壬癸各是一组视同相等的字；子、丑不在任何一组里 */
const eq: Equivalents = {
  fail: ['∟', '＝'],
  blank: ['□', '〼'],
  same: [['甲', '乙', '丙', '丁'], ['戊', '己'], ['庚', '辛', '壬', '癸']],
};
const t = (s: string): Cell => ({ t: s });
const PUA = String.fromCodePoint(0xe003);

describe('切记号', () => {
  it('一个字一个记号，〚…〛（可嵌套）算一个，码位超过 U+FFFF 的字也是一个', () => {
    expect(tokenize('甲〚F乙〛〚⿰丙〚⿱丁戊〛〛𠀀')).toEqual(['甲', '〚F乙〛', '〚⿰丙〚⿱丁戊〛〛', '𠀀']);
  });
  it('〚〛不成对就报错', () => {
    expect(() => tokenize('甲〚⿰乙')).toThrow('不成对');
  });
});

describe('显示用的字', () => {
  const glyphs = new Map([['〚⿰甲□〛', 0xe003]]);
  it('残字、造字、普通字', () => {
    expect(glyphOf('〚F乙〛', glyphs)).toEqual({ text: '乙', damaged: true });
    expect(glyphOf('〚⿰甲□〛', glyphs)).toEqual({ text: PUA, damaged: false });
    expect(glyphOf('〚⿰甲乙〛', glyphs)).toEqual({ text: '〚⿰甲乙〛', damaged: false }); // 补充字体里查不到：原样写出
    expect(glyphOf('〚F〚⿰甲□〛〛', glyphs)).toEqual({ text: PUA, damaged: true });
    expect(glyphOf('甲', glyphs)).toEqual({ text: '甲', damaged: false });
  });
  it('一段文字里的记号都换成显示用的字', () => {
    expect(showText('〚F甲〛乙〚⿰甲□〛', glyphs)).toBe(`甲乙${PUA}`);
  });
  it('一行的 HTML：每个字带“章.列”，缺字与符号有各自的样式，文字被转义', () => {
    const html = lineHtml({ no: '1', text: '甲□∟〚F乙〛<', refs: [[1, [5, 6, 7, 8, 9]]] }, glyphs);
    expect(html).toBe(
      '<span class="c" data-k="1.5">甲</span><span class="c d-missing" data-k="1.6">□</span>' +
        '<span class="c mk" data-k="1.7">∟</span><span class="c d-part" data-k="1.8">乙</span>' +
        '<span class="c" data-k="1.9">&lt;</span>',
    );
  });
  it('给了章次地址就在每一章开头插一个章次标记；没有对应关系的字不带 data-k', () => {
    const html = lineHtml({ no: '2', text: '甲乙丙丁', refs: [[1, [3]], [2, [0, 1]]] }, new Map(), (n) => `/c/${n}/`);
    expect(html).toBe(
      '<a class="cm" href="/c/1/" data-n="1" aria-label="第 1 章"></a><span class="c" data-k="1.3">甲</span>' +
        '<a class="cm" href="/c/2/" data-n="2" aria-label="第 2 章"></a><span class="c" data-k="2.0">乙</span>' +
        '<span class="c" data-k="2.1">丙</span><span class="c">丁</span>',
    );
  });
  it('符号集合：句读符、分章圆点、缺字、句序标记', () => {
    for (const c of '∟＝◍□〼▩▦🅰🅱') expect(MARK_CHARS.has(c), c).toBe(true);
    expect(MARK_CHARS.has('甲')).toBe(false);
  });
});

describe('共用通行字', () => {
  it('各字视同相等：代表字是同组里排在最前的', () => {
    expect(sharedReading(['甲', '丙', '乙', '甲', '□'], eq)).toEqual({ reading: '甲', also: ['丙', '乙'] });
    expect(sharedReading(['丙', '乙'], eq)).toEqual({ reading: '乙', also: ['丙'] });
  });
  it('通行字、正确字参与折算', () => {
    expect(sharedReading(['子', '', '（子）', '子', '□'], eq)).toEqual({ reading: '子', also: [] });
    expect(sharedReading(['甲', '（丙）'], eq)).toEqual({ reading: '甲', also: ['丙'] });
    expect(sharedReading(['甲', '〈丁〉'], eq)).toEqual({ reading: '甲', also: ['丁'] });
  });
  it('用字不同就没有', () => {
    expect(sharedReading(['子', '丑'], eq)).toBeNull();
    expect(sharedReading(['甲', '子'], eq)).toBeNull();
  });
  it('只有一个字、全缺、只有通行字的列没有', () => {
    expect(sharedReading(['子', '', '□', '〼'], eq)).toBeNull();
    expect(sharedReading(['□', '〼'], eq)).toBeNull();
    expect(sharedReading(['（子）', '（子）'], eq)).toBeNull();
  });
  it('列里有句读符就不判定', () => {
    expect(sharedReading(['子', '∟', '子'], eq)).toBeNull();
    expect(sharedReading(['子', '＝', '子'], eq)).toBeNull();
  });
  it('列的情形：有共用字、有差异、无可比', () => {
    expect(columnKind(['甲', '丙'], eq).kind).toBe('shared');
    expect(columnKind(['子', '丑'], eq).kind).toBe('diff');
    expect(columnKind(['子', '', '□'], eq).kind).toBe('none');
    expect(columnKind(['子', '∟', '丑'], eq).kind).toBe('none');
  });
});

describe('一格怎么画', () => {
  it('类别', () => {
    expect(cellKind(cellOf(''))).toBe('blank');
    expect(cellKind(cellOf({ f: '脱' }))).toBe('tuo');
    expect(cellKind(cellOf({ f: '占' }))).toBe('zhan');
    expect(cellKind(cellOf('□'))).toBe('miss');
    expect(cellKind(cellOf('〼'))).toBe('miss');
    expect(cellKind(cellOf('∟'))).toBe('mark');
    expect(cellKind(cellOf({ t: '子', f: '残' }))).toBe('text');
  });
  it('比较用的字', () => {
    expect(compareKey({ t: '子', r: '丑' })).toBe('（丑）');
    expect(compareKey({ t: '𠀁', c: '丑' })).toBe('〈丑〉');
    expect(compareKey(t('子'))).toBe('子');
  });
  it('折算成同组的代表字', () => {
    expect(foldKey(t('丙'), eq)).toBe('甲');
    expect(foldKey({ t: '子', r: '丁' }, eq)).toBe('甲');
    expect(foldKey(t('子'), eq)).toBe('子');
  });
  it('与校订本比：相同、写法不同、用字不同', () => {
    expect(diffOf(t('甲'), t('甲'), eq)).toBe('');
    expect(diffOf(t('乙'), t('甲'), eq)).toBe('var');
    expect(diffOf({ t: '子', r: '丑' }, t('丑'), eq)).toBe('var');
    expect(diffOf(t('丑'), t('子'), eq)).toBe('diff');
    expect(diffOf(t('丑'), t(''), eq)).toBe('diff');
    expect(diffOf(t('□'), t('子'), eq)).toBe('');
    expect(diffOf(t(''), t('子'), eq)).toBe('');
  });
});

describe('一章的版面', () => {
  const base: Cell[] = Array.from({ length: 50 }, (_, i) => ({ t: i % 5 === 4 ? '' : '甲', ...(i % 5 === 3 ? { p: i % 10 === 8 ? '。' : '，' } : {}) }));
  it('每段不超过 max 列，断在句读后，首尾相接', () => {
    const bs = bands(base, 20, 8);
    expect(bs[0][0]).toBe(0);
    expect(bs.at(-1)![1]).toBe(50);
    bs.forEach(([a, b], i) => {
      expect(b - a).toBeLessThanOrEqual(20);
      if (i) expect(a).toBe(bs[i - 1][1]);
    });
    // 第一段断在第 19 列（句末）之后，并带上紧跟的空列
    expect(bs[0]).toEqual([0, 20]);
  });
  it('短的一章只有一段', () => {
    expect(bands(base.slice(0, 12))).toEqual([[0, 12]]);
  });
  it('没有标点时按 max 硬切', () => {
    expect(bands(Array.from({ length: 45 }, () => t('甲')), 20, 8)).toEqual([[0, 20], [20, 40], [40, 45]]);
  });
  it('标题取校订本第一个分句，符号不计', () => {
    expect(chapterTitle([t('◍'), t('甲'), t('乙'), { t: '甲' }, { t: '丙', p: '，' }, t('丁')])).toBe('甲乙甲丙');
    expect(chapterTitle(Array.from({ length: 12 }, () => t('甲')), 6)).toBe('甲甲甲甲甲甲'); // 没有断句时取到 limit 个字
  });
  it('同一版本的几行并成一行', () => {
    const rows = mergeParts([
      { version: 'a', part: 'A', cells: [t('甲'), t(''), t('')] },
      { version: 'a', part: 'B', cells: [t(''), t('乙'), t('')] },
      { version: 'b', cells: [t('丙'), t('丁'), t('戊')] },
    ]);
    expect(rows.map((r) => [r.version, r.cells.map((c) => c.t).join('')])).toEqual([
      ['a', '甲乙'],
      ['b', '丙丁戊'],
    ]);
  });
});

describe('读取对读表（占位数据）', () => {
  const dir = join(tmp.dir, 'al');
  fixtureCorpus(tmp.dir, 'al', {}, true, true);
  const al = loadAlignment(dir) as Alignment;

  it('没有 alignment/ 的目录返回 null', () => {
    fixtureCorpus(tmp.dir, 'plain');
    expect(loadAlignment(join(tmp.dir, 'plain'))).toBeNull();
  });

  it('版本、章、格、等同表、造字码位、对照资料说明', () => {
    expect(al.versions.map((v) => v.id)).toEqual(['jiaoding', 'w-t', 'w-a', 'w-b']);
    expect(al.chapters.map((c) => [c.n, c.columns, c.rows.length])).toEqual([[1, 6, 4], [2, 4, 3]]);
    expect(al.chapter(1).rows[2].cells[1]).toEqual({ t: '丑', r: '乙' }); // 对象的格
    expect(al.chapter(1).rows[2].cells[3]).toEqual({ t: '' }); // 空格
    expect(al.chapter(1).rows[0].cells[0]).toEqual({ t: '甲' }); // 只有正文的格
    expect(al.equivalents.same[0]).toEqual(['甲', '子']);
    expect(al.glyphs.get('〚⿰甲乙〛')).toBe(0xe000);
    expect(al.study.references).toHaveLength(2);
    expect(al.version('w-a')?.short).toBe('甲组');
    expect(al.version('nope')).toBeUndefined();
  });

  it('各章 JSON 的原文原样留着，供网站提供下载', () => {
    expect(al.chapterFiles).toHaveLength(2);
    expect(al.chapterFiles[1]).toBe(readFileSync(join(dir, 'alignment/chapters/002.json'), 'utf-8'));
  });

  it('章号越界就报错', () => {
    expect(() => al.chapter(3)).toThrow('没有第 3 章');
    expect(() => al.chapter(0)).toThrow('没有第 0 章');
  });

  it('只有带逐行释文、且不是以章为单位的本才能读', () => {
    expect(al.hasLines('w-a')).toBe(true);
    expect(al.hasLines('w-b')).toBe(false); // 没有逐行释文
    expect(al.hasLines('jiaoding')).toBe(false);
  });

  it('第 n 章在某个本里占哪几简', () => {
    expect(al.linesOf('w-a', 1)).toEqual(['1', '2']);
    expect(al.linesOf('w-a', 2)).toEqual(['2', '3']);
    expect(al.linesOf('w-b', 1)).toEqual([]);
  });

  it('各章在各本里有没有、是否存字', () => {
    expect(al.presence(1, ['w-b'])).toEqual({ has: true, legible: true });
    expect(al.presence(2, ['w-b'])).toEqual({ has: false, legible: false });
    expect(al.presence(2, ['w-b', 'w-a']).has).toBe(true); // 几个本合看：有一个有就算有
    const lost = new Alignment([], [{ n: 1, columns: 2, rows: [{ version: 'x', cells: [t('□'), { t: '', f: '脱' }] }], notes: [] }], new Map(), eq, new Map(), { overview: [], legend: [], references: [] }, []);
    expect(lost.presence(1, ['x'])).toEqual({ has: true, legible: false }); // 有这一章，但字全残缺
  });
});

describe('整套对读数据（data/alignment）', () => {
  const al = loadAlignment('data') as Alignment;

  it('八个版本、81 章、各章的各行一样长，校订本在最上', () => {
    expect(al.versions.map((v) => v.id)).toEqual(['jiaoding', 'wangbi', 'beida', 'mawangdui-jia', 'mawangdui-yi', 'guodian-jia', 'guodian-yi', 'guodian-bing']);
    expect(al.chapters).toHaveLength(81);
    al.chapters.forEach((ch, i) => {
      expect(ch.n).toBe(i + 1);
      expect(ch.rows[0].version).toBe('jiaoding');
      for (const r of ch.rows) expect(r.cells, `第 ${ch.n} 章 ${r.version}`).toHaveLength(ch.columns);
    });
  });

  it('每章分段后列数不变，段内不超过 20 列', () => {
    for (const ch of al.chapters) {
      const bs = bands(ch.rows[0].cells);
      expect(bs.reduce((n, [a, b]) => n + (b - a), 0)).toBe(ch.columns);
      for (const [a, b] of bs) expect(b - a).toBeLessThanOrEqual(20);
    }
  });

  it('同一版本的几行（分段）并成一行，并成之后每个版本一行', () => {
    for (const ch of al.chapters) {
      const merged = mergeParts(ch.rows);
      expect(new Set(merged.map((r) => r.version)).size, `第 ${ch.n} 章`).toBe(merged.length);
      expect(merged.map((r) => r.version)).toEqual([...new Set(ch.rows.map((r) => r.version))]);
    }
  });

  it('每一章每一列：共用通行字的判定不报错，且共用字不为空', () => {
    for (const ch of al.chapters) {
      const rows = mergeParts(ch.rows);
      for (let i = 0; i < ch.columns; i++) {
        const k = columnKind(rows.map((r) => compareKey(r.cells[i])), al.equivalents);
        if (k.kind === 'shared') expect(k.shared!.reading, `第 ${ch.n} 章第 ${i} 列`).not.toBe('');
      }
    }
  });

  it('逐行释文每个字都指向对读表里正文相同的一格', () => {
    for (const [vid, lines] of al.lines) {
      if (vid === 'wangbi') continue; // 王弼本的“行”是整章，不逐字对
      for (const line of lines) {
        const toks = tokenize(line.text);
        const where = line.refs.flatMap(([n, cols]) => cols.map((col) => [n, col] as const));
        expect(where, `${vid} ${line.no}`).toHaveLength(toks.length);
        where.forEach(([n, col], i) => {
          const cells = al.chapter(n).rows.filter((r) => r.version === vid).map((r) => r.cells[col]);
          const cell = cells.find((c) => cellKind(c) !== 'blank');
          expect(cell, `${vid} ${line.no} 第 ${n} 章第 ${col} 列`).toBeDefined();
          if (cell!.t !== '〼' && toks[i] !== '□') expect(glyphOf(toks[i], al.glyphs).text).toBe(glyphOf(cell!.t, al.glyphs).text);
        });
      }
    }
  });

  it('逐行释文的简号、行号在各本里不重复；linesOf 与逐行释文互相对得上', () => {
    for (const [vid, lines] of al.lines) {
      const nos = lines.map((l) => l.no);
      expect(new Set(nos).size, vid).toBe(nos.length);
      for (const n of [1, 40, 81]) {
        const mine = al.linesOf(vid, n);
        expect(mine.every((no) => nos.includes(no)), `${vid} 第 ${n} 章`).toBe(true);
      }
    }
  });

  it('能读的本：有逐行释文、不是以章为单位的', () => {
    expect([...al.lines.keys()].filter((id) => al.hasLines(id)).sort()).toEqual(
      ['beida', 'guodian-bing', 'guodian-jia', 'guodian-yi', 'mawangdui-jia', 'mawangdui-yi'],
    );
  });

  it('造字序列在补充字体里都有码位，且落在私用区或 U+20000 以后', () => {
    expect(al.glyphs.size).toBeGreaterThan(0);
    for (const [tok, cp] of al.glyphs) {
      expect(tok.startsWith('〚') && tok.endsWith('〛'), tok).toBe(true);
      expect((cp >= 0xe000 && cp <= 0xf8ff) || cp >= 0x20000, tok).toBe(true);
    }
  });

  it('对照资料说明齐全', () => {
    expect(al.study.overview.length).toBeGreaterThan(0);
    expect(al.study.references).toHaveLength(15);
  });
});
