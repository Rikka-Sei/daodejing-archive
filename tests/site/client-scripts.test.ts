/**
 * 页面脚本里有逻辑的两个：阅读器（src/scripts/reader.js）与对读表页（align.js）。
 * 它们是浏览器里直接跑的普通脚本。这里用 node:vm 把脚本放进一个只有几个桩的假页面里跑，不引入 DOM 库：
 * 点一个字、拖选几个字，读各章的对读表，看弹出的“透视”。
 * 阅读器里重抄了一份比较与共用通行字的规则（同 src/lib/alignment.ts，要一起改），所以对占位数据和整套真实数据
 * 逐列把两边对一遍；真实数据只比两边的结果是否一致，不测字句。
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { runInNewContext } from 'node:vm';
import { afterAll, describe, expect, it, vi } from 'vitest';
import {
  type Alignment,
  type Cell,
  type Row,
  cellKind,
  columnKind,
  compareKey,
  diffOf,
  mergeParts,
  readerMeta,
  showText,
} from '../../src/lib/alignment';
import { loadAlignment } from '../../src/lib/alignment';
import { fixtureCorpus, tempDir } from './fixtures';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

const script = (name: string) => readFileSync(join(process.cwd(), 'src/scripts', name), 'utf-8');
/** 让已经排上的承诺都跑完 */
const settle = () => new Promise<void>((r) => setImmediate(r));

type Ev = Record<string, unknown>;
type Handler = (ev: Ev) => void;

// ── 阅读器 ──────────────────────────────────────────────────

/** 假的字：reader.js 只读它的 dataset.k，加减 class，取位置，找最近的祖先 */
class Char {
  classes = new Set<string>();
  dataset: { k: string };
  constructor(k: string) {
    this.dataset = { k };
  }
  classList = { add: (c: string) => void this.classes.add(c), remove: (c: string) => void this.classes.delete(c) };
  getBoundingClientRect = () => ({ left: 100, top: 50, right: 120, bottom: 70 });
  closest = (sel: string) => (sel === '.c[data-k]' ? this : null);
}

/** 没有祖先可找的目标（页面空白处） */
const blank = { closest: () => null };

/**
 * 把 reader.js 放进一个假页面里跑。files：地址 → 文件内容，读不到的地址返回 404。
 * present 为 false 时页面里没有阅读区（别的页面也会载入脚本，应当什么也不做）。
 */
function readerPage(files: Record<string, string>, me: string, present = true) {
  const onRd: Record<string, Handler> = {};
  const onDoc: Record<string, Handler> = {};
  const fetched: string[] = [];
  const bodyClasses = new Set<string>();
  const chars: Char[] = [];
  let selection: unknown = null;
  const lens = { hidden: true, innerHTML: '', style: {}, offsetWidth: 300, offsetHeight: 200, contains: (n: unknown) => n === lens };
  const rd = {
    dataset: { chapters: '/c/chapters/', meta: '/c/alignment.json', w: me },
    clientWidth: 800,
    addEventListener: (t: string, f: Handler) => void (onRd[t] = f),
    querySelectorAll: () => chars,
    scrollBy: vi.fn(),
  };
  runInNewContext(script('reader.js'), {
    document: {
      getElementById: (id: string) => (!present ? null : id === 'rd' ? rd : id === 'lens' ? lens : null),
      body: {
        classList: {
          toggle: (c: string, on?: boolean) => {
            const want = on ?? !bodyClasses.has(c);
            if (want) bodyClasses.add(c);
            else bodyClasses.delete(c);
            return want;
          },
          contains: (c: string) => bodyClasses.has(c),
        },
      },
      addEventListener: (t: string, f: Handler) => void (onDoc[t] = f),
    },
    window: { matchMedia: () => ({ matches: false }), getSelection: () => selection, innerWidth: 1000, innerHeight: 800 },
    fetch: (u: string) => {
      fetched.push(u);
      const body = files[u];
      return Promise.resolve(body === undefined ? { ok: false, status: 404 } : { ok: true, status: 200, json: () => Promise.resolve(JSON.parse(body)) });
    },
    setTimeout: (f: () => void) => f(),
  });
  return {
    lens,
    rd,
    fetched,
    focused: () => bodyClasses.has('focus'),
    listening: () => Object.keys(onRd).length + Object.keys(onDoc).length,
    /** 点一个字，返回弹出的透视 */
    async click(k: string) {
      const c = new Char(k);
      selection = null;
      onRd.pointerup({ target: c });
      await settle();
      return { html: lens.innerHTML, picked: [c] };
    },
    /** 拖选几个字；页面上另有一个没选中的字，不应被取到 */
    async drag(ks: string[]) {
      const picked = ks.map((k) => new Char(k));
      chars.splice(0, chars.length, new Char('9.9'), ...picked);
      selection = { isCollapsed: false, rangeCount: 1, getRangeAt: () => ({ intersectsNode: (n: unknown) => picked.includes(n as Char) }) };
      onRd.pointerup({ target: picked[0] });
      await settle();
      return { html: lens.innerHTML, picked };
    },
    /** 点页面上别的地方（不是字，也不是链接） */
    async clickAway() {
      selection = null;
      onRd.pointerup({ target: blank });
      await settle();
    },
    pointerdown: (target: unknown) => onDoc.pointerdown({ target }),
    scroll: () => onRd.scroll({}),
    key: (key: string, over: Partial<Ev> = {}) => {
      const preventDefault = vi.fn();
      onDoc.keydown({ key, target: blank, metaKey: false, ctrlKey: false, altKey: false, preventDefault, ...over });
      return preventDefault;
    },
  };
}

