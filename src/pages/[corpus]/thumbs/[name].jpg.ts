// 影像缩略图：<典籍>/thumbs/<名>.jpg，构建时由 sharp 从 data/images/ 缩出。哪些要生成，见 lib/thumbs.ts 的 thumbJobs。
import type { APIRoute, GetStaticPaths } from 'astro';
import { makeThumb, thumbJobs, type ThumbJob } from '../../../lib/thumbs';
import { allCorpora } from '../../../lib/site';

export const getStaticPaths = (() =>
  allCorpora().flatMap((c) =>
    // 路由参数里不带 .jpg 扩展名
    thumbJobs(c).map((job) => ({ params: { corpus: c.id, name: job.name.replace(/\.jpg$/, '') }, props: { job } })),
  )) satisfies GetStaticPaths;

export const GET: APIRoute<{ job: ThumbJob }> = async ({ props: { job } }) =>
  new Response(await makeThumb(job.rel, job.width, job.crop), { headers: { 'Content-Type': 'image/jpeg' } });
