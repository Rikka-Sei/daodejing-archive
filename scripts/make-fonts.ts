/**
 * 生成站点用的固定字体（WOFF2）：思源黑体、思源宋体的子集，加上 tt24h 的补充字体 DaoDeJingExt（整个转成 WOFF2），都是 SIL OFL 1.1。
 *
 * 先构建站点（npm run build），统计 dist/ 里页面实际出现的字，再从固定来源的字体里裁出这些字，存到 public/fonts/。
 * 来源文件按 URL + SHA-256 固定，下载后先校验；子集的哈希和覆盖的字记在 fonts.json。
 * 新增典籍、页面出现新字后重新运行即可（构建时会提示哪些字不在子集里），然后重新构建。
 *
 * 用法：npm run build && npm run fonts [-- --site dist --cache 目录]
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { Blob as FontBlob, Face, versionString } from 'harfbuzzjs';
import wawoff2 from 'wawoff2';
import { parse as parseYaml } from 'yaml';
import { siteChars } from '../src/lib/verify';
import { hbSubset } from './hb-subset';

const REPO = fileURLToPath(new URL('..', import.meta.url));
const FONT_DIR = join(REPO, 'public/fonts');

type Family = 'sans' | 'serif';

interface Source {
  name: string;
  slug: string;
  licenseFile: string;
  /** 每个字重一个静态字体文件 */
  files: Record<number, { url: string; sha256: string }>;
  licenseUrl: string;
  licenseSha256: string;
}

/**
 * 来源是 Adobe 发布的静态 OpenType（CFF）版，不用 Google Fonts 的可变 TrueType 版：两者字形相同，
 * 但只有 CFF 版带 hinting（让笔画在小字号时对齐像素）。没有 hinting 的字体在 Windows、Linux 的普通分辨率屏上，
 * 横画时而落在一列像素上、时而摊成两列浅灰，同一行字看着有粗有细。
 */
const CJK = 'https://raw.githubusercontent.com/notofonts/noto-cjk/Serif2.003';
const GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl';
export const SOURCES: Record<Family, Source> = {
  sans: {
    name: 'Noto Sans SC',
    slug: 'noto-sans-sc',
    licenseFile: 'OFL-NotoSansSC.txt',
    files: {
      400: { url: `${CJK}/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf`, sha256: 'faa6c9df652116dde789d351359f3d7e5d2285a2b2a1f04a2d7244df706d5ea9' },
      500: { url: `${CJK}/Sans/SubsetOTF/SC/NotoSansSC-Medium.otf`, sha256: '7633f5a016d4dd95e685a69633d818aabc4644c4b08e26bd35b1b30c45ed5dda' },
    },
    // 授权文本取 Google Fonts 的那份：同一套字体，它写明了版权与保留名 Source
    licenseUrl: `${GF}/notosanssc/OFL.txt`,
    licenseSha256: '1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9',
  },
  serif: {
    name: 'Noto Serif SC',
    slug: 'noto-serif-sc',
    licenseFile: 'OFL-NotoSerifSC.txt',
    files: {
      400: { url: `${CJK}/Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf`, sha256: 'e8f396decc1f0963a016a989c3d8852e863d1350996f573860a80767c83a1cd3' },
      500: { url: `${CJK}/Serif/SubsetOTF/SC/NotoSerifSC-Medium.otf`, sha256: 'e4e9beb5aaeb951e101aa8f122e2a6801ea9e48ac9f9b6bdfeef2436b55bc8ee' },
    },
    licenseUrl: `${GF}/notoserifsc/OFL.txt`,
    licenseSha256: '5e0da210fb04058a8c0087985d2d456b931c2579811a49655721d3cf0c36b6d6',
  },
};

const WEIGHTS = [400, 500];
const WEIGHT_NAME: Record<number, string> = { 400: 'Regular', 500: 'Medium' };

/**
 * 宋体 400 用本项目的派生字体 DaoSong：思源宋体 Regular 加上 font/glyphs/ 里手绘的生僻字（见 font/README.md）。
 * 字形原样沿用思源宋体，所以和 500 字重的思源宋体、黑体放在一起风格一致。制作字体用 Python（font/build.py），只在重新生成字体时需要。
 */
export const DERIVED = {
  name: 'DaoSong',
  slug: 'dao-song',
  weight: 400,
  dir: 'font',
  licenseFile: 'OFL-DaoSong.txt',
  url: 'https://github.com/Rikka-Sei/daodejing-archive/tree/main/font',
};

