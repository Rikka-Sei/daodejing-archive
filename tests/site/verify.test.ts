import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import verify from '../../src/integrations/verify';
import { checkLinks, siteChars, unescapeHtml } from '../../src/lib/verify';
import { tempDir } from './fixtures';

let tmp: ReturnType<typeof tempDir>;
beforeEach(() => {
  tmp = tempDir();
});
afterEach(() => tmp.cleanup());

const put = (rel: string, text: string) => {
  const path = join(tmp.dir, rel);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, text);
};

/** 一个最小的站点：封面、一个本、下载文件、样式 */
function site(extraBody = '', base = '') {
  put('index.html', `<a href="${base}/a/">封面</a><a href="${base}/a/w-a/#u1">甲</a>`);
  put('a/index.html', `<h1 id="top">封面</h1><a href="${base}/a/w-a/">甲</a>`);
  put('a/w-a/index.html', `<link rel="stylesheet" href="${base}/_astro/x.css"><div id="u1"></div>${extraBody}`);
  put('a/w-a.txt', '甲');
  put('_astro/x.css', 'a{background:url(data:image/png;base64,AA)}');
}

describe('链接检查', () => {
  it('完好的站点没有问题，外部地址、data:、mailto: 不检查', () => {
    site('<a href="https://example.test/x">外</a><a href="mailto:x@y.z">信</a><img src="data:image/png;base64,AA"><a href="//cdn.test/x">外</a>');
    expect(checkLinks(tmp.dir)).toEqual([]);
  });

  it('文件不存在', () => {
    site('<a href="/a/w-b.txt">乙</a>');
    expect(checkLinks(tmp.dir)).toEqual(['a/w-a/index.html: /a/w-b.txt 指向的文件不存在']);
  });

  it('锚点在目标页面里不存在；页内锚点也检查', () => {
    site('<a href="/a/#nope">x</a><a href="#u1">本页</a><a href="#gone">本页</a>');
    expect(checkLinks(tmp.dir)).toEqual([
      'a/w-a/index.html: /a/#nope 的锚点 #nope 在目标页面里不存在',
      'a/w-a/index.html: #gone 的锚点 #gone 在目标页面里不存在',
    ]);
  });

  it('样式里的 url() 也检查，相对样式文件所在位置', () => {
    site();
    put('_astro/x.css', '@font-face{src:url(../fonts/none.woff2)}');
    expect(checkLinks(tmp.dir)).toEqual(['_astro/x.css: ../fonts/none.woff2 指向的文件不存在']);
    put('fonts/none.woff2', '');
    expect(checkLinks(tmp.dir)).toEqual([]);
  });

  it('页面内联样式里的 url() 同样检查', () => {
    site('<style>@font-face{src:url(/fonts/none.woff2)}</style>');
    expect(checkLinks(tmp.dir).join()).toContain('/fonts/none.woff2');
  });

  it('阅读器读对读表公共部分的 data-meta 也检查', () => {
    site('<div data-meta="/a/meta.json"></div>');
    expect(checkLinks(tmp.dir)).toEqual(['a/w-a/index.html: /a/meta.json 指向的文件不存在']);
    put('a/meta.json', '{}');
    expect(checkLinks(tmp.dir)).toEqual([]);
  });

  it('地址里的查询串忽略，百分号转义还原成文件名', () => {
    site('<a href="/a/w-a.txt?x=1">下载</a><a href="/a/%E7%94%B2.txt">甲</a>');
    put('a/甲.txt', '');
    expect(checkLinks(tmp.dir)).toEqual([]);
  });

  it('指向目录的地址必须以斜杠结尾', () => {
    site('<a href="/a/w-a">甲</a>');
    expect(checkLinks(tmp.dir)).toEqual(['a/w-a/index.html: /a/w-a 指向目录，地址应以 / 结尾']);
  });

  it('部署在子路径下：绝对路径必须带 base', () => {
    site('', '/repo');
    expect(checkLinks(tmp.dir, '/repo')).toEqual([]);
    expect(checkLinks(tmp.dir, '/repo/')).toEqual([]); // base 末尾的斜杠无所谓
    put('a/w-a/index.html', '<div id="u1"></div><a href="/a/">漏了前缀</a><a href="/repository/a/">前缀只是同样开头</a>');
    expect(checkLinks(tmp.dir, '/repo')).toEqual([
      'a/w-a/index.html: /a/ 没有带站点前缀 /repo',
      'a/w-a/index.html: /repository/a/ 没有带站点前缀 /repo',
    ]);
  });

  it('相对地址按所在文件解析', () => {
    site('<a href="../index.html">封面</a><a href="../../index.html">根</a><a href="../nothing.html">无</a>');
    expect(checkLinks(tmp.dir)).toEqual(['a/w-a/index.html: ../nothing.html 指向的文件不存在']);
  });
});

describe('HTML 实体', () => {
  it('还原常见的命名与数字实体', () => {
    expect(unescapeHtml('&lt;a&gt; &amp; &quot;x&quot; &#39;y&#39; &#x7532; &unknown;')).toBe('<a> & "x" \'y\' 甲 &unknown;');
  });
});

describe('站点用字', () => {
  it('页面正文加外部样式与脚本里的字符串，去掉注释与空白', () => {
    put('index.html', '<h1>标 题</h1><p>释文</p>');
    put('_astro/x.css', '/* 备忘 */a:before{content:"、"}');
    put('_astro/app.js', '/* 备忘 */var s="本页命中";');
    const chars = siteChars(tmp.dir);
    for (const c of '标题释文、本页命中') expect(chars.has(c), c).toBe(true);
    for (const c of ['备', '忘', ' ']) expect(chars.has(c), c).toBe(false);
  });

  it('分档：去掉释文正文', () => {
    put('index.html', '<h1>标题</h1><p>释文</p>');
    expect(siteChars(tmp.dir, false).has('释')).toBe(false);
    expect(siteChars(tmp.dir).has('释')).toBe(true);
  });
});

describe('构建集成', () => {
  const logger = () => ({ info: vi.fn(), warn: vi.fn(), error: vi.fn() });
  const run = (base: string, lg: ReturnType<typeof logger>) => {
    const hooks = verify().hooks as Record<string, (arg: unknown) => void>;
    hooks['astro:config:done']({ config: { base, publicDir: pathToFileURL(join(tmp.dir, 'public/')) } });
    hooks['astro:build:done']({ dir: pathToFileURL(`${tmp.dir}/`), logger: lg });
  };

  it('链接都通：记一条信息，不抛错；没有字体清单只提示', () => {
    site();
    const lg = logger();
    expect(() => run('/', lg)).not.toThrow();
    expect(lg.info).toHaveBeenCalledWith('链接检查通过');
    expect(lg.warn.mock.calls[0][0]).toContain('npm run fonts');
  });

  it('有断链：逐条报错并让构建失败', () => {
    site('<a href="/a/gone.txt">x</a>');
    const lg = logger();
    expect(() => run('/', lg)).toThrow('链接检查未通过，共 1 个问题');
    expect(lg.error).toHaveBeenCalledTimes(1);
    expect(lg.info).not.toHaveBeenCalled();
  });

  it('读取 public/fonts/fonts.json，把新字提示出来', () => {
    site();
    put('public/fonts/fonts.json', JSON.stringify({ chars: '甲', unavailable: '' }));
    put('index.html', '<a href="/a/">封面</a><p>乙</p>');
    const lg = logger();
    run('/', lg);
    expect(lg.warn.mock.calls.map((c) => c[0]).join()).toContain('不在固定字体里');
  });
});
