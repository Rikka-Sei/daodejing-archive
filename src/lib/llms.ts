/** llms.txt 与 llms-full.txt（https://llmstxt.org 格式）。 */
import type { Corpus } from './corpus';
import { witnessTxt } from './downloads';
import { colophon, UNIT_WORD } from './text';
import { REPO_URL } from './url';

/** base 为站点的绝对地址（可空）；空时链接写相对地址，相对 llms.txt 所在的站点根。 */
export function llmsTxt(corpora: Corpus[], base = ''): { short: string; full: string } {
  const link = (rel: string) => (base ? `${base}/${rel}` : rel);
  const title = corpora.length === 1 ? corpora[0].title : '典籍';
  const head = [
    `# ${title}`,
    '',
    '> 典籍的释文、影像索引与来源登记。释文照录来源，未经复核；每条文本可追溯到登记了 SHA-256 的原始文件。',
    '',
    '释文中 □ 表示残缺字；括号内为整理者的读法；符号照抄来源。授权与来源见各本页面顶部的“来源与授权”。',
    '',
  ];
  const lines = [...head];
  const full = [...head];
  for (const c of corpora) {
    const heading = corpora.length > 1 ? c.title : '版本';
    lines.push(`## ${heading}`, '', `${c.subtitle}。`, '');
    full.push(`## ${heading}`, '');
    for (const wit of c.witnesses) {
      const n = wit.units.length;
      lines.push(`- [${wit.meta.name}](${link(`${c.id}/${wit.id}.txt`)}): ${n}${UNIT_WORD[wit.units[0].unit_type]}。${colophon(wit.meta)}`);
      full.push(witnessTxt(c, wit, 3));
    }
    lines.push('', `- [${c.title}（网页）](${link(`${c.id}/`)}): 封面、目录，每本一页，释文可横排或竖排`);
    lines.push(`- [凡例](${link(`${c.id}/preface/`)}): 收录与呈现的体例`);
    if (c.alignment) {
      const n = c.alignment.chapters.length;
      lines.push(
        `- [章节对读](${link(`${c.id}/chapters/1/`)}): ${n} 章，各本同列逐字对读；每章的对读表数据是 ${link(`${c.id}/chapters/001.json`)} 起的 JSON`,
      );
      for (const s of c.studies) lines.push(`- [${s.short ?? s.title}](${link(`${c.id}/study/${s.id}/`)}): 对照资料的说明与本站用到的部分`);
    }
    lines.push('');
  }
  lines.push(
    '## Optional',
    '',
    `- [完整释文合集](${link('llms-full.txt')}): 全部典籍的释文，单个文本文件`,
    `- [数据仓库](${REPO_URL}): 原始文件、元数据与校验脚本`,
    '',
  );
  return { short: lines.join('\n'), full: full.join('\n') };
}