/** 把透视里的内容读成结构：每个本一行，页脚各段 */
function parseLens(html: string) {
  const rows = [...html.matchAll(/<div class="lr( me)?"><b>([^<]*)<\/b>(.*?)<\/div>/gs)].map((m) => ({
    me: !!m[1],
    name: m[2],
    glyphs: [...m[3].matchAll(/<span class="(g[^"]*)">([^<]*)<\/span>/g)].map((g) => ({ cls: g[1], text: g[2] })),
    note: /<small>([^<]*)<\/small>/.exec(m[3])?.[1],
  }));
  const foot = /<div class="ft">(.*)<\/div>/s.exec(html)?.[1]?.split('<br>') ?? [];
  return { head: /<h4>([^<]*)<\/h4>/.exec(html)?.[1], rows, foot };
}

const SHARED = /共用通行字：<b class="g">([^<]*)<\/b>(?:（([^）]*)同）)?/;

/** 阅读器的脚本读这两种文件：公共部分 alignment.json 和各章的 NNN.json */
const filesOf = (al: Alignment) => ({
  '/c/alignment.json': JSON.stringify(readerMeta(al)),
  ...Object.fromEntries(al.chapterFiles.map((text, i) => [`/c/chapters/${String(i + 1).padStart(3, '0')}.json`, text])),
});

