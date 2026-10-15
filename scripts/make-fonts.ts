/**
 * 生成站点用的固定字体子集（WOFF2）：思源黑体、思源宋体，SIL OFL 1.1。
 *
 * 先构建站点（npm run build），统计 dist/ 里页面实际出现的字，再从固定来源的字体里裁出这些字，存到 public/fonts/。
 * 来源文件按 URL + SHA-256 固定，下载后先校验；子集的哈希和覆盖的字记在 fonts.json。
 * 新增典籍、页面出现新字后重新运行即可（构建时会提示哪些字不在子集里），然后重新构建。
 *
 * 用法：npm run build && npm run fonts [-- --site dist --cache 目录]
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { Blob as FontBlob, Face, versionString } from 'harfbuzzjs';
import wawoff2 from 'wawoff2';
import { siteChars } from '../src/lib/verify';
import { hbSubset } from './hb-subset';

const REPO = fileURLToPath(new URL('..', import.meta.url));
const FONT_DIR = join(REPO, 'public/fonts');

type Family = 'sans' | 'serif';

interface Source {
  name: string;
  slug: string;
  licenseFile: string;
  url: string;
  sha256: string;
  licenseUrl: string;
  licenseSha256: string;
}

const GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl';
export const SOURCES: Record<Family, Source> = {
  sans: {
    name: 'Noto Sans SC',
    slug: 'noto-sans-sc',
    licenseFile: 'OFL-NotoSansSC.txt',
    url: `${GF}/notosanssc/NotoSansSC%5Bwght%5D.ttf`,
    sha256: 'a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da',
    licenseUrl: `${GF}/notosanssc/OFL.txt`,
    licenseSha256: '1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9',
  },
  serif: {
    name: 'Noto Serif SC',
    slug: 'noto-serif-sc',
    licenseFile: 'OFL-NotoSerifSC.txt',
    url: `${GF}/notoserifsc/NotoSerifSC%5Bwght%5D.ttf`,
    sha256: '050080d9255a86808f2945bffac582b31ef32bc36411ce29563b4961670c66f9',
    licenseUrl: `${GF}/notoserifsc/OFL.txt`,
    licenseSha256: '5e0da210fb04058a8c0087985d2d456b931c2579811a49655721d3cf0c36b6d6',
  },
};

const WEIGHTS = [400, 500];

/** 页面用字的三档：全部；去掉释文正文；再去掉来源注释 */
export type Tier = 'all' | 'text' | 'ui';

/** 各字体各字重装哪些字：说明，以及用 usedChars 里的哪一档。宋体 400 用于释文，要全；500 字重只用于标题和界面。 */
const SCOPE: Record<string, [string, Tier]> = {
  'sans-400': ['界面、识语与注释用字', 'text'],
  'sans-500': ['界面与标题用字', 'ui'],
  'serif-400': ['全部用字', 'all'],
  'serif-500': ['界面与标题用字', 'ui'],
};

/** 页面上没出现、但样式会生成或常用的字：ASCII、序号后的“、”、常见标点 */
export const EXTRA =
  Array.from({ length: 0x7f - 0x20 }, (_, i) => String.fromCharCode(0x20 + i)).join('') +
  '、。，；：？！“”‘’（）《》〈〉【】「」『』·—…›';

const sha256 = (data: Uint8Array) => createHash('sha256').update(data).digest('hex');
const byCodePoint = (a: string, b: string) => a.codePointAt(0)! - b.codePointAt(0)!;

/**
 * 页面用字，按用在哪里分三档（都加上常用标点）：
 * all 全部；text 去掉释文正文（黑体 400：界面、识语、注释）；ui 再去掉注释（500 字重：标题与界面）。
 * 释文只用宋体 400，所以其余字体的子集小得多。
 */
export function usedChars(site: string): Record<Tier, Set<string>> {
  const pool = (units: boolean, notes: boolean) => new Set([...siteChars(site, units, notes), ...EXTRA]);
  return { all: pool(true, true), text: pool(false, true), ui: pool(false, false) };
}

/** 下载到缓存目录并校验哈希；缓存里已有且哈希对就直接用。 */
export async function fetchPinned(url: string, hash: string, cache: string, get: typeof fetch = fetch): Promise<Buffer> {
  mkdirSync(cache, { recursive: true });
  const dest = join(cache, `${hash.slice(0, 12)}-${decodeURIComponent(basename(url))}`);
  if (existsSync(dest)) {
    const cached = readFileSync(dest);
    if (sha256(cached) === hash) return cached;
  }
  const res = await get(url, { signal: AbortSignal.timeout(300_000) });
  if (!res.ok) throw new Error(`下载失败（HTTP ${res.status}）：${url}`);
  const data = Buffer.from(await res.arrayBuffer());
  const got = sha256(data);
  if (got !== hash) {
    throw new Error(
      `校验失败：${url}\n  应为 ${hash}\n  实为 ${got}\n上游文件变了。确认新版可用后，更新本脚本里固定的 SHA-256。`,
    );
  }
  writeFileSync(dest, data);
  return data;
}

