// 一个本的释文数据：<典籍>/<本>.jsonl，与仓库里的 jsonl 逐字相同。
import type { APIRoute, GetStaticPaths } from 'astro';
import { textResponse, witnessJsonl } from '../../lib/downloads';
import { allCorpora, corpusById } from '../../lib/site';

export const getStaticPaths = (() =>
  allCorpora().flatMap((c) => c.witnesses.map((w) => ({ params: { corpus: c.id, id: w.id } })))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ params }) => {
  const corpus = corpusById(params.corpus!);
  return textResponse(witnessJsonl(corpus.witness(params.id!)!), 'application/x-ndjson');
};
