// 对读表的公共部分：各行（版本）的简称、共用通行字的规则、造字码位。阅读器读它来显示与比较。
import type { APIRoute, GetStaticPaths } from 'astro';
import { readerMeta } from '../../lib/alignment';
import { textResponse } from '../../lib/downloads';
import { allCorpora, corpusById } from '../../lib/site';

export const getStaticPaths = (() =>
  allCorpora()
    .filter((c) => c.alignment)
    .map((c) => ({ params: { corpus: c.id } }))) satisfies GetStaticPaths;

export const GET: APIRoute = ({ params }) => textResponse(JSON.stringify(readerMeta(corpusById(params.corpus!).alignment!)), 'application/json');
