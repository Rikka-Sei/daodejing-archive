import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { CATEGORIES, loadCorpus, type Corpus, type Kind } from '../../src/lib/corpus';
import { prefaceItems } from '../../src/lib/preface';
import { fixtureCorpus, tempDir } from './fixtures';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

describe('典籍的读取与分组', () => {
  let c: Corpus;
  // 每个用例用自己的一份，因为有的用例会改影像列表
  beforeAll(() => {
    c = fixtureCorpus(tmp.dir, 'base', { title: '占位书' });
  });

  it('每部文献带着自己的本', () => {
    expect(c.title).toBe('占位书');
    expect(c.groups.map((g) => [g.name, g.id, g.witnesses.map((w) => w.label), g.single])).toEqual([
      ['甲书', 'w', ['甲组', '乙组'], false],
      ['乙书', 'w-c', ['全本'], true],
    ]);
  });

  it('目录里用的名字', () => {
    expect(c.witnesses.map((w) => w.title)).toEqual(['甲书 甲组', '甲书 乙组', '乙书']);
  });

  it('合计', () => {
    expect(c.totals).toEqual([6, 3]);
    expect(c.groups[0].plates).toBe(3);
  });

  it('封面取图：先实物照片，再整页图版，最后单简图版', () => {
    const d = fixtureCorpus(tmp.dir, 'cover');
    const g = d.groups[0];
    expect(g.coverPlate()?.file).toBe('data/images/b1.jpg'); // 乙组有实物照片，优先于甲组的图版
    expect(d.groups[1].coverPlate()).toBeNull(); // 没有影像
    g.witnesses[1].plates.length = 0;
    expect(g.coverPlate()?.file).toBe('data/images/a2.jpg'); // 没有照片就取整页图版
    g.witnesses[0].plates.splice(1, 1);
    expect(g.coverPlate()?.file).toBe('data/images/a1.jpg');
  });

  it('文本单位对应的影像', () => {
    const w = c.witnesses[0];
    expect(w.byUnit.get('w-a.001')?.map((p) => p.file)).toEqual(['data/images/a1.jpg', 'data/images/a2.jpg']);
    expect(w.byUnit.get('w-a.002')).toBeUndefined();
  });

  it('版本的来源', () => {
    expect(c.sourcesOf(c.witnesses[0]).map((s) => s.id)).toEqual(['s', 't']);
    expect(c.sourcesOf(c.witnesses[1])).toEqual([]);
  });

  it('展示信息：参数优先，缺省有默认值', () => {
    const d = loadCorpus('plain', `${tmp.dir}/base`);
    expect(d.title).toBe('plain');
    expect(d.intro).toBe('释文照录来源，未经复核。');
    expect(d.licenseNote).toBe('各来源自身的声明见仓库中的来源记录。');
  });
});

describe('材料分类、对照资料与对读表', () => {
  let x: Corpus;
  beforeAll(() => {
    x = fixtureCorpus(tmp.dir, 'al', { chapter_parts: [{ title: '上篇', to: 1 }, { title: '下篇', to: 2 }] }, true, true);
  });

  it('版本的性质：登记表里没写 kind 的按出土本算', () => {
    expect(x.witnesses.map((w) => [w.id, w.kind])).toEqual([
      ['w-a', 'excavated'],
      ['w-b', 'excavated'],
      ['w-c', 'excavated'],
      ['w-t', 'transmitted'],
      ['jiaoding', 'edition'],
    ]);
  });

  it('文献按性质分类：出土文献一手，传世本与校订本一栏；没有版本的分类不列', () => {
    expect(x.categories.map((cat) => [cat.id, cat.title, cat.note, cat.groups.map((g) => g.name)])).toEqual([
      ['excavated', '出土文献', '一手', ['甲书', '乙书']],
      ['transmitted', '传世本与校订本', '', ['传世本', '校订本']],
    ]);
  });

  it('石刻与拓本是二手一栏，排在出土文献之后', () => {
    const dir = join(tmp.dir, 'rub');
    fixtureCorpus(tmp.dir, 'rub');
    const yaml = join(dir, 'witnesses.yaml');
    writeFileSync(yaml, readFileSync(yaml, 'utf-8').replace('{id: w-c, name: 乙书}', '{id: w-c, name: 乙书, kind: rubbing}'));
    const c = loadCorpus('rub', dir);
    expect(c.categories.map((cat) => [cat.id, cat.note, cat.groups.map((g) => g.name)])).toEqual([
      ['excavated', '一手', ['甲书']],
      ['rubbing', '二手', ['乙书']],
    ]);
  });

  it('每一种性质都归在某个分类里，不会有版本从侧栏上消失', () => {
    const kinds: Kind[] = ['excavated', 'rubbing', 'transmitted', 'edition'];
    for (const k of kinds) expect(CATEGORIES.filter((cat) => cat.kinds.includes(k)), k).toHaveLength(1);
  });

  it('对照资料：来源登记里写了 study: true 的', () => {
    expect(x.studies.map((s) => s.id)).toEqual(['u']);
    expect(x.studies[0].short).toBe('对照表');
    expect(fixtureCorpus(tmp.dir, 'nostudy').studies).toEqual([]);
  });

  it('读取对读表；阅读器的对象是有逐行释文的本', () => {
    expect(x.alignment?.chapters).toHaveLength(2);
    expect(x.readable.map((w) => w.id)).toEqual(['w-a']);
  });

  it('章节分篇取自展示信息；没有对读表的典籍这些都是空的', () => {
    expect(x.chapterParts).toEqual([{ title: '上篇', to: 1 }, { title: '下篇', to: 2 }]);
    const plain = fixtureCorpus(tmp.dir, 'noal');
    expect([plain.alignment, plain.chapterParts, plain.readable]).toEqual([null, [], []]);
  });
});

describe('凡例', () => {
  it('没给体例就用通用的，状态按数据补', () => {
    const items = prefaceItems(fixtureCorpus(tmp.dir, 'pf1'));
    expect(items[0]).toContain('释文照录来源，不改字');
    expect(items.join('')).toContain('只核对过一个来源'); // 全部 unverified
    expect(items.at(-1)).toContain('SHA-256');
  });

  it('自拟的体例取代通用的，状态说明仍在', () => {
    const items = prefaceItems(fixtureCorpus(tmp.dir, 'pf2', { preface: ['自拟的体例。'], preface_extra: ['追加。'] }));
    expect(items.slice(0, 2)).toEqual(['自拟的体例。', '追加。']);
    expect(items.join('')).not.toContain('释文照录来源，不改字');
    expect(items.at(-1)).toContain('SHA-256');
  });
});