interface DerivedConfig {
  family: string;
  version: string;
  glyphs: { cp: number; char: string; ids: string; svg: string; note: string }[];
}

/** 读 font/font.yaml */
export function derivedConfig(repo: string = REPO): DerivedConfig {
  return parseYaml(readFileSync(join(repo, DERIVED.dir, 'font.yaml'), 'utf-8')) as DerivedConfig;
}

/** 调 Python 生成 DaoSong（OTF）；upstream 是固定版本的思源宋体 Regular（静态 OTF）的路径。 */
export function buildDerived(upstream: string, out: string, repo: string = REPO): Buffer {
  const run = spawnSync('python3', [join(repo, DERIVED.dir, 'build.py'), '--upstream', upstream, '--out', out], { encoding: 'utf-8' });
  if (run.status !== 0) {
    throw new Error(`生成 ${DERIVED.name} 失败（需要 python3 与 fonttools、skia-pathops、pyyaml、afdko，见 font/README.md）：\n${run.stderr || run.stdout || run.error}`);
  }
  return readFileSync(out);
}

/**
 * tt24h 的补充字体（造字序列的码位和 Noto 里没有的生僻字），原文件登记在 data/raw/ 里，按 SHA-256 核对后整个转成 WOFF2。
 * 页面用 unicode-range 声明它，只在用到这些码位时才下载。
 */
export const EXT = {
  name: 'DaoDeJingExt-Light（tt24h 补充字体）',
  raw: 'data/raw/tt24h-daodejing/v0.1.3/DaoDeJingExt-Light.ttf',
  sha256: '0a6d66177e80625381aa04440889553d86b8ffedcdb5f7806c2599d3ac666407',
  licenseRaw: 'data/raw/tt24h-daodejing/v0.1.3/LICENSE-OFL',
  licenseSha256: '958428ba1d0cac3063a5c0de611b2aa151fb9ca26cd1beba91106605072bbbc3',
  licenseFile: 'OFL-DaoDeJingExt.txt',
  file: 'dg-ext-400.woff2',
  url: 'https://github.com/tt24h/daodejing',
};

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
 * 只留 chars 里的字，存成 WOFF2（format 为 'sfnt' 时不压缩，测试用）。
 * hinting、竖排用的 vert/vrt2 等排版特征、版权与授权信息、缺字时画的 .notdef 方框都保留。
 */
export async function makeSubset(font: Uint8Array, chars: string, format: 'woff2' | 'sfnt' = 'woff2'): Promise<Uint8Array> {
  const sfnt = await hbSubset(font, chars);
  return format === 'woff2' ? wawoff2.compress(sfnt) : sfnt;
}

/**
 * 补充字体：核对登记的原文件与授权文本的哈希，整个转成 WOFF2（同样的输入得到逐字节相同的结果）。
 * 原文件不在 repo 里（没有拉取 data/raw/）就返回 null，这时字体清单里不含补充字体。
 */
