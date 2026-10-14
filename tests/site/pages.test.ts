/** 页面结构：用占位典籍渲染各个视图，检查封面、目录树、菜单、来源与授权等。 */
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { Corpus } from '../../src/lib/corpus';
import Cover from '../../src/views/Cover.astro';
import DataView from '../../src/views/DataView.astro';
import Volume from '../../src/views/Volume.astro';
import { fixtureCorpus, tempDir } from './fixtures';
import { count, render } from './render';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

let a: Corpus;
let b: Corpus;
let corpora: Corpus[];
beforeAll(() => {
  a = fixtureCorpus(tmp.dir, 'a', { title: '典籍甲', subtitle: '甲乙', license_note: '占位授权说明' });
  b = fixtureCorpus(tmp.dir, 'b', { title: '典籍乙' });
  corpora = [a, b];
});

const cover = (c = a, cs = corpora) => render(Cover, { props: { corpus: c, corpora: cs } });
const volume = (i: number, cs = corpora) => render(Volume, { props: { corpus: cs[0], wit: cs[0].witnesses[i], corpora: cs } });
const data = (cs = corpora) => render(DataView, { props: { corpus: cs[0], corpora: cs } });

describe('封面', () => {
  it('书名、开始阅读与数据版入口、凡例', async () => {
    const page = await cover();
    expect(page).toContain('<h1>典籍甲</h1>');
    expect(page).toContain('<div class="eyebrow">甲乙</div>');
    expect(page).toContain('<a class="btn pri" href="/a/w-a/">开始阅读</a>');
    expect(page).toContain('<a class="btn" href="/a/data/">数据版</a>');
    expect(page).toContain('id="preface"');
  });

  it('每部文献一张卡片，多个本的列出各本', async () => {
    const page = await cover();
    expect(count(page, '<article class="doc">')).toBe(2); // 甲书、乙书
    expect(page).toContain('<span class="t">甲书</span><span class="m">2 个版本 · 4 条释文 · 3 张影像</span>');
    expect(page).toContain('<div class="subs"><a href="/a/w-a/">甲组</a><a href="/a/w-b/">乙组</a></div>');
    expect(page).toContain('<span class="t">乙书</span><span class="m">2 条释文</span>'); // 只有一个本：不写版本数，没有子项
    expect(count(page, 'class="subs"')).toBe(1);
  });

  it('卡片配图：有影像用缩略图（取实物照片），没有影像用文字占位', async () => {
    const page = await cover();
    expect(page).toContain('<img loading="lazy" src="/a/thumbs/b1@720.jpg" alt="">');
    expect(page).toContain('<span class="ph">乙</span>');
  });

  it('没有编号，来源与授权放在各本页面里', async () => {
    const page = await cover();
    for (const s of ['第一部分', '卷一', '卷三', 'id="sources"', '<span class="t">来源与授权</span>']) expect(page).not.toContain(s);
    expect(page).toContain('3 个版本 · 6 条释文 · 3 张影像');
  });

  it('凡例按数据生成', async () => {
    const page = await cover();
    expect(page).toContain('释文照录来源，不改字'); // 没给 preface：用通用体例
    expect(page).toContain('只核对过一个来源'); // 全部 unverified，按数据补
    expect(page).toContain('SHA-256');
  });

  it('没有影像的典籍不写影像张数', async () => {
    const c = fixtureCorpus(tmp.dir, 'noimg', { title: '无图' }, false);
    const page = await cover(c, [c]);
    expect(page).toContain('<div class="stats">3 个版本 · 6 条释文</div>');
    expect(page).not.toContain('class="pic"><img');
  });

  it('只有封面的主题开关，没有排版与图版开关', async () => {
    const page = await cover();
    expect(page).toContain('data-k="theme"');
    expect(page).not.toContain('data-k="layout"');
  });

  it('封面不是宽栏，搜索框带词去数据版', async () => {
    const page = await cover();
    expect(page).toContain('<div class="content">');
    expect(page).toContain('data-go="/a/data/"');
  });
});

