/**
 * 整站构建：用真实数据跑两遍 astro build——一遍照 GitHub Pages 项目站点的方式带上 --site 与 --base，
 * 一遍什么都不带（本地预览）——检查输出的文件、链接、下载内容与 llms.txt。每遍约 15 秒。
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { allCorpora } from '../../src/lib/site';
import { thumbJobs } from '../../src/lib/thumbs';
import { checkLinks, siteChars } from '../../src/lib/verify';
import { tempDir } from './fixtures';

const ROOT = process.cwd();
const tmp = tempDir();
afterAll(() => tmp.cleanup());

/** vitest 会往环境里写 SITE=undefined、NODE_ENV=test 之类的变量，子进程里的构建不该继承，要和 CI 里一致。 */
function cleanEnv(): NodeJS.ProcessEnv {
  const drop = /^(SITE|ASSETS_PREFIX|BASE_URL|MODE|DEV|PROD|SSR|TEST|NODE_ENV|VITEST.*)$/;
  return Object.fromEntries(Object.entries(process.env).filter(([k]) => !drop.test(k)));
}

function build(name: string, flags: string[]): string {
  const out = join(tmp.dir, name);
  execFileSync('npx', ['--no-install', 'astro', 'build', '--outDir', out, ...flags], {
    cwd: ROOT,
    env: cleanEnv(),
    stdio: 'pipe',
    timeout: 170_000,
  });
  return out;
}

/** scripts/make_fonts.py 统计出的页面用字，三档：全部、去掉释文正文、再去掉来源注释。没有 python3 时返回 null。 */
function pythonChars(site: string): Record<'all' | 'text' | 'ui', string[]> | null {
  const code = [
    'import importlib.util, json, sys',
    'from pathlib import Path',
    'spec = importlib.util.spec_from_file_location("make_fonts", sys.argv[1])',
    'm = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)',
    'site = Path(sys.argv[2])',
    'tiers = {"all": m.site_chars(site), "text": m.site_chars(site, units=False), "ui": m.site_chars(site, units=False, notes=False)}',
    'print(json.dumps({k: sorted(v) for k, v in tiers.items()}, ensure_ascii=False))',
  ].join('\n');
  try {
    return JSON.parse(execFileSync('python3', ['-I', '-c', code, join(ROOT, 'scripts/make_fonts.py'), site], { encoding: 'utf-8' }));
  } catch {
    return null;
  }
}

const SITE = 'https://example.test';
const cases = [
  { name: '带 site 与 base（GitHub Pages 项目站点）', dir: 'pages', base: '/x', flags: ['--site', SITE, '--base', '/x'] },
  { name: '不带 site 与 base（本地）', dir: 'local', base: '', flags: [] as string[] },
];

