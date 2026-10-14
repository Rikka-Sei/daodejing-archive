/** 纯文本释文与 jsonl 数据下载。 */
import { readFileSync } from 'node:fs';
import type { Corpus, Group, Witness } from './corpus';
import { colophon, labelText, licenseLabel } from './text';

export const NOTE = '释文照录来源，未经复核。□ 表示残缺字；括号内为整理者的读法。';

/** 一个本的纯文本。level 为标题级别，合集里把各本降一级。 */
export function witnessTxt(corpus: Corpus, wit: Witness, level = 1): string {
  const h = '#'.repeat(level);
  const lines = [`${h} ${wit.meta.name}`, '', `> ${colophon(wit.meta)}`, '', NOTE, ''];
  for (const u of wit.units) lines.push(`[${labelText(u)}] ${u.text}`);
  lines.push('', `${h}# 来源`, '');
  for (const s of corpus.sourcesOf(wit)) {
    lines.push(`- ${s.title}（授权：${licenseLabel(s.license)}）${s.url ? ` ${s.url}` : ''}`);
  }
  return lines.join('\n') + '\n';
}

/** 一部文献下所有本的合集。 */
export function groupTxt(corpus: Corpus, group: Group): string {
  return [`# ${group.name}\n`, ...group.witnesses.map((w) => witnessTxt(corpus, w, 2))].join('\n');
}

/** 释文数据：与仓库里的 jsonl 逐字相同；没有源文件时按解析结果重写。 */
export function witnessJsonl(wit: Witness): string {
  const text = wit.file
    ? readFileSync(wit.file, 'utf-8')
    : wit.units.map((u) => JSON.stringify(u) + '\n').join('');
  return text.endsWith('\n') ? text : text + '\n';
}

export function groupJsonl(group: Group): string {
  return group.witnesses.map(witnessJsonl).join('');
}

/** 文本响应：UTF-8，不带 BOM。 */
export function textResponse(body: string, type = 'text/plain'): Response {
  return new Response(body, { headers: { 'Content-Type': `${type}; charset=utf-8` } });
}
