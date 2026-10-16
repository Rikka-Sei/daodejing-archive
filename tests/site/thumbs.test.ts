import { writeFileSync } from 'node:fs';
import sharp from 'sharp';
import { afterAll, describe, expect, it } from 'vitest';
import { COVER_WIDTH, fullUrl, makeThumb, thumbJobs, thumbName, thumbPath, WIDTH } from '../../src/lib/thumbs';
import { fixtureCorpus, tempDir } from './fixtures';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

describe('缩略图文件名', () => {
  it('去掉 data/images/，斜杠换成双下划线，扩展名统一为 .jpg', () => {
    expect(thumbName('data/images/jianbo-shufa-guodian-2002/jia-001.jpg')).toBe('jianbo-shufa-guodian-2002__jia-001.jpg');
    expect(thumbName('data/images/commons/Mawangdui_LaoTsu_Ms2.JPG')).toBe('commons__Mawangdui_LaoTsu_Ms2.jpg');
  });

  it('宽度不是默认值时带上 @宽度', () => {
    expect(thumbName('data/images/a/b.jpg', COVER_WIDTH)).toBe('a__b@720.jpg');
    expect(thumbName('data/images/a/b.jpg', WIDTH)).toBe('a__b.jpg');
  });

  it('文件名里有非 ASCII 字符：目录名加路径的哈希', () => {
    const rel = 'data/images/commons/郭店楚简《老子乙》01826.jpg';
    expect(thumbName(rel)).toBe('commons__d9a29621c2.jpg');
    expect(thumbName(rel, COVER_WIDTH)).toBe('commons__d9a29621c2@720.jpg');
  });

  it('从整页图上裁出的块：带上 ~左-上-宽-高', () => {
    expect(thumbName('data/images/a/b.jpg', WIDTH, [1, 2, 3, 4])).toBe('a__b~1-2-3-4.jpg');
    expect(thumbName('data/images/a/b.jpg', COVER_WIDTH, [1, 2, 3, 4])).toBe('a__b~1-2-3-4@720.jpg');
  });

  it('站内路径与原图地址', () => {
    expect(thumbPath('laozi', 'data/images/a/b.jpg')).toBe('laozi/thumbs/a__b.jpg');
    expect(fullUrl('data/images/a/郭 店.jpg')).toBe(
      'https://raw.githubusercontent.com/Rikka-Sei/daodejing-archive/main/data/images/a/%E9%83%AD%20%E5%BA%97.jpg',
    );
  });
});

describe('需要哪些缩略图', () => {
  it('每张影像一张，每部文献的封面图再加一张封面宽度的', () => {
    const c = fixtureCorpus(tmp.dir, 'a');
    expect(thumbJobs(c)).toEqual([
      { name: 'a1.jpg', rel: 'data/images/a1.jpg', width: 360 },
      { name: 'a2.jpg', rel: 'data/images/a2.jpg', width: 360 },
      { name: 'b1.jpg', rel: 'data/images/b1.jpg', width: 360 },
      { name: 'b1@720.jpg', rel: 'data/images/b1.jpg', width: 720 },
    ]);
  });

  it('有阅读器的本，单简图版再加一张阅读器用的大图；整页图版和没有阅读器的本不加', () => {
    const c = fixtureCorpus(tmp.dir, 'x', {}, true, true);
    const big = thumbJobs(c).filter((j) => j.width === 960).map((j) => j.name);
    expect(big).toEqual(['a1@960.jpg']); // w-a 有逐行释文，它的单简图版
  });
});

describe('生成缩略图', () => {
  const make = async (name: string, w: number, h: number, orientation?: number) => {
    const path = `${tmp.dir}/${name}`;
    let img = sharp({ create: { width: w, height: h, channels: 3, background: '#c33' } }).jpeg();
    if (orientation) img = img.withMetadata({ orientation });
    writeFileSync(path, await img.toBuffer());
    return path;
  };
  const dims = async (buf: Uint8Array) => {
    const m = await sharp(buf).metadata();
    return [m.format, m.width, m.height];
  };

  it('缩到指定宽度，保持比例，输出 JPEG', async () => {
    expect(await dims(await makeThumb(await make('big.jpg', 1000, 2000), 360))).toEqual(['jpeg', 360, 720]);
  });

  it('不放大', async () => {
    expect(await dims(await makeThumb(await make('small.jpg', 100, 80), 360))).toEqual(['jpeg', 100, 80]);
  });

  it('带裁块时先裁再缩', async () => {
    expect(await dims(await makeThumb(await make('page.jpg', 1000, 2000), 360, [10, 20, 100, 300]))).toEqual(['jpeg', 100, 300]);
    expect(await dims(await makeThumb(await make('page2.jpg', 1000, 2000), 50, [10, 20, 100, 300]))).toEqual(['jpeg', 50, 150]);
  });

  it('按 EXIF 方向摆正', async () => {
    // 200×100 的图带“顺时针转 90 度”的标记，摆正后是 100×200
    expect(await dims(await makeThumb(await make('rot.jpg', 200, 100, 6), 360))).toEqual(['jpeg', 100, 200]);
  });
});