describe.each(cases)('$name', ({ dir, base, flags }) => {
  let out: string;
  const read = (rel: string) => readFileSync(join(out, rel), 'utf-8');
  const c = allCorpora()[0];

  beforeAll(() => {
    out = build(dir, flags);
  }, 180_000);

  it('页面、下载文件与固定字体都在', () => {
    const files = ['index.html', 'llms.txt', 'llms-full.txt', 'laozi/index.html', 'laozi/data/index.html'];
    for (const w of c.witnesses) files.push(`laozi/${w.id}/index.html`, `laozi/${w.id}.txt`, `laozi/${w.id}.jsonl`);
    for (const g of c.groups.filter((x) => !x.single)) files.push(`laozi/${g.id}-all.txt`, `laozi/${g.id}-all.jsonl`);
    for (const f of files) expect(existsSync(join(out, f)), f).toBe(true);
    // 只有一个本的文献没有合集
    expect(existsSync(join(out, 'laozi/beida-all.txt'))).toBe(false);
    for (const f of JSON.parse(read('fonts/fonts.json')).files) expect(existsSync(join(out, 'fonts', f.file)), f.file).toBe(true);
  });

  it('缩略图一张不少，都是 JPEG，宽度不超过要求', async () => {
    const jobs = thumbJobs(c);
    expect(readdirSync(join(out, 'laozi/thumbs')).sort()).toEqual(jobs.map((j) => j.name).sort());
    for (const job of jobs.slice(0, 5)) {
      const meta = await sharp(join(out, 'laozi/thumbs', job.name)).metadata();
      expect(meta.format).toBe('jpeg');
      expect(meta.width).toBeLessThanOrEqual(job.width);
    }
  });

  it('站内链接都通，绝对路径都带 base', () => {
    expect(checkLinks(out, base)).toEqual([]);
  });

  it('首页是第一部典籍的封面，标题与页面地址带 base', () => {
    const home = read('index.html');
    expect(home).toContain('<h1>道德经</h1>');
    expect(home).toContain('<title>道德经</title>');
    expect(home).toContain(`href="${base}/laozi/guodian-jia/"`);
    expect(home).toContain(`data-go="${base}/laozi/data/"`);
  });

  it('侧栏目录：郭店楚简、马王堆帛书各自成文件夹，北大只有一个本直接一项', () => {
    const page = read('laozi/guodian-jia/index.html');
    expect(page).toContain('<details class="dir" data-g="guodian" open>');
    expect(page).toContain('data-g="mawangdui"');
    expect(page).not.toContain('data-g="beida"');
    expect(page).toContain(`href="${base}/laozi/guodian-all.txt" download="郭店楚简-全部.txt"`);
  });

  it('数据版里“阅读版”开关的地址模板带 base', () => {
    expect(read('laozi/data/index.html')).toContain(`data-tpl="${base}/laozi/{id}/"`);
  });

  it('样式与脚本是带哈希文件名的外部文件，字体引用带 base', () => {
    const page = read('laozi/index.html');
    expect(page).toMatch(new RegExp(`href="${base}/_astro/Shell\\.[\\w-]+\\.css"`));
    expect(page).toMatch(new RegExp(`src="${base}/_astro/app\\.[\\w-]+\\.js"`));
    expect(page).toContain(`url(${base}/fonts/noto-serif-sc-400.woff2)`);
  });

  it('下载的 jsonl 与仓库里的数据逐字相同，合集是各本依次相接', () => {
    const src = (id: string) => readFileSync(join(ROOT, 'data/witnesses', `${id}.jsonl`), 'utf-8');
    for (const w of c.witnesses) expect(read(`laozi/${w.id}.jsonl`), w.id).toBe(src(w.id));
    expect(read('laozi/guodian-all.jsonl')).toBe(['guodian-jia', 'guodian-yi', 'guodian-bing'].map(src).join(''));
  });

  it('纯文本释文', () => {
    const txt = read('laozi/guodian-jia.txt');
    expect(txt.startsWith('# 郭店楚简《老子》甲组\n')).toBe(true);
    expect(read('laozi/guodian-all.txt').startsWith('# 郭店楚简\n')).toBe(true);
  });

  it('构建时的字体提示与 make_fonts.py 对“页面用了哪些字”的看法一致', () => {
    const py = pythonChars(out);
    if (!py) return; // 没有 python3 就不比
    const byCodePoint = (a: string, b: string) => a.codePointAt(0)! - b.codePointAt(0)!;
    const ts = { all: siteChars(out), text: siteChars(out, false), ui: siteChars(out, false, false) };
    for (const tier of ['all', 'text', 'ui'] as const) expect([...ts[tier]].sort(byCodePoint), tier).toEqual(py[tier]);
    expect(py.text.length).toBeLessThan(py.all.length); // 释文用字确实被单独分出来了
  });

  it('llms.txt：配了 site 就是绝对链接，否则相对链接', () => {
    const text = read('llms.txt');
    expect(text.startsWith('# 道德经\n')).toBe(true);
    if (flags.length) {
      expect(text).toContain(`(${SITE}${base}/laozi/guodian-jia.txt)`);
      expect(text).toContain(`(${SITE}${base}/laozi/): 封面`);
      expect(text).toContain(`(${SITE}${base}/llms-full.txt)`);
    } else {
      expect(text).toContain('(laozi/guodian-jia.txt)');
      expect(text).toContain('(laozi/data/): 所有版本一页');
    }
    expect(read('llms-full.txt')).toContain('## 郭店楚简《老子》甲组');
  });
});
