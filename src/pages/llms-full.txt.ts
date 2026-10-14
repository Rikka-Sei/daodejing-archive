// llms-full.txt：全部释文合成一个文本文件。
import type { APIRoute } from 'astro';
import { textResponse } from '../lib/downloads';
import { llmsTxt } from '../lib/llms';
import { allCorpora } from '../lib/site';
import { absoluteBase } from '../lib/url';

export const GET: APIRoute = () => textResponse(llmsTxt(allCorpora(), absoluteBase()).full, 'text/markdown');
