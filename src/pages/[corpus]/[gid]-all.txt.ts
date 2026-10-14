// 有多个本的文献的纯文本合集：<典籍>/<文献>-all.txt
import type { APIRoute, GetStaticPaths } from 'astro';
import { groupTxt, textResponse } from '../../lib/downloads';
import { allCorpora, corpusById } from '../../lib/site';

export const getStaticPaths = (() =>
  allCorpora().flatMap((c) => c.groups.filter((g) => !g.single).map((g) => ({ params: { corpus: c.id, gid: g.id } })))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ params }) => {
  const corpus = corpusById(params.corpus!);
  return textResponse(groupTxt(corpus, corpus.groups.find((g) => g.id === params.gid)!));
};
