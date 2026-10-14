// 一个本的纯文本释文：<典籍>/<本>.txt
import type { APIRoute, GetStaticPaths } from 'astro';
import { textResponse, witnessTxt } from '../../lib/downloads';
import { allCorpora, corpusById } from '../../lib/site';

export const getStaticPaths = (() =>
  allCorpora().flatMap((c) => c.witnesses.map((w) => ({ params: { corpus: c.id, id: w.id } })))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ params }) => {
  const corpus = corpusById(params.corpus!);
  return textResponse(witnessTxt(corpus, corpus.witness(params.id!)!));
};