describe('阅读器脚本（占位数据）', () => {
  const al = fixtureCorpus(tmp.dir, 'al', {}, true, true).alignment as Alignment;
  const page = () => readerPage(filesOf(al), 'w-a');

  it('点一个字：各本在同一处写的什么，本页这一本标出来', async () => {
    const p = page();
    const { head, rows, foot } = parseLens((await p.click('1.2')).html);
    expect(head).toBe('透视 · 第 1 章 · 同处各本');
    expect(rows.map((r) => [r.name, r.me, r.glyphs.map((g) => g.text)])).toEqual([
      ['校订', false, ['丙']],
      ['传世', false, ['丙']],
      ['甲组', true, ['丙']],
      ['乙组', false, ['子']],
    ]);
    expect(foot).toEqual(['各本用字有差异', '<a href="/c/chapters/1/#c2">在对读表里看 ›</a>']);
    expect(p.lens.hidden).toBe(false);
  });

  it('每格的说明：通行字、残字、缺字、无字、脱文', async () => {
    const p = page();
    expect(parseLens((await p.click('1.1')).html).rows.map((r) => r.note)).toEqual(['', '', '通行字 乙', '']);
    expect(parseLens((await p.click('1.2')).html).rows.map((r) => r.note)).toEqual(['', '', '', '残字']);
    const col4 = parseLens((await p.click('1.4')).html);
    expect(col4.rows.map((r) => r.note)).toEqual(['', '', '缺字', '脱文']);
    expect(col4.rows[2].glyphs[0]).toEqual({ cls: 'g d-missing', text: '□' });
    expect(col4.rows[3].glyphs[0]).toEqual({ cls: 'g nil', text: '·' });
    expect(parseLens((await p.click('1.3')).html).rows[2].note).toBe('无字');
  });

  it('与校订本比：写法不同但视同相等的标 var，用字不同的标 diff，残字另带 d-part', async () => {
    const p = page();
    expect(parseLens((await p.click('1.1')).html).rows.map((r) => r.glyphs[0].cls)).toEqual(['g', 'g', 'g var', 'g']);
    expect(parseLens((await p.click('1.2')).html).rows.map((r) => r.glyphs[0].cls)).toEqual(['g', 'g', 'g', 'g d-part diff']);
    expect(parseLens((await p.click('1.4')).html).rows[1].glyphs[0].cls).toBe('g diff');
  });

  it('共用通行字：写在页脚，异体并入同一列', async () => {
    const p = page();
    expect(SHARED.exec((await p.click('1.0')).html)?.slice(1)).toEqual(['甲', undefined]);
    expect(SHARED.exec((await p.click('1.1')).html)?.slice(1)).toEqual(['乙', undefined]);
    expect((await p.click('1.2')).html).not.toMatch(SHARED);
  });

  it('造字序列换成补充字体里的码位', async () => {
    const { rows } = parseLens((await page().click('2.3')).html);
    expect(rows[2].glyphs[0].text).toBe('');
  });

  it('各章的对读表第一次用到才读，读过不再读', async () => {
    const p = page();
    expect(p.fetched).toEqual([]);
    await p.click('1.0');
    expect(p.fetched).toEqual(['/c/alignment.json', '/c/chapters/001.json']);
    await p.click('1.3');
    await p.drag(['1.4', '1.5']);
    expect(p.fetched).toHaveLength(2);
    await p.click('2.0');
    expect(p.fetched).toEqual(['/c/alignment.json', '/c/chapters/001.json', '/c/chapters/002.json']);
  });

  it('拖选：只取选区碰到的字，几列并排；选中的字加上 sel', async () => {
    const p = page();
    const { html, picked } = await p.drag(['1.4', '1.5']);
    const { rows, foot } = parseLens(html);
    expect(rows.map((r) => r.glyphs.map((g) => g.text).join(''))).toEqual(['戊己', '庚己', '□己', '·己']);
    expect(foot).toEqual(['<a href="/c/chapters/1/#c4">在对读表里看 ›</a>']); // 几列并排不判定共用通行字
    expect(picked.map((c) => c.classes.has('sel'))).toEqual([true, true]);
  });

  it('拖选跨章：只列第一个字所在的章，并说明另有几个字在别的章', async () => {
    const p = page();
    const { html, picked } = await p.drag(['1.5', '2.0', '2.1']);
    const { head, rows, foot } = parseLens(html);
    expect(head).toBe('透视 · 第 1 章 · 同处各本');
    expect(rows[0].glyphs).toHaveLength(1);
    expect(foot).toEqual(['共用通行字：<b class="g">己</b>', '另有 2 个字在别的章，这里只列了第 1 章的', '<a href="/c/chapters/1/#c5">在对读表里看 ›</a>']);
    expect(picked.map((c) => c.classes.has('sel'))).toEqual([true, false, false]);
  });

  it('选得太多：不读对读表，提示先选几个字', async () => {
    const p = page();
    const ks = Array.from({ length: 41 }, (_, i) => `1.${i}`);
    const { html, picked } = await p.drag(ks);
    expect(html).toContain('选得太多了');
    expect(p.fetched).toEqual([]);
    expect(picked.some((c) => c.classes.has('sel'))).toBe(false);
    const { rows } = parseLens((await p.drag(ks.slice(0, 40))).html); // 40 列还可以（章里只有 6 列，其余补空）
    expect(rows.map((r) => r.glyphs.length)).toEqual([40, 40, 40, 40]);
  });

  it('读不到对读表：给提示，不留下选中', async () => {
    const p = readerPage({}, 'w-a');
    const { html, picked } = await p.click('1.0');
    expect(html).toContain('读不到这一章的对读表');
    expect(picked[0].classes.has('sel')).toBe(false);
    expect(p.lens.hidden).toBe(false);
  });

  it('点到字以外的地方、滚动、点透视外面：关闭并清掉选中；点链接不处理', async () => {
    const p = page();
    let { picked } = await p.click('1.0');
    expect(picked[0].classes.has('sel')).toBe(true);
    await p.clickAway();
    expect(p.lens.hidden).toBe(true);
    expect(picked[0].classes.has('sel')).toBe(false);

    ({ picked } = await p.click('1.0'));
    p.pointerdown(p.lens); // 点在透视里面不关
    expect(p.lens.hidden).toBe(false);
    p.pointerdown({});
    expect(p.lens.hidden).toBe(true);

    ({ picked } = await p.click('1.0'));
    p.scroll();
    expect(p.lens.hidden).toBe(true);
    expect(picked[0].classes.has('sel')).toBe(false);

    await p.click('1.0');
    const link = { closest: (sel: string) => (sel === 'a,button' ? {} : null) };
    // 点在链接或按钮上：脚本不接手，透视原样
    expect(() => p.pointerdown(link)).not.toThrow();
  });

  it('键盘：F 进出专注，Esc 先关透视再退出专注，输入框里不响应，← → 翻一屏', async () => {
    const p = page();
    p.key('f');
    expect(p.focused()).toBe(true);
    await p.click('1.0');
    p.key('Escape');
    expect([p.lens.hidden, p.focused()]).toEqual([true, true]);
    p.key('Escape');
    expect(p.focused()).toBe(false);

    p.key('F', { target: { closest: (sel: string) => (sel === 'input,select,textarea' ? {} : null) } });
    p.key('f', { ctrlKey: true });
    expect(p.focused()).toBe(false);

    const left = p.key('ArrowLeft');
    const right = p.key('ArrowRight');
    expect(p.rd.scrollBy.mock.calls).toEqual([[{ left: -480, behavior: 'smooth' }], [{ left: 480, behavior: 'smooth' }]]);
    expect([left, right].map((f) => f.mock.calls.length)).toEqual([1, 1]);
  });

  it('页面里没有阅读区：什么也不做', () => {
    const p = readerPage(filesOf(al), 'w-a', false);
    expect(p.listening()).toBe(0);
  });
});

