/** 页面结构：用占位典籍渲染各个视图，检查封面、侧栏、本的页面、章节对读页、阅读器与对照资料页。 */
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { Corpus } from '../../src/lib/corpus';
import Chapter from '../../src/views/Chapter.astro';
import Cover from '../../src/views/Cover.astro';
import Preface from '../../src/views/Preface.astro';
import Reader from '../../src/views/Reader.astro';
import Study from '../../src/views/Study.astro';
import Volume from '../../src/views/Volume.astro';
import { fixtureCorpus, tempDir } from './fixtures';
import { count, render } from './render';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

let a: Corpus;
let b: Corpus;
let corpora: Corpus[];
/** 带对读表的占位典籍：出土本 w-a、w-b、w-c，传世本 w-t，校订本 jiaoding，一份对照资料 u */
let x: Corpus;
beforeAll(() => {
  a = fixtureCorpus(tmp.dir, 'a', { title: '典籍甲', subtitle: '甲乙', license_note: '占位授权说明' });
  b = fixtureCorpus(tmp.dir, 'b', { title: '典籍乙' });
  corpora = [a, b];
  x = fixtureCorpus(tmp.dir, 'x', { title: '典籍叉', chapter_parts: [{ title: '上篇', to: 1 }, { title: '下篇', to: 2 }] }, true, true);
});

const cover = (c = a, cs = corpora) => render(Cover, { props: { corpus: c, corpora: cs } });
const preface = (c = a, cs = corpora) => render(Preface, { props: { corpus: c, corpora: cs } });
const volume = (i: number, cs = corpora) => render(Volume, { props: { corpus: cs[0], wit: cs[0].witnesses[i], corpora: cs } });
const xVolume = (id: string) => render(Volume, { props: { corpus: x, wit: x.witness(id)!, corpora: [x] } });
const chapter = (n: number) => render(Chapter, { props: { corpus: x, corpora: [x], n } });
const reader = (id = 'w-a') => render(Reader, { props: { corpus: x, wit: x.witness(id)!, corpora: [x] } });
const study = () => render(Study, { props: { corpus: x, corpora: [x], source: x.studies[0] } });

