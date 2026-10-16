import { mkdirSync, writeFileSync } from 'node:fs';
import { afterAll, describe, expect, it } from 'vitest';
import { commitUrl, readCommit } from '../../src/lib/commit';
import { tempDir } from './fixtures';

const tmp = tempDir();
afterAll(() => tmp.cleanup());
const A = 'a'.repeat(40);
const B = 'b'.repeat(40);

const repo = (name: string, files: Record<string, string>) => {
  const root = `${tmp.dir}/${name}`;
  for (const [p, v] of Object.entries(files)) {
    const f = `${root}/.git/${p}`;
    mkdirSync(f.replace(/\/[^/]+$/, ''), { recursive: true });
    writeFileSync(f, v);
  }
  return root;
};

describe('构建所用的提交号', () => {
  it('Actions 里用 GITHUB_SHA', () => {
    expect(readCommit(repo('env', { HEAD: `${B}\n` }), { GITHUB_SHA: A })).toBe(A);
  });

  it('本地读分支引用：散的引用文件或 packed-refs', () => {
    expect(readCommit(repo('loose', { HEAD: 'ref: refs/heads/main\n', 'refs/heads/main': `${A}\n` }), {})).toBe(A);
    expect(readCommit(repo('packed', { HEAD: 'ref: refs/heads/main\n', 'packed-refs': `# pack-refs\n${B} refs/heads/main\n` }), {})).toBe(B);
  });

  it('游离 HEAD 直接是提交号', () => {
    expect(readCommit(repo('detached', { HEAD: `${A}\n` }), {})).toBe(A);
  });

  it('没有 .git 或读不出时为空', () => {
    expect(readCommit(`${tmp.dir}/none`, {})).toBe('');
    expect(readCommit(repo('bad', { HEAD: 'ref: refs/heads/x\n' }), { GITHUB_SHA: 'nope' })).toBe('');
  });

  it('链到仓库的提交页', () => {
    expect(commitUrl(A)).toBe(`https://github.com/Rikka-Sei/daodejing-archive/commit/${A}`);
  });
});