// ── 阅读器与 alignment.ts 的比较规则一致 ────────────────────────

/** 透视里每个本、每个字应有的样子，按 alignment.ts 的规则算 */
function expectedLens(al: Alignment, n: number, cols: number[], me: string) {
  const eq = al.equivalents;
  const merged = mergeParts(al.chapter(n).rows);
  const at = (r: Row, col: number): Cell => r.cells[col] ?? { t: '' };
  return merged.map((r, i) => ({
    name: al.version(r.version)?.short ?? r.version,
    me: r.version === me,
    glyphs: cols.map((col) => {
      const c = at(r, col);
      switch (cellKind(c)) {
        case 'text':
          return { cls: ['g', c.f === '残' ? 'd-part' : '', i > 0 ? diffOf(c, at(merged[0], col), eq) : ''].filter(Boolean).join(' '), text: showText(c.t, al.glyphs) };
        case 'mark':
          return { cls: 'g mk', text: c.t };
        case 'miss':
          return { cls: 'g d-missing', text: '□' };
        default:
          return { cls: 'g nil', text: '·' };
      }
    }),
  }));
}

/** 单列时页脚的判定：共用通行字，或“各本用字有差异”，或都没有 */
function expectedVerdict(al: Alignment, n: number, col: number) {
  const keys = mergeParts(al.chapter(n).rows).map((r) => compareKey(r.cells[col] ?? { t: '' }));
  const { kind, shared } = columnKind(keys, al.equivalents);
  return {
    shared: shared && { reading: showText(shared.reading, al.glyphs), also: shared.also.map((x) => showText(x, al.glyphs)).join('、') },
    differs: kind === 'diff',
  };
}