describe('侧栏', () => {
  it('目录树：每部文献的本收在它自己的文件夹里', async () => {
    const page = await volume(1);
    expect(page).toContain('<details class="dir" data-g="w" open>'); // 甲书：文件夹
    expect(page).toContain('<span class="t">甲书</span>');
    expect(page).toContain('<a class="lk" href="/a/w-a/"><span class="t">甲组</span></a>');
    expect(page).toContain('<div class="item leaf on"><a class="lk" href="/a/w-b/" aria-current="page">'); // 当前本
    expect(page).toContain('<a class="lk" href="/a/w-c/"><svg'); // 乙书只有一个本：直接一项，带文件图标
    expect(page).not.toContain('data-g="w-c"');
    expect(page).not.toContain('卷');
  });

  it('每一行的“⋯”菜单提供下载', async () => {
    const page = await volume(1);
    expect(page).toContain('href="/a/w-a.txt" download="甲书-甲组.txt"');
    expect(page).toContain('href="/a/w-a.jsonl" download="甲书-甲组.jsonl"');
    expect(page).toContain('href="/a/w-all.txt" download="甲书-全部.txt"'); // 文件夹行：整部文献的合集
    expect(page).toContain('下载全部释文（.txt）');
    expect(page).toContain('href="/a/w-c.txt" download="乙书.txt"');
    expect(count(page, 'class="more"')).toBe(4); // 一个文件夹 + 三个本
    expect(page).toContain('id="pop"');
  });

  it('封面的侧栏里也有同样的下载入口', async () => {
    const page = await cover();
    expect(page).toContain('href="/a/w-a.txt" download="甲书-甲组.txt"');
    expect(page).toContain('href="/a/w-all.jsonl"');
  });

  it('收录多部典籍时才有典籍切换', async () => {
    expect(await volume(0)).toContain('class="sb-label">典籍<');
    expect(await volume(0)).toContain('<a class="item" href="/b/">');
    expect(await volume(0, [a])).not.toContain('class="sb-label">典籍<');
  });

  it('阅读版与数据版切换：读到哪个本，数据版就落在哪个本；当前在哪种版式，哪个键亮', async () => {
    const page = await volume(1);
    expect(page).toContain('href="/a/data/#w-b"');
    expect(page).toContain('href="/llms.txt"');
    expect(page).toContain('<a id="to-read" class="on"');
    expect(await data()).toContain('<a id="to-data" class="on"');
  });

  it('搜索框：本页就地过滤，数据版同样不跳转', async () => {
    expect(await volume(0)).not.toContain('data-go');
    expect(await data()).not.toContain('data-go');
    expect(await volume(0)).toContain('id="q"');
  });

  it('数据版的侧栏：每个本都能切换，阅读版开关带地址模板', async () => {
    const page = await data();
    for (const wid of ['w-a', 'w-b', 'w-c']) expect(page).toContain(`data-w="${wid}"`);
    expect(page).toContain('data-tpl="/a/{id}/"');
  });
});

