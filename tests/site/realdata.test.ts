/** 本仓库 data/ 里的真实数据：站点依赖的结构上的约定。字句内容不在这里测。 */
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'yaml';
import { describe, expect, it } from 'vitest';
import { CATEGORIES } from '../../src/lib/corpus';
import { allCorpora } from '../../src/lib/site';

const c = allCorpora()[0];
const rows = (file: string) => readFileSync(file, 'utf-8').split('\n').filter((l) => l.trim());

describe('真实数据', () => {
  it('文献与各自的本', () => {
    expect(c.groups.map((g) => [g.name, g.id, g.witnesses.map((w) => w.id)])).toEqual([
      ['郭店楚简', 'guodian', ['guodian-jia', 'guodian-yi', 'guodian-bing']],
      ['马王堆帛书', 'mawangdui', ['mawangdui-jia', 'mawangdui-yi']],
      ['北京大学藏西汉竹书', 'beida', ['beida']],
      ['王弼本', 'wangbi', ['wangbi']],
      ['校订本（tt24h）', 'jiaoding', ['jiaoding']],
    ]);
  });

  it('版本登记表里每个版本都写明了材料的性质，侧栏按它分类', () => {
    const reg = parse(readFileSync('data/witnesses.yaml', 'utf-8')).witnesses as { id: string; kind?: string }[];
    const known = CATEGORIES.flatMap((cat) => cat.kinds as string[]);
    for (const w of reg) expect(known, `${w.id} 的 kind`).toContain(w.kind);
    expect(c.categories.map((cat) => [cat.id, cat.groups.map((g) => g.id)])).toEqual([
      ['excavated', ['guodian', 'mawangdui', 'beida']],
      ['transmitted', ['wangbi', 'jiaoding']],
    ]);
  });

  it('王弼本与校订本各 81 章，章号 1–81 依次排列', () => {
    for (const id of ['wangbi', 'jiaoding']) {
      const w = c.witness(id)!;
      expect(w.units.map((u) => [u.unit_type, String(u.unit_no)]), id).toEqual(Array.from({ length: 81 }, (_, i) => ['chapter', String(i + 1)]));
    }
  });

  it('展示信息取自 src/config', () => {
    expect([c.id, c.title]).toEqual(['laozi', '道德经']);
    expect(c.subtitle).toBeTruthy();
    expect(c.preface).toHaveLength(7);
  });

  it('释文与影像的合计与数据文件逐行相符', () => {
    const units = c.witnesses.reduce((n, w) => n + rows(join('data/witnesses', `${w.id}.jsonl`)).length, 0);
    const plates = c.witnesses.reduce((n, w) => {
      const f = join('data/plates', `${w.id}.jsonl`);
      return n + (existsSync(f) ? rows(f).length : 0);
    }, 0);
    expect(c.totals).toEqual([units, plates]);
  });

  it('登记的每个本都有释文文件，释文目录里没有没登记的', () => {
    const files = readdirSync('data/witnesses').filter((f) => f.endsWith('.jsonl')).map((f) => f.replace('.jsonl', ''));
    expect(files.sort()).toEqual(c.witnesses.map((w) => w.id).sort());
  });

  it('条目 id 在全站唯一（它们是页面里的锚点）', () => {
    const ids = c.witnesses.flatMap((w) => w.units.map((u) => u.id));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('每张影像的文件都存在，指向的条目都在本里', () => {
    for (const w of c.witnesses) {
      const unitIds = new Set(w.units.map((u) => u.id));
      for (const p of w.plates) {
        expect(existsSync(p.file), p.file).toBe(true);
        for (const id of p.units) expect(unitIds.has(id), `${w.id}: ${id}`).toBe(true);
      }
    }
  });

  it('残缺标注的区间落在文字范围内', () => {
    for (const w of c.witnesses) {
      for (const u of w.units) {
        const n = Array.from(u.text).length;
        for (const d of u.damage ?? []) expect(d.start >= 0 && d.start < d.end && d.end <= n, `${u.id}`).toBe(true);
      }
    }
  });

  it('出土文献都有封面图，封面图在影像里；没有影像的传世本与校订本封面上写成文字行', () => {
    for (const cat of c.categories) {
      for (const g of cat.groups) {
        const cover = g.coverPlate();
        if (cat.id === 'excavated') expect(cover, g.name).not.toBeNull();
        if (cover) expect(g.witnesses.some((w) => w.plates.includes(cover)), g.name).toBe(true);
      }
    }
    expect(c.categories.find((cat) => cat.id === 'transmitted')!.groups.some((g) => g.coverPlate())).toBe(false);
  });

  it('章节目录的分篇覆盖全部章，最后一篇到最后一章', () => {
    const tos = c.chapterParts.map((p) => p.to);
    expect(tos).toEqual([...tos].sort((a, b) => a - b));
    expect(tos.at(-1)).toBe(c.alignment!.chapters.length);
  });
});

describe('真实数据：对读表与对照资料', () => {
  const al = c.alignment!;

  it('对读表里的每个版本都是登记过的版本', () => {
    for (const v of al.versions) expect(c.witness(v.id), v.id).toBeDefined();
  });

  it('data/alignment/ 里的每个逐行释文文件都属于对读表里的版本', () => {
    const files = readdirSync('data/alignment/lines').map((f) => f.replace('.jsonl', ''));
    const ids = al.versions.map((v) => v.id);
    for (const f of files) expect(ids, f).toContain(f);
  });

  it('可读的本都有单简或整行的编号，阅读器里的编号在本页内唯一（它们是页面里的锚点）', () => {
    for (const w of c.readable) {
      const nos = al.lines.get(w.id)!.map((l) => l.no);
      expect(new Set(nos).size, w.id).toBe(nos.length);
    }
  });

  it('对照资料：来源登记里写了 study 的那份，它覆盖的本都登记过', () => {
    expect(c.studies.map((s) => s.id)).toEqual(['tt24h-daodejing']);
    for (const s of c.studies) {
      expect(s.short ?? s.title).toBeTruthy();
      for (const id of s.witnesses as string[]) expect(c.witness(id), `${s.id}: ${id}`).toBeDefined();
    }
  });

  it('补充字体及其授权文本已登记为原始文件', () => {
    const tt = c.sources.find((s) => s.id === 'tt24h-daodejing')!;
    const paths = (tt.retrieval.files as { path: string }[]).map((f) => f.path);
    for (const p of ['DaoDeJingExt-Light.ttf', 'LICENSE-OFL', 'LICENSE-CC0']) expect(paths).toContain(`data/raw/tt24h-daodejing/v0.1.3/${p}`);
  });
});
