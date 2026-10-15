/**
 * 构建后检查，对着输出目录做，不依赖页面是怎么生成的：
 * - 站内链接（href、src、样式里的 url()、data-go）必须指向存在的文件，带锚点的链接目标页里必须有这个 id；
 *   站点部署在子路径（base）下时，绝对路径必须带上 base，否则线上会 404。
 * - 页面实际用到的字与固定字体的对照：提示要不要重新生成子集，以及只能靠系统字体显示的字。
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';

/** fonts.json 里这里用到的部分 */
export interface FontManifest {
  /** 子集里收的字 */
  chars: string;
  /** 字体本身没有、只能用系统字体显示的字 */
  unavailable: string;
}

function walk(dir: string, exts: string[]): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir).sort()) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) out.push(...walk(path, exts));
    else if (exts.some((e) => name.endsWith(e))) out.push(path);
  }
  return out;
}

const read = (path: string) => readFileSync(path, 'utf-8');

/** 地址里的百分号转义还原成字；转义本身不合法时原样返回，让后面按“文件不存在”报出来。 */
function decode(s: string): string {
  try {
    return decodeURI(s);
  } catch {
    return s;
  }
}

/** 反转义页面属性里的 HTML 实体（数据版面包屑的初始内容放在 data-base 里）。 */
export function unescapeHtml(s: string): string {
  const named: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
  return s.replace(/&(?:#x([0-9a-f]+)|#(\d+)|([a-z]+));/gi, (m, hex, dec, name) => {
    if (hex) return String.fromCodePoint(parseInt(hex, 16));
    if (dec) return String.fromCodePoint(parseInt(dec, 10));
    return named[name.toLowerCase()] ?? m;
  });
}

const REF = /(?:\bhref|\bsrc|\bdata-go)="([^"]+)"|url\(([^)"']+)\)/g;
const BASE_ATTR = /\bdata-base="([^"]*)"/g;
const ID = /\bid="([^"]+)"/g;

/** 页面里的全部站内引用：属性、样式里的 url()，以及 data-base 里 HTML 片段的链接。 */
function references(text: string): string[] {
  const refs = [...text.matchAll(REF)].map((m) => m[1] ?? m[2]);
  for (const m of text.matchAll(BASE_ATTR)) {
    for (const r of unescapeHtml(m[1]).matchAll(REF)) refs.push(r[1] ?? r[2]);
  }
  return refs;
}

/** 检查输出目录里的站内链接。base 是站点的子路径（如 /daodejing-archive），根部署时为空。返回问题列表，空表示通过。 */
export function checkLinks(outDir: string, base = ''): string[] {
  const prefix = base.replace(/\/+$/, '');
  const problems: string[] = [];
  const idCache = new Map<string, Set<string>>();
  const idsOf = (file: string): Set<string> => {
    let ids = idCache.get(file);
    if (!ids) idCache.set(file, (ids = new Set([...read(file).matchAll(ID)].map((m) => m[1]))));
    return ids;
  };

  for (const file of walk(outDir, ['.html', '.css'])) {
    const rel = relative(outDir, file).split(sep).join('/');
    for (const ref of references(read(file))) {
      if (/^[a-z][a-z0-9+.-]*:/i.test(ref) || ref.startsWith('//')) continue;
      const [pathAndQuery, ...frag] = ref.split('#');
      const path = decode(pathAndQuery.split('?')[0]);
      const fragment = decode(frag.join('#'));

      let target: string;
      if (!path) {
        target = file;
      } else if (path.startsWith('/')) {
        if (prefix && path !== prefix && !path.startsWith(`${prefix}/`)) {
          problems.push(`${rel}: ${ref} 没有带站点前缀 ${prefix}`);
          continue;
        }
        target = join(outDir, path.slice(prefix.length));
      } else {
        target = join(dirname(file), path);
      }
      // 以 / 结尾的地址指向目录下的 index.html（Pages 就是这样提供的）
      if (path.endsWith('/') || (existsSync(target) && statSync(target).isDirectory())) {
        if (!path.endsWith('/')) {
          problems.push(`${rel}: ${ref} 指向目录，地址应以 / 结尾`);
          continue;
        }
        target = join(target, 'index.html');
      }
      if (!existsSync(target)) {
        problems.push(`${rel}: ${ref} 指向的文件不存在`);
        continue;
      }
      if (fragment && target.endsWith('.html')) {
        const ids = idsOf(target);
        // 数据版里 #<版本id> 由脚本映射到 w-<版本id>
        if (!ids.has(fragment) && !ids.has(`w-${fragment}`)) {
          problems.push(`${rel}: ${ref} 的锚点 #${fragment} 在目标页面里不存在`);
        }
      }
    }
  }
  return problems;
}

