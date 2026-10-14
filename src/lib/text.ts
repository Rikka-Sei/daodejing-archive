/** 分组命名、识语、标签与残缺标注。纯函数，不读写文件。 */
import { esc } from './html';
import type { Damage, Meta, Unit } from './types';

/** 数量后面：39 枚简、81 章 */
export const UNIT_WORD: Record<string, string> = { slip: '枚简', 'silk-line': '行', chapter: '章' };
/** 单说一个单位：跳转到简 */
export const UNIT_NOUN: Record<string, string> = { slip: '简', 'silk-line': '行', chapter: '章' };

/** [前缀, 编号, 后缀]：简 1 / 第 38 章。编号单独返回，竖排时可做数字并排。 */
export function unitLabel(u: Unit): [string, string | number, string] {
  if (u.unit_type === 'chapter') return ['第', u.unit_no, '章'];
  return [u.unit_type === 'slip' ? '简' : '行', u.unit_no, ''];
}

export function labelText(u: Unit): string {
  const [pre, no, suf] = unitLabel(u);
  return `${pre}${no}${suf}`;
}

/** 一组版本 id 的共同前缀（去掉结尾的连字符）：guodian-jia、guodian-yi → guodian。无共同前缀时取第一个 id。 */
export function commonId(ids: string[]): string {
  let prefix = ids[0];
  if (ids.length > 1) {
    for (const s of ids.slice(1)) {
      let i = 0;
      while (i < prefix.length && i < s.length && prefix[i] === s[i]) i++;
      prefix = prefix.slice(0, i);
    }
  }
  return prefix.replace(/[-_.]+$/, '') || ids[0];
}

/** 版本名拆成 [文献名, 本名]：“郭店楚简《老子》甲组” → [“郭店楚简”, “甲组”]；无后缀时本名为“全本”。 */
export function splitName(name: string): [string, string] {
  const m = /^([^《]*)《[^》]*》(.*)$/.exec(name);
  if (!m) return [name, '全本'];
  const group = m[1].trim();
  const suffix = m[2].trim();
  return [group || name, suffix || '全本'];
}

export const LICENSE_STATUS: Record<string, string> = {
  'public-domain': '来源未标明，按可收录处理',
  cc: '知识共享',
  'all-rights-reserved': '保留所有权利',
  'permission-granted': '已获许可',
  unknown: '来源未标明',
};

/** 授权的一句话：登记了名字（如 CC BY-SA 4.0）就用名字，没有就按状态说。 */
export function licenseLabel(lic?: Meta | null): string {
  const l = lic ?? {};
  return l.name || LICENSE_STATUS[l.status] || '来源未标明';
}

/** 折叠收起时的授权概要：各来源授权名去重（一个来源写了几种授权时拆开），没登记名字的记作“未标明”。 */
export function licenseBrief(sources: Meta[]): string {
  const names: string[] = [];
  for (const s of sources) {
    const name = s.license?.name;
    for (const t of name ? String(name).split('；') : ['未标明']) {
      if (!names.includes(t)) names.push(t);
    }
  }
  return names.join('、');
}

const filled = (o?: Meta | null): boolean => !!o && Object.keys(o).length > 0;

/** 把登记表里的事实写成一段识语，而不是字段表。 */
export function colophon(w: Meta): string {
  const ex = w.excavated ?? {};
  const parts: string[] = [];
  if (ex.year) parts.push(`${ex.year}年${ex.month ? `${ex.month}月` : ''}出土于${ex.place || ''}`);
  else if (ex.place) parts.push(ex.place);
  const de = w.date_estimate?.text;
  if (de) parts.push(de);
  const sl = w.slips ?? {};
  if (sl.count) parts.push(`存简${sl.count}枚`);
  const pub = w.published;
  if (filled(pub)) parts.push(`${pub.year}年收入《${pub.title}》（${pub.publisher}）`);
  const hold = w.holder?.name;
  if (hold) parts.push(`现藏${hold}`);
  return parts.join('；') + '。';
}

/** 版本登记表里的事实，按研究者常看的顺序列成 [标签, 值]。 */
export function facts(w: Meta): [string, string][] {
  const ex = w.excavated ?? {};
  const when = ex.year ? `${ex.year} 年${ex.month ? ` ${ex.month} 月` : ''}` : '';
  const sl = w.slips ?? {};
  const pub = w.published;
  const rows: [string, string][] = [
    ['材质', [w.medium, w.script].filter(Boolean).join(' · ')],
    ['出土 / 入藏', [when, ex.place].filter(Boolean).join(' · ')],
    ['年代', w.date_estimate?.text || ''],
    ['简数', sl.count ? `${sl.count} 枚` : ''],
    ['篇章', w.chapter_order?.text || w.scope || ''],
    ['出版', filled(pub) ? `《${pub.title}》，${pub.publisher}，${pub.year}` : ''],
    ['现藏', w.holder?.name || ''],
  ];
  return rows.filter(([, v]) => v);
}

/** 按码点区间给残缺处加样式，其余原样转义。注意 JS 字符串按 UTF-16 编码单元计数，所以先拆成码点。 */
export function markDamage(text: string, damage?: Damage[] | null): string {
  const chars = Array.from(text);
  const flags: (string | null)[] = new Array(chars.length).fill(null);
  for (const d of damage ?? []) {
    for (let i = d.start; i < Math.min(d.end, chars.length); i++) flags[i] = d.kind;
  }
  const out: string[] = [];
  let i = 0;
  while (i < chars.length) {
    let j = i;
    while (j < chars.length && flags[j] === flags[i]) j++;
    const seg = esc(chars.slice(i, j).join(''));
    out.push(flags[i] ? `<span class="d-${flags[i]}">${seg}</span>` : seg);
    i = j;
  }
  return out.join('');
}
