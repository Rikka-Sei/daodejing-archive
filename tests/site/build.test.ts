/**
 * 整站构建：用真实数据跑两遍 astro build——一遍照 GitHub Pages 项目站点的方式带上 --site 与 --base，
 * 一遍什么都不带（本地预览）——检查输出的文件、链接、下载内容与 llms.txt。每遍约 15 秒。
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { usedChars } from '../../scripts/make-fonts';
import { allCorpora } from '../../src/lib/site';
import { thumbJobs } from '../../src/lib/thumbs';
import { checkLinks } from '../../src/lib/verify';
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
    const al = c.alignment!;
    const files = ['index.html', 'llms.txt', 'llms-full.txt', 'laozi/index.html', 'laozi/preface/index.html', 'laozi/alignment.json'];
    for (const w of c.witnesses) files.push(`laozi/${w.id}/index.html`, `laozi/${w.id}.txt`, `laozi/${w.id}.jsonl`);
    for (const w of c.readable) files.push(`laozi/${w.id}/read/index.html`);
    for (const g of c.groups.filter((x) => !x.single)) files.push(`laozi/${g.id}-all.txt`, `laozi/${g.id}-all.jsonl`);
    for (const ch of al.chapters) files.push(`laozi/chapters/${ch.n}/index.html`, `laozi/chapters/${String(ch.n).padStart(3, '0')}.json`);
    for (const s of c.studies) files.push(`laozi/study/${s.id}/index.html`);
    for (const f of files) expect(existsSync(join(out, f)), f).toBe(true);
    // 只有一个本的文献没有合集；以章为单位的本没有阅读器；不再有数据版
    expect(existsSync(join(out, 'laozi/beida-all.txt'))).toBe(false);
    expect(existsSync(join(out, 'laozi/wangbi/read'))).toBe(false);
    expect(existsSync(join(out, 'laozi/data'))).toBe(false);
    expect(c.readable.length).toBeGreaterThan(0);
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
    expect(home).toContain(`href="${base}/laozi/chapters/1/"`);
    expect(home).toContain(`href="${base}/laozi/study/tt24h-daodejing/"`);
  });

  it('侧栏目录：郭店楚简、马王堆帛书各自成文件夹，北大只有一个本直接一项；分类与“材料｜章节”两条轴都在', () => {
    const page = read('laozi/guodian-jia/index.html');
    expect(page).toContain('<details class="dir" data-g="guodian" open>');
    expect(page).toContain('data-g="mawangdui"');
    expect(page).not.toContain('data-g="beida"');
    expect(page).toContain(`href="${base}/laozi/guodian-all.txt" download="郭店楚简-全部.txt"`);
    for (const label of ['出土文献', '传世本与校订本', '论文与对照资料']) expect(page).toContain(label);
    expect(page).toContain('data-axis="c" aria-pressed="false">章节</button>');
    expect(page.match(/class="item ch"/g)).toHaveLength(81);
    expect(page).toContain(`href="${base}/laozi/chapters/81/"`);
  });

  it('章节页与阅读器：脚本、章节链接与数据地址都带 base', () => {
    const ch = read('laozi/chapters/12/index.html');
    expect(ch).toContain('<table class="al"');
    expect(ch).toContain(`href="${base}/laozi/chapters/11/"`);
    expect(ch).toContain(`href="${base}/laozi/chapters/13/"`);
    expect(ch).toMatch(new RegExp(`src="${base}/_astro/align\\.[\\w-]+\\.js"`));
    expect(ch).not.toMatch(/reader\.[\w-]+\.js/);
    const rd = read('laozi/guodian-jia/read/index.html');
    expect(rd).toContain(`data-chapters="${base}/laozi/chapters/" data-meta="${base}/laozi/alignment.json"`);
    expect(rd).toMatch(new RegExp(`src="${base}/_astro/reader\\.[\\w-]+\\.js"`));
    expect(rd).toContain(`href="${base}/laozi/chapters/`); // 每一章开头的章次标记
    expect(read('laozi/guodian-jia/index.html')).toContain(`href="${base}/laozi/guodian-jia/read/"`); // 本页的阅读器入口
  });

  it('对读表数据：每章的 JSON 与仓库里的文件逐字相同，公共部分带简称、等同表与造字码位', () => {
    for (const n of ['001', '037', '081']) {
      expect(read(`laozi/chapters/${n}.json`), n).toBe(readFileSync(join(ROOT, 'data/alignment/chapters', `${n}.json`), 'utf-8'));
    }
    const al = c.alignment!;
    const meta = JSON.parse(read('laozi/alignment.json'));
    expect(meta.versions.map((v: { id: string }) => v.id)).toEqual(al.versions.map((v) => v.id));
    expect(Object.keys(meta.equivalents)).toEqual(['fail', 'blank', 'same']);
    expect(Object.keys(meta.glyphs)).toHaveLength(al.glyphs.size);
  });

  it('样式与脚本是带哈希文件名的外部文件，字体引用带 base', () => {
    const page = read('laozi/index.html');
    expect(page).toMatch(new RegExp(`href="${base}/_astro/Shell\\.[\\w-]+\\.css"`));
    expect(page).toMatch(new RegExp(`src="${base}/_astro/app\\.[\\w-]+\\.js"`));
    expect(page).toContain(`url(${base}/fonts/noto-serif-sc-400.woff2)`);
    // 补充字体只管私用区与生僻字，用到才下载
    expect(page).toContain(`url(${base}/fonts/dg-ext-400.woff2) format("woff2");unicode-range:U+E000-F8FF,U+20000-2FFFF`);
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

  it('释文用字单独分档：黑体与 500 字重的子集因此小得多', () => {
    const pools = usedChars(out);
    expect(pools.text.size).toBeLessThan(pools.all.size);
    expect(pools.ui.size).toBeLessThanOrEqual(pools.text.size);
  });

  it('llms.txt：配了 site 就是绝对链接，否则相对链接', () => {
    const text = read('llms.txt');
    expect(text.startsWith('# 道德经\n')).toBe(true);
    if (flags.length) {
      expect(text).toContain(`(${SITE}${base}/laozi/guodian-jia.txt)`);
      expect(text).toContain(`(${SITE}${base}/laozi/): 封面`);
      expect(text).toContain(`(${SITE}${base}/laozi/chapters/1/): 81 章`);
      expect(text).toContain(`(${SITE}${base}/llms-full.txt)`);
    } else {
      expect(text).toContain('(laozi/guodian-jia.txt)');
      expect(text).toContain('(laozi/chapters/1/): 81 章');
    }
    expect(read('llms-full.txt')).toContain('## 郭店楚简《老子》甲组');
  });
});