export async function makeExt(repo: string = REPO): Promise<{ woff2: Uint8Array; licence: Buffer; cmap: Set<number> } | null> {
  const path = join(repo, EXT.raw);
  if (!existsSync(path)) return null;
  const ttf = readFileSync(path);
  if (sha256(ttf) !== EXT.sha256) throw new Error(`校验失败：${EXT.raw}\n  应为 ${EXT.sha256}\n  实为 ${sha256(ttf)}`);
  const licence = readFileSync(join(repo, EXT.licenseRaw));
  if (sha256(licence) !== EXT.licenseSha256) throw new Error(`校验失败：${EXT.licenseRaw}`);
  return { woff2: await wawoff2.compress(ttf), licence, cmap: codePoints(ttf) };
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
  let serifHas = new Set<string>(); // 宋体收了哪些页面用字（含派生字体补的字）
  for (const [family, s] of Object.entries(SOURCES) as [Family, Source][]) {
    writeFileSync(join(FONT_DIR, s.licenseFile), await fetchPinned(s.licenseUrl, s.licenseSha256, cache));
    const fonts: Record<number, Buffer> = {};
    for (const weight of WEIGHTS) fonts[weight] = await fetchPinned(s.files[weight].url, s.files[weight].sha256, cache);
    // 宋体 400 用派生字体 DaoSong（在固定版本的思源宋体 Regular 上补字），其余字重与黑体直接用上游字体
    let derived: Buffer | undefined;
    if (family === 'serif') {
      const up = s.files[DERIVED.weight];
      const upstream = join(cache, `${up.sha256.slice(0, 12)}-${decodeURIComponent(basename(up.url))}`);
      derived = buildDerived(upstream, join(cache, 'DaoSong-Regular.otf'));
      fonts[DERIVED.weight] = derived;
    }
    // 各字重收的字相同（派生字体多出补绘的字），以 400 为准
    const cmap = codePoints(fonts[400]);
    const have = new Set([...wanted].filter((c) => cmap.has(c.codePointAt(0)!)));
    if (family === 'serif') serifHas = have;
    for (const weight of WEIGHTS) {
      const [scope, tier] = SCOPE[`${family}-${weight}`];
      const pool = [...have].filter((c) => pools[tier].has(c)).sort(byCodePoint);
      const own = derived !== undefined && weight === DERIVED.weight;
      const file = `${own ? DERIVED.slug : s.slug}-${weight}.woff2`;
      const data = await makeSubset(fonts[weight], pool.join(''));
      writeFileSync(join(FONT_DIR, file), data);
      files.push({ file, family, weight, scope, chars: pool.length, bytes: data.length, sha256: sha256(data) });
      if (own) continue;
      sources.push({
        family,
        name: `${s.name} ${WEIGHT_NAME[weight]}`,
        url: s.files[weight].url,
        sha256: s.files[weight].sha256,
        license: 'SIL OFL 1.1',
        license_file: s.licenseFile,
        reserved_font_name: 'Source',
        weights: String(weight),
      });
    }
    if (derived) {
      const cfg = derivedConfig();
      writeFileSync(join(FONT_DIR, DERIVED.licenseFile), readFileSync(join(REPO, DERIVED.dir, 'OFL.txt')));
      sources.push({
        family,
        name: `${DERIVED.name} ${cfg.version}（${s.name} Regular 的派生字体，补绘 ${cfg.glyphs.length} 字：${cfg.glyphs.map((g) => g.char).join('')}）`,
        url: DERIVED.url,
        upstream_sha256: s.files[DERIVED.weight].sha256,
        license: 'SIL OFL 1.1',
        license_file: DERIVED.licenseFile,
        reserved_font_name: '',
        weights: String(DERIVED.weight),
        derived_from: `${s.name} ${WEIGHT_NAME[DERIVED.weight]}`,
      });
    }
  }

  // 补充字体：登记的原文件在就用（核对哈希），转成 WOFF2；它的字不必再由黑体、宋体提供
  const ext = await makeExt();
  const extCmap = ext?.cmap ?? new Set<number>();
  if (ext) {
    writeFileSync(join(FONT_DIR, EXT.file), ext.woff2);
    writeFileSync(join(FONT_DIR, EXT.licenseFile), ext.licence);
    files.push({ file: EXT.file, family: 'ext', weight: 400, scope: '造字与生僻字（用到才下载）', chars: extCmap.size, bytes: ext.woff2.length, sha256: sha256(ext.woff2) });
    sources.push({ family: 'ext', name: EXT.name, url: EXT.url, sha256: EXT.sha256, license: 'SIL OFL 1.1', license_file: EXT.licenseFile, reserved_font_name: '' });
  }
  const extHas = (c: string) => extCmap.has(c.codePointAt(0)!);
  // 宋体有的字；黑体缺的字回退到宋体（--sans 里列了 DG Serif），所以只看宋体。或者补充字体有这个字
  const covered = new Set([...wanted].filter((c) => serifHas.has(c) || extHas(c)));
  const chars = [...covered].sort(byCodePoint).join('');
  const unavailable = [...wanted].filter((c) => !covered.has(c)).sort(byCodePoint).join('');
  const manifest = {
    about:
      '站点自带的固定字体子集，由 scripts/make-fonts.ts（npm run fonts）生成；只含站点用到的字，其余字回退到系统字体。' +
      '各文件装哪些字见 files[].scope：释文只用宋体 400，所以其余文件只装界面、标题、识语等处的字。' +
      '补充字体（ext）整个收录，页面用 unicode-range 声明它，用到才下载。',
    tool: toolVersion(),
    chars,
    unavailable,
    files,
    licenses: [...Object.values(SOURCES).map((s) => s.licenseFile), DERIVED.licenseFile, ...(ext ? [EXT.licenseFile] : [])],
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
