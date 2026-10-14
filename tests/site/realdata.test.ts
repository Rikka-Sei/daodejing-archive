/** 本仓库 data/ 里的真实数据：站点依赖的结构上的约定。字句内容不在这里测。 */
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { allCorpora } from '../../src/lib/site';

const c = allCorpora()[0];
const rows = (file: string) => readFileSync(file, 'utf-8').split('\n').filter((l) => l.trim());

describe('真实数据', () => {
  it('文献与各自的本', () => {
    expect(c.groups.map((g) => [g.name, g.id, g.witnesses.map((w) => w.id)])).toEqual([
      ['郭店楚简', 'guodian', ['guodian-jia', 'guodian-yi', 'guodian-bing']],
      ['马王堆帛书', 'mawangdui', ['mawangdui-jia', 'mawangdui-yi']],
      ['北京大学藏西汉竹书', 'beida', ['beida']],
    ]);
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

  it('文献都有封面图，封面图在影像里', () => {
    for (const g of c.groups) {
      const cover = g.coverPlate();
      expect(cover, g.name).not.toBeNull();
      expect(g.witnesses.some((w) => w.plates.includes(cover!))).toBe(true);
    }
  });
});
