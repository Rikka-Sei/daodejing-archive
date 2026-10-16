/**
 * 固定字体脚本（scripts/make-fonts.ts）：页面用字统计、来源字体的下载校验、按字重裁出子集。
 * 全部离线：子集用 assets/mini-sans.otf 测，那是从固定来源的思源黑体 Regular（NotoSansSC-Regular.otf，SIL OFL 1.1）
 * 里只裁出“甲乙丙「」A”六个字的小字体（pyftsubset，保留 hinting 与全部排版特征）。
 */
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { Blob as FontBlob, Face, Font } from 'harfbuzzjs';
import { parse } from 'yaml';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import manifest from '../../public/fonts/fonts.json';
import { hbSubset } from '../../scripts/hb-subset';
import wawoff2 from 'wawoff2';
import { codePoints, DERIVED, derivedConfig, EXT, EXTRA, fetchPinned, main, makeExt, makeSubset, SOURCES, usedChars } from '../../scripts/make-fonts';
import { tempDir } from './fixtures';

/**
 * 数 CFF 字形里声明的笔画提示（hstem、vstem 及其 hm 形式，hintmask 前隐含的 vstem）：只读每个字形开头、第一个 moveto 之前的部分。
 * 这里只为测试 hinting 是否保留，够用即可：不展开子程序（思源的提示都直接写在字形里）。
 */
function cffStems(font: Uint8Array): number[] {
  const dir = [...Array((font[4] << 8) | font[5]).keys()].map((i) => 12 + i * 16);
  const rec = dir.find((r) => String.fromCharCode(...font.subarray(r, r + 4)) === 'CFF ')!;
  const at32 = (o: number) => ((font[o] << 24) | (font[o + 1] << 16) | (font[o + 2] << 8) | font[o + 3]) >>> 0;
  const t = font.subarray(at32(rec + 8), at32(rec + 8) + at32(rec + 12));
  const u8 = (o: number) => t[o];
  const off = (o: number, size: number) => [...Array(size).keys()].reduce((a, i) => a * 256 + t[o + i], 0);
  /** 读一个 INDEX，返回各项的 [起, 止) 与 INDEX 之后的位置 */
  const index = (o: number): [[number, number][], number] => {
    const count = off(o, 2);
    if (!count) return [[], o + 2];
    const size = u8(o + 2);
    const at = (i: number) => off(o + 3 + i * size, size);
    const base = o + 2 + (count + 1) * size;
    return [[...Array(count).keys()].map((i) => [base + at(i), base + at(i + 1)]), base + at(count)];
  };
  const [, afterName] = index(t[2]);
  const [[top]] = index(afterName);
  // Top DICT 里找 CharStrings（操作符 17）的偏移
  let charStrings = 0;
  const stack: number[] = [];
  for (let i = top[0]; i < top[1]; ) {
    const b = t[i];
    if (b <= 21) {
      if (b === 17) charStrings = stack[stack.length - 1];
      i += b === 12 ? 2 : 1;
      stack.length = 0;
    } else if (b === 28) (stack.push((t[i + 1] << 24 >> 16) | t[i + 2]), (i += 3));
    else if (b === 29) (stack.push(off(i + 1, 4) | 0), (i += 5));
    else if (b === 30) {
      i++;
      while ((t[i] & 0x0f) !== 0x0f && (t[i] >> 4) !== 0x0f) i++;
      i++;
      stack.push(0);
    } else if (b <= 246) (stack.push(b - 139), (i += 1));
    else if (b <= 250) (stack.push((b - 247) * 256 + t[i + 1] + 108), (i += 2));
    else (stack.push(-(b - 251) * 256 - t[i + 1] - 108), (i += 2));
  }
  const [glyphs] = index(charStrings);
  return glyphs.map(([a, z]) => {
    let stems = 0;
    let args = 0;
    for (let i = a; i < z; ) {
      const b = t[i];
      if (b === 28) (args++, (i += 3));
      else if (b === 255) (args++, (i += 5));
      else if (b >= 32) (args++, (i += b <= 246 ? 1 : 2));
      else if ([1, 3, 18, 23].includes(b)) ((stems += args >> 1), (args = 0), i++);
      else if (b === 19 || b === 20) ((stems += args >> 1), (args = 0), (i += 1 + Math.ceil(stems / 8)));
      else break; // moveto、callsubr、endchar 等：提示部分到此为止
    }
    return stems;
  });
}
const stemTotal = (font: Uint8Array) => cffStems(font).reduce((a, b) => a + b, 0);

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

  it('来源按地址与哈希固定：每个字重一个 Adobe 发布的静态 OTF（固定在一个标签上），两种字体各带授权文本', () => {
    for (const s of Object.values(SOURCES)) {
      expect(Object.keys(s.files)).toEqual(['400', '500']);
      for (const f of Object.values(s.files)) {
        expect(f.url).toMatch(/^https:\/\/raw\.githubusercontent\.com\/notofonts\/noto-cjk\/(Sans|Serif)[\d.]+\/.+\.otf$/);
        expect(f.sha256).toMatch(/^[0-9a-f]{64}$/);
      }
      expect(s.licenseSha256).toMatch(/^[0-9a-f]{64}$/);
    }
  });
});

