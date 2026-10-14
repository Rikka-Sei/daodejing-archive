/**
 * 构建结束时检查输出：站内链接有断的就让构建失败，免得把坏链接发布出去；
 * 页面用到了固定字体之外的字，只提示，不失败。
 */
import type { AstroIntegration } from 'astro';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkLinks, fontNotes, type FontManifest } from '../lib/verify';

/** 固定字体清单；没有生成过就返回 null。 */
function readManifest(publicDir: string): FontManifest | null {
  const path = join(publicDir, 'fonts', 'fonts.json');
  return existsSync(path) ? (JSON.parse(readFileSync(path, 'utf-8')) as FontManifest) : null;
}

export default function verify(): AstroIntegration {
  let base = '';
  let publicDir = '';
  return {
    name: 'dg-verify',
    hooks: {
      'astro:config:done': ({ config }) => {
        base = config.base;
        publicDir = fileURLToPath(config.publicDir);
      },
      'astro:build:done': ({ dir, logger }) => {
        const out = fileURLToPath(dir);
        for (const note of fontNotes(out, readManifest(publicDir))) logger.warn(`字体：${note}`);
        const problems = checkLinks(out, base);
        for (const p of problems) logger.error(`链接检查：${p}`);
        if (problems.length) throw new Error(`链接检查未通过，共 ${problems.length} 个问题`);
        logger.info('链接检查通过');
      },
    },
  };
}
