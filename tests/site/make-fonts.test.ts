/**
 * 固定字体脚本（scripts/make-fonts.ts）：页面用字统计、来源字体的下载校验、按字重裁出子集。
 * 全部离线：子集用 assets/mini-vf.ttf 测，那是从固定来源的思源黑体变体字体（NotoSansSC[wght].ttf，SIL OFL 1.1）
 * 里只裁出“甲乙丙「」A”六个字、保留字重轴得到的小字体：hbSubset(font, '甲乙丙「」A')。
 */
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { Blob as FontBlob, Face, Font } from 'harfbuzzjs';
import { parse } from 'yaml';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import manifest from '../../public/fonts/fonts.json';
import { hbSubset } from '../../scripts/hb-subset';
import { codePoints, EXT, EXTRA, fetchPinned, main, makeExt, makeSubset, SOURCES, usedChars } from '../../scripts/make-fonts';
import { tempDir } from './fixtures';

let tmp: ReturnType<typeof tempDir>;
beforeEach(() => {
  tmp = tempDir();
});
afterEach(() => tmp.cleanup());

const put = (rel: string, text: string) => {
  const path = join(tmp.dir, rel);
  mkdirSync(join(path, '..'), { recursive: true });
  writeFileSync(path, text);
};

describe('页面用字统计', () => {
  beforeEach(() => {
    put('a/index.html', '<h1>标 题</h1><p>释文</p><div class="note">注</div>');
    put('_astro/x.css', '/* 备忘 */a:before{content:"、"}');
    put('_astro/app.js', '/* 备忘 */var s="本页命中";');
  });

  it('分三档：释文只用宋体 400，所以其余字体的子集不含释文用字', () => {
    const pools = usedChars(tmp.dir);
    expect(pools.all.has('释')).toBe(true);
    expect(pools.text.has('释')).toBe(false);
    expect(pools.text.has('注')).toBe(true);
    expect(pools.ui.has('注')).toBe(false);
    expect(pools.ui.has('标')).toBe(true);
  });

  it('页面正文、外部样式与脚本里的字符串都算，注释不算', () => {
    const { all } = usedChars(tmp.dir);
    for (const c of '标题释文注、本页命中') expect(all.has(c), c).toBe(true);
    for (const c of '备忘') expect(all.has(c), c).toBe(false);
  });

  it('常用标点与 ASCII 每一档都带上', () => {
    for (const pool of Object.values(usedChars(tmp.dir))) expect([...EXTRA].filter((c) => !pool.has(c))).toEqual([]);
  });
});