describe.each([
  ['占位数据', () => fixtureCorpus(tmp.dir, 'parity', {}, true, true).alignment as Alignment, 'w-a'],
  ['整套真实数据', () => loadAlignment('data') as Alignment, 'mawangdui-jia'],
] as const)('阅读器与 alignment.ts 的比较规则一致（%s）', (_name, load, me) => {
  const al = load();
  const page = readerPage(filesOf(al), me);

  it('单列：每个本的字与样式、共用通行字、有无差异，逐列一致', async () => {
    const bad: string[] = [];
    for (const ch of al.chapters) {
      for (let col = 0; col < ch.columns; col++) {
        const { html } = await page.click(`${ch.n}.${col}`);
        const got = parseLens(html);
        const want = expectedLens(al, ch.n, [col], me);
        const where = `第 ${ch.n} 章第 ${col} 列`;
        if (JSON.stringify(got.rows.map((r) => ({ name: r.name, me: r.me, glyphs: r.glyphs }))) !== JSON.stringify(want)) {
          bad.push(`${where}：各本的字或样式不一致`);
        }
        const verdict = expectedVerdict(al, ch.n, col);
        const m = SHARED.exec(html);
        const shared = m && { reading: m[1], also: m[2] ?? '' };
        if (JSON.stringify(shared ?? null) !== JSON.stringify(verdict.shared ?? null)) bad.push(`${where}：共用通行字 ${JSON.stringify(shared)} ≠ ${JSON.stringify(verdict.shared)}`);
        if (html.includes('各本用字有差异') !== verdict.differs) bad.push(`${where}：“各本用字有差异”应为 ${verdict.differs}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it('多列：每章每 40 列一选，各字的样式一致', async () => {
    const bad: string[] = [];
    for (const ch of al.chapters) {
      for (let from = 0; from < ch.columns; from += 40) {
        const cols = Array.from({ length: Math.min(40, ch.columns - from) }, (_, i) => from + i);
        const { html } = await page.drag(cols.map((c) => `${ch.n}.${c}`));
        const got = parseLens(html).rows.map((r) => ({ name: r.name, me: r.me, glyphs: r.glyphs }));
        if (JSON.stringify(got) !== JSON.stringify(expectedLens(al, ch.n, cols, me))) bad.push(`第 ${ch.n} 章第 ${from} 列起`);
      }
    }
    expect(bad).toEqual([]);
  });
});

// ── 对读表页 ────────────────────────────────────────────────

/** 假的格：align.js 只读 dataset.col，开关 class，找最近的格 */
class Td {
  classes = new Set<string>();
  dataset: { col: string };
  constructor(col: number) {
    this.dataset = { col: String(col) };
  }
  classList = { toggle: (c: string, on: boolean) => void (on ? this.classes.add(c) : this.classes.delete(c)) };
  closest = (sel: string) => (sel === 'table.al td[data-col]' ? this : null);
}

/** 假的对读表页：三列，每列两个格（两个版本）。hash 是打开页面时地址里的 #… */
function alignPage(hash = '', cells = 2) {
  const tds = [0, 1, 2].flatMap((col) => Array.from({ length: cells }, () => new Td(col)));
  const onDoc: Record<string, Handler> = {};
  const replaceState = vi.fn();
  const anchor = { scrollIntoView: vi.fn() };
  runInNewContext(script('align.js'), {
    document: {
      querySelectorAll: () => tds,
      getElementById: (id: string) => (id === 'c1' ? anchor : null),
      addEventListener: (t: string, f: Handler) => void (onDoc[t] = f),
    },
    location: { hash, pathname: '/c/chapters/1/', search: '?x=1' },
    history: { replaceState },
  });
  const col = (i: number, cls: string) => tds.filter((t) => t.dataset.col === String(i)).map((t) => t.classes.has(cls));
  return {
    tds,
    replaceState,
    anchor,
    listening: () => Object.keys(onDoc).length,
    col,
    over: (td: Td | null) => onDoc.mouseover({ target: td ?? blank }),
    click: (td: Td | null) => onDoc.click({ target: td ?? blank }),
  };
}

describe('对读表页脚本', () => {
  it('指到一个字，同一列的格都高亮；移到别的列或移开就取消', () => {
    const p = alignPage();
    p.over(p.tds[0]);
    expect(p.col(0, 'hl')).toEqual([true, true]);
    expect(p.col(1, 'hl')).toEqual([false, false]);
    p.over(p.tds[1]); // 同一列内移动，仍高亮
    expect(p.col(0, 'hl')).toEqual([true, true]);
    p.over(p.tds[2]);
    expect([p.col(0, 'hl'), p.col(1, 'hl')]).toEqual([[false, false], [true, true]]);
    p.over(null);
    expect(p.col(1, 'hl')).toEqual([false, false]);
  });

  it('点一下把这一列钉住，再点取消；地址里的 #c<列> 跟着变', () => {
    const p = alignPage();
    p.click(p.tds[2]);
    expect(p.col(1, 'pin')).toEqual([true, true]);
    expect(p.replaceState).toHaveBeenLastCalledWith(null, '', '#c1');
    p.click(p.tds[0]); // 钉另一列：前一列松开
    expect([p.col(0, 'pin'), p.col(1, 'pin')]).toEqual([[true, true], [false, false]]);
    p.click(p.tds[1]); // 同一列再点：取消，地址回到不带锚点
    expect(p.col(0, 'pin')).toEqual([false, false]);
    expect(p.replaceState).toHaveBeenLastCalledWith(null, '', '/c/chapters/1/?x=1');
    p.click(null); // 点在别处不动
    expect(p.replaceState).toHaveBeenCalledTimes(3);
  });

  it('地址里带 #c<列> 打开：钉住那一列并滚过去；写得不对的锚点忽略', () => {
    const p = alignPage('#c1');
    expect(p.col(1, 'pin')).toEqual([true, true]);
    expect(p.anchor.scrollIntoView).toHaveBeenCalledWith({ block: 'center' });
    expect(alignPage('#c').col(1, 'pin')).toEqual([false, false]);
    expect(alignPage('#top').replaceState).not.toHaveBeenCalled();
  });

  it('页面里没有对读表：什么也不做', () => {
    const p = alignPage('', 0);
    expect(p.listening()).toBe(0);
  });
});

// ── 透视页（简牍排布） ───────────────────────────────────────

class Tile {
  classes = new Set<string>();
  dataset: { ch: string; no: string };
  constructor(ch: string, no: string) {
    this.dataset = { ch, no };
  }
  classList = { toggle: (c: string, on: boolean) => void (on ? this.classes.add(c) : this.classes.delete(c)) };
}

/** 假的透视页：两个本，一共三简。hash 是打开页面时地址里的 #… */
function layoutPage(hash = '', present = true) {
  const tiles = [new Tile('1', '1'), new Tile('1 2', '2'), new Tile('2', '1')];
  const sections = [
    { dataset: { name: '甲组', unit: '简' }, querySelectorAll: () => tiles.slice(0, 2).filter((t) => t.classes.has('hit')) },
    { dataset: { name: '乙本', unit: '行' }, querySelectorAll: () => tiles.slice(2).filter((t) => t.classes.has('hit')) },
  ];
  const input = { value: '', max: '3', focus: vi.fn(), addEventListener: (t: string, f: Handler) => void (on[`i:${t}`] = f) };
  const say = { textContent: '' };
  const clear = { hidden: true, addEventListener: (t: string, f: Handler) => void (on[`c:${t}`] = f) };
  const on: Record<string, Handler> = {};
  const body = new Set<string>();
  const replaceState = vi.fn();
  runInNewContext(script('layout.js'), {
    document: {
      getElementById: (id: string) => (!present ? null : id === 'lv-n' ? input : id === 'lv-say' ? say : id === 'lv-clear' ? clear : null),
      querySelectorAll: (sel: string) => (sel === '.sl' ? tiles : sel === 'section.lv' ? sections : []),
      body: { classList: { toggle: (c: string, v: boolean) => void (v ? body.add(c) : body.delete(c)) } },
    },
    location: { hash, pathname: '/c/lens/', search: '' },
    history: { replaceState },
  });
  return {
    input,
    say,
    clear,
    body,
    replaceState,
    hits: () => tiles.map((t) => t.classes.has('hit')),
    type: (v: string) => {
      input.value = v;
      on['i:input']({});
    },
    clickClear: () => on['c:click']({}),
    listening: () => Object.keys(on).length,
  };
}

describe('透视页脚本', () => {
  it('选一章：写了这一章的简亮起来，页面标出各本的简号；地址带 #ch<章>', () => {
    const p = layoutPage();
    p.type('2');
    expect(p.hits()).toEqual([false, true, true]);
    expect(p.body.has('lv-pick')).toBe(true);
    expect(p.clear.hidden).toBe(false);
    expect(p.say.textContent).toBe('第 2 章：甲组 简 2；乙本 行 1');
    expect(p.replaceState).toHaveBeenLastCalledWith(null, '', '#ch2');
  });

  it('清空或超出范围：恢复原样，地址不带锚点', () => {
    const p = layoutPage();
    p.type('1');
    p.type('9');
    expect(p.hits()).toEqual([false, false, false]);
    expect(p.body.has('lv-pick')).toBe(false);
    expect(p.say.textContent).toBe('');
    expect(p.replaceState).toHaveBeenLastCalledWith(null, '', '/c/lens/');
    p.type('2');
    p.clickClear();
    expect(p.input.value).toBe('');
    expect(p.clear.hidden).toBe(true);
  });

  it('地址里带 #ch<章> 打开就选好那一章；写得不对的忽略', () => {
    const p = layoutPage('#ch1');
    expect(p.input.value).toBe('1');
    expect(p.hits()).toEqual([true, true, false]);
    expect(layoutPage('#ch').input.value).toBe('');
    expect(layoutPage('#top').body.size).toBe(0);
  });

  it('这一章哪个本都没有：照实说', () => {
    const p = layoutPage();
    p.input.max = '3';
    p.type('3');
    expect(p.hits()).toEqual([false, false, false]);
    expect(p.say.textContent).toBe('第 3 章在这些本里都没有简或行');
  });

  it('页面里没有选章框：什么也不做', () => {
    expect(layoutPage('', false).listening()).toBe(0);
  });
});
