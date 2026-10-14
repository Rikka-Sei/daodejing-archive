import { defineConfig } from 'astro/config';
import verify from './src/integrations/verify.ts';

// site 与 base 由 GitHub Actions 的 configure-pages 通过命令行传入（见 .github/workflows/astro.yml）。
export default defineConfig({
  // 页面用目录式地址（/laozi/guodian-yi/），下载文件与缩略图是带扩展名的文件
  build: { assetsInlineLimit: 0 },
  // 构建结束时检查站内链接，并提示固定字体没覆盖的字
  integrations: [verify()],
});