describe('裁出子集', () => {
  const otf = readFileSync(new URL('./assets/mini-sans.otf', import.meta.url));
  const face = (font: Uint8Array) => new Face(new FontBlob(font));
  const unicodes = (font: Uint8Array) => [...codePoints(font)].sort((a, b) => a - b);

  it('小字体是 CFF 轮廓的静态字体，收着六个字', () => {
    expect(face(otf).getAxisInfos()).toEqual({});
    expect(cffStems(otf).length).toBe(11); // .notdef、六个字，加竖排与全角半角的替换字形
    expect(unicodes(otf)).toEqual([...'「」丙乙甲A'].map((c) => c.codePointAt(0)!).sort((a, b) => a - b));
  });

  it('只留要的字', async () => {
    expect(unicodes(await makeSubset(otf, '甲乙', 'sfnt'))).toEqual([0x4e59, 0x7532]);
  });

  it('hinting 保留：没有它，小字号下横画时而对齐像素、时而摊成两列浅灰，一行字看着有粗有细', async () => {
    const before = stemTotal(otf);
    expect(before).toBe(36); // 与 fontTools 解出的数目一致
    expect(stemTotal(await makeSubset(otf, '甲乙丙「」A', 'sfnt'))).toBe(before);
  });

  it('排版特征全部保留，包括竖排用的 vert、vrt2 和 HarfBuzz 默认会去掉的全角、半角形（fwid、hwid）', async () => {
    const font = face(await makeSubset(otf, '甲「A', 'sfnt'));
    expect(font.getTableFeatureTags('GSUB')).toEqual(expect.arrayContaining(['vert', 'vrt2', 'fwid', 'hwid']));
    expect(font.getTableFeatureTags('GPOS')).toEqual(expect.arrayContaining(['vhal', 'vpal']));
  });

  it('版权与授权信息原样保留', async () => {
    const font = face(await makeSubset(otf, '甲', 'sfnt'));
    expect(font.getName(0, 'en')).toContain('Adobe');
    expect(font.getName(13, 'en')).toContain('SIL Open Font License');
  });

  it('缺字时浏览器画的 .notdef 方框保留（去掉轮廓，缺字处就成了空白，读者看不出缺了字）', async () => {
    const font = new Font(face(await makeSubset(otf, '甲', 'sfnt')));
    expect(font.glyphToPath(0)).not.toBe('');
  });

  it('默认存成 WOFF2', async () => {
    const out = await makeSubset(otf, '甲');
    expect(Buffer.from(out.subarray(0, 4)).toString('latin1')).toBe('wOF2');
  });

  it('同样的输入得到逐字节相同的结果', async () => {
    expect(await makeSubset(otf, '甲乙丙')).toEqual(await makeSubset(otf, '甲乙丙'));
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

describe('命令', () => {
  it('没构建过站点：提示先构建', async () => {
    await expect(main(['--site', tmp.dir])).rejects.toThrow('npm run build');
    await expect(main(['--site', join(tmp.dir, 'none')])).rejects.toThrow('npm run build');
  });
});

describe('派生字体 DaoSong（宋体 400）', () => {
  const cfg = derivedConfig();
  const entry = manifest.files.find((f) => f.family === 'serif' && f.weight === DERIVED.weight)!;
  const ttf = () => wawoff2.decompress(readFileSync(`public/fonts/${entry.file}`));

  it('宋体 400 的文件就是 DaoSong，授权文本与 font/OFL.txt 逐字相同', () => {
    expect(entry.file).toBe(`${DERIVED.slug}-400.woff2`);
    expect(manifest.licenses).toContain(DERIVED.licenseFile);
    expect(readFileSync(`public/fonts/${DERIVED.licenseFile}`).equals(readFileSync('font/OFL.txt'))).toBe(true);
  });

  it('登记的手绘字都在这个字体里，字体清单里不再有缺字', async () => {
    const have = codePoints(await ttf());
    expect(cfg.glyphs.length).toBeGreaterThan(0);
    for (const g of cfg.glyphs) {
      expect(have.has(g.cp), g.char).toBe(true);
      expect(manifest.chars).toContain(g.char);
      expect(manifest.unavailable).not.toContain(g.char);
    }
  });

  it('字体里的名字是 DaoSong，不再叫思源（也没有保留名 Source）', async () => {
    const face = new Face(new FontBlob(await ttf()));
    for (const id of [1, 4, 6]) {
      const name = face.getName(id, 'en');
      expect(name, `name ${id}`).toContain(cfg.family);
      expect(name, `name ${id}`).not.toMatch(/Noto|Source/);
    }
    expect(face.getName(13, 'en')).toContain('SIL Open Font License');
  });

  it('字体清单的来源里登记了派生关系与上游哈希', () => {
    const own = manifest.sources.find((x) => x.license_file === DERIVED.licenseFile) as unknown as Record<string, string>;
    expect(own.upstream_sha256).toBe(SOURCES.serif.files[400].sha256);
    expect(own.weights).toBe('400');
    expect(manifest.sources.find((x) => x.license_file === SOURCES.serif.licenseFile)?.weights).toBe('500');
  });

  it('补绘的字也带 hinting，和思源宋体原有的字一样', async () => {
    const font = await ttf();
    const stems = cffStems(font);
    const ids = new Font(new Face(new FontBlob(font)));
    for (const g of [...cfg.glyphs, { cp: '道'.codePointAt(0)!, char: '道' }]) expect(stems[ids.nominalGlyph(g.cp)!], g.char).toBeGreaterThan(0);
  });
});
