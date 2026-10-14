// 有多个本的文献的数据合集：<典籍>/<文献>-all.jsonl
import type { APIRoute, GetStaticPaths } from 'astro';
import { groupJsonl, textResponse } from '../../lib/downloads';
import { allCorpora, corpusById } from '../../lib/site';

export const getStaticPaths = (() =>
  allCorpora().flatMap((c) => c.groups.filter((g) => !g.single).map((g) => ({ params: { corpus: c.id, gid: g.id } })))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ params }) => {
  const corpus = corpusById(params.corpus!);
  return textResponse(groupJsonl(corpus.groups.find((g) => g.id === params.gid)!), 'application/x-ndjson');
};
