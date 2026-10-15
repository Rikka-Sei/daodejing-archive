/**
 * 固定字体：站点随附子集字体，页面只用 @font-face 引用这几个文件，不依赖观看者机器上装了什么字体；
 * 子集里没有的字，浏览器逐字回退到系统字体。
 *
 * 字体文件在 public/fonts/，由 scripts/make-fonts.ts 生成（思源黑体、思源宋体，SIL OFL 1.1，
 * 来源与哈希记在 fonts.json）。另有 tt24h 的补充字体 DaoDeJingExt（SIL OFL 1.1）：
 * 竹简、帛书里的造字和 Noto 里没有的生僻字用它，只在页面用到这些码位时才下载。
 */
import manifest from '../../public/fonts/fonts.json';
import { url } from './url';

export interface FontFile {
  family: 'sans' | 'serif' | 'ext';
  weight: number;
  file: string;
}

export const FILES: FontFile[] = (manifest as { files: FontFile[] }).files;
/** CSS 里的字体族名 */
export const FAMILY = { sans: 'DG Sans', serif: 'DG Serif', ext: 'DG Ext' } as const;
/** 补充字体负责的码位：私用区（造字）与 U+20000 以后的生僻字 */
const RANGE: Partial<Record<FontFile['family'], string>> = { ext: 'U+E000-F8FF,U+20000-3FFFF' };
/** 每页都用到的两个字重，提前加载 */
const PRELOAD: [FontFile['family'], number][] = [
  ['sans', 400],
  ['serif', 400],
];

/** @font-face 规则 */
export function facesCss(files: FontFile[] = FILES): string {
  return files.map(
    (f) =>
      `@font-face{font-family:"${FAMILY[f.family]}";font-weight:${f.weight};font-style:normal;font-display:swap;` +
      `src:url(${url(`fonts/${f.file}`)}) format("woff2")${RANGE[f.family] ? `;unicode-range:${RANGE[f.family]}` : ''}}`,
  ).join('');
}

/** 提前加载的字体文件地址 */
export function preloadHrefs(files: FontFile[] = FILES): string[] {
  return PRELOAD.flatMap(([family, weight]) => {
    const f = files.find((x) => x.family === family && x.weight === weight);
    return f ? [url(`fonts/${f.file}`)] : [];
  });
}
