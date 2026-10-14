import type { Corpus } from './corpus';

export const GENERIC_PREFACE = [
  '释文照录来源，不改字，不校勘：通假字、异体字、隶定字形和符号都保持原样。',
  '灰色为残缺字，括号内为整理者的读法；点选图版缩略图可看原图。',
  '各本的版本信息、来源与授权，收在该本页面顶部的折叠栏里；侧栏目录每一项右侧的“⋯”可下载释文与数据。',
];

/**
 * 凡例：体例部分取 corpus 的 preface，没有就用通用的，再追加 preface_extra；
 * 释文是否复核、能否追溯，是数据的状态，由这里按数据补在最后。
 */
export function prefaceItems(c: Corpus): string[] {
  const items = [...(c.preface.length ? c.preface : GENERIC_PREFACE), ...c.prefaceExtra];
  const total = c.totals[0];
  const pending = c.witnesses.reduce((n, w) => n + w.units.filter((u) => u.status !== 'double-checked').length, 0);
  if (pending === total) items.push('全部释文目前只核对过一个来源，尚未经第二个独立来源复核，引用前请对照影像或原书。');
  else if (pending) items.push(`其中 ${pending} 条释文尚未经第二个独立来源复核。`);
  items.push('每条释文都能追溯到登记了 SHA-256 的原始文件。');
  return items;
}