describe('封面', () => {
  it('书名与开始阅读；没有对读表的典籍只有一个按钮', async () => {
    const page = await cover();
    expect(page).toContain('<h1>典籍甲</h1>');
    expect(page).toContain('<div class="eyebrow">甲乙</div>');
    expect(page).toContain('<div class="actions"><a class="btn pri" href="/a/w-a/">开始阅读</a></div>');
    expect(page).not.toContain('id="preface"'); // 凡例是单独一页
    expect(page).not.toContain('class="axis"');
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

  it('凡例按数据生成，是单独一页；侧栏里“凡例”选中，“封面”不选中', async () => {
    const page = await preface();
    expect(page).toContain('<h1>凡例</h1>');
    expect(page).toContain('<title>凡例 · 典籍甲</title>');
    expect(page).toContain('<a class="item on" href="/a/preface/">');
    expect(page).toContain('<a class="item" href="/a/">');
    expect((await cover()).toString()).toContain('<a class="item" href="/a/preface/">');
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

  it('封面不是宽栏，搜索框过滤侧栏目录', async () => {
    const page = await cover();
    expect(page).toContain('<div class="content">');
    expect(page).toContain('placeholder="筛选目录"');
  });
});

describe('封面（有对读表）', () => {
  it('第二个按钮去章节对读，数字里带上章数', async () => {
    const page = await cover(x, [x]);
    expect(page).toContain('<a class="btn pri" href="/x/w-a/">开始阅读</a><a class="btn" href="/x/chapters/1/">章节对读</a>');
    expect(page).toContain('<div class="stats">5 个版本 · 10 条释文 · 3 张影像 · 2 章逐字对读</div>');
  });

  it('按材料的性质分类：出土文献标“一手”，传世本与校订本没有影像、写成文字行', async () => {
    const page = await cover(x, [x]);
    expect(page).toContain('<h2>出土文献<span class="note">一手</span></h2>');
    expect(count(page, '<article class="doc">')).toBe(2); // 出土文献的两部文献有卡片
    expect(page).toContain('<h2>传世本与校订本</h2><div class="rows"><a class="row" href="/x/w-t/">');
    expect(page).toContain('<span class="t">校订本</span><span class="m">2 条释文</span>');
    expect(page).not.toContain('石刻与拓本'); // 没有这一类版本，不列空分类
  });

  it('论文与对照资料另成一类，写出处与授权', async () => {
    const page = await cover(x, [x]);
    expect(page).toContain('<h2>论文与对照资料</h2>');
    expect(page).toContain('<a class="row" href="/x/study/u/"><span class="bd"><span class="t">对照表</span><span class="m">占位出版者 · 2026 · CC0</span>');
    expect(await cover()).not.toContain('论文与对照资料');
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

  it('搜索框的提示：本页有释文时搜释文，其余页面筛选目录', async () => {
    expect(await volume(0)).toContain('placeholder="搜索本页释文"');
    expect(await cover()).toContain('placeholder="筛选目录"');
    expect(await volume(0)).toContain('id="q"');
  });

  it('没有对读表的典籍：只有材料一栏，没有“材料｜章节”切换', async () => {
    const page = await volume(0);
    expect(page).toContain('data-pane="m"');
    expect(page).not.toContain('data-pane="c"');
    expect(page).not.toContain('class="axis"');
  });

  it('有对读表：材料与章节两条轴，封面停在材料，章节页停在章节', async () => {
    const page = await cover(x, [x]);
    expect(page).toContain('<aside id="side" data-axis="m">');
    expect(page).toContain('<button type="button" data-axis="m" aria-pressed="true">材料</button>');
    expect(page).toContain('<button type="button" data-axis="c" aria-pressed="false">章节</button>');
    const ch = await chapter(1);
    expect(ch).toContain('<aside id="side" data-axis="c">');
    expect(ch).toContain('<button type="button" data-axis="c" aria-pressed="true">章节</button>');
  });

  it('材料一栏：按分类列文献，再列论文与对照资料；当前的对照资料标出', async () => {
    const page = await cover(x, [x]);
    expect(page).toContain('<div class="sb-label">出土文献<span class="note">· 一手</span></div>');
    expect(page).toContain('<div class="sb-label">传世本与校订本</div>');
    expect(page).toContain('<div class="sb-label">论文与对照资料</div>');
    expect(page).toContain('<a class="item" href="/x/study/u/">');
    expect(await study()).toContain('<a class="item on" href="/x/study/u/">');
  });

  it('章节一栏：按配置分篇，每章带标题和各出土本有没有这一章的圆点', async () => {
    const page = await cover(x, [x]);
    expect(page).toContain('<span class="t">上篇</span><span class="rng">1–1 章</span>');
    expect(page).toContain('<span class="t">下篇</span><span class="rng">2–2 章</span>');
    expect(page).toContain('<a class="item ch" href="/x/chapters/1/" data-n="1" data-t="甲乙丙">');
    expect(page).not.toContain('圆点依次是'); // 圆点的含义悬停看，不在栏里写说明
    expect(page).not.toContain('依王弼本分章');
    expect(page).toContain('<span class="dots" title="甲组 有；乙组 有"><i class="on"></i><i class="on"></i></span>');
    expect(page).toContain('<span class="dots" title="甲组 有；乙组 无"><i class="on"></i><i></i></span>'); // 第 2 章没有 w-b
  });

  it('没有配置分篇时章节不分篇', async () => {
    const c = fixtureCorpus(tmp.dir, 'nopart', {}, true, true);
    const page = await cover(c, [c]);
    expect(page).toContain('<span class="t">全部</span><span class="rng">1–2 章</span>');
  });

  it('当前章在章节一栏里标出', async () => {
    const page = await chapter(2);
    expect(page).toContain('<a class="item ch on" href="/x/chapters/2/" data-n="2" data-t="乙丙丁戊" aria-current="page">');
    expect(count(page, 'class="item ch on"')).toBe(1);
  });
});

describe('本的页面', () => {
  it('页面标题与描述', async () => {
    const page = await volume(1);
    expect(page).toContain('<title>甲书《占位》乙组 · 典籍甲</title>');
    expect(page).toContain('<meta name="description" content="甲书《占位》乙组的释文与影像">');
  });

  it('每个页面都有内联图标，免得浏览器去请求 /favicon.ico', async () => {
    for (const page of [await cover(), await volume(0), await chapter(1), await reader(), await study()]) {
      expect(page).toContain('<link rel="icon" href="data:image/svg+xml,%3Csvg');
    }
  });

  it('提前加载字体，字体族由 @font-face 声明', async () => {
    const page = await volume(0);
    expect(page).toContain('<link rel="preload" href="/fonts/noto-sans-sc-400.woff2" as="font" type="font/woff2" crossorigin>');
    expect(page).toContain('font-family:"DG Serif"');
    expect(page).toContain('font-family:"DG Ext"'); // 造字与生僻字的补充字体，用到才下载
  });

  it('有释文的页面用宽栏，三个开关齐全', async () => {
    const page = await volume(0);
    expect(page).toContain('<div class="content wide">');
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

  it('无属性的 <p> 只用于释文（字体子集按此区分释文与界面文字）', async () => {
    for (const page of [await volume(0), await cover()]) {
      expect(count(page, '<p>')).toBe(count(page, '<div class="u" '));
    }
    expect(count(await reader(), '<p>')).toBe(3); // 阅读器：每简一个
    expect(count(await study(), '<p>')).toBe(0); // 对照资料页的说明文字都是界面文字
    expect(count(await cover(x, [x]), '<p>')).toBe(0);
  });
});

describe('本的页面（有对读表）', () => {
  it('只有带逐行释文的本才有阅读器入口', async () => {
    expect(await xVolume('w-a')).toContain('<a class="btn" href="/x/w-a/read/">阅读器</a>');
    expect(await xVolume('w-b')).not.toContain('阅读器'); // 在对读表里，但没有逐行释文
    expect(await xVolume('jiaoding')).not.toContain('阅读器'); // 以章为单位，用章节页读
  });

  it('以章为单位的释文每条带“对读”链接，竹简帛书没有', async () => {
    const page = await xVolume('jiaoding');
    expect(page).toContain('<a class="cmp" href="/x/chapters/1/">对读</a>');
    expect(page).toContain('<a class="cmp" href="/x/chapters/2/">对读</a>');
    expect(count(await xVolume('w-a'), 'class="cmp"')).toBe(0);
    expect(count(await volume(2), 'class="cmp"')).toBe(0); // 没有对读表的典籍
  });

  it('对照资料也算这个本的来源', async () => {
    expect(await xVolume('w-a')).toContain('《占位对照表》');
  });
});

describe('章节对读页', () => {
  it('标题、面包屑、开头一段取校订本的释文（去掉句序记号），样式与脚本', async () => {
    const page = await chapter(1);
    expect(page).toContain('<title>第 1 章 · 典籍叉</title>');
    expect(page).toContain('<meta name="description" content="第 1 章在各本中的逐字对读：甲乙丙">');
    expect(page).toContain('<a href="/x/">典籍叉</a><span class="sep">›</span><span>章节对读</span><span class="sep">›</span><b>第 1 章</b>');
    expect(page).toContain('<h1>第 1 章</h1>');
    expect(page).toContain('<div class="lead cn"><p>甲乙，丙丁。</p></div>');
    expect(page).toContain('src="/src/scripts/align.js"');
    expect(page).not.toContain('reader.js');
  });

  it('每个版本一行，行首是简称，校订本在最上', async () => {
    const page = await chapter(1);
    const rows = [...page.matchAll(/<tr data-v="([^"]+)"><th scope="row">([^<]+)<\/th>/g)].map((m) => [m[1], m[2]]);
    expect(rows).toEqual([['jiaoding', '校订'], ['w-t', '传世'], ['w-a', '甲组'], ['w-b', '乙组']]);
    expect(count(page, '<table class="al"')).toBe(1); // 6 列，一段就够
    expect(page).toContain('<table class="al" style="--n:6">');
  });

  it('“通行”一行：各本相同的列写共用通行字，用字不同的列写 ≠', async () => {
    const page = await chapter(1);
    const row = /<tr class="sh">(.*?)<\/tr>/s.exec(page)![1];
    expect([...row.matchAll(/<td(?: class="ne")?>\s*<p>([^<]*)<\/p>/g)].map((m) => m[1])).toEqual(['甲', '乙', '≠', '丁', '≠', '己']);
    expect(count(row, 'class="ne"')).toBe(2);
    // 第 1 列：丑通行字乙，视同相等，所以仍有共用通行字
    expect(count(await chapter(2), 'class="ne"')).toBe(1);
  });

  it('格子：与校订本同字不着色，写法不同的浅底，用字不同的着色；缺字、脱文、空格各有样式', async () => {
    const page = await chapter(1);
    expect(page).toContain('<td class="text var" data-col="1" title="甲组 · 通行字 乙"><p><span>丑</span><sup class="r">乙</sup></p></td>');
    expect(page).toContain('<td class="text diff" data-col="4" title="传世"><p><span>庚</span></p></td>');
    expect(page).toContain('<td class="text diff f-can" data-col="2" title="乙组 · 残字">');
    expect(page).toContain('<td class="miss" data-col="4" title="甲组">');
    expect(page).toContain('<td class="tuo" data-col="4" title="乙组 · 脱文"></td>');
    expect(page).toContain('<td class="b" data-col="3" title="甲组"></td>');
    expect(page).toContain('<td id="c2" class="text" data-col="2" title="校订"><p><span>丙</span><i class="p">，</i></p></td>'); // 校订本的断句
  });

  it('格子的提示写明简号或行号的末尾；列号 id 只给校订本这一行（供地址里的 #c<列> 用）', async () => {
    const page = await chapter(1);
    expect(page).toContain('title="甲组 · 简 1 的末尾"');
    expect([...page.matchAll(/\bid="c(\d+)"/g)].map((m) => m[1])).toEqual(['0', '1', '2', '3', '4', '5']);
  });

  it('造字序列换成补充字体里的码位', async () => {
    const page = await chapter(2);
    expect(page).toContain(''); // 〚⿰甲乙〛 → U+E000
    expect(page).not.toContain('〚⿰甲乙〛');
  });

  it('在底本里的位置：竹简帛书的简号链到阅读器；没有逐行释文的本不列', async () => {
    const page = await chapter(1);
    expect(page).toContain('<dt>甲组</dt><dd>简 <a href="/x/w-a/read/#l-1">1</a>、<a href="/x/w-a/read/#l-2">2</a></dd>');
    expect(page).not.toContain('<dt>乙组</dt>');
    expect(page).not.toContain('<dt>传世</dt>');
  });

  it('尾注：有才有，并注明抄自来源', async () => {
    expect(await chapter(1)).toContain('<section class="notes"><h2>尾注</h2><div class="note">占位尾注</div>');
    expect(await chapter(2)).not.toContain('尾注');
  });

  it('上一章、下一章：第一章没有上一章，最后一章没有下一章', async () => {
    const first = await chapter(1);
    expect(first).toContain('<a class="next" href="/x/chapters/2/"><small>下一章 · 第 2 章</small>乙丙丁戊</a>');
    expect(first).not.toContain('上一章');
    const last = await chapter(2);
    expect(last).toContain('<a class="prev" href="/x/chapters/1/"><small>上一章 · 第 1 章</small>甲乙丙</a>');
    expect(last).not.toContain('下一章');
  });

  it('长的一章分成几段，每段一张表', async () => {
    const c = fixtureCorpus(tmp.dir, 'long', {}, true, true);
    const ch = c.alignment!.chapter(1);
    const widen = (n: number) => ch.rows.forEach((r) => (r.cells = Array.from({ length: n }, (_, i) => r.cells[i % r.cells.length])));
    widen(45);
    ch.columns = 45;
    const page = await render(Chapter, { props: { corpus: c, corpora: [c], n: 1 } });
    expect(count(page, '<table class="al"')).toBeGreaterThan(1);
    expect([...page.matchAll(/<table class="al" style="--n:(\d+)">/g)].map((m) => Number(m[1])).reduce((s, n) => s + n, 0)).toBe(45);
  });
});

describe('阅读器', () => {
  it('标题、面包屑、竖排阅读区的数据属性', async () => {
    const page = await reader();
    expect(page).toContain('<title>甲书《占位》甲组 · 阅读器 · 典籍叉</title>');
    expect(page).toContain('<a href="/x/w-a/">甲组</a><span class="sep">›</span><b>阅读器</b>');
    expect(page).toContain('data-chapters="/x/chapters/" data-meta="/x/alignment.json" data-w="w-a"');
    expect(page).toContain('<body class="rdr">');
    expect(page).toContain('<div class="content wide reader">');
    expect(page).toContain('src="/src/scripts/reader.js"');
    expect(page).not.toContain('align.js');
  });

  it('每简一列，每个字带“章.列”；跨章的简在每章开头有章次标记', async () => {
    const page = await reader();
    expect(count(page, 'class="rl"')).toBe(3);
    expect(page).toContain('<span class="c" data-k="1.0">甲</span><span class="c" data-k="1.1">丑</span><span class="c" data-k="1.2">丙</span>');
    expect(count(page, 'class="cm"')).toBe(4); // 第 1 简一章，第 2 简两章，第 3 简一章
    expect(page).toContain('<a class="cm" href="/x/chapters/2/" data-n="2" aria-label="第 2 章"></a><span class="c" data-k="2.0">乙</span>');
  });

  it('缺字、残字有样式，造字序列换成补充字体里的码位', async () => {
    const page = await reader();
    expect(page).toContain('<span class="c d-missing" data-k="1.4">□</span>');
    expect(page).toContain('<span class="c d-part" data-k="2.2">丁</span>');
    expect(page).toContain('<span class="c" data-k="2.3"></span>');
  });

  it('单简图版挂在对应的简下', async () => {
    const page = await reader();
    expect(page).toContain('<a class="plate" href="https://raw.githubusercontent.com/Rikka-Sei/daodejing-archive/main/data/images/a1.jpg"');
    expect(page).toContain('<img loading="lazy" src="/x/thumbs/a1.jpg" alt="简 1图版">');
    expect(count(page, 'class="plate"')).toBe(1);
  });

  it('透视浮层与专注模式的按钮；顶栏是阅读器的一组开关', async () => {
    const page = await reader();
    expect(page).toContain('<div id="lens" class="lens" role="dialog" aria-label="透视" hidden></div>');
    expect(page).toContain('id="unfocus"');
    expect(page).toContain('id="focus"');
    for (const k of ['rsize', 'plates', 'theme']) expect(page).toContain(`data-k="${k}"`);
    expect(page).not.toContain('data-k="layout"'); // 阅读器永远是竖排
  });

  it('侧栏停在材料一栏，当前本标出', async () => {
    const page = await reader();
    expect(page).toContain('<aside id="side" data-axis="m">');
    expect(page).toContain('class="item leaf on"><a class="lk" href="/x/w-a/" aria-current="page">');
  });
});

describe('对照资料页', () => {
  it('标题、来源与授权、本站用了它什么', async () => {
    const page = await study();
    expect(page).toContain('<title>对照表 · 典籍叉</title>');
    expect(page).toContain('<h1>《占位对照表》</h1>');
    expect(page).toContain('<span class="t">来源与授权</span><span class="m">占位出版者 · 2026 · CC0</span>');
    // 它覆盖的各本，以及整张对读表（章数取自数据）
    for (const href of ['/x/w-a/', '/x/w-b/', '/x/jiaoding/']) expect(page).toContain(`<a class="row" href="${href}">`);
    expect(page).toContain('<span class="t">2 章对读表</span>');
  });

  it('它自己的概述、凡例与参考书目照录', async () => {
    const page = await study();
    expect(page).toContain('<p class="plain">占位概述一。</p>');
    expect(page).toContain('<h2>占位凡例</h2><p class="plain">占位凡例段。</p>');
    expect(page).toContain('<ol class="refs"><li>占位书目一.</li><li>占位书目二.</li></ol>');
    expect(page).toContain('以上文字抄自 tt24h 的原表（CC0）');
  });

  it('没有对读表时不写对读表那一行', async () => {
    const c = fixtureCorpus(tmp.dir, 'bare', {}, true, true);
    c.alignment = null;
    const page = await render(Study, { props: { corpus: c, corpora: [c], source: c.studies[0] } });
    expect(page).not.toContain('章对读表');
    expect(page).not.toContain('参考书目');
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
    expect(page).toContain('<a class="btn" href="/laozi/guodian-jia/read/">阅读器</a>');
  });

  it('侧栏分类：出土文献一手，传世本与校订本、论文与对照资料各自成栏', async () => {
    const { default: Home } = await import('../../src/pages/index.astro');
    const page = await render(Home);
    expect(page).toContain('<div class="sb-label">出土文献<span class="note">· 一手</span></div>');
    expect(page).toContain('<div class="sb-label">传世本与校订本</div>');
    expect(page).toContain('<div class="sb-label">论文与对照资料</div>');
    expect(page).toContain('<span class="t">道经</span><span class="rng">1–37 章</span>');
    expect(page).toContain('<span class="t">德经</span><span class="rng">38–81 章</span>');
    expect(count(page, 'class="item ch"')).toBe(81);
  });
});
