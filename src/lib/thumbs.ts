/** 影像缩略图：站点只放缩略图，原图链到 GitHub。缩略图由 pages/[corpus]/thumbs/ 路由用 sharp 生成。 */
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import sharp from 'sharp';
import { quotePath } from './html';
import { ROOT, type Corpus } from './corpus';
import { REPO_RAW, url } from './url';

/** 释文旁与整页图版的缩略图宽度 */
export const WIDTH = 360;
/** 封面卡片的缩略图宽度，高分屏下仍然清楚 */
export const COVER_WIDTH = 720;

export function fullUrl(rel: string): string {
  return REPO_RAW + quotePath(rel);
}

/**
 * 缩略图文件名：data/images/ 之后的路径把 / 换成 __，扩展名统一为 .jpg；宽度不是默认值时带上 @宽度。
 * 文件名里有非 ASCII 字符时，改用目录名加路径的哈希，免得地址里出现要转义的字。
 */
export function thumbName(rel: string, width: number = WIDTH): string {
  const flat = rel.replace('data/images/', '').replaceAll('/', '__');
  const stem = flat.replace(/\.[^./]*$/, '');
  const safe = /^[A-Za-z0-9._-]+$/.test(stem)
    ? stem
    : `${stem.split('__')[0]}__${createHash('sha1').update(rel).digest('hex').slice(0, 10)}`;
  return width === WIDTH ? `${safe}.jpg` : `${safe}@${width}.jpg`;
}

/** 缩略图在站内的路径（相对站点根） */
export function thumbPath(corpusId: string, rel: string, width: number = WIDTH): string {
  return `${corpusId}/thumbs/${thumbName(rel, width)}`;
}

export function thumbUrl(corpusId: string, rel: string, width: number = WIDTH): string {
  return url(thumbPath(corpusId, rel, width));
}

export interface ThumbJob {
  name: string;
  rel: string;
  width: number;
}

/** 一部典籍需要的全部缩略图：每张影像一张默认宽度的，每部文献的封面图再加一张封面宽度的。 */
export function thumbJobs(c: Corpus): ThumbJob[] {
  const jobs = new Map<string, ThumbJob>();
  const add = (rel: string, width: number) => jobs.set(thumbName(rel, width), { name: thumbName(rel, width), rel, width });
  for (const w of c.witnesses) for (const p of w.plates) add(p.file, WIDTH);
  for (const g of c.groups) {
    const cover = g.coverPlate();
    if (cover) add(cover.file, COVER_WIDTH);
  }
  return [...jobs.values()];
}

/** 生成缩略图（JPEG）。不放大；按 EXIF 方向摆正。 */
export async function makeThumb(rel: string, width: number): Promise<Uint8Array<ArrayBuffer>> {
  const buf = await sharp(resolve(ROOT, rel))
    .rotate()
    .resize({ width, withoutEnlargement: true, kernel: 'lanczos3' })
    .toColorspace('srgb')
    .jpeg({ quality: 72, mozjpeg: true })
    .toBuffer();
  return new Uint8Array(buf);
}
