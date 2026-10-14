// llms.txt（https://llmstxt.org）：站点的释文索引。构建时配置了 site 就写绝对链接，否则写相对链接。
import type { APIRoute } from 'astro';
import { textResponse } from '../lib/downloads';
import { llmsTxt } from '../lib/llms';
import { allCorpora } from '../lib/site';
import { absoluteBase } from '../lib/url';

export const GET: APIRoute = () => textResponse(llmsTxt(allCorpora(), absoluteBase()).short, 'text/markdown');