/** 字体收了哪些字（码点） */
export function codePoints(font: Uint8Array): Set<number> {
  return new Set(new Face(new FontBlob(font)).collectUnicodes());
}

/**
 * 在变体字体上取定字重（得到静态字体），只留 chars 里的字，存成 WOFF2。
 * 竖排用的 vert/vrt2 等排版特征、版权与授权信息、缺字时画的 .notdef 方框都保留。
 */
export async function makeSubset(font: Uint8Array, weight: number, chars: string, format: 'woff2' | 'truetype' = 'woff2'): Promise<Uint8Array> {
  const ttf = await hbSubset(font, chars, { wght: weight });
  return format === 'woff2' ? wawoff2.compress(ttf) : ttf;
}

const hasPages = (dir: string) => existsSync(dir) && readdirSync(dir, { recursive: true }).some((f) => String(f).endsWith('.html'));

/** 生成子集所用工具的版本，记在 fonts.json 里 */
function toolVersion(): string {
  const { version } = createRequire(import.meta.url)('wawoff2/package.json') as { version: string };
  return `HarfBuzz ${versionString()}（hb-subset）、wawoff2 ${version}`;
}

export async function main(argv: string[] = process.argv.slice(2)): Promise<void> {
  const { values } = parseArgs({ args: argv, options: { site: { type: 'string' }, cache: { type: 'string' } } });
  const site = resolve(values.site ?? join(REPO, 'dist'));
  const cache = resolve(values.cache ?? join(homedir(), '.cache/daodejing-archive/fonts'));
  if (!hasPages(site)) throw new Error(`${site} 里没有页面，先运行 npm run build`);

  const pools = usedChars(site);
  const wanted = pools.all;
  mkdirSync(FONT_DIR, { recursive: true });
  const files: Record<string, string | number>[] = [];
  const sources: Record<string, string>[] = [];
  const haves: Set<string>[] = [];
  for (const [family, s] of Object.entries(SOURCES) as [Family, Source][]) {
    const font = await fetchPinned(s.url, s.sha256, cache);
    writeFileSync(join(FONT_DIR, s.licenseFile), await fetchPinned(s.licenseUrl, s.licenseSha256, cache));
    const cmap = codePoints(font);
    const have = new Set([...wanted].filter((c) => cmap.has(c.codePointAt(0)!)));
    haves.push(have);
    for (const weight of WEIGHTS) {
      const [scope, tier] = SCOPE[`${family}-${weight}`];
      const pool = [...have].filter((c) => pools[tier].has(c)).sort(byCodePoint);
      const file = `${s.slug}-${weight}.woff2`;
      const data = await makeSubset(font, weight, pool.join(''));
      writeFileSync(join(FONT_DIR, file), data);
      files.push({ file, family, weight, scope, chars: pool.length, bytes: data.length, sha256: sha256(data) });
    }
    sources.push({
      family,
      name: s.name,
      url: s.url.replace('%5B', '[').replace('%5D', ']'),
      sha256: s.sha256,
      license: 'SIL OFL 1.1',
      license_file: s.licenseFile,
      reserved_font_name: 'Source',
    });
  }

  const covered = new Set([...wanted].filter((c) => haves.every((have) => have.has(c)))); // 黑体、宋体共有的字
  const chars = [...covered].sort(byCodePoint).join('');
  const unavailable = [...wanted].filter((c) => !covered.has(c)).sort(byCodePoint).join('');
  const manifest = {
    about:
      '站点自带的固定字体子集，由 scripts/make-fonts.ts（npm run fonts）生成；只含站点用到的字，其余字回退到系统字体。' +
      '各文件装哪些字见 files[].scope：释文只用宋体 400，所以其余文件只装界面、标题、识语等处的字。',
    tool: toolVersion(),
    chars,
    unavailable,
    files,
    licenses: Object.values(SOURCES).map((s) => s.licenseFile),
    sources,
  };
  writeFileSync(join(FONT_DIR, 'fonts.json'), `${JSON.stringify(manifest, null, 1)}\n`);

  for (const f of files) console.log(`${String(f.file).padEnd(26)} ${String(Math.round(Number(f.bytes) / 1024)).padStart(7)} KB`);
  const total = files.reduce((sum, f) => sum + Number(f.bytes), 0);
  console.log(`共 ${Math.round(total / 1024)} KB；覆盖 ${[...chars].length} 字；字体里没有 ${[...unavailable].length} 字：${unavailable || '无'}`);
}

/** 作为命令运行时才执行，被测试引入时不执行 */
function isMain(): boolean {
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isMain()) {
  main().catch((e: Error) => {
    console.error(e.message);
    process.exitCode = 1;
  });
}