describe('下载来源字体并校验', () => {
  const data = Buffer.from('字体数据');
  const hash = createHash('sha256').update(data).digest('hex');
  const reply = (body: Buffer | string, status = 200) => vi.fn(async () => new Response(typeof body === 'string' ? body : new Uint8Array(body), { status })) as unknown as typeof fetch;
  const cacheFiles = (dir: string) => readdirSync(dir);

  it('缓存里没有：下载、校验、存进缓存，再要就不用下载了', async () => {
    const get = reply(data);
    const cache = join(tmp.dir, 'cache');
    expect(await fetchPinned('https://x.test/a/Font%5Bwght%5D.ttf', hash, cache, get)).toEqual(data);
    expect(cacheFiles(cache)).toEqual([`${hash.slice(0, 12)}-Font[wght].ttf`]);
    expect(await fetchPinned('https://x.test/a/Font%5Bwght%5D.ttf', hash, cache, get)).toEqual(data);
    expect(get).toHaveBeenCalledTimes(1);
  });

  it('缓存里的文件哈希不对：当作没有，重新下载', async () => {
    const cache = join(tmp.dir, 'cache');
    put('cache/' + `${hash.slice(0, 12)}-f.ttf`, '被改过');
    const get = reply(data);
    expect(await fetchPinned('https://x.test/f.ttf', hash, cache, get)).toEqual(data);
    expect(get).toHaveBeenCalledTimes(1);
  });

  it('下载下来的哈希不对：报错，说明怎么办，不存进缓存', async () => {
    const cache = join(tmp.dir, 'cache');
    await expect(fetchPinned('https://x.test/f.ttf', hash, cache, reply('别的内容'))).rejects.toThrow(/校验失败[\s\S]*上游文件变了/);
    expect(cacheFiles(cache)).toEqual([]);
  });

  it('服务器报错：说明是哪个地址', async () => {
    await expect(fetchPinned('https://x.test/f.ttf', hash, join(tmp.dir, 'cache'), reply('', 404))).rejects.toThrow('HTTP 404');
  });

  it('来源按地址与哈希固定，两种字体各带授权文本', () => {
    for (const s of Object.values(SOURCES)) {
      expect(s.url).toMatch(/^https:\/\/raw\.githubusercontent\.com\/google\/fonts\/[^/]+\/ofl\//);
      expect([s.sha256, s.licenseSha256].every((h) => /^[0-9a-f]{64}$/.test(h))).toBe(true);
    }
  });
});

describe('裁出子集', () => {
  const vf = readFileSync(new URL('./assets/mini-vf.ttf', import.meta.url));
  const face = (font: Uint8Array) => new Face(new FontBlob(font));
  const unicodes = (font: Uint8Array) => [...codePoints(font)].sort((a, b) => a - b);
  const path = (font: Uint8Array, char: string) => {
    const f = new Font(face(font));
    return f.glyphToPath(f.nominalGlyph(char.codePointAt(0)!)!);
  };

  it('小字体是变体字体，收着六个字', () => {
    expect(Object.keys(face(vf).getAxisInfos())).toEqual(['wght']);
    expect(unicodes(vf)).toEqual([...'「」丙乙甲A'].map((c) => c.codePointAt(0)!).sort((a, b) => a - b));
  });

  it('只留要的字', async () => {
    expect(unicodes(await makeSubset(vf, 400, '甲乙', 'truetype'))).toEqual([0x4e59, 0x7532]);
  });

  it('取定字重得到静态字体：没有字重轴，不同字重的字形不同', async () => {
    const light = await makeSubset(vf, 400, '甲乙丙', 'truetype');
    const bold = await makeSubset(vf, 700, '甲乙丙', 'truetype');
    expect(face(light).getAxisInfos()).toEqual({});
    expect(face(bold).getAxisInfos()).toEqual({});
    expect(path(light, '甲')).not.toBe(path(bold, '甲'));
    expect(path(light, '甲')).not.toBe(path(vf, '甲')); // 也不是变体字体的默认字重
  });

  it('排版特征全部保留，包括竖排用的 vert、vrt2 和 HarfBuzz 默认会去掉的全角、半角形（fwid、hwid）', async () => {
    const font = face(await makeSubset(vf, 400, '甲「A', 'truetype'));
    expect(font.getTableFeatureTags('GSUB')).toEqual(expect.arrayContaining(['vert', 'vrt2', 'fwid', 'hwid']));
    expect(font.getTableFeatureTags('GPOS')).toEqual(expect.arrayContaining(['vhal', 'vpal']));
  });

  it('版权与授权信息原样保留', async () => {
    const font = face(await makeSubset(vf, 400, '甲', 'truetype'));
    expect(font.getName(0, 'en')).toContain('Adobe');
    expect(font.getName(13, 'en')).toContain('SIL Open Font License');
  });

  it('缺字时浏览器画的 .notdef 方框保留（去掉轮廓，缺字处就成了空白，读者看不出缺了字）', async () => {
    const font = new Font(face(await makeSubset(vf, 400, '甲', 'truetype')));
    expect(font.glyphToPath(0)).not.toBe('');
  });

  it('默认存成 WOFF2', async () => {
    const out = await makeSubset(vf, 400, '甲');
    expect(Buffer.from(out.subarray(0, 4)).toString('latin1')).toBe('wOF2');
  });

  it('同样的输入得到逐字节相同的结果', async () => {
    expect(await makeSubset(vf, 500, '甲乙丙')).toEqual(await makeSubset(vf, 500, '甲乙丙'));
  });
});

describe('补充字体（tt24h 的 DaoDeJingExt）', () => {
  const sha = (data: Uint8Array) => createHash('sha256').update(data).digest('hex');
  /** 把仓库里登记的原文件（字体与授权文本）拷进临时目录，之后可以改动其中一份 */
  const copyRaw = () => {
    for (const rel of [EXT.raw, EXT.licenseRaw]) {
      mkdirSync(join(tmp.dir, rel, '..'), { recursive: true });
      copyFileSync(rel, join(tmp.dir, rel));
    }
  };

  it('脚本里固定的哈希与来源记录里登记的一致', () => {
    const src = parse(readFileSync('data/sources/tt24h-daodejing.yaml', 'utf-8'));
    const registered = Object.fromEntries((src.retrieval.files as { path: string; sha256: string }[]).map((f) => [f.path, f.sha256]));
    expect(registered[EXT.raw]).toBe(EXT.sha256);
    expect(registered[EXT.licenseRaw]).toBe(EXT.licenseSha256);
  });

  it('整个转成 WOFF2，收着私用区的造字码位', async () => {
    const ext = (await makeExt())!;
    expect(Buffer.from(ext.woff2.subarray(0, 4)).toString('latin1')).toBe('wOF2');
    expect([...ext.cmap].some((cp) => cp >= 0xe000 && cp <= 0xf8ff)).toBe(true);
    expect(sha(ext.woff2)).toBe(sha((await makeExt())!.woff2)); // 同样的输入得到逐字节相同的结果
  });

  it('随站点发布的文件就是这样得到的：字节、哈希与字体清单一致，授权文本逐字相同', async () => {
    const ext = (await makeExt())!;
    const entry = manifest.files.find((f) => f.family === 'ext')!;
    expect(entry.file).toBe(EXT.file);
    expect(sha(ext.woff2)).toBe(entry.sha256);
    expect(Buffer.from(ext.woff2).equals(readFileSync(`public/fonts/${EXT.file}`))).toBe(true);
    expect(ext.licence.equals(readFileSync(`public/fonts/${EXT.licenseFile}`))).toBe(true);
    expect(manifest.licenses).toContain(EXT.licenseFile);
    expect(manifest.sources.find((x) => x.family === 'ext')?.sha256).toBe(EXT.sha256);
  });

  it('原文件被改过：报错，不生成', async () => {
    copyRaw();
    writeFileSync(join(tmp.dir, EXT.raw), '被改动');
    await expect(makeExt(tmp.dir)).rejects.toThrow('校验失败');
  });

  it('授权文本被改过：同样报错', async () => {
    copyRaw();
    writeFileSync(join(tmp.dir, EXT.licenseRaw), '被改动');
    await expect(makeExt(tmp.dir)).rejects.toThrow(`校验失败：${EXT.licenseRaw}`);
  });

  it('原文件没拉取下来（data/raw/ 不在）：返回 null，字体清单里就没有补充字体', async () => {
    expect(await makeExt(tmp.dir)).toBeNull();
  });

  it('原文件和校订好的授权拷贝没问题时通过', async () => {
    copyRaw();
    expect(await makeExt(tmp.dir)).not.toBeNull();
  });
});

describe('取定不存在的轴', () => {
  it('报错，说明是哪根轴', async () => {
    const vf = readFileSync(new URL('./assets/mini-vf.ttf', import.meta.url));
    await expect(hbSubset(vf, '甲', { wdth: 100 })).rejects.toThrow('wdth');
  });
});

describe('命令', () => {
  it('没构建过站点：提示先构建', async () => {
    await expect(main(['--site', tmp.dir])).rejects.toThrow('npm run build');
    await expect(main(['--site', join(tmp.dir, 'none')])).rejects.toThrow('npm run build');
  });
});
