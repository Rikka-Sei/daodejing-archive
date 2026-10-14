/** 本站收录的典籍。新增一部典籍：在 src/config/ 加一份展示信息，再把它列进下面的 SOURCES。 */
import { parse } from 'yaml';
import laozi from '../config/laozi.yaml?raw';
import { loadCorpus, type Corpus } from './corpus';

/** [典籍 id, 数据目录, 展示信息（标题、副题、简介、凡例、授权说明）] */
const SOURCES: [string, string, string][] = [['laozi', 'data', laozi]];

let cache: Corpus[] | undefined;

/** 构建时读一次就够；本地预览（dev）每次重读，改了 data/ 刷新页面就能看到。 */
export function allCorpora(): Corpus[] {
  const load = () => SOURCES.map(([id, dir, meta]) => loadCorpus(id, dir, parse(meta)));
  if (import.meta.env.DEV) return load();
  return (cache ??= load());
}

export function corpusById(id: string): Corpus {
  const c = allCorpora().find((x) => x.id === id);
  if (!c) throw new Error(`没有这部典籍：${id}`);
  return c;
}