describe('本的页面', () => {
  it('页面标题与描述', async () => {
    const page = await volume(1);
    expect(page).toContain('<title>甲书《占位》乙组 · 典籍甲</title>');
    expect(page).toContain('<meta name="description" content="甲书《占位》乙组的释文与影像">');
  });

  it('每个页面都有内联图标，免得浏览器去请求 /favicon.ico', async () => {
    for (const page of [await cover(), await volume(0), await data()]) {
      expect(page).toContain('<link rel="icon" href="data:image/svg+xml,%3Csvg');
    }
  });

  it('提前加载字体，字体族由 @font-face 声明', async () => {
    const page = await volume(0);
    expect(page).toContain('<link rel="preload" href="/fonts/noto-sans-sc-400.woff2" as="font" type="font/woff2" crossorigin>');
    expect(page).toContain('font-family:"DG Serif"');
  });

  it('有释文的页面用宽栏，三个开关齐全', async () => {
    const page = await volume(0);
    expect(page).toContain('<div class="content wide">');
    expect((await data())).toContain('<div class="content wide">');
    for (const k of ['layout', 'plates', 'theme']) expect(page).toContain(`data-k="${k}"`);
  });

  it('上一本与下一本：第一个本没有上一本，最后一个没有下一本', async () => {
    const page = await volume(1);
    expect(page).toContain('<a class="prev" href="/a/w-a/"><small>上一本</small>甲书 甲组</a>');
    expect(page).toContain('<a class="next" href="/a/w-c/"><small>下一本</small>乙书</a>');
    expect(await volume(0)).not.toContain('上一本');
    expect(await volume(2)).not.toContain('下一本');
  });

  it('面包屑跟着文献自己的层级走', async () => {
    expect(await volume(1)).toContain('<a href="/a/">典籍甲</a><span class="sep">›</span><span>甲书</span><span class="sep">›</span><b>乙组</b>');
    expect(await volume(2)).toContain('<span class="sep">›</span><b>乙书</b></nav>'); // 单个本：不多一级
  });

  it('释文：残缺字标样式，当前本的图版放在对应条目下', async () => {
    const page = await volume(0);
    expect(page).toContain('<p>甲<span class="d-missing">乙</span>丙</p>');
    expect(page).toContain('<a class="no" href="#w-a.001">简<span class="n">1</span></a>');
    expect(page).toContain('src="/a/thumbs/a1.jpg" alt="简1图版"');
    expect(page).toContain('href="https://raw.githubusercontent.com/Rikka-Sei/daodejing-archive/main/data/images/a1.jpg"');
  });

  it('没有对应条目的图版放在页尾的整页图版里', async () => {
    const page = await volume(0);
    expect(page).toContain('<h3>整页图版</h3>');
    expect(page).toContain('src="/a/thumbs/a2.jpg" alt="2 页"');
    expect(await volume(2)).not.toContain('<h3>整页图版</h3>'); // 乙书没有影像
  });

  it('跳转到某条：条目不多时展开，超过 60 条收起', async () => {
    expect(await volume(0)).toContain('<details class="fold jump" open>');
    const c = fixtureCorpus(tmp.dir, 'many');
    const w = c.witnesses[0];
    w.units = Array.from({ length: 61 }, (_, i) => ({ ...w.units[0], id: `w-a.${i}`, unit_no: String(i + 1) }));
    const page = await render(Volume, { props: { corpus: c, wit: w, corpora: [c] } });
    expect(page).toContain('<details class="fold jump">');
    expect(page).toContain('<span class="t">跳转到简</span>');
  });

  it('“版本信息”折叠栏只在登记了信息时出现', async () => {
    const fold = '<span class="t">版本信息</span>';
    expect(await volume(0)).toContain(fold); // w-a 登记了出土信息
    expect(await volume(1)).not.toContain(fold);
  });

  it('每个本的页面带自己的来源与授权', async () => {
    const fold = '<span class="t">来源与授权</span>';
    const page = await volume(0);
    expect(page).toContain(fold);
    expect(page).toContain('占位来源');
    expect(page).toContain('2 个来源 · CC0、未标明'); // 授权概要：各来源的授权名去重，没登记的记作未标明
    expect(page).toContain('占位授权说明'); // 授权说明来自典籍的设置
    expect(page).toContain('授权：CC0；抓取于 2026-01-02');
    expect(page).toContain('授权：来源未标明，按可收录处理；仅登记，未抓取');
    expect(page).toContain('<dt>授权依据</dt><dd>占位依据</dd>'); // 授权依据、备注、原始文件收在来源下面的折叠里
    expect(page).toContain('<dt>备注</dt><dd>占位备注</dd>');
    expect(page).toContain('href="https://github.com/Rikka-Sei/daodejing-archive/blob/main/data/raw/s/x.html"');
    expect(page).toContain('SHA-256 <code>0123456789ab…</code>');
    for (const i of [1, 2]) expect(await volume(i)).not.toContain(fold); // 没有登记来源的本不显示
  });
});

describe('数据版', () => {
  it('所有版本在一页，各带自己的来源', async () => {
    const page = await data();
    for (const wid of ['w-a', 'w-b', 'w-c']) {
      expect(page).toContain(`id="w-${wid}"`);
      expect(page).toContain(`data-w="${wid}"`); // 目录里每个本都能切换
    }
    expect(page).toContain('id="q"');
    expect(count(page, '<span class="t">来源与授权</span>')).toBe(1); // 只有 w-a 登记了来源
    expect(page).not.toContain('id="sources"');
  });

  it('无属性的 <p> 只用于释文（字体子集按此区分释文与界面文字）', async () => {
    for (const page of [await data(), await volume(0), await cover()]) {
      expect(count(page, '<p>')).toBe(count(page, '<div class="u" '));
    }
  });

  it('面包屑的初始内容放在 data-base 里，脚本切换版本时还原再追加', async () => {
    const page = await data();
    expect(page).toContain('<nav class="crumb" id="crumb"');
    expect(page).toContain('<a href="/a/">典籍甲</a><span class="sep">›</span><span>数据版</span>');
  });
});

describe('真实数据', () => {
  it('首页是第一部典籍的封面；郭店楚简三个本在一个文件夹里，北大只有一个本', async () => {
    const { default: Home } = await import('../../src/pages/index.astro');
    const { default: Page } = await import('../../src/pages/[corpus]/[id].astro');
    expect(await render(Home)).toContain('<h1>道德经</h1>');
    const page = await render(Page, { params: { corpus: 'laozi', id: 'guodian-jia' } });
    expect(page).toContain('<details class="dir" data-g="guodian" open>');
    expect(page).toContain('data-g="mawangdui"');
    expect(page).not.toContain('data-g="beida"');
    expect(page).toContain('<b>甲组</b>');
  });
});