const BLOCKS = /<(style|script)\b[^>]*>([\s\S]*?)<\/\1>/g;
const COMMENT = /\/\*[\s\S]*?\*\//g;
const TAGS = /<[^>]+>/g;
/** 释文正文（不带 class 的 <p>）：只用宋体 400 */
const UNIT_P = /<p>[\s\S]*?<\/p>/g;
/** 来源附带的注释：黑体 400 */
const NOTES = /<div class="note">[\s\S]*?<\/div>/g;
/** 属性值里会画出来的文字：输入框提示、图片加载失败时的替代文字 */
const SHOWN_ATTRS = /\b(?:placeholder|alt)="([^"]*)"/g;

/**
 * 页面上会画出来的文字：标签之间的正文，输入框提示和图片替代文字，以及样式、脚本里（去掉注释）的字符串，
 * 脚本会往页面里写字（如“本页命中”），样式会给序号加“、”。units、notes 为 false 时分别不含释文正文、来源注释。
 */
export function visibleText(page: string, units = true, notes = true): string {
  if (!units) page = page.replace(UNIT_P, '');
  if (!notes) page = page.replace(NOTES, '');
  const shown = [...page.matchAll(BLOCKS)].map((m) => m[2].replace(COMMENT, ''));
  shown.push(...[...page.matchAll(SHOWN_ATTRS)].map((m) => m[1]));
  return unescapeHtml(page.replace(BLOCKS, '').replace(TAGS, '') + shown.join(''));
}

/** 站点用到的字：全部页面的可见文字，加上外部样式与脚本里的字符串。 */
export function siteChars(outDir: string, units = true, notes = true): Set<string> {
  const chars = new Set<string>();
  const add = (text: string) => {
    for (const c of text) if (/\S/u.test(c) && !/\p{C}/u.test(c)) chars.add(c);
  };
  for (const file of walk(outDir, ['.html'])) add(visibleText(read(file), units, notes));
  for (const file of walk(outDir, ['.css', '.js'])) add(read(file).replace(COMMENT, ''));
  return chars;
}

/** [需要重新生成子集的字, 字体本身没有、只能用系统字体显示的字] */
export function uncovered(chars: Set<string>, manifest: FontManifest): [string, string] {
  const known = new Set([...manifest.chars, ...manifest.unavailable]);
  const fresh = [...chars].filter((c) => !known.has(c)).sort().join('');
  return [fresh, manifest.unavailable];
}

/** 站点用字与固定字体的对照，返回要提示的几句话。 */
export function fontNotes(outDir: string, manifest: FontManifest | null): string[] {
  if (!manifest) return ['没有固定字体（public/fonts/），页面用系统字体；先运行 npm run fonts'];
  const [fresh, system] = uncovered(siteChars(outDir), manifest);
  const notes: string[] = [];
  if (fresh) notes.push(`${[...fresh].length} 个字不在固定字体里，暂用系统字体显示：${fresh}；重新运行 npm run fonts 可收进子集`);
  if (system) notes.push(`${[...system].length} 个字固定字体本身没有，由系统字体显示：${system}`);
  return notes;
}
