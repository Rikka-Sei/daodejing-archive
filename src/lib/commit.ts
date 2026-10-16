/** 站点是从哪个提交构建的：Actions 里读 GITHUB_SHA，本地读 .git 下的 HEAD（不调用 git 命令）。读不到时为空串。 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { REPO_URL } from './url';

const HEX = /^[0-9a-f]{40}$/;

export function readCommit(root = process.cwd(), env: Record<string, string | undefined> = process.env): string {
  const sha = env.GITHUB_SHA?.trim() ?? '';
  if (HEX.test(sha)) return sha;
  try {
    const git = join(root, '.git');
    const head = readFileSync(join(git, 'HEAD'), 'utf8').trim();
    if (HEX.test(head)) return head; // 游离 HEAD
    const ref = head.match(/^ref: (.+)$/)?.[1];
    if (!ref) return '';
    const loose = join(git, ref);
    if (existsSync(loose)) {
      const v = readFileSync(loose, 'utf8').trim();
      return HEX.test(v) ? v : '';
    }
    for (const line of readFileSync(join(git, 'packed-refs'), 'utf8').split('\n')) {
      const [v, name] = line.trim().split(' ');
      if (name === ref && HEX.test(v)) return v;
    }
  } catch {
    // 没有 .git（如从压缩包构建）
  }
  return '';
}

export const COMMIT = readCommit();
export const commitUrl = (sha: string) => `${REPO_URL}/commit/${sha}`;
