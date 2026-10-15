// 一章的对读表数据：<典籍>/chapters/<三位章号>.json，与仓库里 data/alignment/chapters/ 的文件逐字相同。阅读器按需读取。
import type { APIRoute, GetStaticPaths } from 'astro';
import { textResponse } from '../../../lib/downloads';
import { allCorpora, corpusById } from '../../../lib/site';

export const getStaticPaths = (() =>
  allCorpora().flatMap((c) =>
    (c.alignment?.chapters ?? []).map((ch) => ({ params: { corpus: c.id, n: String(ch.n).padStart(3, '0') } })),
  )) satisfies GetStaticPaths;

export const GET: APIRoute = ({ params }) => {
  const corpus = corpusById(params.corpus!);
  return textResponse(corpus.alignment!.chapterFiles[Number(params.n) - 1], 'application/json');
};
