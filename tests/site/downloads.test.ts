import { readFileSync } from 'node:fs';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { Corpus } from '../../src/lib/corpus';
import { groupJsonl, groupTxt, textResponse, witnessJsonl, witnessTxt } from '../../src/lib/downloads';
import { llmsTxt } from '../../src/lib/llms';
import { fixtureCorpus, tempDir } from './fixtures';

const tmp = tempDir();
afterAll(() => tmp.cleanup());

let c: Corpus;
beforeAll(() => {
  c = fixtureCorpus(tmp.dir, 'a', { title: '占位书' });
});

describe('纯文本释文', () => {
  it('列出该本的识语、释文和只属于它的来源', () => {
    const txt = witnessTxt(c, c.witnesses[0]);
    expect(txt.startsWith('# 甲书《占位》甲组\n\n> 2000年出土于某地。\n')).toBe(true);
    expect(txt).toContain('[简1] 甲乙丙');
    expect(txt).toContain('- 占位来源（授权：CC0） https://example.test/s');
    expect(txt).toContain('- 另一来源（授权：来源未标明，按可收录处理）');
    expect(txt.endsWith('\n')).toBe(true);
  });

  it('没有登记来源的本不列来源', () => {
    expect(witnessTxt(c, c.witnesses[1])).not.toContain('占位来源');
  });

  it('合集里各本标题降一级', () => {
    const txt = groupTxt(c, c.groups[0]);
    expect(txt.startsWith('# 甲书\n')).toBe(true);
    expect(txt).toContain('## 甲书《占位》甲组');
    expect(txt).toContain('## 甲书《占位》乙组');
    expect(txt.indexOf('甲组')).toBeLessThan(txt.indexOf('乙组'));
  });
});

describe('jsonl 数据', () => {
  it('与仓库里的文件逐字相同（补上结尾换行）', () => {
    const src = readFileSync(`${tmp.dir}/a/witnesses/w-a.jsonl`, 'utf-8');
    expect(witnessJsonl(c.witnesses[0])).toBe(src + '\n');
  });

  it('合集是各本依次相接', () => {
    expect(groupJsonl(c.groups[0])).toBe(witnessJsonl(c.witnesses[0]) + witnessJsonl(c.witnesses[1]));
  });

  it('没有源文件时按解析结果重写', () => {
    const w = { ...c.witnesses[2], file: null } as typeof c.witnesses[2];
    const lines = witnessJsonl(w).trimEnd().split('\n');
    expect(lines).toHaveLength(2);
    expect(JSON.parse(lines[0]).id).toBe('w-c.001');
  });
});

describe('文本响应', () => {
  it('UTF-8，不带 BOM', async () => {
    const r = textResponse('甲');
    expect(r.headers.get('Content-Type')).toBe('text/plain; charset=utf-8');
    expect(new Uint8Array(await r.arrayBuffer())).toEqual(new Uint8Array([0xe7, 0x94, 0xb2]));
  });
});

describe('llms.txt', () => {
  it('单部典籍：以书名为题，链接带站点根地址', () => {
    const { short, full } = llmsTxt([c], 'https://example.test/x');
    expect(short.startsWith('# 占位书\n\n> ')).toBe(true);
    expect(short).toContain('## 版本');
    expect(short).toContain('(https://example.test/x/a/w-a.txt)');
    expect(short).toContain('(https://example.test/x/a/): 封面');
    expect(short).toContain('(https://example.test/x/a/data/): 所有版本一页');
    expect(short).toContain('## Optional');
    expect(short).toContain('(https://example.test/x/llms-full.txt)');
    expect(full).toContain('[简1] 甲乙丙');
    expect(full).toContain('### 来源'); // 完整合集里各本降到二级标题
  });

  it('没有站点地址时写相对链接', () => {
    expect(llmsTxt([c]).short).toContain('(a/w-a.txt)');
  });

  it('多部典籍：总标题为“典籍”，各部分节', () => {
    const b = fixtureCorpus(tmp.dir, 'b', { title: '另一书' });
    const { short } = llmsTxt([c, b]);
    expect(short.startsWith('# 典籍\n\n> ')).toBe(true);
    expect(short).toContain('## 占位书');
    expect(short).toContain('## 另一书');
  });
});
