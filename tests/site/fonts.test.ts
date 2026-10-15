import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import manifest from '../../public/fonts/fonts.json';
import { facesCss, FILES, preloadHrefs, type FontFile } from '../../src/lib/fonts';
import { fontNotes, uncovered, visibleText } from '../../src/lib/verify';

/** 用假的字体清单测机制 */
const FAKE: FontFile[] = [
  { file: 's-400.woff2', family: 'sans', weight: 400 },
  { file: 's-500.woff2', family: 'sans', weight: 500 },
  { file: 'f-400.woff2', family: 'serif', weight: 400 },
];

describe('字体引用', () => {
  it('每个字体文件一条 @font-face，地址指向站点的 fonts/', () => {
    const css = facesCss(FAKE);
    expect(css).toContain('font-family:"DG Sans";font-weight:400;font-style:normal;font-display:swap;src:url(/fonts/s-400.woff2) format("woff2")');
    expect(css).toContain('font-family:"DG Serif";font-weight:400');
    expect(css.match(/@font-face/g)).toHaveLength(3);
  });

  it('补充字体声明 unicode-range（私用区与生僻字），用到才下载；黑体宋体不限范围', () => {
    const ext: FontFile = { file: 'x-400.woff2', family: 'ext', weight: 400 };
    const css = facesCss([...FAKE, ext]);
    expect(css).toContain(
      'font-family:"DG Ext";font-weight:400;font-style:normal;font-display:swap;src:url(/fonts/x-400.woff2) format("woff2");unicode-range:U+E000-F8FF,U+20000-2FFFF',
    );
    expect(css.match(/unicode-range/g)).toHaveLength(1);
    expect(preloadHrefs([...FAKE, ext])).toEqual(['/fonts/s-400.woff2', '/fonts/f-400.woff2']); // 不提前加载
  });

  it('只提前加载每页都用的两个', () => {
    expect(preloadHrefs(FAKE)).toEqual(['/fonts/s-400.woff2', '/fonts/f-400.woff2']);
  });

  it('没有字体清单就是系统字体', () => {
    expect([facesCss([]), preloadHrefs([])]).toEqual(['', []]);
  });
});

describe('用字统计', () => {
  it('统计页面上画出来的字', () => {
    const page =
      '<style>/* 注释甲 */a:before{content:"、"}</style><p>乙<b>丙</b></p><input placeholder="搜索">' +
      '<img alt="替代" src="x.jpg" title="不画"><script>/* 注释丁 */ x("命中&lt;")</script>';
    const text = visibleText(page);
    for (const ch of '乙丙搜索替代命中、') expect(text).toContain(ch);
    for (const ch of '注释甲丁不画<>') expect(text.replace('命中<', '')).not.toContain(ch); // 注释、标签、不会画出的属性不计
  });

  it('可以去掉释文正文与来源注释，分档统计', () => {
    const page = '<h1>标题</h1><p>释文</p><div class="note">注</div><p class="x">界面</p>';
    expect(visibleText(page, false, false)).toBe('标题界面');
    expect(visibleText(page, false, true)).toBe('标题注界面');
    expect(visibleText(page)).toBe('标题释文注界面');
  });

  it('新字与字体里没有的字分开提示', () => {
    expect(uncovered(new Set(['甲', '乙', '丙', '丁', '戊']), { chars: '甲乙', unavailable: '丙' })).toEqual(['丁戊', '丙']);
  });

  it('没有固定字体时提示去运行脚本', () => {
    expect(fontNotes('/nonexistent', null)[0]).toContain('npm run fonts');
  });
});

describe('随站点发布的固定字体', () => {
  const dir = new URL('../../public/fonts/', import.meta.url);

  it('文件与清单里登记的哈希、大小一致', () => {
    expect(manifest.files.length).toBeGreaterThan(0);
    for (const f of manifest.files) {
      const data = readFileSync(new URL(f.file, dir));
      expect(createHash('sha256').update(data).digest('hex'), f.file).toBe(f.sha256);
      expect(data.length, f.file).toBe(f.bytes);
    }
  });

  it('页面引用的就是清单里的文件', () => {
    expect(FILES.map((f) => f.file)).toEqual(manifest.files.map((f) => f.file));
  });

  it('附有授权文本', () => {
    for (const name of manifest.licenses) {
      expect(readFileSync(new URL(name, dir), 'utf-8').toUpperCase()).toContain('SIL OPEN FONT LICENSE');
    }
  });

  it('子集收的字与“字体里没有的字”不重叠', () => {
    const have = new Set(manifest.chars);
    expect([...manifest.unavailable].filter((c) => have.has(c))).toEqual([]);
  });
});
